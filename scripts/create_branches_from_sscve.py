#!/usr/bin/env python3
"""
SSCVE 이슈 -> git flow feature 브랜치 생성 스크립트

[Phase 2] SSCVE 할일/진행중 이슈 -> C:\\workspace\\c-project git flow feature 브랜치 생성

중복 방지:
  - 로컬에 이미 존재하는 브랜치는 건너뜀

로그:
  - 저장 위치: %USERPROFILE%\\Desktop\\jira-sync-logs\\
  - 파일명: create_branches_YYYYMMDD.log (일별 자동 로테이션)
  - 포맷: [YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE

Usage:
    python scripts/create_branches_from_sscve.py [--dry-run]

    --dry-run  브랜치 생성을 실제로 수행하지 않고 목록만 출력

환경변수:
    JIRA_BASE_URL    - Jira 인스턴스 URL (필수)
    JIRA_EMAIL       - Jira 로그인 이메일 (필수)
    JIRA_API_TOKEN   - Jira API 토큰 (필수)

Python 3.9+ 필요
"""

from __future__ import annotations

import argparse
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

JIRA_URL       = os.environ.get("JIRA_BASE_URL", "")
EMAIL          = os.environ.get("JIRA_EMAIL", "")
TOKEN          = os.environ.get("JIRA_API_TOKEN", "")

TARGET_PROJECT = "SSCVE"

SSCVE_TODO_STATUS_ID         = "10138"           # 할일
SSCVE_IN_PROGRESS_STATUS_IDS = ("10109", "10148") # 진행중, 진행 중
SSCVE_BRANCH_ISSUE_TYPE_IDS  = ("10124", "10004") # 작업, 버그

REPO_PATH = r"C:\workspace\c-project"

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
        logger.error(f"API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return e.code, None
    except urllib.error.URLError as e:
        logger.error(f"네트워크 오류: {e.reason}")
        return 0, None


# ─── Phase 2: SSCVE 할일/진행중 -> 브랜치 생성 ──────────────────────────────

def fetch_sscve_issues_for_branch() -> list[dict]:
    """SSCVE 할일 + 진행중 이슈 중 이슈 유형이 '작업' 또는 '버그'인 것만 조회"""
    status_ids     = ", ".join([SSCVE_TODO_STATUS_ID] + list(SSCVE_IN_PROGRESS_STATUS_IDS))
    issue_type_ids = ", ".join(SSCVE_BRANCH_ISSUE_TYPE_IDS)
    _, data = jira_post("/rest/api/3/search/jql", {
        "jql": (
            f"project={TARGET_PROJECT} "
            f"AND assignee=currentUser() "
            f"AND status IN ({status_ids}) "
            f"AND issuetype IN ({issue_type_ids}) "
            f"ORDER BY updated DESC"
        ),
        "fields": ["summary", "issuetype", "status"],
        "maxResults": 100,
    })
    if not data:
        return []
    issues = data.get("issues", [])
    total  = data.get("total", len(issues))
    logger.info(f"{TARGET_PROJECT} '할일 + 진행중' 이슈: {total}건 조회됨")
    return issues


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


def pull_base_branches() -> None:
    """develop, release 브랜치 git pull (브랜치 생성 전 최신 상태 유지)"""
    cur = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_PATH, capture_output=True, text=True,
    )
    current_branch = cur.stdout.strip() if cur.returncode == 0 else ""

    for branch in ("develop", "release"):
        if current_branch == branch:
            result = subprocess.run(
                ["git", "pull"],
                cwd=REPO_PATH, capture_output=True, text=True,
            )
        else:
            result = subprocess.run(
                ["git", "fetch", "origin", f"{branch}:{branch}"],
                cwd=REPO_PATH, capture_output=True, text=True,
            )

        if result.returncode == 0:
            log_ok(f"{branch} 브랜치 pull 완료")
        else:
            stderr = result.stderr.strip()
            if any(msg in stderr for msg in ("couldn't find remote ref", "does not exist")):
                logger.warning(f"{branch} 브랜치가 원격에 존재하지 않아 건너뜁니다.")
            else:
                logger.warning(f"{branch} 브랜치 pull 실패: {stderr}")


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


def run_phase2(dry_run: bool) -> None:
    """Phase 2: SSCVE 할일/진행중 이슈 -> git flow feature 브랜치 생성"""
    logger.info("=" * 50)
    logger.info(f"[Phase 2] {TARGET_PROJECT} '할일/진행중' -> git flow feature 브랜치 생성")
    if dry_run:
        logger.info("[DRY-RUN 모드: 실제 브랜치 생성 안 함]")
    logger.info("=" * 50)
    logger.info(f"저장소: {REPO_PATH}")

    pull_base_branches()

    issues = fetch_sscve_issues_for_branch()
    if not issues:
        logger.info("'할일/진행중' 상태인 SSCVE 이슈가 없습니다.")
        return

    local_branches = get_local_branches()
    logger.info(f"로컬 브랜치: {len(local_branches)}개")

    created, skipped, failed = 0, 0, 0
    for issue in issues:
        key     = issue["key"]
        summary = issue["fields"]["summary"]
        status  = issue["fields"]["status"]["name"]
        branch  = f"feature/{key}"

        logger.info(f"[{key}] [{status}] 브랜치: {branch}")
        logger.info(f"제목: {summary}")

        if branch in local_branches:
            log_skip(f"[{key}] 이미 존재하는 브랜치")
            skipped += 1
            continue

        if dry_run:
            logger.info(f"[{key}] [DRY-RUN] 생성 예정")
            created += 1
            continue

        if create_flow_feature_branch(key):
            log_ok(f"[{key}] 브랜치 생성 완료")
            local_branches.add(branch)
            created += 1
        else:
            logger.error(f"[{key}] 브랜치 생성 실패")
            failed += 1

    action = "생성 예정" if dry_run else "생성 완료"
    logger.info(f"Phase 2 완료: {action} {created}건 / 건너뜀 {skipped}건 / 실패 {failed}건")


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    global logger

    parser = argparse.ArgumentParser(
        description="SSCVE 할일/진행중 이슈 -> git flow feature 브랜치 생성"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="브랜치 생성을 실제로 수행하지 않고 목록만 출력",
    )
    args = parser.parse_args()

    logger = _setup_logger()
    check_env()

    logger.info(f"SSCVE 이슈 -> git flow 브랜치 생성 시작")
    logger.info(f"저장소: {REPO_PATH}")

    run_phase2(args.dry_run)

    logger.info("완료")


if __name__ == "__main__":
    main()
