#!/usr/bin/env python3
"""
SSCVE 할일 이슈 -> git flow feature 브랜치 생성 스크립트

SSCVE 프로젝트에서 현재 사용자(하수임)에게 할당되고 상태가 '할일'인 이슈를 조회하여
C:\\workspace\\c-project 저장소에 git flow feature 브랜치를 자동 생성합니다.

브랜치명 형식: feature/{ISSUE_KEY}  (예: feature/SSCVE-2704)

로그:
  - 저장 위치: %USERPROFILE%\Desktop\jira-sync-logs\
  - 파일명: create_branches_YYYYMMDD.log (일별 자동 로테이션)
  - 포맷: [YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE

Usage:
    python scripts/create_branches_from_sscve_todo.py [--dry-run]

    --dry-run  실제 브랜치 생성 없이 생성될 브랜치명만 출력

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
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL    = os.environ.get("JIRA_BASE_URL", "")
EMAIL       = os.environ.get("JIRA_EMAIL", "")
TOKEN       = os.environ.get("JIRA_API_TOKEN", "")

PROJECT     = "SSCVE"
STATUS_NAME = "\ud560\uc77c"  # 할일, status id=10138, categoryKey=new
STATUS_ID   = "10138"
REPO_PATH   = r"C:\workspace\c-project"

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
    log_file = LOG_DIR / f"create_branches_{datetime.now().strftime('%Y%m%d')}.log"

    formatter = _LevelFormatter()

    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1,
        backupCount=0, encoding="utf-8"
    )
    file_handler.suffix = "%Y%m%d"
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("create_branches")
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


def jira_post(path: str, payload: dict) -> dict | None:
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
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return None


# ─── Jira 조회 ───────────────────────────────────────────────────────────────

def fetch_sscve_todo_issues() -> list[dict]:
    """SSCVE에서 현재 사용자 할당 + 할일 상태 이슈 조회"""
    data = jira_post("/rest/api/3/search/jql", {
        "jql": (
            f"project={PROJECT} "
            f"AND assignee=currentUser() "
            f"AND status = {STATUS_ID} "
            f"ORDER BY updated DESC"
        ),
        "fields": ["summary", "issuetype", "status"],
        "maxResults": 100,
    })
    if not data:
        return []
    issues = data.get("issues", [])
    total  = data.get("total", len(issues))
    logger.info(f"{PROJECT} '{STATUS_NAME}' 이슈: {total}건 조회됨")
    return issues


# ─── git 브랜치 조회 ─────────────────────────────────────────────────────────

def get_local_branches() -> set[str]:
    """로컬 브랜치 목록 반환"""
    result = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"git branch 조회 실패: {result.stderr.strip()}")
        return set()
    return {b.strip() for b in result.stdout.splitlines() if b.strip()}


# ─── git flow 브랜치 생성 ────────────────────────────────────────────────────

def create_flow_feature_branch(feature_name: str) -> bool:
    """git flow feature start {feature_name} 실행"""
    result = subprocess.run(
        ["git", "flow", "feature", "start", feature_name],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    logger.error(f"git flow feature start 실패: {result.stderr.strip()}")
    return False


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    global logger
    logger  = _setup_logger()
    dry_run = "--dry-run" in sys.argv
    check_env()

    mode = "DRY-RUN" if dry_run else "실행"
    logger.info(f"SSCVE '{STATUS_NAME}' 이슈 -> git flow feature 브랜치 생성 [{mode}]")
    logger.info(f"저장소: {REPO_PATH}")

    # Step 1: 이슈 조회
    logger.info(f"[1/3] SSCVE '{STATUS_NAME}' 이슈 조회 중...")
    issues = fetch_sscve_todo_issues()
    if not issues:
        logger.info(f"'{STATUS_NAME}' 상태인 이슈가 없습니다. 종료합니다.")
        return

    # Step 2: 로컬 브랜치 목록 조회
    logger.info("[2/3] 로컬 브랜치 목록 조회 중...")
    local_branches = get_local_branches()
    logger.info(f"로컬 브랜치: {len(local_branches)}개")

    # Step 3: 브랜치 생성
    logger.info("[3/3] git flow feature 브랜치 생성 중...")
    created, skipped, failed = 0, 0, 0

    for issue in issues:
        key       = issue["key"]
        summary   = issue["fields"]["summary"]
        itype     = issue["fields"]["issuetype"]["name"]
        feat_name = key
        branch    = f"feature/{feat_name}"

        logger.info(f"[{key}] {itype} / 브랜치: {branch}")
        logger.info(f"제목: {summary}")

        if branch in local_branches:
            log_skip(f"[{key}] 이미 존재하는 브랜치")
            skipped += 1
            continue

        if dry_run:
            logger.info(f"[{key}] [DRY-RUN] 생성 예정")
            created += 1
            continue

        if create_flow_feature_branch(feat_name):
            log_ok(f"[{key}] 브랜치 생성 완료")
            local_branches.add(branch)
            created += 1
        else:
            logger.error(f"[{key}] 브랜치 생성 실패")
            failed += 1

    action = "생성 예정" if dry_run else "생성 완료"
    logger.info(f"{action}: {created}건 / 건너뜀: {skipped}건 / 실패: {failed}건")


if __name__ == "__main__":
    main()
