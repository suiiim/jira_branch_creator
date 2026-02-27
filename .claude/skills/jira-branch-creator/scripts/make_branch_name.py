#!/usr/bin/env python3
"""
브랜치명 생성 헬퍼

Usage:
    python make_branch_name.py <issue_key>

    python make_branch_name.py SSCVE-2704
    → feature/SSCVE-2704

Exit codes:
    0 - 성공 (stdout에 브랜치명 출력)
    1 - 인수 오류
"""

import re
import sys


ALLOWED_PROJECT = "SSCVE"
ISSUE_KEY_RE    = re.compile(r"^([A-Z][A-Z0-9]+)-(\d+)$")


def make_branch_name(issue_key: str) -> str:
    return f"feature/{issue_key}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_branch_name.py <issue_key>")
        print("Example: python make_branch_name.py SSCVE-2704")
        sys.exit(1)

    key = sys.argv[1].strip().upper()

    if not ISSUE_KEY_RE.match(key):
        print(f"Invalid issue key format: '{key}' (expected: SSCVE-123)", file=sys.stderr)
        sys.exit(1)

    project = key.split("-")[0]
    if project != ALLOWED_PROJECT:
        print(f"Only '{ALLOWED_PROJECT}' project is supported. Got: '{project}'", file=sys.stderr)
        sys.exit(1)

    print(make_branch_name(key))
