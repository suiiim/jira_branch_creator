# 🌿 Jira Branch Creator

> Jira 이슈가 생성되면 자동으로 로컬 Git 브랜치를 만들어주는 Agent Skill

[![Agent Skills](https://img.shields.io/badge/Agent_Skills-v1.2-blue)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## 📖 개요

**Jira Branch Creator**는 [Agent Skills](https://agentskills.io) 표준을 따르는 스킬로, Jira 이슈 정보를 기반으로 Git 브랜치를 자동 생성합니다.

두 가지 모드를 지원합니다:

- **단일 모드** — 이슈 키를 지정하여 즉시 브랜치 생성
- **감시 모드** — Jira 프로젝트를 폴링하여 새 이슈 발생 시 자동 브랜치 생성

## 📁 프로젝트 구조

```
jira_branch_creator/
├── SKILL.md                                # Agent Skill 정의 (메인 파일)
├── README.md                               # 이 파일
├── scripts/
│   ├── create_branch_from_jira.ps1         # ⭐ 단일 브랜치 생성 (Windows)
│   ├── create_branch_from_jira.sh          #    단일 브랜치 생성 (macOS/Linux)
│   ├── watch_jira.ps1                      # ⭐ 자동 감시 모드 (Windows)
│   ├── watch_jira.py                       #    자동 감시 모드 (Python, 크로스플랫폼)
│   ├── setup.ps1                           # ⭐ 초기 설정 (Windows)
│   ├── setup.sh                            #    초기 설정 (macOS/Linux)
│   └── test_validate.py                    #    스킬 유효성 검증 테스트
├── references/
│   ├── BRANCH_NAMING.md                    # 브랜치 네이밍 컨벤션 문서
│   └── COMMIT_MESSAGE.md                   # 커밋 메시지 컨벤션 문서
└── assets/
    └── config.template.json                # 설정 파일 템플릿
```

> ⭐ 표시된 파일이 **Windows 전용 PowerShell 스크립트**입니다.

---

## ⚡ Windows에서 시작하기

### Step 1. 사전 요구사항

| 도구       | 확인 명령              | 설치 방법                          |
|-----------|----------------------|-----------------------------------|
| Git         | `git --version`    | `winget install Git.Git`            |
| Python 3.12 | `python --version` | `winget install Python.Python.3.12` |

> `curl`은 Windows 10 이상에 기본 내장되어 있습니다.
> `jq`는 PowerShell 스크립트에서는 불필요합니다 (Invoke-RestMethod로 JSON을 직접 처리).

### Step 2. 환경변수 설정

PowerShell을 열고 다음 중 하나를 선택합니다:

**방법 A: 현재 세션에만 적용 (테스트용)**

```powershell
$env:JIRA_BASE_URL = "https://YOUR_DOMAIN.atlassian.net"
$env:JIRA_EMAIL = "your-email@example.com"
$env:JIRA_API_TOKEN = "your-api-token"
```

**방법 B: 영구 적용 (권장)**

```powershell
[System.Environment]::SetEnvironmentVariable("JIRA_BASE_URL", "https://YOUR_DOMAIN.atlassian.net", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_EMAIL", "your-email@example.com", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "your-api-token", "User")
```

> 설정 후 PowerShell을 재시작해야 반영됩니다.

**방법 C: Windows GUI로 설정**

1. `시작` → "환경 변수" 검색 → `시스템 환경 변수 편집` 클릭
2. `환경 변수` 버튼 클릭
3. `사용자 변수`에서 `새로 만들기` → 위 3개 변수 추가

> 💡 API 토큰은 [Atlassian API Token 관리](https://id.atlassian.com/manage-profile/security/api-tokens)에서 발급받으세요.

### Step 3. 설정 확인

```powershell
cd D:\git\suiiim\jira_branch_creator
.\scripts\setup.ps1
```

이 스크립트가 확인하는 것:
- ✅ Git, Python 설치 여부
- ✅ 환경변수 설정 여부
- ✅ Jira API 연결 테스트

### Step 4. PowerShell 실행 정책 설정 (처음 한 번만)

PowerShell 스크립트 실행이 차단되면 아래 명령을 실행합니다:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## 🚀 사용법 (Windows)

### 방법 1: 단일 이슈에서 브랜치 생성

```powershell
# Jira 이슈 키로 브랜치 생성 (기본 base: develop)
.\scripts\create_branch_from_jira.ps1 -IssueKey PROJ-123

# base 브랜치 지정
.\scripts\create_branch_from_jira.ps1 -IssueKey PROJ-123 -BaseBranch main
```

**실행 결과:**

```
========================================
  Jira Branch Creator
========================================

📋 Fetching issue PROJ-123 from Jira...
   Issue Key : PROJ-123
   Type      : Bug
   Summary   : Fix login error on mobile

🌿 Branch name: bugfix/PROJ-123-fix-login-error-on-mobile

📥 Fetching latest from origin...
🔀 Switching to develop...
🌱 Creating branch bugfix/PROJ-123-fix-login-error-on-mobile...

========================================
  ✅ Branch created successfully!
========================================
   Branch  : bugfix/PROJ-123-fix-login-error-on-mobile
   Based on: develop
========================================
```

### 방법 2: 자동 감시 모드

**PowerShell 버전:**

```powershell
# 기본 설정
.\scripts\watch_jira.ps1 -ProjectKey PROJ

# 상세 설정
.\scripts\watch_jira.ps1 -ProjectKey PROJ -BaseBranch main -PollInterval 15
```

**Python 버전 (크로스플랫폼):**

```powershell
$env:JIRA_PROJECT_KEY = "PROJ"
python scripts\watch_jira.py
```

**실행 결과:**

```
========================================
  Jira Branch Creator - Watch Mode
========================================
  Project       : PROJ
  Repo path     : D:\git\suiiim\jira_branch_creator
  Base branch   : develop
  Poll interval : 30s
========================================

👀 Scanning existing issues...
   Skipped 5 existing issue(s).

🔄 Watching for new issues... (Ctrl+C to stop)

[2026-02-24 14:32:15] 🆕 New issue detected!
    Key     : PROJ-456
    Type    : Story
    Summary : Add user profile page
    Branch  : feature/PROJ-456-add-user-profile-page
    ✅ Branch created successfully!
```

### 방법 3: AI 에이전트와 사용

Agent Skill을 지원하는 에이전트(Claude Code 등)에서:

```
"PROJ-123에서 브랜치 만들어줘"
"Jira 이슈 감시 시작해"
"PROJ-456 브랜치 생성해줘, base는 main으로"
```

---

## 🌿 브랜치 네이밍 규칙

| Jira Issue Type | Branch Prefix | 예시                                      |
|-----------------|---------------|------------------------------------------|
| Bug             | `bugfix/`     | `bugfix/PROJ-123-fix-login-error`        |
| Story           | `feature/`    | `feature/PROJ-456-add-user-profile`      |
| Task            | `task/`       | `task/PROJ-789-update-dependencies`      |
| Epic            | `epic/`       | `epic/PROJ-101-payment-system`           |
| Sub-task        | `feature/`    | `feature/PROJ-102-implement-api`         |

형식: `{prefix}/{ISSUE_KEY}-{summary-slug}`

> 자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md) 참조

## 📝 커밋 메시지 규칙

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `style` | UI/스타일 변경 (기능 무관) |
| `refactor` | 리팩토링 (기능/버그 변경 없음) |
| `docs` | 문서 수정 |
| `chore` | 설정, 패키지 등 기타 작업 |
| `remove` | 파일/코드 삭제 |
| `wip` | 작업 중 (임시 커밋) |

형식: `<type>: <제목(한국어, 50자 이내, 마침표 없이)>`

> 자세한 규칙은 [references/COMMIT_MESSAGE.md](references/COMMIT_MESSAGE.md) 참조

## 🧪 테스트

```powershell
python scripts\test_validate.py
```

검증 항목:
- Agent Skills 스펙 준수 (디렉토리 구조, frontmatter)
- SKILL.md name 필드 유효성
- Python 스크립트 구문 오류
- JSON 설정 파일 유효성
- 브랜치명 생성 로직 (한글, 특수문자, 공백 처리)

## ⚙️ 설정 옵션

| 환경변수           | 기본값      | 설명                          |
|-------------------|------------|-------------------------------|
| `JIRA_BASE_URL`   | (필수)      | Jira URL                     |
| `JIRA_EMAIL`      | (필수)      | Jira 이메일                   |
| `JIRA_API_TOKEN`  | (필수)      | Jira API 토큰                |
| `JIRA_PROJECT_KEY`| (입력받음)  | 감시할 프로젝트 키             |
| `REPO_PATH`       | 현재 디렉토리| Git 레포 경로                |
| `BASE_BRANCH`     | `develop`   | 기준 브랜치                   |
| `POLL_INTERVAL`   | `30`        | 폴링 간격 (초)                |

## 🔧 에지 케이스 처리

| 상황                          | 동작                                          |
|-------------------------------|----------------------------------------------|
| 브랜치가 이미 존재             | 에러 메시지 후 중단                              |
| Jira API 연결 실패             | 자격증명/URL 확인 안내                           |
| 한글만 있는 이슈 요약           | 이슈 키만으로 브랜치 생성 (`feature/PROJ-123`)   |
| base 브랜치 없음               | develop → main → master 순 폴백               |
| 실행 정책 차단                 | `Set-ExecutionPolicy RemoteSigned` 안내        |

## 🗂️ 스크립트별 OS 지원

| 스크립트                        | Windows | macOS/Linux |
|--------------------------------|---------|-------------|
| `create_branch_from_jira.ps1`  | ✅       | ❌          |
| `create_branch_from_jira.sh`   | ❌ (Git Bash로 가능) | ✅ |
| `watch_jira.ps1`               | ✅       | ❌          |
| `watch_jira.py`                | ✅       | ✅          |
| `setup.ps1`                    | ✅       | ❌          |
| `setup.sh`                     | ❌ (Git Bash로 가능) | ✅ |
| `test_validate.py`             | ✅       | ✅          |

## 📚 참고

- [Agent Skills 공식 사이트](https://agentskills.io)
- [Agent Skills 스펙](https://agentskills.io/specification)
- [Anthropic Skills GitHub](https://github.com/anthropics/skills)
- [Jira REST API 문서](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
