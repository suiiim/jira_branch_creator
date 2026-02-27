#!/usr/bin/env python3
"""
INTQA → SSCVE 이슈 동기화 스크립트

INTQA 프로젝트에서 현재 사용자(하수임)에게 할당되고 상태가 '처리중'인 이슈를
SSCVE 프로젝트에 동일한 제목(summary)으로 새 이슈(작업)를 생성합니다.

중복 방지:
  - INTQA 이슈에 '문의대응 처리 이슈' 링크(SSCVE 연결)가 이미 있으면 생성 건너뜀
  - 생성 후 INTQA ↔ SSCVE 간 '문의대응' 이슈 링크를 자동으로 추가

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
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL = os.environ.get("JIRA_BASE_URL", "")
EMAIL    = os.environ.get("JIRA_EMAIL", "")
TOKEN    = os.environ.get("JIRA_API_TOKEN", "")

SOURCE_PROJECT       = "INTQA"
TARGET_PROJECT       = "SSCVE"
TARGET_ISSUE_TYPE_ID = "10124"  # 작업
LINK_TYPE_ID         = "10000"  # 문의대응 (outward: 문의대응 처리 이슈)


# ─── 유틸리티 ────────────────────────────────────────────────────────────────

def check_env() -> None:
    missing = [v for v in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN") if not os.environ.get(v)]
    if missing:
        print(f"[ERROR] 환경변수 누락: {', '.join(missing)}")
        sys.exit(1)


def _auth_header() -> str:
    return "Basic " + base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()


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
        print(f"[ERROR] API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return None
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
        return None


def jira_post(path: str, payload: dict) -> tuple[int, dict | None]:
    """POST 요청 → (status_code, body) 반환. body가 빈 경우 None."""
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
        print(f"[ERROR] API {e.code} {e.reason}: {e.read().decode()[:300]}")
        return e.code, None
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
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
    print(f"  {SOURCE_PROJECT} 처리중 이슈: {len(issues)}건 조회됨")
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
    """SSCVE에 작업 이슈 생성 → 새 이슈 키 반환. 실패 시 None."""
    status, data = jira_post("/rest/api/3/issue", {
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
    """INTQA → SSCVE '문의대응 처리 이슈' 링크 생성"""
    status, _ = jira_post("/rest/api/3/issueLink", {
        "type":          {"id": LINK_TYPE_ID},
        "inwardIssue":   {"key": intqa_key},   # 문의대응에 접수된 이슈
        "outwardIssue":  {"key": sscve_key},   # 문의대응 처리 이슈
    })
    return status == 201


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    check_env()

    print("=" * 52)
    print(f"  {SOURCE_PROJECT} -> {TARGET_PROJECT} 이슈 동기화")
    print("=" * 52)
    print()

    # Step 1: INTQA 처리중 이슈 조회
    print(f"[1/2] {SOURCE_PROJECT} 처리중 이슈 조회 중...")
    intqa_issues = fetch_intqa_in_progress()
    if not intqa_issues:
        print("  처리중인 이슈가 없습니다. 종료합니다.")
        return
    print()

    # Step 2: 링크 확인 후 신규만 생성
    print(f"[2/2] {TARGET_PROJECT} 이슈 생성 중...")
    created, skipped = 0, 0

    for issue in intqa_issues:
        key     = issue["key"]
        summary = issue["fields"]["summary"]

        # 이미 연결된 SSCVE 이슈가 있으면 건너뜀
        linked_key = fetch_linked_sscve_key(key)
        if linked_key:
            print(f"  [SKIP] [{key}] 이미 연결된 SSCVE 이슈 존재: {linked_key}")
            print(f"         제목: {summary}")
            skipped += 1
            continue

        # SSCVE 이슈 생성
        new_key = create_sscve_issue(summary)
        if not new_key:
            print(f"  [FAIL] [{key}] SSCVE 이슈 생성 실패")
            print(f"         제목: {summary}")
            continue

        # 이슈 링크 생성 (INTQA → SSCVE, 문의대응 처리 이슈)
        linked = create_issue_link(key, new_key)
        link_status = "링크 완료" if linked else "링크 실패 (수동 연결 필요)"

        print(f"  [OK]   [{key}] -> [{new_key}] 생성 완료 / {link_status}")
        print(f"         제목: {summary}")
        created += 1

    print()
    print("=" * 52)
    print(f"  완료: 생성 {created}건 / 건너뜀 {skipped}건")
    print("=" * 52)


if __name__ == "__main__":
    main()
