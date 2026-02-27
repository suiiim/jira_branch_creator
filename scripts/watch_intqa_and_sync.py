#!/usr/bin/env python3
"""
INTQA 처리중 이슈 감시 → SSCVE 자동 동기화 워처

INTQA에서 현재 사용자에게 할당된 이슈가 '처리중'으로 바뀌면
자동으로 감지하여 SSCVE에 동일한 제목의 이슈를 생성하고
INTQA ↔ SSCVE 간 '문의대응 처리 이슈' 링크를 연결합니다.

중복 방지:
  - INTQA 이슈에 '문의대응 처리 이슈' 링크(SSCVE 연결)가 이미 있으면 생성 건너뜀

Usage:
    python scripts/watch_intqa_and_sync.py [--interval 30]

    --interval N  폴링 간격 (초, 기본값: 30)

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
import time
import base64
import urllib.request
import urllib.error
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")


# ─── 설정 ────────────────────────────────────────────────────────────────────

JIRA_URL             = os.environ.get("JIRA_BASE_URL", "")
EMAIL                = os.environ.get("JIRA_EMAIL", "")
TOKEN                = os.environ.get("JIRA_API_TOKEN", "")

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
    req = urllib.request.Request(
        f"{JIRA_URL}{path}",
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] API {e.code} {e.reason}: {e.read().decode()[:200]}")
        return None
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
        return None


def jira_post(path: str, payload: dict) -> tuple[int, dict | None]:
    """POST 요청 → (status_code, body). body가 빈 경우 None."""
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
        print(f"[ERROR] API {e.code} {e.reason}: {e.read().decode()[:200]}")
        return e.code, None
    except urllib.error.URLError as e:
        print(f"[ERROR] 네트워크 오류: {e.reason}")
        return 0, None


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── Jira 조회/생성 ──────────────────────────────────────────────────────────

def fetch_intqa_in_progress() -> dict[str, dict]:
    """INTQA 처리중 이슈 조회 → {issueKey: issue}"""
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
    """SSCVE에 작업 이슈 생성 → 새 이슈 키 반환. 실패 시 None."""
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
    """INTQA → SSCVE '문의대응 처리 이슈' 링크 생성"""
    status, _ = jira_post("/rest/api/3/issueLink", {
        "type":         {"id": LINK_TYPE_ID},
        "inwardIssue":  {"key": intqa_key},   # 문의대응에 접수된 이슈
        "outwardIssue": {"key": sscve_key},   # 문의대응 처리 이슈
    })
    return status == 201


# ─── 동기화 실행 ─────────────────────────────────────────────────────────────

def sync_issues(keys: set[str], in_progress: dict[str, dict]) -> set[str]:
    """주어진 INTQA 키들을 SSCVE에 동기화. 성공한 키 집합 반환."""
    synced = set()
    for key in keys:
        summary = in_progress[key]["fields"]["summary"]

        # 이미 연결된 이슈 재확인 (레이스 컨디션 방지)
        linked_key = fetch_linked_sscve_key(key)
        if linked_key:
            print(f"[{ts()}] [SKIP] [{key}] 이미 연결된 SSCVE 이슈 존재: {linked_key}")
            synced.add(key)
            continue

        # SSCVE 이슈 생성
        new_key = create_sscve_issue(summary)
        if not new_key:
            print(f"[{ts()}] [FAIL] [{key}] SSCVE 이슈 생성 실패")
            continue

        # 이슈 링크 생성
        linked = create_issue_link(key, new_key)
        link_status = "링크 완료" if linked else "링크 실패 (수동 연결 필요)"

        print(f"[{ts()}] [OK]   [{key}] -> [{new_key}] 생성 완료 / {link_status}")
        print(f"         제목: {summary}")
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
    check_env()
    interval = parse_interval()

    print("=" * 56)
    print(f"  INTQA 처리중 감시 -> SSCVE 자동 동기화 워처")
    print("=" * 56)
    print(f"  폴링 간격 : {interval}초")
    print(f"  Ctrl+C    : 종료")
    print("=" * 56)
    print()

    # 초기 스캔
    print(f"[{ts()}] 초기 상태 스캔 중...")
    in_progress = fetch_intqa_in_progress()

    # 이미 처리중인 이슈 중 SSCVE 링크가 없는 것은 즉시 동기화
    no_link_keys = {k for k in in_progress if not fetch_linked_sscve_key(k)}
    if no_link_keys:
        print(f"[{ts()}] 미동기화 이슈 {len(no_link_keys)}건 발견 - 즉시 동기화 실행")
        synced = sync_issues(no_link_keys, in_progress)
        print(f"[{ts()}] 초기 동기화 완료: {len(synced)}건")
    else:
        print(f"[{ts()}] 현재 처리중 이슈 {len(in_progress)}건 - 모두 SSCVE 연결 완료")

    known_keys = set(in_progress.keys())
    print(f"[{ts()}] 감시 시작... (새 '처리중' 이슈 대기 중)\n")

    while True:
        try:
            time.sleep(interval)
            current      = fetch_intqa_in_progress()
            current_keys = set(current.keys())

            # 새로 처리중이 된 이슈
            new_keys = current_keys - known_keys
            if new_keys:
                print(f"[{ts()}] 신규 처리중 이슈 {len(new_keys)}건 감지!")
                sync_issues(new_keys, current)
                known_keys = current_keys

            # 처리중에서 벗어난 이슈 (완료/취소 등)
            removed_keys = known_keys - current_keys
            if removed_keys:
                for key in removed_keys:
                    print(f"[{ts()}] [INFO] [{key}] 처리중 상태 해제됨")
                known_keys = current_keys

        except KeyboardInterrupt:
            print(f"\n[{ts()}] 워처 종료.")
            break


if __name__ == "__main__":
    main()
