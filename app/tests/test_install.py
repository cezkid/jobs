import re

import cfg

PAGE = cfg.ROOT / "docs" / "index.html"
README = cfg.ROOT / "README.md"
WINDOWS = cfg.APP / "install" / "install-windows.ps1"


def windows_lines():
    page = re.search(r"win: ai => `(.+?)`,", PAGE.read_text(encoding="utf-8")).group(1)
    readme = next(l for l in README.read_text(encoding="utf-8").splitlines() if l.startswith("powershell "))
    return [page.replace("${RAW}", "https://x/").replace("${ai}", "1"), readme]


def test_windows_line_survives_being_pasted_into_powershell():
    # "$env:JOBS_AI=..." pasted into PowerShell => outer shell expands $env before the child runs
    for line in windows_lines():
        assert "$" not in line, line


def test_windows_line_lets_uv_installer_run():
    # Windows default policy Restricted => uv's installer stops: "requires an execution policy in
    # [Unrestricted, RemoteSigned, Bypass]"; Bypass on the line + in script = this window only
    for line in windows_lines():
        assert line.startswith("powershell -ExecutionPolicy Bypass "), line
    script = WINDOWS.read_text(encoding="utf-8")
    assert script.index("Set-ExecutionPolicy Bypass -Scope Process") < script.index("astral.sh/uv/install.ps1")
    assert "CurrentUser" not in script  # never changes the user's setting for good


def test_windows_steps_use_terminal_not_run_box():
    # security software blocks download-and-run lines typed into Win+R (ClickFix pattern)
    page = PAGE.read_text(encoding="utf-8")
    steps = re.search(r'<ol class="steps win-only">(.+?)</ol>', page, re.S).group(1)
    assert "Terminal" in steps and "+ <kbd>R</kbd>" not in steps
