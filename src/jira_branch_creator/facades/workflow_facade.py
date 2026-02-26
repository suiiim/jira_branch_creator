"""워크플로우 Facade.

JiraService와 GitLabService를 조합하여 고수준 워크플로우를 제공합니다.

주요 워크플로우:
    1. 이슈 조회 → 브랜치 생성
    2. 이슈 생성 → 상태 전환 → 브랜치 생성
    3. 이슈 상태 전환
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jira_branch_creator.config import AppConfig
from jira_branch_creator.models.issue import BranchInfo, CreateIssueRequest, JiraIssue
from jira_branch_creator.services.gitlab_service import GitLabService
from jira_branch_creator.services.jira_service import JiraService
from jira_branch_creator.utils.branch_naming import generate_branch_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowResult:
    """워크플로우 실행 결과."""

    issue: JiraIssue
    branch: BranchInfo | None = None
    message: str = ""


class WorkflowFacade:
    """Jira + GitLab 워크플로우를 조합하는 Facade 클래스.

    두 서비스를 조합하여 다음과 같은 고수준 작업을 제공합니다:
        - 이슈에서 브랜치 생성
        - 이슈 생성 후 브랜치 생성
        - 이슈 상태 전환
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._jira = JiraService(config.jira)
        self._gitlab = GitLabService(config.gitlab)

    # ─── 워크플로우 1: 기존 이슈에서 브랜치 생성 ──────────────────────────

    def create_branch_from_issue(
        self,
        issue_key: str,
        ref: str | None = None,
    ) -> WorkflowResult:
        """기존 Jira 이슈에서 GitLab 브랜치를 생성합니다.

        1. Jira에서 이슈 정보 조회
        2. 이슈 타입/요약 기반으로 브랜치명 생성
        3. GitLab에 브랜치 생성

        Args:
            issue_key: Jira 이슈 키 (예: "SSCVE-123").
            ref: 기준 브랜치 (None이면 설정의 기본값 사용).

        Returns:
            이슈 정보와 생성된 브랜치 정보.
        """
        issue = self._jira.get_issue(issue_key)
        branch_name = generate_branch_name(issue, self._config.branch_naming)
        branch = self._gitlab.create_branch(
            branch_name=branch_name,
            ref=ref,
            issue_key=issue_key,
        )

        logger.info(
            "워크플로우 완료: %s → %s",
            issue_key,
            branch.name,
        )
        return WorkflowResult(
            issue=issue,
            branch=branch,
            message=f"브랜치 '{branch.name}'이(가) 성공적으로 생성되었습니다.",
        )

    # ─── 워크플로우 2: 이슈 생성 + 브랜치 생성 ───────────────────────────

    def create_issue_and_branch(
        self,
        summary: str,
        issue_type: str = "Task",
        description: str = "",
        labels: list[str] | None = None,
        transition_to: str | None = None,
        ref: str | None = None,
    ) -> WorkflowResult:
        """새 Jira 이슈를 생성하고, GitLab 브랜치까지 자동 생성합니다.

        1. Jira에 이슈 생성
        2. (선택) 이슈 상태 전환
        3. GitLab에 브랜치 생성

        Args:
            summary: 이슈 제목.
            issue_type: 이슈 타입 (Bug, Story, Task, Epic).
            description: 이슈 설명 (선택).
            labels: 레이블 목록 (선택).
            transition_to: 생성 후 전환할 상태명 (선택).
            ref: 기준 브랜치 (None이면 설정의 기본값 사용).

        Returns:
            생성된 이슈 정보와 브랜치 정보.
        """
        request = CreateIssueRequest(
            project_key=self._config.jira.project_key,
            summary=summary,
            issue_type=issue_type,
            description=description,
            labels=labels or [],
        )
        issue = self._jira.create_issue(request)
        logger.info("이슈 생성: %s (%s)", issue.key, issue.summary)

        if transition_to:
            issue = self._jira.transition_issue(issue.key, transition_to)
            logger.info("이슈 상태 전환: %s → %s", issue.key, transition_to)

        branch_name = generate_branch_name(issue, self._config.branch_naming)
        branch = self._gitlab.create_branch(
            branch_name=branch_name,
            ref=ref,
            issue_key=issue.key,
        )

        logger.info(
            "워크플로우 완료: 이슈 %s 생성 → 브랜치 %s 생성",
            issue.key,
            branch.name,
        )
        return WorkflowResult(
            issue=issue,
            branch=branch,
            message=(
                f"이슈 '{issue.key}'와 "
                f"브랜치 '{branch.name}'이(가) 성공적으로 생성되었습니다."
            ),
        )

    # ─── 워크플로우 3: 이슈 상태 전환만 ──────────────────────────────────

    def transition_issue(
        self,
        issue_key: str,
        target_status: str,
    ) -> WorkflowResult:
        """Jira 이슈의 상태를 전환합니다.

        Args:
            issue_key: Jira 이슈 키 (예: "SSCVE-123").
            target_status: 전환할 상태명 (예: "진행 중", "In Progress").

        Returns:
            상태가 전환된 이슈 정보.
        """
        issue = self._jira.transition_issue(issue_key, target_status)

        return WorkflowResult(
            issue=issue,
            message=(
                f"이슈 '{issue_key}' 상태가 "
                f"'{issue.status}'(으)로 전환되었습니다."
            ),
        )

    # ─── 유틸리티 ────────────────────────────────────────────────────────

    def get_available_transitions(self, issue_key: str) -> list[str]:
        """이슈에서 가능한 상태 전환 목록을 조회합니다.

        Args:
            issue_key: Jira 이슈 키.

        Returns:
            전환 가능한 상태명 목록.
        """
        transitions = self._jira.get_transitions(issue_key)
        return [t.name for t in transitions]

    def preview_branch_name(self, issue_key: str) -> str:
        """이슈에서 생성될 브랜치명을 미리보기합니다.

        Args:
            issue_key: Jira 이슈 키.

        Returns:
            생성될 브랜치명.
        """
        issue = self._jira.get_issue(issue_key)
        return generate_branch_name(issue, self._config.branch_naming)
