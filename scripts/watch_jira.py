#!/usr/bin/env python3
"""
Jira 이슈 자동 감시 → 브랜치 생성 스크립트

새로 생성되는 Jira 이슈를 폴링하여 자동으로 Git 브랜치를 생성합니다.

Python 3.12+ 필요

Usage:
    python scripts/watch_jira.py

환경변수:
    JIRA_BASE_URL    - Jira 인스턴스 URL (필수)
    JIRA_EMAIL       - Jira 로그인 이메일 (필수)
    JIRA_API_TOKEN   - Jira API 토큰 (필수)
    JIRA_PROJECT_KEY - 프로젝트 키 (선택, 없으면 입력 받음)
    REPO_PATH        - Git 레포지토리 경로 (선택, 기본: 현재 디렉토리)
    POLL_INTERVAL    - 폴링 간격 초 (선택, 기본: 30)
    BASE_BRANCH      - 기본 브랜치 (선택, 기본: develop)
"""

import os
import sys
import re
import time
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import base64
from datetime import datetime

# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL = os.environ.get("JIRA_BASE_URL", "")
EMAIL = os.environ.get("JIRA_EMAIL", "")
TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT = os.environ.get("JIRA_PROJECT_KEY", "")
REPO_PATH = os.environ.get("REPO_PATH", os.getcwd())
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))
BASE_BRANCH = os.environ.get("BASE_BRANCH", "develop")

ALLOWED_PROJECT = "SSCVE"


# ─── 유틸리티 ────────────────────────────────────────────────────────────────

def check_python_version() -> None:
    """Python 3.12 이상인지 확인"""
    if sys.version_info < (3, 12):
        print(f"❌ Python 3.12 이상이 필요합니다. 현재 버전: {sys.version}")
        sys.exit(1)


def check_env() -> None:
    """필수 환경변수 확인"""
    missing = [
        var for var in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
        if not os.environ.get(var)
    ]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Set them in your shell profile or .env file.\n")
        print("   Example:")
        print('   export JIRA_BASE_URL="https://myteam.atlassian.net"')
        print('   export JIRA_EMAIL="your-email@example.com"')
        print('   export JIRA_API_TOKEN="your-api-token"')
        sys.exit(1)


def jira_request(path: str) -> dict | None:
    """Jira REST API 요청"""
    url = f"{JIRA_URL}{path}"
    creds = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"❌ Jira API error: {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"❌ Network error: {e.reason}")
        return None


def get_recent_issues(project_key: str, since_minutes: int = 2) -> list[dict]:
    """최근 N분 이내 생성된 이슈 조회"""
    jql = (
        f"project={project_key} "
        f"AND created >= -{since_minutes}m "
        f"ORDER BY created DESC"
    )
    encoded_jql = urllib.parse.quote(jql)
    path = f"/rest/api/3/search?jql={encoded_jql}&maxResults=10&fields=summary,issuetype"
    data = jira_request(path)
    return data.get("issues", []) if data else []


def make_branch_name(issue: dict) -> str:
    """이슈 정보로부터 브랜치명 생성 (match-case 사용)"""
    key = issue["key"]
    itype = issue["fields"]["issuetype"]["name"].lower()
    summary = issue["fields"]["summary"]

    # Python 3.10+ match-case
    match itype:
        case "bug":
            prefix = "bugfix"
        case "story":
            prefix = "feature"
        case "task":
            prefix = "task"
        case "epic":
            prefix = "epic"
        case "subtask" | "sub-task":
            prefix = "feature"
        case _:
            prefix = "feature"

    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:50]
    return f"{prefix}/{key}-{slug}" if slug else f"{prefix}/{key}"


def create_branch(branch_name: str) -> bool:
    """Git 브랜치 생성 (Windows/Linux/Mac 호환)"""
    cmds = [
        ["git", "fetch", "origin"],
        ["git", "checkout", BASE_BRANCH],
        ["git", "pull", "origin", BASE_BRANCH],
        ["git", "checkout", "-b", branch_name],
    ]
    try:
        for cmd in cmds:
            subprocess.run(cmd, cwd=REPO_PATH, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ❌ Git error: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("    ❌ git not found. Make sure Git is installed and in PATH.")
        return False


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    check_python_version()
    check_env()

    project = PROJECT or input(
        f"Enter Jira project key (only {ALLOWED_PROJECT} is allowed): "
    ).strip().upper()

    if not project:
        print("❌ Project key is required.")
        sys.exit(1)

    if project != ALLOWED_PROJECT:
        print(f"❌ 이 스크립트는 {ALLOWED_PROJECT} 프로젝트만 지원합니다.")
        print(f"   입력된 프로젝트: {project}")
        sys.exit(1)

    seen: set[str] = set()

    print("========================================")
    print("  Jira Branch Creator - Watch Mode")
    print("========================================")
    print(f"  Project       : {project}")
    print(f"  Python        : {sys.version.split()[0]}")
    print(f"  Repo path     : {REPO_PATH}")
    print(f"  Base branch   : {BASE_BRANCH}")
    print(f"  Poll interval : {POLL_INTERVAL}s")
    print("========================================\n")
    print("👀 Scanning existing issues...")

    # 첫 실행: 기존 이슈를 seen에 등록 (브랜치 생성 안 함)
    existing = get_recent_issues(project, since_minutes=60)
    seen.update(issue["key"] for issue in existing)
    print(f"   Skipped {len(seen)} existing issue(s).\n")
    print("🔄 Watching for new issues... (Ctrl+C to stop)\n")

    while True:
        try:
            issues = get_recent_issues(project, since_minutes=2)
            for issue in issues:
                if issue["key"] not in seen:
                    seen.add(issue["key"])
                    branch = make_branch_name(issue)
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    summary = issue["fields"]["summary"]
                    itype = issue["fields"]["issuetype"]["name"]

                    print(f"[{ts}] 🆕 New issue detected!")
                    print(f"    Key     : {issue['key']}")
                    print(f"    Type    : {itype}")
                    print(f"    Summary : {summary}")
                    print(f"    Branch  : {branch}")

                    if create_branch(branch):
                        print("    ✅ Branch created successfully!")
                    print()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n👋 Stopped watching. Goodbye!")
            break


if __name__ == "__main__":
    main()
