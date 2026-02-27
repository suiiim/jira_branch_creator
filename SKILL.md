---
name: jira-branch-creator
description: >
  INTQA 처리중 이슈를 SSCVE에 자동 동기화하고, SSCVE 할일 이슈에서
  로컬 git flow feature 브랜치를 자동 생성합니다.
  "jira 브랜치", "이슈에서 브랜치", "branch from jira", "create branch",
  "INTQA 동기화", "SSCVE 이슈 생성" 키워드에 반응합니다.
  SSCVE 프로젝트 이슈에만 적용되며, 다른 프로젝트 키 입력 시 오류가 발생합니다.
compatibility: Python 3.9+, 표준 라이브러리만 사용 (외부 패키지 불필요). Windows 환경 기준.
allowed-tools: Bash(python:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "3.0"
  python: "3.9+"
---

# Jira Branch Creator

INTQA → SSCVE 이슈 동기화 및 git flow feature 브랜치 자동 생성 스크립트입니다.

## 사전 요구사항

환경변수 설정 (필수):
- `JIRA_BASE_URL`: Jira 인스턴스 URL (예: `https://myteam.atlassian.net`)
- `JIRA_EMAIL`: Jira 로그인 이메일
- `JIRA_API_TOKEN`: Jira API 토큰

## 메인 스크립트

### `scripts/sync_and_create_branches.py`

INTQA 동기화와 브랜치 생성을 **단일 실행**으로 처리하는 통합 스크립트입니다.

```bash
python scripts/sync_and_create_branches.py [--dry-run]
```

| 옵션 | 설명 |
|------|------|
| `--dry-run` | Phase 2 브랜치 생성을 실제로 수행하지 않고 목록만 출력 |

---

## 실행 흐름

### 시작 시 프롬프트

실행하면 SSCVE 이슈 생성에 사용할 값을 확인/변경할 수 있습니다.
엔터를 누르면 기본값이 유지됩니다.

```
상위 항목 (에픽) [SSCVE-2561]:  ← 엔터 = 기본값, 입력 = 변경
수정 버전        [2.0.32]:      ← 엔터 = 기본값, 입력 = 변경
```

### Phase 1 — INTQA → SSCVE 이슈 동기화

1. INTQA 프로젝트에서 **하수임 할당 + 처리중** 이슈 조회
2. 각 이슈에 `문의대응 처리 이슈` 링크(SSCVE 연결)가 이미 있는지 확인
   - 있으면 → **SKIP**
   - 없으면 → SSCVE에 **작업 이슈 자동 생성**
3. 생성된 SSCVE 이슈와 INTQA 이슈 간 **문의대응 링크 자동 연결**

SSCVE 이슈 생성 시 자동 지정되는 필드:

| 필드 | 값 | 변경 방법 |
|------|----|-----------|
| 담당자 | 하수임 (`60fe2779e6e6f800718020a3`) | 코드 고정 |
| 상위 항목 (에픽) | `SSCVE-2561` (2.0.32-fix) | 실행 시 프롬프트 |
| 수정 버전 | `2.0.32` | 실행 시 프롬프트 |
| 이슈 타입 | 작업 (`10124`) | 코드 고정 |

### Phase 2 — SSCVE → git flow 브랜치 생성

1. SSCVE 프로젝트에서 **하수임 할당 + 할일** 이슈 조회
2. `C:\workspace\c-project` 저장소의 로컬 브랜치 목록 확인
3. 각 이슈마다 이미 브랜치가 있는지 확인
   - 있으면 → **SKIP**
   - 없으면 → `git flow feature start SSCVE-XXXX` 실행

---

## 브랜치 네이밍 규칙

| 형식 | 예시 |
|------|------|
| `feature/{ISSUE_KEY}` | `feature/SSCVE-2704` |

자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)를 참조하세요.

---

## 로그

모든 스크립트 실행 시 로그가 자동 생성됩니다.
자세한 규칙은 [references/LOG_FORMAT.md](references/LOG_FORMAT.md)를 참조하세요.

| 항목 | 내용 |
|------|------|
| 저장 위치 | `%USERPROFILE%\Desktop\jira-sync-logs\` |
| 파일명 | `sync_and_branch_YYYYMMDD.log` (일별 자동 로테이션) |
| 포맷 | `[YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE` |
| 레벨 | `INFO` / `OK` / `SKIP` / `WARN` / `ERROR` |
| 출력 | 콘솔 + 파일 동시 출력 |

로그 경로 변경 시 환경변수 `LOG_DIR` 사용:
```bash
LOG_DIR="D:\my-logs" python scripts/sync_and_create_branches.py
```

---

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

커밋 메시지는 항상 3가지 후보를 제시하고 사용자 승인 후 commit & push 합니다.
