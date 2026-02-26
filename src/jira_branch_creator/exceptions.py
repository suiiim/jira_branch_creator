"""커스텀 예외 정의."""


class JiraBranchCreatorError(Exception):
    """프로젝트 최상위 예외."""


class ConfigError(JiraBranchCreatorError):
    """설정 관련 오류."""


class JiraApiError(JiraBranchCreatorError):
    """Jira API 호출 실패."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class GitLabApiError(JiraBranchCreatorError):
    """GitLab API 호출 실패."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class BranchAlreadyExistsError(JiraBranchCreatorError):
    """이미 존재하는 브랜치."""


class IssueNotFoundError(JiraApiError):
    """Jira 이슈를 찾을 수 없음."""


class TransitionNotFoundError(JiraApiError):
    """요청한 상태 전환을 찾을 수 없음."""
