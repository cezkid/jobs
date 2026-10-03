# Paste-line install (docs/index.html), pasted into PowerShell:
#   irm <raw url of this file> | iex
# Runs in the user's own window, no second powershell: a child started w/ -ExecutionPolicy Bypass
# got an empty download on a real PC while the same irm in the window got the whole file. iex
# ignores execution policy; Bypass for uv's installer is set below. AI asked below, not on the page
# (JOBS_AI or an argument skips it: 1|claude, 2|chatgpt, 3|copilot).
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
# 1|claude 2|chatgpt 3|copilot, any case => the word; anything else => $null (asked again)
function Ai-Word($text) {
    switch ("$text".Trim().ToLower()) {
        { $_ -in '1', 'claude' } { return 'claude' }
        { $_ -in '2', 'chatgpt' } { return 'chatgpt' }
        { $_ -in '3', 'copilot' } { return 'copilot' }
    }
    return $null
}
# asked first, while the user is still at the window
# Copilot never guessed from extensions: its chat is built into VS Code for everyone
function Pick-Ai {
    $word = Ai-Word $AiArg
    $saved = Join-Path $Dir '.data\ai'
    if (-not $word -and (Test-Path $saved)) { $word = Ai-Word (Get-Content $saved -Raw) }
    if (-not $word -and (Have 'code')) {  # re-run to repair => keep the AI already set up, no question
        # default profile + Job Finder's own (absent before its first setup: "not found", exit 1)
        $have = @(cmd /c 'code --list-extensions 2>nul & code --list-extensions --profile "CEZ Job Finder" 2>nul' |
            ForEach-Object { "$_".ToLower() })
        if ($have -contains 'anthropic.claude-code') { $word = 'claude' }
        elseif ($have -contains 'openai.chatgpt') { $word = 'chatgpt' }
    }
    if ($word) { return $word }
    if (-not [Environment]::UserInteractive -or [Console]::IsInputRedirected) {
        throw 'Could not ask which AI you use. Open PowerShell, paste the install line there and press Enter.'
    }
    Write-Host "`nWhich AI do you use?" -ForegroundColor Cyan
    Write-Host '  1 = Claude (Pro or Max)'
    Write-Host '  2 = ChatGPT (Plus or Pro)'
    Write-Host '  3 = GitHub Copilot Pro ($10 a month)'
    while ($true) {
        $word = Ai-Word (Read-Host 'Type 1, 2 or 3, then press Enter')
        if ($word) { return $word }
    }
}

try {
    Write-Host "`nInstalling CEZ Job Finder. This takes about 5 minutes - keep this window open." -ForegroundColor Cyan
    Refresh-Path
    $Ai = Pick-Ai
    # explicit per AI; copilot => none (Copilot Chat built into VS Code 1.140)
    $AiExtension, $SignIn = switch ($Ai) {
        'claude' { 'anthropic.claude-code', 'Click Sign in on the chat panel on the right, then press Enter.' }
        'chatgpt' { 'openai.chatgpt', 'Click the ChatGPT icon at the top left, then Sign in, then press Enter.' }
        'copilot' { '', 'Click Sign in on the chat panel on the right, then pick Claude Sonnet in the model list under the chat box, then press Enter. No GitHub account? Make one with your Google or Apple account.' }
    }

    # uv's installer refuses Windows' default policy (Restricted) => this window only, nothing saved
    try { Set-ExecutionPolicy Bypass -Scope Process -Force } catch {}

    Step 1 'installing uv (runs CEZ Job Finder)...'
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
        # VS Code is ours => launcher may quiet its app-wide settings (never a developer's own)
        New-Item -ItemType Directory -Force (Join-Path $Dir '.data') | Out-Null
        Set-Content -Path (Join-Path $Dir '.data\vscode-ours') -Value '' -Encoding ascii
        Refresh-Path
    }
    if (-not (Have 'code')) { throw 'Could not install VS Code.' }

    Step 3 "downloading CEZ Job Finder to $Dir..."
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
    # private, kept by updates; launcher + `jobs.py ai` read it
    Set-Content -Path (Join-Path $Dir '.data\ai') -Value $Ai -Encoding ascii

    Step 4 'getting CEZ Job Finder ready...'
    Push-Location $Dir
    uv sync --quiet
    Pop-Location
    Check 'get CEZ Job Finder ready'

    Step 5 'adding the AI panel to VS Code...'
    # Job Finder's own VS Code profile + AI panel, PDF viewer, typo checker, its window (plain lines);
    # VS Code open => default profile. Fails => AI panel the plain way, as before the profile
    Push-Location $Dir
    uv run app/jobs.py window-setup
    $setupFailed = $LASTEXITCODE
    Pop-Location
    if ($setupFailed) {
        if ($AiExtension) {
            cmd /c "code --install-extension $AiExtension --force >nul 2>&1"
            Check 'add the AI panel to VS Code'
        }
    }

    $start = Join-Path $Dir 'app\install\start-windows.bat'
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'CEZ Job Finder.lnk'))
    $link.TargetPath = $start
    $link.WorkingDirectory = $Dir
    $link.IconLocation = (Join-Path $Dir 'app\install\icon.ico') + ',0'
    # 7 = minimized: the console stays in the taskbar during update + launch, never over the screen
    $link.WindowStyle = 7
    $link.Save()

    Write-Host "`nDone. Next time, open 'CEZ Job Finder' on your Desktop." -ForegroundColor Green
    Write-Host "VS Code opens now. $SignIn" -ForegroundColor Green
    if (-not $env:JOBS_NO_LAUNCH) { & $start }
} catch {
    Write-Host "`nInstall stopped: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Run the same steps again. If it fails twice, send a photo of this window to whoever shared CEZ Job Finder with you.'
    if ([Console]::IsInputRedirected) { exit 1 }  # no window to keep open
    Read-Host 'Press Enter to close'
}
