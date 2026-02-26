"""Jira REST API 서비스.

이슈 조회, 생성, 상태 전환 기능을 제공합니다.
Jira REST API v3 사용: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

from __future__ import annotations

import logging

import requests

from jira_branch_creator.config import JiraConfig
from jira_branch_creator.exceptions import (
    IssueNotFoundError,
    JiraApiError,
    TransitionNotFoundError,
)
from jira_branch_creator.models.issue import (
    CreateIssueRequest,
    JiraIssue,
    TransitionInfo,
)

logger = logging.getLogger(__name__)


class JiraService:
    """Jira REST API를 캡슐화하는 서비스 클래스."""

    def __init__(self, config: JiraConfig) -> None:
        self._config = config
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        """인증이 설정된 HTTP 세션을 생성합니다."""
        session = requests.Session()
        session.auth = (self._config.email, self._config.api_token)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        return session

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Jira API 요청을 수행하고, 에러를 처리합니다."""
        url = f"{self._config.base_url}{path}"
        logger.debug("%s %s", method, url)

        try:
            resp = self._session.request(method, url, timeout=30, **kwargs)
        except requests.ConnectionError as e:
            raise JiraApiError(f"Jira 서버 연결 실패: {e}") from e
        except requests.Timeout as e:
            raise JiraApiError("Jira API 요청 시간 초과 (30초)") from e

        if resp.status_code == 404:
            raise IssueNotFoundError(
                f"리소스를 찾을 수 없습니다: {path}",
                status_code=404,
            )
        if not resp.ok:
            body = resp.text[:200]
            raise JiraApiError(
                f"Jira API 오류 (HTTP {resp.status_code}): {body}",
                status_code=resp.status_code,
            )

        if resp.status_code == 204:
            return {}
        return resp.json()

    # ─── 이슈 조회 ──────────────────────────────────────────────────────

    def get_issue(self, issue_key: str) -> JiraIssue:
        """Jira 이슈를 조회합니다.

        Args:
            issue_key: 이슈 키 (예: "SSCVE-123").

        Returns:
            조회된 이슈 정보.

        Raises:
            IssueNotFoundError: 이슈를 찾을 수 없을 때.
            JiraApiError: API 호출 실패 시.
        """
        data = self._request(
            "GET",
            f"/rest/api/3/issue/{issue_key}",
            params={"fields": "summary,issuetype,status"},
        )
        logger.info("이슈 조회 완료: %s", issue_key)
        return JiraIssue.from_api_response(data)

    # ─── 이슈 생성 ──────────────────────────────────────────────────────

    def create_issue(self, request: CreateIssueRequest) -> JiraIssue:
        """새로운 Jira 이슈를 생성합니다.

        Args:
            request: 이슈 생성 요청 정보.

        Returns:
            생성된 이슈 정보.

        Raises:
            JiraApiError: API 호출 실패 시.
        """
        payload = {
            "fields": {
                "project": {"key": request.project_key},
                "summary": request.summary,
                "issuetype": {"name": request.issue_type},
            }
        }

        if request.description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": request.description}
                        ],
                    }
                ],
            }

        if request.labels:
            payload["fields"]["labels"] = request.labels

        data = self._request("POST", "/rest/api/3/issue", json=payload)
        issue_key = data["key"]
        logger.info("이슈 생성 완료: %s", issue_key)

        return self.get_issue(issue_key)

    # ─── 상태 전환 ──────────────────────────────────────────────────────

    def get_transitions(self, issue_key: str) -> list[TransitionInfo]:
        """이슈에서 가능한 상태 전환 목록을 조회합니다.

        Args:
            issue_key: 이슈 키 (예: "SSCVE-123").

        Returns:
            가능한 상태 전환 목록.
        """
        data = self._request(
            "GET",
            f"/rest/api/3/issue/{issue_key}/transitions",
        )
        transitions = [
            TransitionInfo.from_api_response(t)
            for t in data.get("transitions", [])
        ]
        logger.info(
            "이슈 %s 전환 목록 조회: %s",
            issue_key,
            [t.name for t in transitions],
        )
        return transitions

    def transition_issue(self, issue_key: str, target_status: str) -> JiraIssue:
        """이슈의 상태를 전환합니다.

        Args:
            issue_key: 이슈 키 (예: "SSCVE-123").
            target_status: 전환할 상태명 (예: "진행 중", "In Progress").

        Returns:
            상태가 전환된 이슈 정보.

        Raises:
            TransitionNotFoundError: 해당 상태로 전환할 수 없을 때.
            JiraApiError: API 호출 실패 시.
        """
        transitions = self.get_transitions(issue_key)
        target_lower = target_status.lower()

        matched = next(
            (t for t in transitions if t.name.lower() == target_lower),
            None,
        )

        if not matched:
            available = [f"'{t.name}'" for t in transitions]
            raise TransitionNotFoundError(
                f"이슈 {issue_key}에서 '{target_status}' 전환을 찾을 수 없습니다.\n"
                f"  가능한 전환: {', '.join(available) or '없음'}",
            )

        self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": matched.id}},
        )
        logger.info("이슈 %s 상태 전환 완료: %s", issue_key, target_status)

        return self.get_issue(issue_key)
