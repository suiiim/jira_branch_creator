---
name: jira-branch-creator
description: >
  Jira 이슈 관리 및 GitLab 브랜치 자동 생성 CLI 도구.
  이슈 조회/생성, 상태 전환, 브랜치 자동 생성을 하나의 워크플로우로 제공합니다.
  "jira 브랜치", "이슈에서 브랜치", "branch from jira", "create branch",
  "이슈 생성", "상태 전환" 키워드에 반응합니다.
compatibility: Python 3.12+, requests 라이브러리. Windows/macOS/Linux.
allowed-tools: Bash(python:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "2.0"
  python: "3.12+"
---

# Jira Branch Creator

Jira 이슈를 관리하고 GitLab 브랜치를 자동 생성하는 CLI 도구입니다.

## 아키텍처

### 디자인 패턴

이 프로젝트는 다음 패턴을 적용하고 있습니다:

| 패턴 | 적용 위치 | 역할 |
|------|----------|------|
| **Facade** | `facades/workflow_facade.py` | Jira + GitLab 서비스를 조합한 고수준 워크플로우 |
| **Service Layer** | `services/jira_service.py`, `gitlab_service.py` | 외부 API 캡슐화, HTTP 세션/에러 관리 |
| **DTO (frozen dataclass)** | `models/issue.py` | 불변 데이터 전달 객체 |
| **Factory Method** | `JiraIssue.from_api_response()` 등 | API 응답 → 모델 변환 |
| **Exception Hierarchy** | `exceptions.py` | 계층적 커스텀 예외 |
| **경량 Command** | `main.py` handlers dict | CLI 서브커맨드 → 핸들러 매핑 |

### 프로젝트 구조

```
jira_branch_creator/
├── main.py                           # CLI 진입점 (argparse)
├── src/jira_branch_creator/          # 패키지 루트
│   ├── config.py                     # 환경변수 → frozen dataclass 설정
│   ├── exceptions.py                 # 예외 계층 (JiraBranchCreatorError 루트)
│   ├── facades/
│   │   └── workflow_facade.py        # Facade: 이슈 조회 → 브랜치 생성 워크플로우
│   ├── models/
│   │   └── issue.py                  # DTO: JiraIssue, BranchInfo, TransitionInfo 등
│   ├── services/
│   │   ├── jira_service.py           # Jira REST API v3 래퍼
│   │   └── gitlab_service.py         # GitLab API v4 래퍼
│   └── utils/
│       └── branch_naming.py          # 브랜치 네이밍 로직 (prefix + slugify)
├── tests/                            # 테스트
├── scripts/                          # 자동화 스크립트 (레거시 + 유틸리티)
└── references/                       # 컨벤션 문서 (브랜치명, 커밋, 로그)
```

### 레이어 흐름

```
CLI (main.py)
  → WorkflowFacade (facades/)
    → JiraService (services/)  ←→ Jira REST API
    → GitLabService (services/) ←→ GitLab API
    → branch_naming (utils/)
  → 결과 출력
```

### 데이터 흐름

- 모든 모델(`JiraIssue`, `BranchInfo` 등)은 `frozen=True` dataclass로 불변
- API 응답은 `from_api_response()` 팩토리 메서드로 모델 변환
- 설정은 `AppConfig` → `JiraConfig` / `GitLabConfig` / `BranchNamingConfig`로 계층 분리

### 예외 계층

```
JiraBranchCreatorError (루트)
├── ConfigError                 # 환경변수 누락 등
├── JiraApiError                # Jira API 실패
│   ├── IssueNotFoundError      # 이슈 없음 (404)
│   └── TransitionNotFoundError # 상태 전환 불가
├── GitLabApiError              # GitLab API 실패
└── BranchAlreadyExistsError    # 브랜치 중복
```

## 사전 요구사항

환경변수 설정 (필수):
- `JIRA_BASE_URL`: Jira 인스턴스 URL
- `JIRA_EMAIL`: Jira 로그인 이메일
- `JIRA_API_TOKEN`: Jira API 토큰
- `GITLAB_URL`: GitLab 인스턴스 URL
- `GITLAB_TOKEN`: GitLab Personal Access Token
- `GITLAB_PROJECT_ID`: GitLab 프로젝트 ID

선택:
- `JIRA_PROJECT_KEY` (기본: `SSCVE`)
- `GITLAB_DEFAULT_BRANCH` (기본: `develop`)
- `BRANCH_MAX_SLUG_LENGTH` (기본: `50`)

## CLI 사용법

```bash
# 기존 이슈에서 브랜치 생성
python main.py branch SSCVE-123

# 이슈 생성 + 브랜치 생성
python main.py create "이슈 제목" --type Bug

# 이슈 상태 전환
python main.py transition SSCVE-123 "진행 중"

# 브랜치명 미리보기
python main.py preview SSCVE-123

# 가능한 상태 전환 조회
python main.py transitions SSCVE-123
```

## 코드 수정 가이드

### 새로운 서비스 추가 시

1. `services/` 아래에 서비스 클래스 생성 (기존 패턴 따라 `_build_session`, `_request` 구현)
2. 필요한 모델을 `models/issue.py`에 frozen dataclass로 추가
3. `WorkflowFacade`에 서비스를 주입하고 워크플로우 메서드 추가
4. `main.py`에 CLI 서브커맨드와 핸들러 추가

### 예외 추가 시

- 반드시 `JiraBranchCreatorError` 하위에 정의
- API 관련이면 해당 서비스 예외(`JiraApiError`, `GitLabApiError`) 상속

### 브랜치 네이밍 규칙 변경 시

- `utils/branch_naming.py`의 `_resolve_prefix()`, `_slugify()` 수정
- `BranchNamingConfig`의 `prefix_map` 설정으로 오버라이드 가능
- 규칙 변경 후 `references/BRANCH_NAMING.md`도 동기화

## 컨벤션

- 브랜치 네이밍: [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)
- 커밋 메시지: [references/COMMIT_MESSAGE.md](references/COMMIT_MESSAGE.md)
- 로그 포맷: [references/LOG_FORMAT.md](references/LOG_FORMAT.md)

## 커밋 컨벤션 요약

형식: `<type>: <제목(한국어, 50자 이내, 마침표 없이)>`

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서 수정 |
| `chore` | 설정, 패키지 등 기타 |
| `remove` | 파일/코드 삭제 |

커밋 메시지는 항상 3가지 후보를 제시하고 사용자 승인 후 commit & push 합니다.
