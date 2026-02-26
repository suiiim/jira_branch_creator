"""GitLab REST API 서비스.

GitLab 프로젝트에서 브랜치를 생성하는 기능을 제공합니다.
GitLab API v4 사용: https://docs.gitlab.com/ee/api/branches.html
"""

from __future__ import annotations

import logging

import requests

from jira_branch_creator.config import GitLabConfig
from jira_branch_creator.exceptions import BranchAlreadyExistsError, GitLabApiError
from jira_branch_creator.models.issue import BranchInfo

logger = logging.getLogger(__name__)


class GitLabService:
    """GitLab REST API를 캡슐화하는 서비스 클래스."""

    def __init__(self, config: GitLabConfig) -> None:
        self._config = config
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        """인증이 설정된 HTTP 세션을 생성합니다."""
        session = requests.Session()
        session.headers.update({
            "PRIVATE-TOKEN": self._config.token,
            "Content-Type": "application/json",
        })
        return session

    @property
    def _project_api_url(self) -> str:
        """프로젝트 API 기본 URL."""
        return (
            f"{self._config.base_url}/api/v4"
            f"/projects/{self._config.project_id}"
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """GitLab API 요청을 수행하고, 에러를 처리합니다."""
        url = f"{self._project_api_url}{path}"
        logger.debug("%s %s", method, url)

        try:
            resp = self._session.request(method, url, timeout=30, **kwargs)
        except requests.ConnectionError as e:
            raise GitLabApiError(f"GitLab 서버 연결 실패: {e}") from e
        except requests.Timeout as e:
            raise GitLabApiError("GitLab API 요청 시간 초과 (30초)") from e

        if resp.status_code == 400 and "already exists" in resp.text.lower():
            raise BranchAlreadyExistsError(
                f"브랜치가 이미 존재합니다: {kwargs.get('json', {}).get('branch', '')}"
            )

        if not resp.ok:
            body = resp.text[:200]
            raise GitLabApiError(
                f"GitLab API 오류 (HTTP {resp.status_code}): {body}",
                status_code=resp.status_code,
            )

        return resp.json()

    # ─── 브랜치 생성 ────────────────────────────────────────────────────

    def create_branch(
        self,
        branch_name: str,
        ref: str | None = None,
        issue_key: str = "",
    ) -> BranchInfo:
        """GitLab 프로젝트에 새 브랜치를 생성합니다.

        Args:
            branch_name: 생성할 브랜치명.
            ref: 기준 브랜치 (기본: 설정의 default_branch).
            issue_key: 연관된 Jira 이슈 키 (메타데이터용).

        Returns:
            생성된 브랜치 정보.

        Raises:
            BranchAlreadyExistsError: 동일한 이름의 브랜치가 이미 존재할 때.
            GitLabApiError: API 호출 실패 시.
        """
        ref = ref or self._config.default_branch

        data = self._request(
            "POST",
            "/repository/branches",
            json={"branch": branch_name, "ref": ref},
        )

        web_url = data.get("web_url", "")
        logger.info("브랜치 생성 완료: %s (ref: %s)", branch_name, ref)

        return BranchInfo(
            name=branch_name,
            ref=ref,
            issue_key=issue_key,
            web_url=web_url,
        )

    # ─── 브랜치 조회 ────────────────────────────────────────────────────

    def branch_exists(self, branch_name: str) -> bool:
        """브랜치가 존재하는지 확인합니다.

        Args:
            branch_name: 확인할 브랜치명.

        Returns:
            존재 여부.
        """
        url = f"{self._project_api_url}/repository/branches/{branch_name}"
        try:
            resp = self._session.get(url, timeout=30)
            return resp.status_code == 200
        except requests.RequestException:
            return False
