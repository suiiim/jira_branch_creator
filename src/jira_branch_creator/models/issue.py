"""Jira 이슈 및 관련 데이터 모델."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JiraIssue:
    """Jira 이슈 정보."""

    key: str
    summary: str
    issue_type: str
    status: str = ""
    project_key: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> "JiraIssue":
        """Jira REST API 응답에서 JiraIssue 생성."""
        fields = data.get("fields", {})
        return cls(
            key=data["key"],
            summary=fields.get("summary", ""),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            status=fields.get("status", {}).get("name", ""),
            project_key=data["key"].split("-")[0],
        )


@dataclass(frozen=True)
class TransitionInfo:
    """Jira 이슈 상태 전환 정보."""

    id: str
    name: str
    to_status: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> "TransitionInfo":
        """Jira transitions API 응답에서 TransitionInfo 생성."""
        return cls(
            id=data["id"],
            name=data["name"],
            to_status=data.get("to", {}).get("name", ""),
        )


@dataclass(frozen=True)
class BranchInfo:
    """GitLab 브랜치 정보."""

    name: str
    ref: str
    issue_key: str = ""
    web_url: str = ""


@dataclass
class CreateIssueRequest:
    """Jira 이슈 생성 요청."""

    project_key: str
    summary: str
    issue_type: str
    description: str = ""
    labels: list[str] = field(default_factory=list)
