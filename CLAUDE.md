# Claude Code 지침

## c-project 브랜치 작업 규칙

**절대 금지 명령어** (C:\workspace\c-project 에서 절대 실행하지 말 것):
- `git clean` (추적되지 않은 파일 삭제)
- `git checkout -- .` / `git checkout .` (변경사항 되돌리기)
- `git restore .` / `git restore --staged .` (변경사항 복원)
- `git reset --hard` (커밋 및 변경사항 강제 되돌리기)
- `git rm` (파일을 git 추적에서 제거 + 로컬 삭제)
- `git stash drop` / `git stash clear` (stash에 저장된 작업 내용 삭제)
- `git branch -D` (브랜치 강제 삭제)
- `git push --force` / `git push -f` (원격 브랜치 강제 덮어쓰기)
- `git filter-branch` / `git filter-repo` (히스토리 재작성으로 커밋/파일 손실)
- `rm`, `del`, `Remove-Item` 등 파일/디렉토리 삭제 명령

브랜치 생성 시 기존 파일은 절대 삭제하지 않는다.
작업 디렉토리의 변경사항(uncommitted changes)을 절대 날리지 않는다.

## 커밋 워크플로우

- 사전 승인 없이 절대 commit/push 하지 않는다.
- 항상 커밋 메시지 후보 3개를 제시하고 사용자가 번호를 선택하면 실행한다.
- 형식: `<type>: <제목(한국어, 50자 이내, 마침표 없이)>`
- Remote: git@github.com-suim:suiiim/jira_branch_creator.git

## 터미널 출력

- CP949 환경: print() 사용 시 ASCII 문자만 사용 (이모지/한글 특수문자 불가)
- 로그 파일은 UTF-8로 저장 가능 (sys.stdout.reconfigure 필요)
