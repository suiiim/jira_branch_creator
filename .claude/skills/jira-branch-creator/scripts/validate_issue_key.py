#!/usr/bin/env python3
"""
이슈 키 유효성 검사 헬퍼

Usage:
    python validate_issue_key.py SSCVE-123
    python validate_issue_key.py PROJ-999   # → 오류 출력 후 exit 1

Exit codes:
    0 - 유효한 SSCVE 이슈 키
    1 - 형식 오류 또는 SSCVE 외 프로젝트 키
"""

import re
import sys

ALLOWED_PROJECT = "SSCVE"
ISSUE_KEY_RE    = re.compile(r"^([A-Z][A-Z0-9]+)-(\d+)$")


def validate(key: str) -> tuple[bool, str]:
    """(ok, message) 반환"""
    key = key.strip().upper()
    m   = ISSUE_KEY_RE.match(key)

    if not m:
        return False, f"❌ Invalid issue key format: '{key}' (expected: SSCVE-123)"

    project = m.group(1)
    if project != ALLOWED_PROJECT:
        return False, (
            f"❌ Only '{ALLOWED_PROJECT}' project is supported.\n"
            f"   Received project: '{project}'\n"
            f"   Example: {ALLOWED_PROJECT}-123"
        )

    return True, f"✅ Valid issue key: {key}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_issue_key.py <ISSUE_KEY>")
        sys.exit(1)

    ok, msg = validate(sys.argv[1])
    print(msg)
    sys.exit(0 if ok else 1)
