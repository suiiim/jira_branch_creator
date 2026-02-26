#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Jira Branch Creator - 초기 설정 스크립트
# 필요한 도구들의 설치 여부를 확인하고 환경변수를 안내합니다.
# Python 3.12 이상이 필요합니다.
# =============================================================================

echo "========================================"
echo "  Jira Branch Creator - Setup"
echo "========================================"
echo ""

# --- 의존성 체크 ---
echo "🔍 Checking dependencies..."
echo ""

ALL_OK=true

# git, curl, jq 확인
for cmd in git curl jq; do
  if command -v "$cmd" &>/dev/null; then
    VERSION=$($cmd --version 2>&1 | head -1)
    echo "  ✅ $cmd : $VERSION"
  else
    echo "  ❌ $cmd : NOT FOUND — Please install it"
    ALL_OK=false
  fi
done

# Python 3.12 이상 확인
PYTHON_CMD=""
MIN_MINOR=12

for cmd in python3.12 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PY_VERSION=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge "$MIN_MINOR" ]; then
      echo "  ✅ python : $($cmd --version 2>&1)"
      PYTHON_CMD="$cmd"
      break
    else
      echo "  ⚠️  $cmd : $($cmd --version 2>&1) — Python 3.12 이상이 필요합니다"
    fi
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo "  ❌ python : Python 3.12 이상을 찾을 수 없습니다"
  ALL_OK=false
fi

echo ""

if [ "$ALL_OK" = false ]; then
  echo "❌ Some dependencies are missing. Please install them first."
  echo ""
  echo "   Windows (winget):"
  echo "     winget install Python.Python.3.12"
  echo "     winget install stedolan.jq"
  echo ""
  echo "   macOS (brew):"
  echo "     brew install python@3.12 jq"
  echo ""
  echo "   Ubuntu/Debian:"
  echo "     sudo apt install python3.12 jq"
  echo ""
  exit 1
fi

echo "✅ All dependencies are installed!"
echo ""

# --- 환경변수 확인 ---
echo "🔍 Checking environment variables..."
echo ""

ENV_OK=true

if [ -n "${JIRA_BASE_URL:-}" ]; then
  echo "  ✅ JIRA_BASE_URL  = ${JIRA_BASE_URL}"
else
  echo "  ⚠️  JIRA_BASE_URL  is not set"
  ENV_OK=false
fi

if [ -n "${JIRA_EMAIL:-}" ]; then
  echo "  ✅ JIRA_EMAIL     = ${JIRA_EMAIL}"
else
  echo "  ⚠️  JIRA_EMAIL     is not set"
  ENV_OK=false
fi

if [ -n "${JIRA_API_TOKEN:-}" ]; then
  echo "  ✅ JIRA_API_TOKEN = (set)"
else
  echo "  ⚠️  JIRA_API_TOKEN is not set"
  ENV_OK=false
fi

echo ""

if [ "$ENV_OK" = false ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Please add these to your shell profile"
  echo "  (~/.bashrc, ~/.zshrc, or ~/.profile):"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo '  export JIRA_BASE_URL="https://YOUR_DOMAIN.atlassian.net"'
  echo '  export JIRA_EMAIL="your-email@example.com"'
  echo '  export JIRA_API_TOKEN="your-api-token"'
  echo ""
  echo "  💡 Get your API token at:"
  echo "     https://id.atlassian.com/manage-profile/security/api-tokens"
  echo ""
fi

# --- Jira 연결 테스트 ---
if [ "$ENV_OK" = true ]; then
  echo "🔗 Testing Jira connection..."
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
    -H "Accept: application/json" \
    "${JIRA_BASE_URL}/rest/api/3/myself")

  if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Jira connection successful!"
  else
    echo "  ❌ Jira connection failed (HTTP ${HTTP_CODE})"
    echo "     Please verify your credentials."
  fi
  echo ""
fi

echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "  Usage:"
echo "    Single branch : bash scripts/create_branch_from_jira.sh SSCVE-123"
echo "    Watch mode    : ${PYTHON_CMD} scripts/watch_jira.py"
echo ""
