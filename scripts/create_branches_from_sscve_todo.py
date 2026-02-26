#!/usr/bin/env python3
"""
SSCVE 할일 이슈 → git flow feature 브랜치 생성 스크립트

SSCVE 프로젝트에서 현재 사용자(하수임)에게 할당되고 상태가 '할일'인 이슈를 조회하여
C:\\workspace\\c-project 저장소에 git flow feature 브랜치를 자동 생성합니다.

브랜치명 형식: feature/{ISSUE_KEY}-{summary-slug}
              (영문 slug가 없으면 feature/{ISSUE_KEY})

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
import re
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL    = os.environ.get("JIRA_BASE_URL", "")
EMAIL       = os.environ.get("JIRA_EMAIL", "")
TOKEN       = os.environ.get("JIRA_API_TOKEN", "")

PROJECT     = "SSCVE"
STATUS_NAME = "\ud560\uc77c"  # 할일, status id=10138, categoryKey=new
STATUS_ID   = "10138"
REPO_PATH   = r"C:\workspace\c-project"


# ─── 유틸리티 ────────────────────────────────────────────────────────────────

def check_env() -> None:
    missing = [v for v in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN") if not os.environ.get(v)]
    if missing:
        print(f"[ERROR] 환경변수 누락: {', '.join(missing)}")
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
        print(f"[ERROR] API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return None
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
        return None


def make_slug(summary: str) -> str:
    """이슈 요약 -> 브랜치 slug 변환 (영문/숫자만, 최대 50자)"""
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower())
    slug = slug.strip("-")[:50].rstrip("-")
    return slug


def make_feature_name(issue_key: str, summary: str) -> str:
    """git flow feature start 에 전달할 이름 생성 (feature/ 제외)"""
    slug = make_slug(summary)
    if slug:
        return f"{issue_key}-{slug}"
    return issue_key


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
    print(f"  {PROJECT} '{STATUS_NAME}' 이슈: {total}건 조회됨")
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
        print(f"[ERROR] git branch 조회 실패: {result.stderr.strip()}")
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
    print(f"  [ERROR] git flow feature start 실패:")
    print(f"          {result.stderr.strip()}")
    return False


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = "--dry-run" in sys.argv
    check_env()

    print("=" * 56)
    print(f"  SSCVE '{STATUS_NAME}' 이슈 -> git flow feature 브랜치 생성")
    if dry_run:
        print("  [DRY-RUN 모드: 실제 브랜치 생성 안 함]")
    print("=" * 56)
    print(f"  저장소: {REPO_PATH}")
    print()

    # Step 1: 이슈 조회
    print(f"[1/3] SSCVE '{STATUS_NAME}' 이슈 조회 중...")
    issues = fetch_sscve_todo_issues()
    if not issues:
        print(f"  '{STATUS_NAME}' 상태인 이슈가 없습니다. 종료합니다.")
        return
    print()

    # Step 2: 로컬 브랜치 목록 조회
    print("[2/3] 로컬 브랜치 목록 조회 중...")
    local_branches = get_local_branches()
    print(f"  로컬 브랜치: {len(local_branches)}개")
    print()

    # Step 3: 브랜치 생성
    print("[3/3] git flow feature 브랜치 생성 중...")
    created, skipped, failed = 0, 0, 0

    for issue in issues:
        key      = issue["key"]
        summary  = issue["fields"]["summary"]
        itype    = issue["fields"]["issuetype"]["name"]
        feat_name = make_feature_name(key, summary)
        branch    = f"feature/{feat_name}"

        print(f"  [{key}] {itype}")
        print(f"    제목: {summary}")
        print(f"    브랜치: {branch}")

        if branch in local_branches:
            print("    [SKIP] 이미 존재하는 브랜치")
            skipped += 1
            print()
            continue

        if dry_run:
            print("    [DRY-RUN] 생성 예정")
            created += 1
            print()
            continue

        if create_flow_feature_branch(feat_name):
            print("    [OK] 브랜치 생성 완료")
            local_branches.add(branch)
            created += 1
        else:
            print("    [FAIL] 브랜치 생성 실패")
            failed += 1
        print()

    print("=" * 56)
    action = "생성 예정" if dry_run else "생성 완료"
    print(f"  {action}: {created}건 / 건너뜀: {skipped}건 / 실패: {failed}건")
    print("=" * 56)


if __name__ == "__main__":
    main()
