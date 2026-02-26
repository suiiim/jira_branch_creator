$RULES_FILE = "D:\git\suiiim\jira_branch_creator\references\COMMIT_MESSAGE.md"
$CONFIG_FILE = "$HOME\.aicommits"

if (-not (Test-Path $RULES_FILE)) {
    Write-Host "[경고] 커밋 규칙 파일을 찾을 수 없습니다: $RULES_FILE" -ForegroundColor Yellow
    aicommits
    exit
}

$RULES = Get-Content $RULES_FILE -Raw -Encoding UTF8
$ORIGINAL_PROMPT = $null

if (Test-Path $CONFIG_FILE) {
    $configContent = Get-Content $CONFIG_FILE -Encoding UTF8
    $promptLine = $configContent | Where-Object { $_ -match "^prompt=" }
    if ($promptLine) {
        $ORIGINAL_PROMPT = $promptLine -replace "^prompt=", ""
    }
}

try {
    $NEW_PROMPT = "Write commit messages following these rules:`n`n$RULES"
    aicommits config set prompt $NEW_PROMPT
    Write-Host "[완료] 커밋 규칙 파일 적용됨: $RULES_FILE" -ForegroundColor Green
    aicommits
}
finally {
    if ($ORIGINAL_PROMPT) {
        aicommits config set prompt $ORIGINAL_PROMPT
        Write-Host "[복원] 기존 prompt 설정 복원 완료" -ForegroundColor Cyan
    } else {
        if (Test-Path $CONFIG_FILE) {
            $configContent = Get-Content $CONFIG_FILE -Encoding UTF8
            $newContent = $configContent | Where-Object { $_ -notmatch "^prompt=" }
            $newContent | Set-Content $CONFIG_FILE -Encoding UTF8
            Write-Host "[복원] 임시 prompt 설정 제거 완료" -ForegroundColor Cyan
        }
    }
}
