---
name: jira-branch-creator
description: >
  INTQA 처리중 이슈를 SSCVE에 자동 동기화하고, SSCVE 할일 이슈에서
  로컬 git flow feature 브랜치를 자동 생성합니다.
  "jira 브랜치", "이슈에서 브랜치", "branch from jira", "create branch",
  "INTQA 동기화", "SSCVE 이슈 생성" 키워드에 반응합니다.
  SSCVE 프로젝트 이슈에만 적용되며, 다른 프로젝트 키 입력 시 오류가 발생합니다.
compatibility: Python 3.9+, 표준 라이브러리만 사용 (외부 패키지 불필요). Windows 환경 기준.
allowed-tools: Bash(git:*) Bash(python:*) Bash(python3:*) Read
metadata:
  author: suiiim
  version: "3.0"
  python: "3.9+"
---

# Jira Branch Creator (Claude Code Skill)

INTQA → SSCVE 이슈 동기화 및 git flow feature 브랜치 자동 생성 스킬입니다.

## 메인 스크립트

### `scripts/sync_and_create_branches.py`

INTQA 동기화와 브랜치 생성을 **단일 실행**으로 처리합니다.

```bash
python scripts/sync_and_create_branches.py [--dry-run]
```

## 실행 흐름

### 시작 시 프롬프트

```
상위 항목 (에픽) [SSCVE-2561]:  ← 엔터 = 기본값, 입력 = 변경
수정 버전        [2.0.32]:      ← 엔터 = 기본값, 입력 = 변경
```

### Phase 1 — INTQA → SSCVE 이슈 동기화

1. INTQA에서 **하수임 할당 + 처리중** 이슈 조회
2. `문의대응 처리 이슈` 링크가 이미 있으면 → **SKIP**
3. 없으면 → SSCVE 작업 이슈 생성 + 문의대응 링크 연결

SSCVE 이슈 생성 시 자동 지정:

| 필드 | 값 | 변경 방법 |
|------|----|-----------|
| 담당자 | 하수임 | 코드 고정 |
| 상위 항목 | `SSCVE-2561` (2.0.32-fix) | 실행 시 프롬프트 |
| 수정 버전 | `2.0.32` | 실행 시 프롬프트 |
| 이슈 타입 | 작업 (`10124`) | 코드 고정 |

### Phase 2 — SSCVE → git flow 브랜치 생성

1. SSCVE에서 **하수임 할당 + 할일** 이슈 조회
2. `C:\workspace\c-project` 로컬 브랜치 중 이미 존재하면 → **SKIP**
3. 없으면 → `git flow feature start SSCVE-XXXX` 실행

## 브랜치 네이밍 규칙

| 형식 | 예시 |
|------|------|
| `feature/{ISSUE_KEY}` | `feature/SSCVE-2704` |

자세한 규칙은 [references/BRANCH_NAMING.md](references/BRANCH_NAMING.md)를 참조하세요.

## 헬퍼 스크립트 (이 스킬 전용)

| 파일 | 설명 |
|------|------|
| `validate_issue_key.py` | SSCVE 이슈 키 형식 유효성 검사 |
| `get_issue_info.py` | Jira API로 단일 이슈 정보 조회 후 JSON 출력 |
| `make_branch_name.py` | 이슈 키로 브랜치명 생성 (`feature/SSCVE-XXXX`) |

## 로그

| 항목 | 내용 |
|------|------|
| 저장 위치 | `%USERPROFILE%\Desktop\jira-sync-logs\` |
| 파일명 | `sync_and_branch_YYYYMMDD.log` (일별 자동 로테이션) |
| 포맷 | `[YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE` |
| 레벨 | `INFO` / `OK` / `SKIP` / `WARN` / `ERROR` |

## 사전 요구사항

환경변수 설정 (필수):
- `JIRA_BASE_URL`: Jira 인스턴스 URL (예: `https://myteam.atlassian.net`)
- `JIRA_EMAIL`: Jira 로그인 이메일
- `JIRA_API_TOKEN`: Jira API 토큰

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

- INTQA 이슈에 이미 문의대응 링크 존재 → SSCVE 이슈 생성 SKIP
- SSCVE 브랜치 로컬에 이미 존재 → 브랜치 생성 SKIP
- 환경변수 미설정 → 누락 변수 명시 후 종료
- Jira API 오류 → 에러 로그 출력 후 해당 이슈 건너뜀
