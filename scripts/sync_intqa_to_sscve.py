#!/usr/bin/env python3
"""
INTQA → SSCVE 이슈 동기화 스크립트

INTQA 프로젝트에서 현재 사용자(하수임)에게 할당되고 상태가 '처리중'인 이슈를
SSCVE 프로젝트에 동일한 제목(summary)으로 새 이슈(작업)를 생성합니다.

중복 방지:
  - INTQA 이슈에 '문의대응 처리 이슈' 링크(SSCVE 연결)가 이미 있으면 생성 건너뜀
  - 생성 후 INTQA <-> SSCVE 간 '문의대응' 이슈 링크를 자동으로 추가

로그:
  - 저장 위치: %USERPROFILE%\Desktop\jira-sync-logs\
  - 파일명: sync_intqa_YYYYMMDD.log (일별 자동 로테이션)
  - 포맷: [YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE

Usage:
    python scripts/sync_intqa_to_sscve.py

환경변수:
    JIRA_BASE_URL    - Jira 인스턴스 URL (필수)
    JIRA_EMAIL       - Jira 로그인 이메일 (필수)
    JIRA_API_TOKEN   - Jira API 토큰 (필수)

Python 3.9+ 필요
"""

from __future__ import annotations

import os
import sys
import json
import base64
import logging
import urllib.request
import urllib.error
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL = os.environ.get("JIRA_BASE_URL", "")
EMAIL    = os.environ.get("JIRA_EMAIL", "")
TOKEN    = os.environ.get("JIRA_API_TOKEN", "")

SOURCE_PROJECT       = "INTQA"
TARGET_PROJECT       = "SSCVE"
TARGET_ISSUE_TYPE_ID = "10124"                    # 작업
LINK_TYPE_ID         = "10000"                    # 문의대응 (outward: 문의대응 처리 이슈)

# SSCVE 이슈 생성 옵션
ASSIGNEE_ID  = "60fe2779e6e6f800718020a3"  # 하수임 (고정)
PARENT_KEY   = "SSCVE-2561"               # 실행 시 프롬프트로 변경 가능
FIX_VERSION  = "2.0.32"                   # 실행 시 프롬프트로 변경 가능

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
    log_file = LOG_DIR / f"sync_intqa_{datetime.now().strftime('%Y%m%d')}.log"

    formatter = _LevelFormatter()

    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1,
        backupCount=0, encoding="utf-8"
    )
    file_handler.suffix = "%Y%m%d"
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("sync_intqa")
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
        logger.error(f"환경변수 누락: {', '.join(missing)}")
        sys.exit(1)


def _auth_header() -> str:
    return "Basic " + base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()


_fix_version_id_cache: str | None = None


def fetch_fix_version_id(version_name: str) -> str | None:
    """버전명으로 SSCVE 프로젝트의 버전 ID 조회 (결과 캐싱)"""
    global _fix_version_id_cache
    if _fix_version_id_cache is not None:
        return _fix_version_id_cache

    data = jira_get(f"/rest/api/3/project/{TARGET_PROJECT}/versions")
    if not data:
        return None
    for v in data:
        if v.get("name") == version_name:
            _fix_version_id_cache = v["id"]
            return _fix_version_id_cache
    logger.warning(f"버전 '{version_name}'을 찾을 수 없습니다.")
    return None


