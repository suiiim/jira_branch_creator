#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Jira 이슈에서 Git 브랜치를 생성하는 스크립트
# Usage: bash create_branch_from_jira.sh <JIRA_ISSUE_KEY> [base_branch]
# Example: bash create_branch_from_jira.sh PROJ-123 develop
# =============================================================================

ISSUE_KEY="${1:?❌ Usage: $0 <JIRA_ISSUE_KEY> [base_branch]}"
BASE_BRANCH="${2:-develop}"

# --- 프로젝트 키 제한 ---
ALLOWED_PROJECT="SSCVE"
ACTUAL_PROJECT="${ISSUE_KEY%%-*}"
if [ "${ACTUAL_PROJECT}" != "${ALLOWED_PROJECT}" ]; then
  echo "❌ 이 스크립트는 ${ALLOWED_PROJECT} 프로젝트 이슈만 지원합니다."
  echo "   입력된 프로젝트: ${ACTUAL_PROJECT}"
  echo "   예시: ${ALLOWED_PROJECT}-123"
  exit 1
fi

# --- 환경변수 확인 ---
: "${JIRA_BASE_URL:?❌ Set JIRA_BASE_URL (e.g. https://myteam.atlassian.net)}"
: "${JIRA_EMAIL:?❌ Set JIRA_EMAIL}"
: "${JIRA_API_TOKEN:?❌ Set JIRA_API_TOKEN}"

echo "========================================"
echo "  Jira Branch Creator"
echo "========================================"
echo ""
echo "📋 Fetching issue ${ISSUE_KEY} from Jira..."

# --- Jira REST API로 이슈 조회 ---
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/3/issue/${ISSUE_KEY}?fields=summary,issuetype")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Failed to fetch issue (HTTP ${HTTP_CODE})."
  echo "   Check your credentials, URL, and issue key."
  exit 1
fi

# --- 이슈 정보 파싱 ---
ISSUE_TYPE=$(echo "$BODY" | jq -r '.fields.issuetype.name')
SUMMARY=$(echo "$BODY" | jq -r '.fields.summary')

echo "   Issue Key : ${ISSUE_KEY}"
echo "   Type      : ${ISSUE_TYPE}"
echo "   Summary   : ${SUMMARY}"
echo ""

# --- 이슈 타입에 따른 prefix 결정 ---
case "${ISSUE_TYPE,,}" in
  bug)                PREFIX="bugfix" ;;
  story)              PREFIX="feature" ;;
  task)               PREFIX="task" ;;
  epic)               PREFIX="epic" ;;
  subtask|sub-task)   PREFIX="feature" ;;
  *)                  PREFIX="feature" ;;
esac

# --- 요약을 URL-safe slug로 변환 ---
SLUG=$(echo "$SUMMARY" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g' \
  | sed 's/--*/-/g' \
  | sed 's/^-//' \
  | sed 's/-$//' \
  | head -c 50)

# 슬러그가 비었으면 (예: 한글만 있는 경우) 이슈 키만 사용
if [ -z "$SLUG" ]; then
  BRANCH_NAME="${PREFIX}/${ISSUE_KEY}"
else
  BRANCH_NAME="${PREFIX}/${ISSUE_KEY}-${SLUG}"
fi

echo "🌿 Branch name: ${BRANCH_NAME}"
echo ""

# --- base 브랜치 존재 확인 및 폴백 ---
if ! git rev-parse --verify "${BASE_BRANCH}" &>/dev/null; then
  echo "⚠️  Base branch '${BASE_BRANCH}' not found. Trying 'main'..."
  BASE_BRANCH="main"
  if ! git rev-parse --verify "${BASE_BRANCH}" &>/dev/null; then
    echo "⚠️  'main' not found either. Trying 'master'..."
    BASE_BRANCH="master"
    if ! git rev-parse --verify "${BASE_BRANCH}" &>/dev/null; then
      echo "❌ No base branch found (develop/main/master). Aborting."
      exit 1
    fi
  fi
fi

# --- 같은 이름의 브랜치 존재 확인 ---
if git rev-parse --verify "${BRANCH_NAME}" &>/dev/null; then
  echo "❌ Branch '${BRANCH_NAME}' already exists!"
  echo "   Use 'git checkout ${BRANCH_NAME}' to switch to it."
  exit 1
fi

# --- 브랜치 생성 ---
echo "📥 Fetching latest from origin..."
git fetch origin

echo "🔀 Switching to ${BASE_BRANCH}..."
git checkout "${BASE_BRANCH}"
git pull origin "${BASE_BRANCH}"

echo "🌱 Creating branch ${BRANCH_NAME}..."
git checkout -b "${BRANCH_NAME}"

echo ""
echo "========================================"
echo "  ✅ Branch created successfully!"
echo "========================================"
echo "   Branch  : ${BRANCH_NAME}"
echo "   Based on: ${BASE_BRANCH}"
echo "========================================"
