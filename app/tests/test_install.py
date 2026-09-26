import re

import cfg

PAGE = cfg.ROOT / "docs" / "index.html"
README = cfg.ROOT / "README.md"
INSTALL = cfg.APP / "install"


def page_line(os: str) -> str:
    return re.search(rf"{os}: `(.+?)`,", PAGE.read_text(encoding="utf-8")).group(1).replace("${RAW}", "https://x/")


def readme_line(start: str) -> str:
    return next(l for l in README.read_text(encoding="utf-8").splitlines() if l.startswith(start))


def page_steps() -> str:
    body = PAGE.read_text(encoding="utf-8")
    return body[body.index('<div class="desktop">'):body.index("<footer>")]


def test_windows_line_survives_being_pasted_into_powershell():
    # "$env:JOBS_AI=..." pasted into PowerShell => outer shell expands $env before the child runs
    for line in page_line("win"), readme_line("irm "):
        assert "$" not in line, line


def test_windows_line_runs_in_the_window_and_script_lets_uv_installer_run():
    # "powershell -ExecutionPolicy Bypass -c 'irm | iex'" => child got an empty download on a real PC
    # ("iex: Cannot bind argument to parameter 'Command' because it is an empty string") while the
    # same irm typed in the window got the whole file => run in the window, no second powershell
    for line in page_line("win"), readme_line("irm "):
        assert re.fullmatch(r"irm https://\S+/install-windows\.ps1 \| iex", line), line
    # Windows default policy Restricted => uv's installer stops: "requires an execution policy in
    # [Unrestricted, RemoteSigned, Bypass]"; script sets Bypass for this window only
    script = (INSTALL / "install-windows.ps1").read_text(encoding="utf-8")
    assert script.index("Set-ExecutionPolicy Bypass -Scope Process") < script.index("astral.sh/uv/install.ps1")
    assert "CurrentUser" not in script  # never changes the user's setting for good


def test_one_line_per_computer_and_installer_asks_the_ai():
    # AI picked on the page => hidden, per-choice line; one visible line + a question in the window
    for line in page_line("win"), page_line("mac"), readme_line("irm "), readme_line("curl "):
        assert "JOBS_AI" not in line and not re.search(r"\s[12]\s*\"?$", line), line
    assert "data-ai" not in PAGE.read_text(encoding="utf-8")
    for name in "install-windows.ps1", "install-mac.sh":
        script = (INSTALL / name).read_text(encoding="utf-8")
        assert "Which AI do you pay for?" in script and "--list-extensions" in script, name


def test_steps_open_the_window_by_clicking_not_key_combos():
    # security software blocks download-and-run lines typed into Win+R (ClickFix pattern);
    # key combos are also where non-technical users get lost
    steps = page_steps()
    assert "PowerShell" in steps and "Terminal" in steps
    assert not re.search(r"<kbd>(Windows key|Win|Cmd|Ctrl)</kbd>", steps)


def test_windows_downloads_never_stop_on_parsing_prompt():
    # Windows PowerShell 5.1 since Dec 2025 (CVE-2025-54100): Invoke-WebRequest w/o -UseBasicParsing
    # asks "Script Execution Risk ... continue?", Enter = No => download cancelled mid-install
    script = (INSTALL / "install-windows.ps1").read_text(encoding="utf-8")
    calls = [l for l in script.splitlines() if re.search(r"\b(Invoke-WebRequest|iwr)\b", l) and not l.lstrip().startswith("#")]
    assert calls
    for line in calls:
        assert "-UseBasicParsing" in line, line
