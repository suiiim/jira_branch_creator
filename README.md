# Jira Branch Creator

INTQA 처리중 이슈를 SSCVE에 자동 동기화하고, SSCVE 할일/진행중 이슈에서
로컬 git flow feature 브랜치를 자동 생성하는 스크립트입니다.

---

## 사전 요구사항

### 1. Python 3.9 이상

```bash
python --version  # Python 3.9.x 이상 확인
```

### 2. 환경변수 설정 (필수)

아래 3가지 환경변수가 반드시 설정되어 있어야 합니다.

| 환경변수 | 설명 | 예시 |
|----------|------|------|
| `JIRA_BASE_URL` | Jira 인스턴스 URL | `https://yourteam.atlassian.net` |
| `JIRA_EMAIL` | Jira 로그인 이메일 | `your-email@example.com` |
| `JIRA_API_TOKEN` | Jira API 토큰 | `ATATT3x...` |

**PowerShell (영구 설정):**

```powershell
[System.Environment]::SetEnvironmentVariable("JIRA_BASE_URL", "https://yourteam.atlassian.net", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_EMAIL", "your-email@example.com", "User")
[System.Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "your-api-token", "User")
```

설정 후 터미널을 재시작해야 적용됩니다.

**Bash (현재 세션만):**

```bash
export JIRA_BASE_URL="https://yourteam.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
```

### 3. git-flow 설치 확인

Phase 2에서 `C:\workspace\c-project` 저장소에 git flow 명령을 실행합니다.

```bash
git flow version  # git-flow version 1.12.3 (AVH Edition) 등 출력 확인
```

---

## 실행 방법

### 기본 실행

프로젝트 루트에서 아래 명령을 실행합니다.

```bash
python scripts/sync_and_create_branches.py
```

실행하면 먼저 설정 프롬프트가 표시됩니다. SSCVE 에픽 중 최근 생성된 5개를 자동으로 조회해서 보여줍니다:

```
  [상위 항목 최근 에픽 5개]
    SSCVE-2652  2.0.33-fix
    SSCVE-2651  2.0.33-dev
    SSCVE-2561  2.0.32-fix
    SSCVE-2560  2.0.32-dev
    SSCVE-2327  2.0.31-fix
  선택 (SSCVE 번호 입력, Enter = SSCVE-2561):
  수정 버전 [2.0.32]:
```

**상위 항목 선택 방법:**
- **Enter를 그냥 누르면** 괄호 안의 기본값이 사용됩니다.
- **목록에 있는 SSCVE 번호를 입력하면** 해당 에픽이 상위 항목으로 지정됩니다.
- **목록에 없는 번호를 직접 입력해도** 됩니다 (예: `SSCVE-2800`).
- 입력한 값은 해당 실행에만 적용됩니다 (다음 실행 시 다시 기본값으로 돌아옴).

예시: 상위 항목을 `SSCVE-2652`로, 수정 버전을 `2.0.33`으로 변경하는 경우:

```
  선택 (SSCVE 번호 입력, Enter = SSCVE-2561): SSCVE-2652
  수정 버전 [2.0.32]: 2.0.33
```

### dry-run 모드 (브랜치 생성 없이 목록만 확인)

Phase 2에서 실제로 브랜치를 생성하지 않고 생성 예정 목록만 출력합니다.
Phase 1(SSCVE 이슈 생성)은 dry-run에 관계없이 실제로 실행됩니다.

```bash
python scripts/sync_and_create_branches.py --dry-run
```

---

## 실행 흐름

### Phase 1 — INTQA → SSCVE 이슈 동기화

1. INTQA 프로젝트에서 **현재 사용자 할당 + 처리중** 이슈를 조회합니다.
2. 각 이슈에 `문의대응 처리 이슈` 링크가 이미 연결되어 있으면 → **SKIP**
3. 없으면 → SSCVE에 버그 이슈를 생성하고 `문의대응 처리 이슈` 링크를 연결합니다.

SSCVE 이슈 생성 시 자동으로 지정되는 필드:

| 필드 | 값 | 변경 방법 |
|------|-----|-----------|
| 이슈 유형 | 버그 | 코드 고정 |
| 담당자 | 하수임 | 코드 고정 |
| 상위 항목 | `SSCVE-2561` | 실행 시 프롬프트 |
| 수정 버전 | `2.0.32` | 실행 시 프롬프트 |

### Phase 2 — SSCVE → git flow feature 브랜치 생성

1. `C:\workspace\c-project` 저장소의 `develop`, `release` 브랜치를 먼저 git pull합니다.
   - 현재 체크아웃된 브랜치인 경우 `git pull`, 아닌 경우 `git fetch origin {branch}:{branch}` 실행
   - 원격에 해당 브랜치가 없으면 건너뜁니다.
