---
name: jira-branch-creator
description: >
  Jira 이슈에서 GitLab 브랜치를 자동 생성하는 CLI + 시스템 트레이 도구의 Claude Code 스킬.
  이슈 키(예: SSCVE-123)를 입력하면 이슈 타입과 요약 기반으로
  브랜치 네이밍 컨벤션에 맞는 브랜치를 생성합니다.
  시스템 트레이에서 백그라운드 폴링으로 새 이슈를 자동 감시합니다.
  "jira 브랜치", "이슈에서 브랜치", "branch from jira", "create branch"
  키워드에 반응합니다.
compatibility: Python 3.12+, requests, pystray, Pillow. Works on Windows (PowerShell), macOS, Linux. Designed for Claude Code.
allowed-tools: Bash(git:*) Bash(curl:*) Bash(python:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "2.1"
  python: "3.12+"
---

# Jira Branch Creator (Claude Code Skill)

Jira 이슈 관리 + GitLab 브랜치 자동 생성 스킬입니다.
CLI 단발 실행과 시스템 트레이 백그라운드 감시 모드를 지원합니다.

## 아키텍처 개요

이 프로젝트는 **Facade + Service Layer 패턴** 기반 패키지 구조입니다:

```
main.py (CLI) / tray.py (시스템 트레이)
  → WorkflowFacade          # 고수준 워크플로우 (Facade 패턴)
    → JiraService            # Jira REST API 래퍼 (Service Layer)
    → GitLabService          # GitLab API 래퍼 (Service Layer)
    → branch_naming utils    # 브랜치명 생성 유틸
```

핵심 패키지: `src/jira_branch_creator/`

| 디렉토리 | 역할 |
|----------|------|
| `config.py` | 환경변수 → frozen dataclass 설정 로드 (TrayConfig 포함) |
| `exceptions.py` | JiraBranchCreatorError 기반 예외 계층 |
| `tray.py` | 시스템 트레이 앱 (pystray 기반, 백그라운드 폴링 감시) |
| `facades/` | WorkflowFacade (Jira+GitLab 조합 워크플로우) |
| `models/` | 불변 DTO (JiraIssue, BranchInfo, TransitionInfo) |
| `services/` | JiraService, GitLabService (API 캡슐화) |
| `utils/` | branch_naming (prefix 결정 + slugify) |

## 사전 요구사항

환경변수 설정 (필수):
- `JIRA_BASE_URL`: Jira 인스턴스 URL (예: https://myteam.atlassian.net)
- `JIRA_EMAIL`: Jira 로그인 이메일
- `JIRA_API_TOKEN`: Jira API 토큰
- `GITLAB_URL`: GitLab 인스턴스 URL
- `GITLAB_TOKEN`: GitLab Personal Access Token
- `GITLAB_PROJECT_ID`: GitLab 프로젝트 ID

트레이 설정 (선택):
- `TRAY_POLL_INTERVAL`: 폴링 간격 초 (기본: 30)
- `TRAY_AUTOSTART`: 로그인 시 자동 시작 (기본: false)
- `TRAY_NOTIFY`: 브랜치 생성 시 시스템 알림 (기본: true)

초기 설정 확인:
- Windows: `.\scripts\setup.ps1`
- macOS/Linux: `bash scripts/setup.sh`

## 워크플로우

### 시스템 트레이 모드 (백그라운드 감시)

```bash
# 트레이 앱 실행
jira-branch-tray

# 또는 직접 실행
python -m jira_branch_creator.tray
```

트레이 앱 동작:
1. 시스템 트레이에 아이콘 표시 (감시 중/일시정지 상태 구분)
2. 설정된 간격으로 Jira 새 이슈 폴링
3. 새 이슈 발견 시 자동으로 GitLab 브랜치 생성 (GitLabService 사용)
4. 시스템 알림으로 결과 표시 (Windows toast notification)
5. 우클릭 메뉴: 시작/일시정지/종료, 폴링 간격 조정, 자동 시작 토글

### CLI 모드 (단발 실행)

```bash
python main.py branch SSCVE-123          # 이슈에서 브랜치 생성
python main.py create "이슈 제목" --type Bug  # 이슈 생성 + 브랜치 생성
python main.py transition SSCVE-123 "진행 중" # 이슈 상태 전환
python main.py preview SSCVE-123              # 브랜치명 미리보기
python main.py transitions SSCVE-123          # 가능한 상태 전환 조회
```

### 경량 헬퍼 스크립트 (이 스킬 전용)

`scripts/` 폴더의 헬퍼는 Claude Code가 빠르게 단일 작업을 수행할 때 사용합니다.

| 파일 | 설명 |
|------|------|
| `validate_issue_key.py` | 이슈 키 형식 및 프로젝트 키(SSCVE) 유효성 검사 |
| `get_issue_info.py` | Jira API로 단일 이슈 정보 조회 후 JSON 출력 |
| `make_branch_name.py` | 이슈 타입 + 요약으로 브랜치명 생성 |

## 브랜치 네이밍 규칙

자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)를 참조하세요.

| 이슈 타입 | Prefix | 예시 |
|-----------|--------|------|
| Bug | bugfix/ | bugfix/SSCVE-123-fix-login-error |
| Story | feature/ | feature/SSCVE-456-add-user-profile |
| Task | task/ | task/SSCVE-789-update-dependencies |
| Epic | epic/ | epic/SSCVE-101-payment-system |
| Subtask | feature/ | feature/SSCVE-102-implement-api |

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
| `remove` | 파일/코드 삭제 |

커밋 메시지는 항상 3가지 후보를 제시하고 사용자 승인 후 commit & push 합니다.

## 에지 케이스

- 이미 같은 이름의 브랜치 존재 → `BranchAlreadyExistsError` 후 건너뜀 (트레이 모드에서는 알림)
- Jira 연결 실패 → `JiraApiError` (트레이 모드에서는 아이콘 상태 변경 + 알림)
- GitLab 연결 실패 → `GitLabApiError`
- 한글 요약 → 슬러그가 빈 경우 이슈 키만으로 브랜치명 생성
- 환경변수 미설정 → `ConfigError` (누락 변수 명시)
- 트레이 앱 비정상 종료 → 다음 실행 시 이전 상태 파일로 중복 방지
