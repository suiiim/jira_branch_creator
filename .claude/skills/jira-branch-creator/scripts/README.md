# Jira Branch Creator Skill - Scripts

이 폴더의 스크립트는 스킬 내에서 Claude가 직접 실행할 수 있는 헬퍼입니다.
실제 핵심 로직은 프로젝트 루트의 `scripts/sync_and_create_branches.py`에 있습니다.

## 스크립트 목록

| 파일 | 설명 |
|------|------|
| `validate_issue_key.py` | SSCVE 이슈 키 형식 유효성 검사 |
| `get_issue_info.py` | Jira API로 단일 이슈 정보 조회 후 JSON 출력 |
| `make_branch_name.py` | 이슈 키로 브랜치명 생성 (`feature/SSCVE-XXXX`) |

## 메인 실행 스크립트 (프로젝트 루트)

```
scripts/
  sync_and_create_branches.py  ← INTQA 동기화 + SSCVE 브랜치 생성 통합 스크립트
```
