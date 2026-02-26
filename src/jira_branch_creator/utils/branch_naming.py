"""브랜치 네이밍 유틸리티.

Jira 이슈 타입과 요약을 기반으로 컨벤션에 맞는 브랜치명을 생성합니다.
규칙: {prefix}/{ISSUE_KEY}-{summary-slug}
"""

import re

from jira_branch_creator.config import BranchNamingConfig
from jira_branch_creator.models.issue import JiraIssue

DEFAULT_PREFIX = "feature"


def _resolve_prefix(issue_type: str, config: BranchNamingConfig) -> str:
    """이슈 타입에 따른 브랜치 prefix를 결정합니다."""
    normalized = issue_type.lower().strip()
    match normalized:
        case "bug":
            return config.prefixes.get("bug", "bugfix")
        case "story":
            return config.prefixes.get("story", "feature")
        case "task":
            return config.prefixes.get("task", "task")
        case "epic":
            return config.prefixes.get("epic", "epic")
        case "subtask" | "sub-task":
            return config.prefixes.get("subtask", "feature")
        case _:
            return config.prefixes.get(normalized, DEFAULT_PREFIX)


def _slugify(text: str, max_length: int) -> str:
    """텍스트를 URL-safe 슬러그로 변환합니다.

    영문/숫자만 유지하고, 나머지는 하이픈으로 치환합니다.
    한글만 있는 경우 빈 문자열을 반환합니다.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def generate_branch_name(issue: JiraIssue, config: BranchNamingConfig) -> str:
    """Jira 이슈 정보로부터 브랜치명을 생성합니다.

    Args:
        issue: Jira 이슈 정보.
        config: 브랜치 네이밍 설정.

    Returns:
        컨벤션에 맞는 브랜치명.
        예: "feature/SSCVE-123-add-user-profile"

    Examples:
        >>> from jira_branch_creator.models.issue import JiraIssue
        >>> from jira_branch_creator.config import BranchNamingConfig
        >>> issue = JiraIssue(key="SSCVE-1", summary="Fix login", issue_type="Bug")
        >>> generate_branch_name(issue, BranchNamingConfig())
        'bugfix/SSCVE-1-fix-login'
    """
    prefix = _resolve_prefix(issue.issue_type, config)
    slug = _slugify(issue.summary, config.max_slug_length)

    if slug:
        return f"{prefix}/{issue.key}-{slug}"
    return f"{prefix}/{issue.key}"
