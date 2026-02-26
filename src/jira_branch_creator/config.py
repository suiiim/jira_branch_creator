"""설정 관리 모듈.

환경변수에서 Jira/GitLab 설정을 로드합니다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from jira_branch_creator.exceptions import ConfigError


@dataclass(frozen=True)
class JiraConfig:
    """Jira 연결 설정."""

    base_url: str
    email: str
    api_token: str
    project_key: str = "SSCVE"


@dataclass(frozen=True)
class GitLabConfig:
    """GitLab 연결 설정."""

    base_url: str
    token: str
    project_id: str
    default_branch: str = "develop"


@dataclass(frozen=True)
class BranchNamingConfig:
    """브랜치 네이밍 설정."""

    max_slug_length: int = 50
    prefix_map: dict[str, str] | None = None

    @property
    def prefixes(self) -> dict[str, str]:
        if self.prefix_map:
            return self.prefix_map
        return {
            "bug": "bugfix",
            "story": "feature",
            "task": "task",
            "epic": "epic",
            "subtask": "feature",
            "sub-task": "feature",
        }


@dataclass(frozen=True)
class AppConfig:
    """애플리케이션 전체 설정."""

    jira: JiraConfig
    gitlab: GitLabConfig
    branch_naming: BranchNamingConfig


def _require_env(name: str) -> str:
    """환경변수를 가져오고, 없으면 ConfigError를 발생시킵니다."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"필수 환경변수 '{name}'이 설정되지 않았습니다.\n"
            f"  export {name}=\"your-value\""
        )
    return value


def load_config() -> AppConfig:
    """환경변수에서 설정을 로드합니다.

    필수 환경변수:
        JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
        GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID

    선택 환경변수:
        JIRA_PROJECT_KEY (기본: SSCVE)
        GITLAB_DEFAULT_BRANCH (기본: develop)
        BRANCH_MAX_SLUG_LENGTH (기본: 50)
    """
    jira = JiraConfig(
        base_url=_require_env("JIRA_BASE_URL").rstrip("/"),
        email=_require_env("JIRA_EMAIL"),
        api_token=_require_env("JIRA_API_TOKEN"),
        project_key=os.environ.get("JIRA_PROJECT_KEY", "SSCVE").strip(),
    )

    gitlab = GitLabConfig(
        base_url=_require_env("GITLAB_URL").rstrip("/"),
        token=_require_env("GITLAB_TOKEN"),
        project_id=_require_env("GITLAB_PROJECT_ID"),
        default_branch=os.environ.get("GITLAB_DEFAULT_BRANCH", "develop").strip(),
    )

    branch_naming = BranchNamingConfig(
        max_slug_length=int(os.environ.get("BRANCH_MAX_SLUG_LENGTH", "50")),
    )

    return AppConfig(jira=jira, gitlab=gitlab, branch_naming=branch_naming)