def jira_get(path: str) -> dict | None:
    """GET 요청"""
    req = urllib.request.Request(
        f"{JIRA_URL}{path}",
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return None


def jira_post(path: str, payload: dict) -> tuple[int, dict | None]:
    """POST 요청 -> (status_code, body) 반환. body가 빈 경우 None."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
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
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return e.code, None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return 0, None


# ─── 핵심 로직 ───────────────────────────────────────────────────────────────

def fetch_intqa_in_progress() -> list[dict]:
    """INTQA에서 현재 사용자 할당 + 처리중 이슈 조회"""
    _, data = jira_post("/rest/api/3/search/jql", {
        "jql": (
            f"project={SOURCE_PROJECT} "
            "AND assignee=currentUser() "
            "AND statusCategory=indeterminate "
            "ORDER BY updated DESC"
        ),
        "fields": ["summary", "status", "issuetype"],
        "maxResults": 100,
    })
    if not data:
        return []
    issues = data.get("issues", [])
    logger.info(f"{SOURCE_PROJECT} 처리중 이슈: {len(issues)}건 조회됨")
    return issues


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
    fields: dict = {
        "project":   {"key": TARGET_PROJECT},
        "summary":   summary,
        "issuetype": {"id": TARGET_ISSUE_TYPE_ID},
        "assignee":  {"accountId": ASSIGNEE_ID},
    }

    if PARENT_KEY:
        fields["parent"] = {"key": PARENT_KEY}

    if FIX_VERSION:
        version_id = fetch_fix_version_id(FIX_VERSION)
        if version_id:
            fields["fixVersions"] = [{"id": version_id}]

    status, data = jira_post("/rest/api/3/issue", {"fields": fields})
    if data and "key" in data:
        return data["key"]
    return None


def create_issue_link(intqa_key: str, sscve_key: str) -> bool:
    """INTQA -> SSCVE '문의대응 처리 이슈' 링크 생성"""
    status, _ = jira_post("/rest/api/3/issueLink", {
        "type":          {"id": LINK_TYPE_ID},
        "inwardIssue":   {"key": intqa_key},   # 문의대응에 접수된 이슈
        "outwardIssue":  {"key": sscve_key},   # 문의대응 처리 이슈
    })
    return status == 201


# ─── 메인 ────────────────────────────────────────────────────────────────────

def prompt_settings() -> None:
    """PARENT_KEY, FIX_VERSION 을 실행 시 프롬프트로 변경할 수 있습니다."""
    global PARENT_KEY, FIX_VERSION

    print(f"  상위 항목 (에픽) [{PARENT_KEY}]: ", end="", flush=True)
    val = input().strip()
    if val:
        PARENT_KEY = val

    print(f"  수정 버전        [{FIX_VERSION}]: ", end="", flush=True)
    val = input().strip()
    if val:
        FIX_VERSION = val

    logger.info(f"설정 - 상위 항목: {PARENT_KEY}, 수정 버전: {FIX_VERSION}")


def main() -> None:
    global logger
    logger = _setup_logger()
    check_env()

    logger.info(f"{SOURCE_PROJECT} -> {TARGET_PROJECT} 이슈 동기화 시작")
    prompt_settings()

    # Step 1: INTQA 처리중 이슈 조회
    logger.info(f"[1/2] {SOURCE_PROJECT} 처리중 이슈 조회 중...")
    intqa_issues = fetch_intqa_in_progress()
    if not intqa_issues:
        logger.info("처리중인 이슈가 없습니다. 종료합니다.")
        return

    # Step 2: 링크 확인 후 신규만 생성
    logger.info(f"[2/2] {TARGET_PROJECT} 이슈 생성 중...")
    created, skipped = 0, 0

    for issue in intqa_issues:
        key     = issue["key"]
        summary = issue["fields"]["summary"]

        linked_key = fetch_linked_sscve_key(key)
        if linked_key:
            log_skip(f"[{key}] 이미 연결된 SSCVE 이슈 존재: {linked_key}")
            logger.info(f"제목: {summary}")
            skipped += 1
            continue

        new_key = create_sscve_issue(summary)
        if not new_key:
            logger.error(f"[{key}] SSCVE 이슈 생성 실패")
            logger.info(f"제목: {summary}")
            continue

        linked = create_issue_link(key, new_key)
        link_status = "링크 완료" if linked else "링크 실패 (수동 연결 필요)"
        log_ok(f"[{key}] -> [{new_key}] 생성 완료 / {link_status}")
        logger.info(f"제목: {summary}")
        created += 1

    logger.info(f"완료: 생성 {created}건 / 건너뜀 {skipped}건")


if __name__ == "__main__":
    main()
