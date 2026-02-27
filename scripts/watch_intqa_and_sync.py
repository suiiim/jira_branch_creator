#!/usr/bin/env python3
"""
INTQA 처리중 이슈 감시 -> SSCVE 자동 동기화 워처

INTQA에서 현재 사용자에게 할당된 이슈가 '처리중'으로 바뀌면
자동으로 감지하여 SSCVE에 동일한 제목의 이슈를 생성하고
INTQA <-> SSCVE 간 '문의대응 처리 이슈' 링크를 연결합니다.

중복 방지:
  - INTQA 이슈에 '문의대응 처리 이슈' 링크(SSCVE 연결)가 이미 있으면 생성 건너뜀

로그:
  - 저장 위치: %USERPROFILE%\Desktop\jira-sync-logs\
  - 파일명: watch_intqa_YYYYMMDD.log (일별 자동 로테이션)
  - 포맷: [YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE
  - LOG_DIR 환경변수로 경로 변경 가능

Usage:
    python scripts/watch_intqa_and_sync.py [--interval 30]

    --interval N  폴링 간격 (초, 기본값: 30)

환경변수:
    JIRA_BASE_URL    - Jira 인스턴스 URL (필수)
    JIRA_EMAIL       - Jira 로그인 이메일 (필수)
    JIRA_API_TOKEN   - Jira API 토큰 (필수)
    LOG_DIR          - 로그 저장 디렉토리 (선택, 기본: Desktop/jira-sync-logs)

Python 3.9+ 필요
"""

from __future__ import annotations

import os
import sys
import json
import time
import base64
import logging
import urllib.request
import urllib.error
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL             = os.environ.get("JIRA_BASE_URL", "")
EMAIL                = os.environ.get("JIRA_EMAIL", "")
TOKEN                = os.environ.get("JIRA_API_TOKEN", "")

SOURCE_PROJECT       = "INTQA"
TARGET_PROJECT       = "SSCVE"
TARGET_ISSUE_TYPE_ID = "10124"  # 작업
LINK_TYPE_ID         = "10000"  # 문의대응 (outward: 문의대응 처리 이슈)

_DEFAULT_LOG_DIR = Path.home() / "Desktop" / "jira-sync-logs"
LOG_DIR          = Path(os.environ.get("LOG_DIR", str(_DEFAULT_LOG_DIR)))


# ─── 로거 설정 ────────────────────────────────────────────────────────────────

class _LevelFormatter(logging.Formatter):
    """레벨명을 5자로 패딩: INFO -> INFO , ERROR -> ERROR"""
    LEVEL_MAP = {
        "INFO":     "INFO ",
        "WARNING":  "WARN ",
        "ERROR":    "ERROR",
        "CRITICAL": "ERROR",
        "OK":       "OK   ",
        "SKIP":     "SKIP ",
    }

    def format(self, record: logging.LogRecord) -> str:
        level = self.LEVEL_MAP.get(record.levelname, record.levelname[:5].ljust(5))
        dt    = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{dt}] [{level}] {record.getMessage()}"


# 커스텀 레벨
OK_LEVEL   = 25
SKIP_LEVEL = 26
logging.addLevelName(OK_LEVEL,   "OK")
logging.addLevelName(SKIP_LEVEL, "SKIP")


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"watch_intqa_{datetime.now().strftime('%Y%m%d')}.log"

    formatter = _LevelFormatter()

    # 파일 핸들러 (일별 로테이션, UTF-8)
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1,
        backupCount=0, encoding="utf-8"
    )
    file_handler.suffix   = "%Y%m%d"
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("watch_intqa")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger: logging.Logger = None  # main()에서 초기화


def log_ok(msg: str)   -> None: logger.log(OK_LEVEL,   msg)
def log_skip(msg: str) -> None: logger.log(SKIP_LEVEL, msg)


# ─── 유틸리티 ────────────────────────────────────────────────────────────────

def check_env() -> None:
    missing = [v for v in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN") if not os.environ.get(v)]
    if missing:
        print(f"[ERROR] 환경변수 누락: {', '.join(missing)}")
        sys.exit(1)


def _auth_header() -> str:
    return "Basic " + base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()


def jira_get(path: str) -> dict | None:
    req = urllib.request.Request(
        f"{JIRA_URL}{path}",
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:200]}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return None


def jira_post(path: str, payload: dict) -> tuple[int, dict | None]:
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{JIRA_URL}{path}",
        data=body,
        headers={
            "Authorization": _auth_header(),
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:200]}")
        return e.code, None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return 0, None


# ─── Jira 조회/생성 ──────────────────────────────────────────────────────────

def fetch_intqa_in_progress() -> dict[str, dict]:
    """INTQA 처리중 이슈 조회 -> {issueKey: issue}"""
    _, data = jira_post("/rest/api/3/search/jql", {
        "jql": (
            f"project={SOURCE_PROJECT} "
            "AND assignee=currentUser() "
            "AND statusCategory=indeterminate "
            "ORDER BY updated DESC"
        ),
        "fields": ["summary", "status"],
        "maxResults": 100,
    })
    if not data:
        return {}
    return {i["key"]: i for i in data.get("issues", [])}


