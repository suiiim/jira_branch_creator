---
name: jira-branch-creator
description: >
  SolidStep CVE Core 프로젝트(SSCVE)의 Jira 이슈에서 로컬 Git 브랜치를 자동으로 생성합니다.
  Jira 이슈 키(예: SSCVE-123)를 입력하면 이슈 타입과 요약을 기반으로
  브랜치 네이밍 컨벤션에 맞는 브랜치를 생성합니다.
  SSCVE 프로젝트 이슈에만 적용되며, 다른 프로젝트 키 입력 시 오류가 발생합니다.
  "jira 브랜치", "이슈에서 브랜치", "branch from jira", "create branch"
  키워드에 반응합니다.
compatibility: Requires git and python3.12+. Works on Windows (PowerShell), macOS, and Linux. Designed for Claude Code.
allowed-tools: Bash(git:*) Bash(curl:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "1.2"
  python: "3.12+"
---

# Jira Branch Creator

Jira 이슈 정보를 가져와서 로컬 Git 브랜치를 자동 생성하는 스킬입니다.

## 사전 요구사항

1. 환경변수 설정:
   - `JIRA_BASE_URL`: Jira 인스턴스 URL (예: https://myteam.atlassian.net)
   - `JIRA_EMAIL`: Jira 로그인 이메일
   - `JIRA_API_TOKEN`: Jira API 토큰 (https://id.atlassian.com/manage-profile/security/api-tokens)
2. 초기 설정 확인:
   - Windows: `.\scripts\setup.ps1`
   - macOS/Linux: `bash scripts/setup.sh`

## 워크플로우

### 방법 1: 단일 이슈에서 브랜치 생성

사용자가 "SSCVE-123에서 브랜치 만들어줘"라고 하면:

1. Jira API로 이슈 정보 조회
2. 이슈 타입에 따라 prefix 결정 (Bug → bugfix/, Story → feature/, Task → task/)
3. 브랜치명 생성: `{prefix}/{이슈키}-{요약-슬러그}`
4. base 브랜치(develop)에서 checkout 후 새 브랜치 생성

**실행 (OS별):**
```powershell
# Windows PowerShell
.\scripts\create_branch_from_jira.ps1 -IssueKey SSCVE-123
```
```bash
# macOS / Linux
bash scripts/create_branch_from_jira.sh SSCVE-123
```

### 방법 2: 자동 감시 (폴링 모드)

새 Jira 이슈가 생성될 때마다 자동으로 브랜치를 생성합니다.

**실행 (OS별):**
```powershell
# Windows PowerShell
.\scripts\watch_jira.ps1 -ProjectKey SSCVE
```
```bash
# macOS / Linux (또는 Windows에서 python 사용)
python scripts/watch_jira.py
```

## 브랜치 네이밍 규칙

자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)를 참조하세요.

| 이슈 타입 | Prefix      | 예시                                    |
|-----------|-------------|----------------------------------------|
| Bug       | bugfix/     | bugfix/SSCVE-123-fix-login-error       |
| Story     | feature/    | feature/SSCVE-456-add-user-profile     |
| Task      | task/       | task/SSCVE-789-update-dependencies     |
| Epic      | epic/       | epic/SSCVE-101-payment-system          |
| Subtask   | feature/    | feature/SSCVE-102-implement-api        |

## 커밋 방법

변경 사항을 커밋할 때는 [references/COMMIT_MESSAGE.md](references/COMMIT_MESSAGE.md)의 규칙을 따릅니다.

### 기본 형식

```
<type>: <제목>

[본문 - 선택]
```

### 커밋 타입

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

### 커밋 예시

```bash
# 새 기능 추가
git add .
git commit -m "feat: SSCVE 이슈에서 브랜치 자동 생성 기능 추가"

# 버그 수정
git commit -m "fix: 한글 이슈 요약 시 브랜치명 생성 오류 수정"

# 문서 수정
git commit -m "docs: README 환경변수 설정 방법 업데이트"

# 스크립트 수정
git commit -m "refactor: 브랜치 네이밍 로직 함수 분리"
```

### 제목 작성 규칙

- 한국어로 작성
- 타입 뒤에 콜론 + 공백 → `feat: `
- 마침표 없이 끝내기
- 50자 이내 권장
- 명령형 또는 명사형으로 작성 → "추가함" ❌ / "추가" ✅

## 에지 케이스

- **SSCVE 외 프로젝트 키 입력 시** → 즉시 오류 메시지 후 중단
- 이미 같은 이름의 브랜치가 존재하면 → 에러 메시지 후 중단
- Jira 연결 실패 → API 토큰/URL 확인 안내
- 한글 요약 → 영문 슬러그가 비는 경우 이슈 키만으로 브랜치명 생성
- base 브랜치가 없으면 → main 또는 master로 폴백
