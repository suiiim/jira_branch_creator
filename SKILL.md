---
name: jira-branch-creator
description: >
  Jira 이슈를 관리(생성, 상태 전환)하고 GitLab에 브랜치를 자동 생성합니다.
  Jira 이슈 키(예: SSCVE-123)를 입력하면 이슈 타입과 요약을 기반으로
  브랜치 네이밍 컨벤션에 맞는 GitLab 브랜치를 생성합니다.
  이슈 생성 → 상태 전환 → 브랜치 생성까지 하나의 워크플로우로 실행 가능합니다.
  "jira 브랜치", "이슈 생성", "상태 전환", "branch from jira", "create issue"
  키워드에 반응합니다.
compatibility: Requires python3.12+ and requests library. Works on Windows, macOS, and Linux.
allowed-tools: Bash(python:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "2.0"
  python: "3.12+"
  pattern: "Facade + Service Layer"
---

# Jira Branch Creator

Jira 이슈 관리 및 GitLab 브랜치 자동 생성 Agent Skill입니다.

## 사전 요구사항

환경변수 설정:
- `JIRA_BASE_URL`: Jira 인스턴스 URL (예: https://myteam.atlassian.net)
- `JIRA_EMAIL`: Jira 로그인 이메일
- `JIRA_API_TOKEN`: Jira API 토큰
- `GITLAB_URL`: GitLab 인스턴스 URL (예: https://gitlab.example.com)
- `GITLAB_TOKEN`: GitLab Private Access Token
- `GITLAB_PROJECT_ID`: GitLab 프로젝트 ID

## 아키텍처

Facade + Service Layer 패턴을 사용합니다:

```
WorkflowFacade (고수준 워크플로우)
├── JiraService    (Jira REST API v3)
└── GitLabService  (GitLab REST API v4)
```

## 워크플로우

### 1. 기존 이슈에서 브랜치 생성

```bash
python main.py branch SSCVE-123
python main.py branch SSCVE-123 --ref main
```

### 2. 이슈 생성 + 브랜치 생성

```bash
python main.py create "로그인 오류 수정" --type Bug
python main.py create "사용자 프로필 추가" --type Story --transition "진행 중"
python main.py create "CI/CD 파이프라인 업데이트" --type Task -d "설명 텍스트"
```

### 3. 이슈 상태 전환

```bash
python main.py transition SSCVE-123 "진행 중"
python main.py transition SSCVE-123 "Done"
```

### 4. 유틸리티

```bash
python main.py preview SSCVE-123       # 브랜치명 미리보기
python main.py transitions SSCVE-123   # 가능한 상태 전환 조회
```

## 브랜치 네이밍 규칙

| 이슈 타입 | Prefix      | 예시                                    |
|-----------|-------------|----------------------------------------|
| Bug       | bugfix/     | bugfix/SSCVE-123-fix-login-error       |
| Story     | feature/    | feature/SSCVE-456-add-user-profile     |
| Task      | task/       | task/SSCVE-789-update-dependencies     |
| Epic      | epic/       | epic/SSCVE-101-payment-system          |
| Sub-task  | feature/    | feature/SSCVE-102-implement-api        |

자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)를 참조하세요.

## 커밋 컨벤션

[references/COMMIT_MESSAGE.md](references/COMMIT_MESSAGE.md)의 규칙을 따릅니다.

형식: `<type>: <제목(한국어, 50자 이내, 마침표 없이)>`

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서 수정 |
| `chore` | 설정, 패키지 등 기타 |

## 에지 케이스

- Jira 연결 실패 → API 토큰/URL 확인 안내
- 한글 요약 → 이슈 키만으로 브랜치명 생성
- 브랜치 이미 존재 → BranchAlreadyExistsError
- 상태 전환 불가 → TransitionNotFoundError + 가능한 전환 목록 안내
