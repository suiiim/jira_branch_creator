<#
.SYNOPSIS
    Jira Branch Creator - 초기 설정 스크립트 (Windows PowerShell)

.DESCRIPTION
    필요한 도구들의 설치 여부를 확인하고 환경변수를 안내합니다.
    Python 3.12 이상이 필요합니다.

.EXAMPLE
    .\setup.ps1
#>

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Jira Branch Creator - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ─── 의존성 체크 ─────────────────────────────────────────────────────────

Write-Host "🔍 Checking dependencies..." -ForegroundColor White
Write-Host ""

$allOk = $true

# git
$gitVer = git --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ git     : $gitVer" -ForegroundColor Green
} else {
    Write-Host "  ❌ git     : NOT FOUND" -ForegroundColor Red
    $allOk = $false
}

# curl (Windows 10+ 내장)
$curlVer = curl.exe --version 2>&1 | Select-Object -First 1
if ($curlVer) {
    Write-Host "  ✅ curl    : $curlVer" -ForegroundColor Green
} else {
    Write-Host "  ❌ curl    : NOT FOUND" -ForegroundColor Red
    $allOk = $false
}

# Python 3.12 이상 확인
$pythonCmd  = $null
$minVersion = [Version]"3.12"

foreach ($cmd in @("python", "python3")) {
    $pyVerStr = & $cmd --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $pyVerStr -match "Python (\d+\.\d+)") {
        $pyVersion = [Version]$Matches[1]
        if ($pyVersion -ge $minVersion) {
            Write-Host "  ✅ python  : $pyVerStr" -ForegroundColor Green
            $pythonCmd = $cmd
            break
        } else {
            Write-Host "  ⚠️  python  : $pyVerStr — Python 3.12 이상이 필요합니다" -ForegroundColor Yellow
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "  ❌ python  : Python 3.12 이상을 찾을 수 없습니다" -ForegroundColor Red
    $allOk = $false
}

Write-Host ""

if (-not $allOk) {
    Write-Host "❌ Some dependencies are missing." -ForegroundColor Red
    Write-Host ""
    Write-Host "   Install with winget:" -ForegroundColor Yellow
    Write-Host "     winget install Git.Git"
    Write-Host "     winget install Python.Python.3.12"
    Write-Host ""
    Write-Host "   Install with scoop:" -ForegroundColor Yellow
    Write-Host "     scoop install git python"
    Write-Host ""
    exit 1
}

Write-Host "✅ All dependencies installed!" -ForegroundColor Green
Write-Host ""

# ─── 환경변수 확인 ───────────────────────────────────────────────────────

Write-Host "🔍 Checking environment variables..." -ForegroundColor White
Write-Host ""

$envOk = $true

if ($env:JIRA_BASE_URL) {
    Write-Host "  ✅ JIRA_BASE_URL  = $env:JIRA_BASE_URL" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  JIRA_BASE_URL  is not set" -ForegroundColor Yellow
    $envOk = $false
}

if ($env:JIRA_EMAIL) {
    Write-Host "  ✅ JIRA_EMAIL     = $env:JIRA_EMAIL" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  JIRA_EMAIL     is not set" -ForegroundColor Yellow
    $envOk = $false
}

if ($env:JIRA_API_TOKEN) {
    Write-Host "  ✅ JIRA_API_TOKEN = (set)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  JIRA_API_TOKEN is not set" -ForegroundColor Yellow
    $envOk = $false
}

Write-Host ""

if (-not $envOk) {
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host "  환경변수 설정 방법" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  방법 1: 현재 세션에만 적용 (임시)" -ForegroundColor White
    Write-Host '  $env:JIRA_BASE_URL   = "https://YOUR_DOMAIN.atlassian.net"'
    Write-Host '  $env:JIRA_EMAIL      = "your-email@example.com"'
    Write-Host '  $env:JIRA_API_TOKEN  = "your-api-token"'
    Write-Host ""
    Write-Host "  방법 2: 영구 적용 (권장)" -ForegroundColor White
    Write-Host '  [System.Environment]::SetEnvironmentVariable("JIRA_BASE_URL",   "https://YOUR_DOMAIN.atlassian.net", "User")'
    Write-Host '  [System.Environment]::SetEnvironmentVariable("JIRA_EMAIL",      "your-email@example.com", "User")'
    Write-Host '  [System.Environment]::SetEnvironmentVariable("JIRA_API_TOKEN",  "your-api-token", "User")'
    Write-Host ""
    Write-Host "  방법 3: Windows 설정 GUI" -ForegroundColor White
    Write-Host "  시작 > '환경 변수' 검색 > '시스템 환경 변수 편집' > '환경 변수' 버튼"
    Write-Host ""
    Write-Host "  💡 API 토큰 발급:" -ForegroundColor Cyan
    Write-Host "     https://id.atlassian.com/manage-profile/security/api-tokens"
    Write-Host ""
}

# ─── Jira 연결 테스트 ────────────────────────────────────────────────────

if ($envOk) {
    Write-Host "🔗 Testing Jira connection..." -ForegroundColor White

    $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${env:JIRA_EMAIL}:${env:JIRA_API_TOKEN}"))
    $headers = @{
        "Authorization" = "Basic $base64Auth"
        "Accept"        = "application/json"
    }

    try {
        $result = Invoke-RestMethod -Uri "$env:JIRA_BASE_URL/rest/api/3/myself" -Headers $headers -Method Get
        Write-Host "  ✅ Jira connection successful! (Logged in as: $($result.displayName))" -ForegroundColor Green
    }
    catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "  ❌ Jira connection failed (HTTP $code)" -ForegroundColor Red
        Write-Host "     자격 증명을 확인하세요." -ForegroundColor Yellow
    }
    Write-Host ""
}

# ─── 완료 ────────────────────────────────────────────────────────────────

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Usage (PowerShell):" -ForegroundColor White
Write-Host "    .\scripts\create_branch_from_jira.ps1 -IssueKey SSCVE-123"
Write-Host "    $pythonCmd scripts\watch_jira.py"
Write-Host ""
