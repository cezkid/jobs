import re

import cfg
from window import brand

INSTALL = cfg.APP / "install"
SPLASH = INSTALL / "splash-windows.ps1"
START = INSTALL / "start-windows.bat"
# not runnable off Windows (no PowerShell 5.1 / WinForms) => source checks here, live check = owner's
# (app/docs/app-window.md "Owner checks still open")


def code() -> str:
    """The script w/o its comments: a rule named in a comment is not the rule kept."""
    return "\n".join(line.split("#")[0] if not re.search(r"'#[0-9a-f]{6}'", line) else line.split("  #")[0]
                     for line in SPLASH.read_text(encoding="utf-8").splitlines())


def test_windows_launcher_is_still_one_command_line():
    raw = START.read_bytes()
    # cmd re-reads the file by byte offset after update swaps it => every command on one line, exit /b on it
    assert raw.endswith(b"\r\n") and b"\n" not in raw.replace(b"\r\n", b"")
    lines = raw.decode("ascii").split("\r\n")[:-1]
    header = [line for line in lines if line.startswith(("@echo off", "cd /d ", "set ", "::"))]
    commands = [line for line in lines if line not in header]
    assert lines[:3] == header[:3] and len(commands) == 1 and lines[-1] == commands[0]
    assert commands[0].endswith(" & exit /b")


def test_windows_launcher_shows_the_splash_before_update_and_closes_it_when_launch_fails():
    line = START.read_bytes().decode("ascii").split("\r\n")[-2]
    steps = [
        # `if` w/o the brackets would swallow the rest of the line whenever .data exists
        "(if not exist .data mkdir .data) & ",
        # a copy => update can rename app\ while the splash runs
        r"copy /y app\install\splash-windows.ps1 .data\ >nul & ",
        r'start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File .data\splash-windows.ps1 "%CD%" & ',
        "uv run app/jobs.py update & ",
        # || binds tighter than &: ready signal only when launch fails, exit either way
        r"uv run app/jobs.py launch || type nul > .data\window-ready & ",
        "exit /b",
    ]
    assert line == "".join(steps)
    # start /b shares the console: hidden, the installer's own PowerShell window would vanish
    assert "windowstyle" not in line.lower() and "hidden" not in line.lower()


def test_windows_splash_source_keeps_the_rules():
    body = SPLASH.read_text(encoding="utf-8")
    assert body.isascii()  # PowerShell 5.1 reads a file w/o BOM as ANSI
    src = code()
    for needed in ("EnableVisualStyles()", "$form.TopMost = $true", "$form.ShowInTaskbar = $false", "::Marquee",
                   "$CapS = 45", "ReadAllBytes(", "System.IO.MemoryStream", "(Get-Process -Id $PID).StartTime",
                   "AppsUseLightTheme", r"'.data\look'", r"'.data\window-ready'", "FormBorderStyle]::None",
                   "Screen]::FromPoint([System.Windows.Forms.Cursor]::Position)"):
        assert needed in src, needed
    # a file under app\ kept open blocks update's rename; a compiled type = csc temp files (antivirus)
    for banned in ("Image.FromFile", "FromFile(", "-TypeDefinition", "WindowStyle Hidden", "ExtractAssociatedIcon",
                   "Start-Sleep", "ShowDialog"):
        assert banned.lower() not in src.lower(), banned
    # no pid file / single instance: a reused pid would hide the splash for good ($PID = its own start time only)
    assert src.lower().count("pid") == 1 and "splash-start" not in src
    # Marquee only animates w/ visual styles on, set before the first control
    assert src.index("EnableVisualStyles()") < src.index("New-Object System.Windows.Forms.Form")


def test_windows_splash_tick_checks_the_cap_first_and_closes_on_any_error():
    src = code()
    tick = src[src.index("$timer.Add_Tick({"):src.index("$timer.Start()")]
    body = tick.split("Add_Tick({", 1)[1].strip()
    assert body.startswith("try {")  # the whole tick
    assert re.search(r"\} catch \{ \$form\.Close\(\) \}\s*\}\)\s*$", tick)
    cap, ready = tick.index("-ge $CapS"), tick.index("GetLastWriteTimeUtc($ready)")
    assert cap < ready
    # >= against the start rounded down to the second (whole-second filesystems); never a slack window
    assert "GetLastWriteTimeUtc($ready) -ge $since" in tick
    assert "$since.AddTicks(-($since.Ticks % [TimeSpan]::TicksPerSecond))" in src
    assert "AddSeconds" not in src
    # the script as a whole: any failure = no splash, never an error in the shared console
    lines = [line for line in src.splitlines() if line.strip()]
    assert lines[-1].rstrip() == "} catch { }"
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")


def colours() -> dict:
    found = {}
    for look, parts in re.findall(r"^\s*(light|dark)\s*=\s*@\{([^}]*)\}", SPLASH.read_text(encoding="utf-8"), re.M):
        found[look] = dict(re.findall(r"(\w+) = '(#[0-9a-f]{6})'", parts))
    return found


def test_windows_splash_colours_are_brand_tokens_and_readable():
    found = colours()
    assert found == {
        "light": {"background": brand.PAPER, "title": brand.INK, "text": brand.INK, "hint": brand.INK_2, "edge": brand.RULE},
        "dark": {"background": brand.DESK, "title": brand.TEXT_DARK, "text": brand.TEXT_DARK, "hint": brand.TEXT_DARK_2,
                 "edge": brand.LINE},
    }
    for look, parts in found.items():
        for part in ("title", "text", "hint"):
            assert brand.contrast(parts[part], parts["background"]) >= 4.5, (look, part)
    # every colour in the file is one of those: none typed in elsewhere, never yellow (= clickable)
    body = SPLASH.read_text(encoding="utf-8").lower()
    assert set(re.findall(r"#[0-9a-f]{6}\b", body)) == {v for parts in found.values() for v in parts.values()}
    assert not {brand.MARK, brand.MARK_2} & set(re.findall(r"#[0-9a-f]{6}\b", body))


def test_windows_splash_says_the_same_words_as_the_mac_one():
    mac = (INSTALL / "splash-mac.js").read_text(encoding="utf-8")
    for words in ("CEZ Job Finder", "Opening...", "The first start can take a minute."):
        assert f"'{words}'" in code() and f"'{words}'" in mac, words
