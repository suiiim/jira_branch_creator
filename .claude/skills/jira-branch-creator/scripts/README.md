# Jira Branch Creator Skill - Scripts

이 폴더의 스크립트는 스킬 내에서 Claude가 직접 실행할 수 있는 헬퍼입니다.
실제 핵심 로직은 프로젝트 루트의 `scripts/` 폴더에 위치합니다.

## 스크립트 목록

| 파일 | 설명 |
|------|------|
| `validate_issue_key.py` | 이슈 키 형식 및 프로젝트 키(SSCVE) 유효성 검사 |
| `get_issue_info.py` | Jira API로 단일 이슈 정보 조회 후 JSON 출력 |
| `make_branch_name.py` | 이슈 타입 + 요약으로 브랜치명 생성 (슬러그 변환 포함) |

## 실제 실행 스크립트 (프로젝트 루트)

```
scripts/
  create_branch_from_jira.ps1  ← Windows: 단일 이슈 브랜치 생성
  create_branch_from_jira.sh   ← macOS/Linux: 단일 이슈 브랜치 생성
  watch_jira.ps1               ← Windows: 폴링 감시 모드
  watch_jira.py                ← 크로스 플랫폼: 폴링 감시 모드
  setup.ps1                    ← Windows: 환경 설정 확인
  setup.sh                     ← macOS/Linux: 환경 설정 확인
```
