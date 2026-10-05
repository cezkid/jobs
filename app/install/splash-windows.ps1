# Loading splash for Windows: on screen from the double-click until the start page shows.
# powershell -NoProfile -ExecutionPolicy Bypass -File .data\splash-windows.ps1 <root folder>
# start-windows.bat copies it to .data first (update renames app\ while it runs) and starts it before update.
# Closes when .data\window-ready is as new as this process's start, after $CapS, or on a click in it.
# Windows PowerShell 5.1 + WinForms (both ship w/ Windows). ASCII only: 5.1 reads a file w/o BOM as ANSI.
# Never a C# type compiled here (csc temp files: antivirus, Smart App Control), never a pid file.
# Why outside VS Code + every rule below: app/docs/app-window.md, plan-ejf.13.
param([string]$Root = '.')

# app/window/brand.py tokens (test_splash_windows.py holds them equal); never yellow: yellow = clickable
$Colours = @{
    light = @{ background = '#ffffff'; title = '#000000'; text = '#000000'; hint = '#3a3a3a'; edge = '#c8c8c8' }  # paper, ink, ink, ink-2, rule
    dark  = @{ background = '#1c1c1e'; title = '#f2f2f2'; text = '#f2f2f2'; hint = '#bdbdbd'; edge = '#48484a' }  # desk, text-dark, text-dark, text-dark-2, line
}
$Words = @{ title = 'CEZ Job Finder'; text = 'Opening...'; hint = 'The first start can take a minute.' }
$CapS = 45
$PollMs = 100
$Width = 380
$Height = 250
$IconSize = 72

# anything going wrong = no splash; the start itself never depends on it, nothing printed in the shared console
try {
    $began = Get-Date
    # this process's start, down to the whole second: a ready file written in the same second on a
    # whole-second filesystem still counts (>=), last start's file never does
    $since = (Get-Process -Id $PID).StartTime.ToUniversalTime()
    $since = $since.AddTicks(-($since.Ticks % [TimeSpan]::TicksPerSecond))
    $ready = Join-Path $Root '.data\window-ready'

    # read now, into memory: update swaps app\ for a new one while the splash is up => no file under it kept open
    $iconBytes = $null
    try { $iconBytes = [System.IO.File]::ReadAllBytes((Join-Path $Root 'app\install\icon.ico')) } catch { }

    # .data\look light | dark wins (app/look.py); anything else = the computer's app theme
    $look = ''
    try { $look = ([System.IO.File]::ReadAllText((Join-Path $Root '.data\look'))).Trim().ToLower() } catch { }
    if ($look -ne 'light' -and $look -ne 'dark') {
        $look = 'light'
        try {
            $theme = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name AppsUseLightTheme -ErrorAction Stop
            if ($theme.AppsUseLightTheme -eq 0) { $look = 'dark' }
        } catch { }
    }
    $c = $Colours[$look]

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    # before any control exists: w/o it the Marquee bar never moves
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $Words.title
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
    $form.TopMost = $true  # VS Code's window would cover a normal one => blank again
    $form.ShowInTaskbar = $false
    $form.ControlBox = $false
    $form.BackColor = [System.Drawing.ColorTranslator]::FromHtml($c.background)
    $form.ClientSize = New-Object System.Drawing.Size($Width, $Height)
    # centred on the screen the pointer is on
    $area = [System.Windows.Forms.Screen]::FromPoint([System.Windows.Forms.Cursor]::Position).WorkingArea
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
    $form.Location = New-Object System.Drawing.Point(
        [int]($area.X + ($area.Width - $Width) / 2), [int]($area.Y + ($area.Height - $Height) / 2))

    # each part closes the splash on a click, like the form itself
    $close = { $form.Close() }
    $form.Add_Click($close)

    if ($iconBytes) {
        try {
            $stream = New-Object System.IO.MemoryStream(, $iconBytes)
            $icon = New-Object System.Drawing.Icon($stream, 256, 256)
            $picture = New-Object System.Windows.Forms.PictureBox
            $picture.Image = $icon.ToBitmap()
            $picture.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
            $picture.SetBounds([int](($Width - $IconSize) / 2), 34, $IconSize, $IconSize)
            $picture.Add_Click($close)
            $form.Controls.Add($picture)
        } catch { }
    }

    function Add-Line([string]$words, [System.Drawing.Font]$font, [string]$hex, [int]$top, [int]$tall) {
        $label = New-Object System.Windows.Forms.Label
        $label.Text = $words
        $label.Font = $font
        $label.ForeColor = [System.Drawing.ColorTranslator]::FromHtml($hex)
        $label.BackColor = $form.BackColor
        $label.AutoSize = $false
        $label.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
        $label.SetBounds(1, $top, $Width - 2, $tall)
        $label.Add_Click($close)
        $form.Controls.Add($label)
    }
    $bold = [System.Drawing.FontStyle]::Bold
    Add-Line $Words.title (New-Object System.Drawing.Font('Segoe UI', 15, $bold)) $c.title 116 32
    Add-Line $Words.text (New-Object System.Drawing.Font('Segoe UI', 10.5)) $c.text 182 22
    Add-Line $Words.hint (New-Object System.Drawing.Font('Segoe UI', 9)) $c.hint 208 20

    $bar = New-Object System.Windows.Forms.ProgressBar
    $bar.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
    $bar.MarqueeAnimationSpeed = 30
    $bar.SetBounds([int](($Width - 160) / 2), 160, 160, 8)
    $bar.Add_Click($close)
    $form.Controls.Add($bar)

    # no border, no shadow => one quiet line round it, else paper on a white screen has no edge
    $edge = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($c.edge))
    $form.Add_Paint({ param($from, $paint) $paint.Graphics.DrawRectangle($edge, 0, 0, $Width - 1, $Height - 1) })
    # the Desktop shortcut starts the launcher minimized: the splash is never to follow it there
    $form.Add_Shown({ $form.WindowState = [System.Windows.Forms.FormWindowState]::Normal })

    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = $PollMs
    $timer.Add_Tick({
        # an error left in a tick would repeat 10 times a second => close instead
        try {
            # cap first: nothing below may keep the splash up past it
            if (((Get-Date) - $began).TotalSeconds -ge $CapS) { $form.Close(); return }
            if ([System.IO.File]::Exists($ready) -and [System.IO.File]::GetLastWriteTimeUtc($ready) -ge $since) { $form.Close() }
        } catch { $form.Close() }
    })
    $timer.Start()
    [System.Windows.Forms.Application]::Run($form)
    $timer.Stop()
} catch { }
