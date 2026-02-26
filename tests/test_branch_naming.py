"""브랜치 네이밍 유틸리티 단위 테스트."""

import unittest

from jira_branch_creator.config import BranchNamingConfig
from jira_branch_creator.models.issue import JiraIssue
from jira_branch_creator.utils.branch_naming import generate_branch_name


class TestGenerateBranchName(unittest.TestCase):
    """generate_branch_name 함수 테스트."""

    def setUp(self) -> None:
        self.config = BranchNamingConfig()

    def _make_issue(
        self, key: str, summary: str, issue_type: str,
    ) -> JiraIssue:
        return JiraIssue(key=key, summary=summary, issue_type=issue_type)

    # ─── 이슈 타입별 prefix 테스트 ───────────────────────────────────────

    def test_bug_prefix(self) -> None:
        issue = self._make_issue("SSCVE-101", "Fix login error", "Bug")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "bugfix/SSCVE-101-fix-login-error")

    def test_story_prefix(self) -> None:
        issue = self._make_issue("SSCVE-202", "Add user profile page", "Story")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "feature/SSCVE-202-add-user-profile-page")

    def test_task_prefix(self) -> None:
        issue = self._make_issue("SSCVE-303", "Update CI/CD pipeline", "Task")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "task/SSCVE-303-update-ci-cd-pipeline")

    def test_epic_prefix(self) -> None:
        issue = self._make_issue("SSCVE-404", "Payment system", "Epic")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "epic/SSCVE-404-payment-system")

    def test_subtask_prefix(self) -> None:
        issue = self._make_issue("SSCVE-505", "Implement API", "Sub-task")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "feature/SSCVE-505-implement-api")

    def test_unknown_type_defaults_to_feature(self) -> None:
        issue = self._make_issue("SSCVE-606", "Something new", "CustomType")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "feature/SSCVE-606-something-new")

    # ─── 슬러그 변환 테스트 ──────────────────────────────────────────────

    def test_korean_only_summary(self) -> None:
        """한글만 있는 경우 이슈 키만 사용."""
        issue = self._make_issue("SSCVE-701", "로그인 기능 구현", "Story")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "feature/SSCVE-701")

    def test_mixed_korean_english(self) -> None:
        """한영 혼합 시 영문 부분만 슬러그로 사용."""
        issue = self._make_issue("SSCVE-702", "Add OAuth2 로그인", "Story")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "feature/SSCVE-702-add-oauth2")

    def test_special_characters(self) -> None:
        """특수문자는 하이픈으로 치환."""
        issue = self._make_issue("SSCVE-801", "Fix   multiple   spaces!!!", "Bug")
        result = generate_branch_name(issue, self.config)
        self.assertEqual(result, "bugfix/SSCVE-801-fix-multiple-spaces")

    def test_slug_max_length(self) -> None:
        """슬러그 최대 길이 제한."""
        long_summary = "a" * 100
        issue = self._make_issue("SSCVE-901", long_summary, "Task")
        result = generate_branch_name(issue, self.config)
        slug_part = result.split("/")[1].split("-", 2)[-1]
        self.assertLessEqual(len(slug_part), 50)

    def test_custom_max_slug_length(self) -> None:
        """커스텀 슬러그 길이 설정."""
        config = BranchNamingConfig(max_slug_length=10)
        issue = self._make_issue("SSCVE-902", "A very long summary text", "Task")
        result = generate_branch_name(issue, config)
        self.assertEqual(result, "task/SSCVE-902-a-very-lon")


class TestJiraIssueModel(unittest.TestCase):
    """JiraIssue 모델 테스트."""

    def test_from_api_response(self) -> None:
        data = {
            "key": "SSCVE-100",
            "fields": {
                "summary": "Test issue",
                "issuetype": {"name": "Bug"},
                "status": {"name": "To Do"},
            },
        }
        issue = JiraIssue.from_api_response(data)

        self.assertEqual(issue.key, "SSCVE-100")
        self.assertEqual(issue.summary, "Test issue")
        self.assertEqual(issue.issue_type, "Bug")
        self.assertEqual(issue.status, "To Do")
        self.assertEqual(issue.project_key, "SSCVE")

    def test_from_api_response_missing_fields(self) -> None:
        data = {"key": "SSCVE-200", "fields": {}}
        issue = JiraIssue.from_api_response(data)

        self.assertEqual(issue.key, "SSCVE-200")
        self.assertEqual(issue.summary, "")
        self.assertEqual(issue.issue_type, "")


if __name__ == "__main__":
    unittest.main()
