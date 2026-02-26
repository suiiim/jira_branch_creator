# 브랜치 네이밍 규칙 (Branch Naming Convention)

이 프로젝트는 **SSCVE(SolidStep CVE Core)** 프로젝트 전용입니다.

## 기본 형식

```
{prefix}/{이슈키}-{요약-슬러그}
```

## Prefix 결정 기준

| Jira 이슈 타입 | Prefix    |
|---------------|-----------|
| Bug           | bugfix/   |
| Story         | feature/  |
| Task          | task/     |
| Epic          | epic/     |
| Subtask       | feature/  |
| 기타 / 알 수 없음 | feature/ |

## 슬러그 변환 규칙

1. Jira 이슈 요약(summary)을 소문자로 변환
2. 한글 및 특수문자 → 영문 변환 또는 제거
3. 공백 → 하이픈(`-`)으로 치환
4. 연속 하이픈 → 단일 하이픈으로 정규화
5. 앞뒤 하이픈 제거
6. 최종 브랜치명 63자 이내 제한
7. **한글만 있어 슬러그가 비는 경우 → 이슈 키만 사용**

### 슬러그 변환 예시

| 원본 요약 | 변환 결과 |
|---------|---------|
| `Fix login error` | `fix-login-error` |
| `Add user profile page` | `add-user-profile-page` |
| `로그인 오류 수정` | *(영문 슬러그 없음 → 이슈 키만 사용)* |
| `[HOTFIX] Null pointer exception` | `hotfix-null-pointer-exception` |

## 전체 브랜치명 예시

```
bugfix/SSCVE-123-fix-login-error
feature/SSCVE-456-add-user-profile-page
task/SSCVE-789-update-dependencies
epic/SSCVE-101-payment-system-integration
feature/SSCVE-202        ← 한글 요약이어서 이슈 키만 사용
```

## 주의사항

- **SSCVE 프로젝트 키만 허용** → 다른 키 입력 시 즉시 중단
- 이미 존재하는 브랜치명 → 에러 후 중단 (덮어쓰기 없음)
- base 브랜치는 `develop` 우선 → 없으면 `main` → 없으면 `master` 순서로 폴백

## 개인 프로젝트 예외 규칙

개인 프로젝트에서는 별도 브랜치를 생성하지 않고 `main` 브랜치에 직접 push합니다.

```bash
git add .
git commit -m "feat: 작업 내용"
git push origin main
```
