<#
.SYNOPSIS
    Jira 이슈에서 Git 브랜치를 생성하는 PowerShell 스크립트

.DESCRIPTION
    Jira REST API로 이슈 정보를 조회하고, 이슈 타입과 요약을 기반으로
    브랜치 네이밍 컨벤션에 맞는 Git 브랜치를 자동 생성합니다.

.PARAMETER IssueKey
    Jira 이슈 키 (예: PROJ-123)

.PARAMETER BaseBranch
    기준 브랜치 (기본: develop)

.EXAMPLE
    .\create_branch_from_jira.ps1 -IssueKey PROJ-123
    .\create_branch_from_jira.ps1 -IssueKey PROJ-123 -BaseBranch main
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$IssueKey,

    [Parameter(Position = 1)]
    [string]$BaseBranch = "develop"
)

$ErrorActionPreference = "Stop"

# ─── 프로젝트 키 제한 ─────────────────────────────────────────────────────

$AllowedProject = "SSCVE"
$ActualProject  = $IssueKey.Split('-')[0]

if ($ActualProject -ne $AllowedProject) {
    Write-Host "❌ 이 스크립트는 $AllowedProject 프로젝트 이슈만 지원합니다." -ForegroundColor Red
    Write-Host "   입력된 프로젝트: $ActualProject" -ForegroundColor Yellow
    Write-Host "   예시: $AllowedProject-123" -ForegroundColor Yellow
    exit 1
}

# ─── 환경변수 확인 ────────────────────────────────────────────────────────

$JIRA_BASE_URL = $env:JIRA_BASE_URL
$JIRA_EMAIL    = $env:JIRA_EMAIL
$JIRA_API_TOKEN = $env:JIRA_API_TOKEN

if (-not $JIRA_BASE_URL) { Write-Error "JIRA_BASE_URL 환경변수를 설정하세요. (예: https://myteam.atlassian.net)"; exit 1 }
if (-not $JIRA_EMAIL)    { Write-Error "JIRA_EMAIL 환경변수를 설정하세요."; exit 1 }
if (-not $JIRA_API_TOKEN){ Write-Error "JIRA_API_TOKEN 환경변수를 설정하세요."; exit 1 }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Jira Branch Creator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ─── Jira API 호출 ───────────────────────────────────────────────────────

Write-Host "📋 Fetching issue $IssueKey from Jira..."

$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${JIRA_EMAIL}:${JIRA_API_TOKEN}"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Accept"        = "application/json"
}

$url = "$JIRA_BASE_URL/rest/api/3/issue/${IssueKey}?fields=summary,issuetype"

try {
    $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "❌ Jira API 호출 실패 (HTTP $statusCode)" -ForegroundColor Red
    Write-Host "   URL, 이메일, API 토큰, 이슈 키를 확인하세요." -ForegroundColor Yellow
    exit 1
}

# ─── 이슈 정보 파싱 ──────────────────────────────────────────────────────

$issueType = $response.fields.issuetype.name
$summary   = $response.fields.summary

Write-Host "   Issue Key : $IssueKey"
Write-Host "   Type      : $issueType"
Write-Host "   Summary   : $summary"
Write-Host ""

# ─── Prefix 결정 ─────────────────────────────────────────────────────────

$prefixMap = @{
    "bug"      = "bugfix"
    "story"    = "feature"
    "task"     = "task"
    "epic"     = "epic"
    "subtask"  = "feature"
    "sub-task" = "feature"
}

$prefix = $prefixMap[$issueType.ToLower()]
if (-not $prefix) { $prefix = "feature" }

# ─── 브랜치명 생성 ───────────────────────────────────────────────────────

# 요약을 slug로 변환: 소문자, 영문/숫자만, 하이픈 구분
$slug = $summary.ToLower()
$slug = $slug -replace '[^a-z0-9]', '-'   # 영문/숫자 외 하이픈으로
$slug = $slug -replace '-+', '-'           # 연속 하이픈 축약
$slug = $slug.Trim('-')                    # 앞뒤 하이픈 제거
if ($slug.Length -gt 50) { $slug = $slug.Substring(0, 50).TrimEnd('-') }

if ($slug) {
    $branchName = "$prefix/$IssueKey-$slug"
} else {
    $branchName = "$prefix/$IssueKey"
}

Write-Host "🌿 Branch name: $branchName" -ForegroundColor Green
Write-Host ""

# ─── Base 브랜치 확인 및 폴백 ────────────────────────────────────────────

$baseCandidates = @($BaseBranch, "main", "master")
$resolvedBase = $null

foreach ($candidate in $baseCandidates) {
    $check = git rev-parse --verify $candidate 2>&1
    if ($LASTEXITCODE -eq 0) {
        $resolvedBase = $candidate
        break
    }
    if ($candidate -eq $BaseBranch) {
        Write-Host "⚠️  Base branch '$BaseBranch' not found. Trying alternatives..." -ForegroundColor Yellow
    }
}

if (-not $resolvedBase) {
    Write-Host "❌ 사용 가능한 base branch를 찾을 수 없습니다 (develop/main/master)" -ForegroundColor Red
    exit 1
}

# ─── 브랜치 중복 확인 ────────────────────────────────────────────────────

$existCheck = git rev-parse --verify $branchName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "❌ Branch '$branchName' already exists!" -ForegroundColor Red
    Write-Host "   Use 'git checkout $branchName' to switch to it." -ForegroundColor Yellow
    exit 1
}

# ─── 브랜치 생성 ─────────────────────────────────────────────────────────

Write-Host "📥 Fetching latest from origin..."
git fetch origin
if ($LASTEXITCODE -ne 0) { Write-Host "❌ git fetch 실패" -ForegroundColor Red; exit 1 }

Write-Host "🔀 Switching to $resolvedBase..."
git checkout $resolvedBase
if ($LASTEXITCODE -ne 0) { Write-Host "❌ git checkout 실패" -ForegroundColor Red; exit 1 }

git pull origin $resolvedBase
if ($LASTEXITCODE -ne 0) { Write-Host "❌ git pull 실패" -ForegroundColor Red; exit 1 }

Write-Host "🌱 Creating branch $branchName..."
git checkout -b $branchName
if ($LASTEXITCODE -ne 0) { Write-Host "❌ branch 생성 실패" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ Branch created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Branch  : $branchName"
Write-Host "   Based on: $resolvedBase"
Write-Host "========================================" -ForegroundColor Green