2. SSCVE 프로젝트에서 **현재 사용자 할당 + 할일 또는 진행중 + 이슈 유형이 버그**인 이슈를 조회합니다.
3. `C:\workspace\c-project` 로컬 저장소에 해당 브랜치가 이미 존재하면 → **SKIP**
4. 없으면 → `git flow feature start SSCVE-XXXX` 명령을 실행합니다.

---

## 브랜치 네이밍 규칙

| 형식 | 예시 |
|------|------|
| `feature/{ISSUE_KEY}` | `feature/SSCVE-2704` |

---

## 로그

| 항목 | 내용 |
|------|------|
| 저장 위치 | `%USERPROFILE%\Desktop\jira-sync-logs\` |
| 파일명 | `sync_and_branch_YYYYMMDD.log` (일별 자동 생성) |
| 포맷 | `[YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE` |
| 레벨 | `INFO` / `OK` / `SKIP` / `WARN` / `ERROR` |

로그는 콘솔과 파일에 동시에 출력됩니다.

실행 예시 출력:

```
[2026-03-04 10:01:42] [INFO ] INTQA -> SSCVE 동기화 + git flow 브랜치 생성 시작
[2026-03-04 10:01:42] [INFO ] 설정 - 상위 항목: SSCVE-2561, 수정 버전: 2.0.32
[2026-03-04 10:01:42] [INFO ] ==================================================
[2026-03-04 10:01:42] [INFO ] [Phase 1] INTQA 처리중 -> SSCVE 이슈 생성
[2026-03-04 10:01:42] [INFO ] ==================================================
[2026-03-04 10:01:42] [INFO ] INTQA 처리중 이슈: 2건 조회됨
[2026-03-04 10:01:42] [SKIP ] [INTQA-4634] 이미 연결된 SSCVE 이슈 존재: SSCVE-2743
[2026-03-04 10:01:42] [INFO ] Phase 1 완료: 생성 0건 / 건너뜀 2건
[2026-03-04 10:01:42] [INFO ] ==================================================
[2026-03-04 10:01:42] [INFO ] [Phase 2] SSCVE '할일/진행중' -> git flow feature 브랜치 생성
[2026-03-04 10:01:42] [INFO ] ==================================================
[2026-03-04 10:01:43] [INFO ] SSCVE '할일 + 진행중' 이슈: 3건 조회됨
[2026-03-04 10:01:43] [INFO ] [SSCVE-2704] [진행중] 브랜치: feature/SSCVE-2704
[2026-03-04 10:01:43] [SKIP ] [SSCVE-2704] 이미 존재하는 브랜치
[2026-03-04 10:01:43] [OK   ] [SSCVE-2743] 브랜치 생성 완료
[2026-03-04 10:01:43] [INFO ] Phase 2 완료: 생성 완료 1건 / 건너뜀 2건 / 실패 0건
[2026-03-04 10:01:43] [INFO ] 전체 완료
```

---

## 에지 케이스

| 상황 | 처리 방식 |
|------|-----------|
| INTQA 이슈에 문의대응 링크가 이미 있음 | SSCVE 이슈 생성 SKIP |
| SSCVE 브랜치가 로컬에 이미 존재 | 브랜치 생성 SKIP |
| SSCVE 이슈 유형이 버그가 아님 (에픽, 스토리, 작업 등) | 브랜치 생성 대상에서 제외 |
| develop/release 브랜치가 현재 체크아웃 상태 | `git fetch` 대신 `git pull`로 자동 처리 |
| develop/release 브랜치가 원격에 없음 | WARN 로그 출력 후 건너뜀 |
| 환경변수 미설정 | 누락 변수 목록 출력 후 종료 |
| Jira API 오류 | ERROR 로그 출력 후 해당 이슈 건너뜀 |
| git flow feature start 실패 | ERROR 로그 출력 후 다음 이슈로 진행 |

---

## 설정 변경 (코드 수정 필요)

자주 바꿀 필요가 없는 값들은 스크립트 상단 상수로 고정되어 있습니다.

| 상수 | 현재 값 | 설명 |
|------|---------|------|
| `ASSIGNEE_ID` | `60fe2779e6e6f800718020a3` | SSCVE 이슈 담당자 (하수임) |
| `PARENT_KEY` | `SSCVE-2561` | 기본 상위 항목 (에픽) |
| `FIX_VERSION` | `2.0.32` | 기본 수정 버전 |
| `REPO_PATH` | `C:\workspace\c-project` | git flow 브랜치를 생성할 저장소 경로 |
