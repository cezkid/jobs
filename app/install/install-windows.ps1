# Paste-line install (docs/index.html), pasted into PowerShell (cmd works too):
#   powershell -ExecutionPolicy Bypass -c "irm <raw url of this file> | iex"
# One line for everyone: no $ => outer shell expands nothing; AI asked below, not on the page.
# Per-user installs only => no admin prompt.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$ZipUrl = 'https://github.com/cezkid/jobs/archive/refs/heads/main.zip'
$Dir = if ($env:JOBS_DIR) { $env:JOBS_DIR } else { Join-Path $HOME 'jobs' }
$AiArg = if ($args.Count) { "$($args[0])" } else { $env:JOBS_AI }
$VsCodeBin = "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin"
$StepCount = 5

function Step($n, $msg) { Write-Host "`nStep $n of ${StepCount}: $msg" -ForegroundColor Cyan }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = @([Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User'), "$HOME\.local\bin", $VsCodeBin) -join ';'
}
function Check($what) { if ($LASTEXITCODE) { throw "Could not $what." } }
# asked first, while the user is still at the window; 1 Claude, 2 ChatGPT
function Pick-Ai {
    if ($AiArg) { return $AiArg }
    if (Have 'code') {  # re-run to repair => keep the AI already set up, no question
        $have = @(cmd /c 'code --list-extensions 2>nul')
        if ($have -contains 'anthropic.claude-code') { return '1' }
        if ($have -contains 'openai.chatgpt') { return '2' }
    }
    Write-Host "`nWhich AI do you pay for?" -ForegroundColor Cyan
    Write-Host '  1 = Claude'
    Write-Host '  2 = ChatGPT'
    while ($true) {
        $answer = (Read-Host 'Type 1 or 2, then press Enter').Trim().ToLower()
        if ($answer -in '1', 'claude') { return '1' }
        if ($answer -in '2', 'chatgpt') { return '2' }
    }
}

try {
    Write-Host "`nInstalling Job Finder. This takes about 5 minutes - keep this window open." -ForegroundColor Cyan
    Refresh-Path
    $AiExtension = if ((Pick-Ai) -eq '2') { 'openai.chatgpt' } else { 'anthropic.claude-code' }

    # uv's installer refuses Windows' default policy (Restricted) => this window only, nothing saved
    try { Set-ExecutionPolicy Bypass -Scope Process -Force } catch {}

    Step 1 'installing uv (runs Job Finder)...'
    if (-not (Have 'uv')) {
        try { Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression } catch {}
        Refresh-Path
    }
    # policy locked by computer's owner (work laptop) => uv's installer still refuses; winget doesn't check
    if (-not (Have 'uv') -and (Have 'winget')) {
        winget install --id astral-sh.uv -e --silent --scope user --accept-package-agreements --accept-source-agreements
        Refresh-Path
    }
    if (-not (Have 'uv')) { throw 'Could not install uv.' }

    Step 2 'installing VS Code...'
    if (-not (Have 'code')) {
        $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
        $setup = Join-Path $env:TEMP 'VSCodeUserSetup.exe'
        # -UseBasicParsing: Dec 2025 update (CVE-2025-54100) asks before IE-engine parsing, Enter = cancel
        Invoke-WebRequest -UseBasicParsing "https://update.code.visualstudio.com/latest/win32-$arch-user/stable" -OutFile $setup
        Start-Process $setup -ArgumentList '/VERYSILENT', '/NORESTART', '/MERGETASKS=!runcode' -Wait
        Refresh-Path
    }
    if (-not (Have 'code')) { throw 'Could not install VS Code.' }

    Step 3 'adding the AI panel to VS Code...'
    cmd /c "code --install-extension $AiExtension --force >nul 2>&1"
    Check 'add the AI panel to VS Code'

    Step 4 "downloading Job Finder to $Dir..."
    # staging under $Dir => Move-Item stays on one drive; My folders + .data never in zip
    $staging = Join-Path $Dir '.data\install'
    if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
    New-Item -ItemType Directory -Force $staging | Out-Null
    Invoke-WebRequest -UseBasicParsing $ZipUrl -OutFile "$staging\jobs.zip"
    Expand-Archive "$staging\jobs.zip" $staging
    Get-ChildItem -Force "$staging\jobs-main" | ForEach-Object {
        $dest = Join-Path $Dir $_.Name
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Move-Item $_.FullName $dest
    }
    Remove-Item $staging -Recurse -Force

    Step 5 'getting Job Finder ready...'
    Push-Location $Dir
    uv sync --quiet
    Pop-Location
    Check 'get Job Finder ready'

    $start = Join-Path $Dir 'app\install\start-windows.bat'
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Job Finder.lnk'))
    $link.TargetPath = $start
    $link.WorkingDirectory = $Dir
    $codeExe = Join-Path (Split-Path (Split-Path (Get-Command code).Source)) 'Code.exe'
    if (Test-Path $codeExe) { $link.IconLocation = "$codeExe,0" }
    $link.Save()

    Write-Host "`nDone. Next time, open 'Job Finder' on your Desktop." -ForegroundColor Green
    Write-Host 'VS Code opens now. Click Sign in on the right-hand panel, then press Enter.' -ForegroundColor Green
    if (-not $env:JOBS_NO_LAUNCH) { & $start }
} catch {
    Write-Host "`nInstall stopped: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Run the same steps again. If it fails twice, send a photo of this window to whoever shared Job Finder with you.'
    Read-Host 'Press Enter to close'
}
