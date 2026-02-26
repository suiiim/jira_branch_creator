# 🌿 Jira Branch Creator v2.0

> Jira 이슈 관리(생성/상태 전환) 및 GitLab 브랜치 자동 생성 도구

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![Pattern](https://img.shields.io/badge/pattern-Facade%20%2B%20Service%20Layer-green)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## 📖 개요

**Jira Branch Creator**는 Jira REST API와 GitLab REST API를 조합하여 개발 워크플로우를 자동화합니다.

**핵심 기능:**
- Jira 이슈 생성 및 상태 전환
- Jira 이슈 기반 GitLab 원격 브랜치 자동 생성
- 이슈 생성 → 상태 전환 → 브랜치 생성 워크플로우 자동화

## 🏗️ 아키텍처

Facade + Service Layer 패턴을 사용합니다:

```
main.py (CLI)
    └── WorkflowFacade (고수준 워크플로우 조합)
            ├── JiraService    (Jira REST API v3 캡슐화)
            └── GitLabService  (GitLab REST API v4 캡슐화)
```

## 📁 프로젝트 구조

```
jira_branch_creator/
├── src/jira_branch_creator/           # 소스 코드
│   ├── __init__.py
│   ├── config.py                      # 환경변수 기반 설정 로드
│   ├── exceptions.py                  # 커스텀 예외 정의
│   ├── models/
│   │   └── issue.py                   # 데이터 모델 (JiraIssue, BranchInfo 등)
│   ├── services/
│   │   ├── jira_service.py            # Jira API 서비스
│   │   └── gitlab_service.py          # GitLab API 서비스
│   ├── facades/
│   │   └── workflow_facade.py         # 워크플로우 Facade
│   └── utils/
│       └── branch_naming.py           # 브랜치 네이밍 유틸리티
├── tests/                             # 단위 테스트
│   └── test_branch_naming.py
├── scripts/                           # 레거시 스크립트 (v1 호환)
├── references/                        # 컨벤션 문서
│   ├── BRANCH_NAMING.md
│   └── COMMIT_MESSAGE.md
├── assets/
│   └── config.template.json           # 설정 템플릿
├── main.py                            # CLI 진입점
├── SKILL.md                           # Agent Skill 정의
├── pyproject.toml                     # 프로젝트 설정
└── README.md
```

## ⚡ 시작하기

### Step 1. 의존성 설치

```bash
cd D:\git\suiiim\jira_branch_creator
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

### Step 2. 환경변수 설정

**PowerShell (영구 적용):**

```powershell
# Jira 설정
[System.Environment]::SetEnvironmentVariable("JIRA_BASE_URL", "https://YOUR_DOMAIN.atlassian.net", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_EMAIL", "your-email@example.com", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "your-jira-api-token", "User")

# GitLab 설정
[System.Environment]::SetEnvironmentVariable("GITLAB_URL", "https://gitlab.example.com", "User")
[System.Environment]::SetEnvironmentVariable("GITLAB_TOKEN", "your-gitlab-private-token", "User")
[System.Environment]::SetEnvironmentVariable("GITLAB_PROJECT_ID", "123", "User")
```

**Bash:**

```bash
export JIRA_BASE_URL="https://YOUR_DOMAIN.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-jira-api-token"
export GITLAB_URL="https://gitlab.example.com"
export GITLAB_TOKEN="your-gitlab-private-token"
export GITLAB_PROJECT_ID="123"
```

### Step 3. 테스트

```bash
python -m pytest tests/ -v
```

## 🚀 사용법

### 기존 이슈에서 브랜치 생성

```bash
python main.py branch SSCVE-123
python main.py branch SSCVE-123 --ref main
```

### 이슈 생성 + 브랜치 생성

```bash
# 기본 (Task 타입)
python main.py create "CI/CD 파이프라인 업데이트"

# Bug 이슈 생성
python main.py create "로그인 오류 수정" --type Bug

# 이슈 생성 + 상태 전환 + 브랜치 생성
python main.py create "사용자 프로필 추가" --type Story --transition "진행 중"

# 설명과 레이블 포함
python main.py create "OAuth2 연동" --type Story -d "Google OAuth2 연동" -l backend auth
```

### 이슈 상태 전환

```bash
python main.py transition SSCVE-123 "진행 중"
python main.py transition SSCVE-123 "Done"
```

### 유틸리티

```bash
# 브랜치명 미리보기 (실제 생성 없이)
python main.py preview SSCVE-123

# 가능한 상태 전환 조회
python main.py transitions SSCVE-123

# 상세 로그
python main.py -v branch SSCVE-123
```

## 🌿 브랜치 네이밍 규칙

| Jira Issue Type | Branch Prefix | 예시                                    |
|-----------------|-------------|----------------------------------------|
| Bug             | `bugfix/`   | `bugfix/SSCVE-123-fix-login-error`     |
| Story           | `feature/`  | `feature/SSCVE-456-add-user-profile`   |
| Task            | `task/`     | `task/SSCVE-789-update-dependencies`   |
| Epic            | `epic/`     | `epic/SSCVE-101-payment-system`        |
| Sub-task        | `feature/`  | `feature/SSCVE-102-implement-api`      |

형식: `{prefix}/{ISSUE_KEY}-{summary-slug}`

## ⚙️ 환경변수

| 환경변수                   | 필수 | 기본값      | 설명                     |
|---------------------------|------|-----------|--------------------------|
| `JIRA_BASE_URL`           | ✅   |           | Jira 인스턴스 URL         |
| `JIRA_EMAIL`              | ✅   |           | Jira 이메일               |
| `JIRA_API_TOKEN`          | ✅   |           | Jira API 토큰             |
| `GITLAB_URL`              | ✅   |           | GitLab 인스턴스 URL       |
| `GITLAB_TOKEN`            | ✅   |           | GitLab Private Token      |
| `GITLAB_PROJECT_ID`       | ✅   |           | GitLab 프로젝트 ID        |
| `JIRA_PROJECT_KEY`        |      | `SSCVE`   | Jira 프로젝트 키          |
| `GITLAB_DEFAULT_BRANCH`   |      | `develop` | 기준 브랜치               |
| `BRANCH_MAX_SLUG_LENGTH`  |      | `50`      | 슬러그 최대 길이          |

## 🔧 에러 처리

| 에러                        | 설명                              |
|----------------------------|----------------------------------|
| `ConfigError`              | 필수 환경변수 미설정               |
| `JiraApiError`             | Jira API 호출 실패                |
| `IssueNotFoundError`       | 이슈를 찾을 수 없음               |
| `TransitionNotFoundError`  | 해당 상태로 전환 불가 (가능 목록 안내) |
| `GitLabApiError`           | GitLab API 호출 실패              |
| `BranchAlreadyExistsError` | 동일 브랜치 이미 존재              |
