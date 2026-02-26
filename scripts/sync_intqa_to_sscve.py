#!/usr/bin/env python3
"""
INTQA → SSCVE 이슈 동기화 스크립트

INTQA 프로젝트에서 현재 사용자(하수임)에게 할당되고 상태가 '처리중'인 이슈를
SSCVE 프로젝트에 동일한 제목(summary)으로 새 이슈(작업)를 생성합니다.

생성된 SSCVE 이슈에는 'intqa-sync-INTQA-XXXX' 레이블이 붙으며,
이 레이블로 중복 생성을 방지합니다.

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
TARGET_ISSUE_TYPE_ID = "10124"   # 작업
LABEL_PREFIX         = "intqa-sync-"  # e.g. intqa-sync-INTQA-4625


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


# ─── 핵심 로직 ───────────────────────────────────────────────────────────────

def fetch_intqa_in_progress() -> list[dict]:
    """INTQA에서 현재 사용자 할당 + 처리중 이슈 조회"""
    data = jira_post("/rest/api/3/search/jql", {
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
    total  = data.get("total", len(issues))
    print(f"  {SOURCE_PROJECT} 처리중 이슈: {total}건 조회됨")
    return issues


def fetch_already_synced_keys() -> set[str]:
    """SSCVE에서 intqa-sync-* 레이블로 이미 동기화된 INTQA 키 목록 반환"""
    data = jira_post("/rest/api/3/search/jql", {
        "jql": (
            f'project={TARGET_PROJECT} '
            f'AND labels in labelsOf("{TARGET_PROJECT}") '
            f'AND labels ~ "{LABEL_PREFIX}"'
        ),
        "fields": ["labels"],
        "maxResults": 500,
    })

    synced: set[str] = set()
    if not data:
        return synced

    for issue in data.get("issues", []):
        for label in issue["fields"].get("labels", []):
            if label.startswith(LABEL_PREFIX):
                intqa_key = label[len(LABEL_PREFIX):]  # e.g. "INTQA-4625"
                synced.add(intqa_key)
    return synced


def fetch_already_synced_keys_v2() -> set[str]:
    """SSCVE에서 intqa-sync-* 레이블이 있는 이슈를 조회하여 이미 동기화된 INTQA 키 반환

    Jira labelsOf 함수가 지원되지 않는 경우를 위한 대안 방법.
    SSCVE 전체 이슈 중 최근 200건의 레이블을 확인합니다.
    """
    data = jira_post("/rest/api/3/search/jql", {
        "jql": f"project={TARGET_PROJECT} ORDER BY created DESC",
        "fields": ["labels"],
        "maxResults": 200,
    })

    synced: set[str] = set()
    if not data:
        return synced

    for issue in data.get("issues", []):
        for label in issue["fields"].get("labels", []):
            if label.startswith(LABEL_PREFIX):
                intqa_key = label[len(LABEL_PREFIX):]
                synced.add(intqa_key)
    return synced


def create_sscve_issue(intqa_key: str, summary: str) -> dict | None:
    """SSCVE에 작업 이슈 생성 (intqa-sync-* 레이블 포함)"""
    label = f"{LABEL_PREFIX}{intqa_key}"
    return jira_post("/rest/api/3/issue", {
        "fields": {
            "project":   {"key": TARGET_PROJECT},
            "summary":   summary,
            "issuetype": {"id": TARGET_ISSUE_TYPE_ID},
            "labels":    [label],
        }
    })


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main() -> None:
    check_env()

    print("=" * 52)
    print(f"  {SOURCE_PROJECT} -> {TARGET_PROJECT} 이슈 동기화")
    print("=" * 52)
    print()

    # Step 1: INTQA 처리중 이슈 조회
    print(f"[1/3] {SOURCE_PROJECT} 처리중 이슈 조회 중...")
    intqa_issues = fetch_intqa_in_progress()
    if not intqa_issues:
        print("  처리중인 이슈가 없습니다. 종료합니다.")
        return
    print()

    # Step 2: 이미 동기화된 INTQA 키 확인 (레이블 기반)
    print(f"[2/3] {TARGET_PROJECT} 동기화 이력 확인 중 (레이블 기반)...")
    already_synced = fetch_already_synced_keys_v2()
    print(f"  이미 동기화된 이슈: {len(already_synced)}건")
    if already_synced:
        for k in sorted(already_synced):
            print(f"    - {k}")
    print()

    # Step 3: 신규 이슈만 SSCVE에 생성
    print(f"[3/3] {TARGET_PROJECT}에 이슈 생성 중...")
    created, skipped = 0, 0

    for issue in intqa_issues:
        key     = issue["key"]
        summary = issue["fields"]["summary"]

        if key in already_synced:
            print(f"  [SKIP] [{key}] 이미 동기화됨 - 건너뜀")
            print(f"         제목: {summary}")
            skipped += 1
            continue

        result = create_sscve_issue(key, summary)
        if result and "key" in result:
            new_key = result["key"]
            print(f"  [OK]   [{key}] -> [{new_key}] 생성 완료")
            print(f"         제목: {summary}")
            print(f"         레이블: {LABEL_PREFIX}{key}")
            already_synced.add(key)
            created += 1
        else:
            print(f"  [FAIL] [{key}] 생성 실패")
            print(f"         제목: {summary}")

    print()
    print("=" * 52)
    print(f"  완료: 생성 {created}건 / 건너뜀 {skipped}건")
    print("=" * 52)


if __name__ == "__main__":
    main()
