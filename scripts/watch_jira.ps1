<#
.SYNOPSIS
    Jira 이슈 자동 감시 → 브랜치 생성 (Windows PowerShell)

.DESCRIPTION
    Jira 프로젝트를 주기적으로 폴링하여 새 이슈 발생 시
    자동으로 Git 브랜치를 생성합니다.

.PARAMETER ProjectKey
    Jira 프로젝트 키 (예: PROJ)

.PARAMETER BaseBranch
    기준 브랜치 (기본: develop)

.PARAMETER PollInterval
    폴링 간격 초 (기본: 30)

.PARAMETER RepoPath
    Git 레포지토리 경로 (기본: 현재 디렉토리)

.EXAMPLE
    .\watch_jira.ps1 -ProjectKey PROJ
    .\watch_jira.ps1 -ProjectKey PROJ -BaseBranch main -PollInterval 15
#>

param(
    [Parameter(Position = 0)]
    [string]$ProjectKey = $env:JIRA_PROJECT_KEY,

    [string]$BaseBranch = $(if ($env:BASE_BRANCH) { $env:BASE_BRANCH } else { "develop" }),

    [int]$PollInterval = $(if ($env:POLL_INTERVAL) { [int]$env:POLL_INTERVAL } else { 30 }),

    [string]$RepoPath = $(if ($env:REPO_PATH) { $env:REPO_PATH } else { Get-Location })
)

$ErrorActionPreference = "Continue"

# ─── 환경변수 확인 ────────────────────────────────────────────────────────

$JIRA_BASE_URL  = $env:JIRA_BASE_URL
$JIRA_EMAIL     = $env:JIRA_EMAIL
$JIRA_API_TOKEN = $env:JIRA_API_TOKEN

if (-not $JIRA_BASE_URL -or -not $JIRA_EMAIL -or -not $JIRA_API_TOKEN) {
    Write-Host "❌ 환경변수가 설정되지 않았습니다." -ForegroundColor Red
    Write-Host '   $env:JIRA_BASE_URL = "https://YOUR_DOMAIN.atlassian.net"' -ForegroundColor Yellow
    Write-Host '   $env:JIRA_EMAIL = "your-email@example.com"' -ForegroundColor Yellow
    Write-Host '   $env:JIRA_API_TOKEN = "your-api-token"' -ForegroundColor Yellow
    exit 1
}

$AllowedProject = "SSCVE"

if (-not $ProjectKey) {
    $ProjectKey = Read-Host "Enter Jira project key (only $AllowedProject is allowed)"
    if (-not $ProjectKey) { Write-Host "❌ Project key is required." -ForegroundColor Red; exit 1 }
}

if ($ProjectKey -ne $AllowedProject) {
    Write-Host "❌ 이 스크립트는 $AllowedProject 프로젝트만 지원합니다." -ForegroundColor Red
    Write-Host "   입력된 프로젝트: $ProjectKey" -ForegroundColor Yellow
    exit 1
}

# ─── 유틸 함수 ───────────────────────────────────────────────────────────

$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${JIRA_EMAIL}:${JIRA_API_TOKEN}"))
$authHeaders = @{
    "Authorization" = "Basic $base64Auth"
    "Accept"        = "application/json"
}

function Get-RecentIssues {
    param([int]$SinceMinutes = 2)

    $jql = "project=$ProjectKey AND created >= -${SinceMinutes}m ORDER BY created DESC"
    $encodedJql = [System.Uri]::EscapeDataString($jql)
    $url = "$JIRA_BASE_URL/rest/api/3/search?jql=$encodedJql&maxResults=10&fields=summary,issuetype"

    try {
        $result = Invoke-RestMethod -Uri $url -Headers $authHeaders -Method Get
        return $result.issues
    }
    catch {
        Write-Host "  ⚠️ Jira API 오류: $($_.Exception.Message)" -ForegroundColor Yellow
        return @()
    }
}

function New-BranchName {
    param($Issue)

    $key     = $Issue.key
    $itype   = $Issue.fields.issuetype.name.ToLower()
    $summary = $Issue.fields.summary

    $prefixMap = @{
        "bug" = "bugfix"; "story" = "feature"; "task" = "task"
        "epic" = "epic"; "subtask" = "feature"; "sub-task" = "feature"
    }
    $prefix = if ($prefixMap.ContainsKey($itype)) { $prefixMap[$itype] } else { "feature" }

    $slug = $summary.ToLower() -replace '[^a-z0-9]', '-' -replace '-+', '-'
    $slug = $slug.Trim('-')
    if ($slug.Length -gt 50) { $slug = $slug.Substring(0, 50).TrimEnd('-') }

    if ($slug) { return "$prefix/$key-$slug" }
    else       { return "$prefix/$key" }
}

function New-GitBranch {
    param([string]$BranchName)

    Push-Location $RepoPath
    try {
        git fetch origin 2>&1 | Out-Null
        git checkout $BaseBranch 2>&1 | Out-Null
        git pull origin $BaseBranch 2>&1 | Out-Null
        git checkout -b $BranchName 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) { return $true }
        else { return $false }
    }
    catch {
        Write-Host "    ❌ Git error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    finally {
        Pop-Location
    }
}

# ─── 메인 루프 ───────────────────────────────────────────────────────────

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Jira Branch Creator - Watch Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Project       : $ProjectKey"
Write-Host "  Repo path     : $RepoPath"
Write-Host "  Base branch   : $BaseBranch"
Write-Host "  Poll interval : ${PollInterval}s"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 기존 이슈 스킵
Write-Host "👀 Scanning existing issues..."
$seen = @{}
$existing = Get-RecentIssues -SinceMinutes 60
foreach ($issue in $existing) {
    $seen[$issue.key] = $true
}
Write-Host "   Skipped $($seen.Count) existing issue(s)."
Write-Host ""
Write-Host "🔄 Watching for new issues... (Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""

try {
    while ($true) {
        $issues = Get-RecentIssues -SinceMinutes 2

        foreach ($issue in $issues) {
            if (-not $seen.ContainsKey($issue.key)) {
                $seen[$issue.key] = $true
                $branch  = New-BranchName -Issue $issue
                $ts      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                $summary = $issue.fields.summary
                $itype   = $issue.fields.issuetype.name

                Write-Host "[$ts] 🆕 New issue detected!" -ForegroundColor Cyan
                Write-Host "    Key     : $($issue.key)"
                Write-Host "    Type    : $itype"
                Write-Host "    Summary : $summary"
                Write-Host "    Branch  : $branch"

                if (New-GitBranch -BranchName $branch) {
                    Write-Host "    ✅ Branch created successfully!" -ForegroundColor Green
                }
                Write-Host ""
            }
        }

        Start-Sleep -Seconds $PollInterval
    }
}
catch {
    # Ctrl+C
}

Write-Host ""
Write-Host "👋 Stopped watching. Goodbye!" -ForegroundColor Yellow
