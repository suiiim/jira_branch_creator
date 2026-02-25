#!/usr/bin/env python3
"""
브랜치명 생성 헬퍼

Usage:
    python make_branch_name.py <issue_type> <issue_key> <summary>

    python make_branch_name.py Bug SSCVE-123 "Fix login error"
    → bugfix/SSCVE-123-fix-login-error

    python make_branch_name.py Story SSCVE-456 "로그인 기능 추가"
    → feature/SSCVE-456   (한글 요약은 슬러그 제거 후 이슈 키만)

Exit codes:
    0 - 성공 (stdout에 브랜치명 출력)
    1 - 인수 오류
"""

import re
import sys


PREFIX_MAP: dict[str, str] = {
    "bug":      "bugfix",
    "story":    "feature",
    "task":     "task",
    "epic":     "epic",
    "subtask":  "feature",
    "sub-task": "feature",
}

MAX_SLUG_LEN  = 50
MAX_BRANCH_LEN = 63


def issue_type_to_prefix(issue_type: str) -> str:
    return PREFIX_MAP.get(issue_type.lower(), "feature")


def summary_to_slug(summary: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")
    return slug[:MAX_SLUG_LEN].rstrip("-")


def make_branch_name(issue_type: str, issue_key: str, summary: str) -> str:
    prefix = issue_type_to_prefix(issue_type)
    slug   = summary_to_slug(summary)

    if slug:
        branch = f"{prefix}/{issue_key}-{slug}"
    else:
        branch = f"{prefix}/{issue_key}"

    # 최대 길이 초과 시 슬러그 잘라냄
    if len(branch) > MAX_BRANCH_LEN:
        allowed = MAX_BRANCH_LEN - len(f"{prefix}/{issue_key}-")
        slug    = slug[:allowed].rstrip("-")
        branch  = f"{prefix}/{issue_key}-{slug}"

    return branch


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python make_branch_name.py <issue_type> <issue_key> <summary>")
        print("Example: python make_branch_name.py Bug SSCVE-123 'Fix login error'")
        sys.exit(1)

    issue_type = sys.argv[1]
    issue_key  = sys.argv[2].strip().upper()
    summary    = sys.argv[3]

    result = make_branch_name(issue_type, issue_key, summary)
    print(result)
