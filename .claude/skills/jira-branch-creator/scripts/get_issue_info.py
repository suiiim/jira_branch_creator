#!/usr/bin/env python3
"""
Jira 단일 이슈 정보 조회 헬퍼

Usage:
    python get_issue_info.py SSCVE-123

Output (stdout):
    JSON 형식으로 이슈 정보 출력
    {
        "key": "SSCVE-123",
        "type": "Bug",
        "summary": "Fix login error",
        "status": "To Do"
    }

Exit codes:
    0 - 성공
    1 - 환경변수 미설정 / API 오류 / 유효하지 않은 이슈 키
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request


ALLOWED_PROJECT = "SSCVE"


def check_env() -> tuple[str, str, str]:
    errors = []
    url   = os.environ.get("JIRA_BASE_URL", "")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not url:   errors.append("JIRA_BASE_URL")
    if not email: errors.append("JIRA_EMAIL")
    if not token: errors.append("JIRA_API_TOKEN")
    if errors:
        print(f"❌ Missing env vars: {', '.join(errors)}", file=sys.stderr)
        print("   Run setup.ps1 (Windows) or setup.sh (macOS/Linux)", file=sys.stderr)
        sys.exit(1)
    return url, email, token


def fetch_issue(base_url: str, email: str, token: str, key: str) -> dict:
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    api   = f"{base_url}/rest/api/3/issue/{key}?fields=summary,issuetype,status"
    req   = urllib.request.Request(api, headers={
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        return {
            "key":     data["key"],
            "type":    data["fields"]["issuetype"]["name"],
            "summary": data["fields"]["summary"],
            "status":  data["fields"]["status"]["name"],
        }
    except urllib.error.HTTPError as e:
        print(f"❌ Jira API error: {e.code} {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("   Check JIRA_EMAIL and JIRA_API_TOKEN.", file=sys.stderr)
        elif e.code == 404:
            print(f"   Issue '{key}' not found.", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ Network error: {e.reason}", file=sys.stderr)
        print("   Check JIRA_BASE_URL and your network.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_issue_info.py <ISSUE_KEY>")
        sys.exit(1)

    key = sys.argv[1].strip().upper()
    project = key.split("-")[0] if "-" in key else ""

    if project != ALLOWED_PROJECT:
        print(f"❌ Only '{ALLOWED_PROJECT}' project is supported. Got: '{project}'", file=sys.stderr)
        sys.exit(1)

    base_url, email, token = check_env()
    info = fetch_issue(base_url, email, token, key)
    print(json.dumps(info, ensure_ascii=False, indent=2))