def fetch_linked_sscve_key(intqa_key: str) -> str | None:
    """INTQA 이슈에 '문의대응 처리 이슈' 링크로 연결된 SSCVE 키 반환. 없으면 None."""
    data = jira_get(f"/rest/api/3/issue/{intqa_key}?fields=issuelinks")
    if not data:
        return None
    for link in data["fields"].get("issuelinks", []):
        if link.get("type", {}).get("id") != LINK_TYPE_ID:
            continue
        outward = link.get("outwardIssue", {})
        if outward.get("key", "").startswith(f"{TARGET_PROJECT}-"):
            return outward["key"]
    return None


def create_sscve_issue(summary: str) -> str | None:
    """SSCVE에 작업 이슈 생성 -> 새 이슈 키 반환. 실패 시 None."""
    _, data = jira_post("/rest/api/3/issue", {
        "fields": {
            "project":   {"key": TARGET_PROJECT},
            "summary":   summary,
            "issuetype": {"id": TARGET_ISSUE_TYPE_ID},
        }
    })
    if data and "key" in data:
        return data["key"]
    return None


def create_issue_link(intqa_key: str, sscve_key: str) -> bool:
    """INTQA -> SSCVE '문의대응 처리 이슈' 링크 생성"""
    status, _ = jira_post("/rest/api/3/issueLink", {
        "type":         {"id": LINK_TYPE_ID},
        "inwardIssue":  {"key": intqa_key},
        "outwardIssue": {"key": sscve_key},
    })
    return status == 201


# ─── 동기화 실행 ─────────────────────────────────────────────────────────────

def sync_issues(keys: set[str], in_progress: dict[str, dict]) -> set[str]:
    """주어진 INTQA 키들을 SSCVE에 동기화. 성공한 키 집합 반환."""
    synced = set()
    for key in keys:
        summary = in_progress[key]["fields"]["summary"]

        linked_key = fetch_linked_sscve_key(key)
        if linked_key:
            log_skip(f"[{key}] 이미 연결된 SSCVE 이슈 존재: {linked_key}")
            synced.add(key)
            continue

        new_key = create_sscve_issue(summary)
        if not new_key:
            logger.error(f"[{key}] SSCVE 이슈 생성 실패")
            continue

        linked = create_issue_link(key, new_key)
        if linked:
            log_ok(f"[{key}] -> [{new_key}] 생성 완료 / 링크 완료")
        else:
            log_ok(f"[{key}] -> [{new_key}] 생성 완료")
            logger.warning(f"[{key}] 이슈 링크 생성 실패 - Jira에서 수동 연결 필요")
        logger.info(f"제목: {summary}")
        synced.add(key)

    return synced


# ─── 메인 ────────────────────────────────────────────────────────────────────

def parse_interval() -> int:
    args = sys.argv[1:]
    if "--interval" in args:
        idx = args.index("--interval")
        try:
            return int(args[idx + 1])
        except (IndexError, ValueError):
            pass
    return 30


def main() -> None:
    global logger
    check_env()

    logger   = _setup_logger()
    interval = parse_interval()
    log_file = LOG_DIR / f"watch_intqa_{datetime.now().strftime('%Y%m%d')}.log"

    print("=" * 56)
    print(f"  INTQA 처리중 감시 -> SSCVE 자동 동기화 워처")
    print("=" * 56)
    print(f"  폴링 간격 : {interval}초")
    print(f"  로그 파일 : {log_file}")
    print(f"  Ctrl+C    : 종료")
    print("=" * 56)
    print()

    logger.info(f"워처 시작 (폴링 간격: {interval}초)")
    logger.info(f"로그 파일: {log_file}")

    # 초기 스캔
    logger.info("초기 상태 스캔 중...")
    in_progress = fetch_intqa_in_progress()
    logger.info(f"초기 스캔: INTQA 처리중 이슈 {len(in_progress)}건 확인")

    no_link_keys = {k for k in in_progress if not fetch_linked_sscve_key(k)}
    if no_link_keys:
        logger.info(f"미동기화 이슈 {len(no_link_keys)}건 발견 - 즉시 동기화 실행")
        synced = sync_issues(no_link_keys, in_progress)
        logger.info(f"초기 동기화 완료: {len(synced)}건")
    else:
        logger.info(f"처리중 이슈 {len(in_progress)}건 - 모두 SSCVE 연결 완료")

    known_keys = set(in_progress.keys())
    logger.info("감시 시작 - 새 '처리중' 이슈 대기 중")

    while True:
        try:
            time.sleep(interval)
            current      = fetch_intqa_in_progress()
            current_keys = set(current.keys())

            new_keys = current_keys - known_keys
            if new_keys:
                logger.info(f"신규 처리중 이슈 {len(new_keys)}건 감지")
                sync_issues(new_keys, current)
                known_keys = current_keys
            else:
                logger.info(f"폴링 중... (처리중 이슈: {len(current_keys)}건)")

            removed_keys = known_keys - current_keys
            if removed_keys:
                for key in removed_keys:
                    logger.info(f"[{key}] 처리중 상태 해제됨")
                known_keys = current_keys

        except KeyboardInterrupt:
            logger.info("워처 종료")
            print()
            break


if __name__ == "__main__":
    main()
