# Branch Naming Convention

## Format

```
{prefix}/{issue-key}-{summary-slug}
```

## Prefix Rules

이슈 타입에 따라 자동으로 prefix가 결정됩니다:

| Jira Issue Type | Branch Prefix | 설명              |
|-----------------|---------------|-------------------|
| Bug             | `bugfix/`     | 버그 수정         |
| Story           | `feature/`    | 새 기능 개발      |
| Task            | `task/`       | 일반 작업         |
| Epic            | `epic/`       | 대규모 기능       |
| Sub-task        | `feature/`    | 하위 작업         |
| 기타            | `feature/`    | 기본값            |

## Summary Slug Rules

이슈 요약(Summary)에서 브랜치명에 사용할 슬러그를 생성합니다:

1. 모두 소문자로 변환
2. 영문 알파벳과 숫자만 유지
3. 나머지 문자는 하이픈(`-`)으로 치환
4. 연속된 하이픈은 하나로 축약
5. 앞뒤 하이픈 제거
6. 최대 50자로 제한
7. 슬러그가 비어있으면(한글만 있는 경우 등) 이슈 키만 사용

## Examples

| Jira Issue                              | Generated Branch Name                          |
|-----------------------------------------|------------------------------------------------|
| BUG PROJ-101 "Fix login error"          | `bugfix/PROJ-101-fix-login-error`              |
| STORY PROJ-202 "Add user profile page"  | `feature/PROJ-202-add-user-profile-page`       |
| TASK PROJ-303 "Update CI/CD pipeline"   | `task/PROJ-303-update-ci-cd-pipeline`          |
| EPIC PROJ-404 "Payment system"          | `epic/PROJ-404-payment-system`                 |
| STORY PROJ-505 "로그인 기능 구현"         | `feature/PROJ-505` (한글만 있으므로 키만 사용)   |
| STORY PROJ-606 "Add OAuth2 로그인"       | `feature/PROJ-606-add-oauth2`                  |

## Base Branch

브랜치 생성 시 기본 base 브랜치는 `develop`이며, 다음 순서로 폴백합니다:

1. `develop` (기본)
2. `main`
3. `master`

수동으로 base 브랜치를 지정할 수도 있습니다:

```bash
bash scripts/create_branch_from_jira.sh PROJ-123 main
```

## 개인 프로젝트 예외 규칙

개인 프로젝트에서는 별도 브랜치를 생성하지 않고 `main` 브랜치에 직접 push합니다.

```bash
git add .
git commit -m "feat: 작업 내용"
git push origin main
```
