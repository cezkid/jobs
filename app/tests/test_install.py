import os
import re
import shutil
import subprocess

import pytest

import cfg

PAGE = cfg.ROOT / "docs" / "index.html"
README = cfg.ROOT / "README.md"
INSTALL = cfg.APP / "install"


def page_line(os: str) -> str:
    return re.search(rf"{os}: `(.+?)`,", PAGE.read_text(encoding="utf-8")).group(1).replace("${SITE}", "https://x/")


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
        assert re.fullmatch(r"irm https://\S+ \| iex", line), line
    # Windows default policy Restricted => uv's installer stops: "requires an execution policy in
    # [Unrestricted, RemoteSigned, Bypass]"; script sets Bypass for this window only
    script = (INSTALL / "install-windows.ps1").read_text(encoding="utf-8")
    assert script.index("Set-ExecutionPolicy Bypass -Scope Process") < script.index("astral.sh/uv/install.ps1")
    assert "CurrentUser" not in script  # never changes the user's setting for good


def test_one_line_per_computer_and_installer_asks_the_ai():
    # AI picked on the page => hidden, per-choice line; one visible line + a question in the window
    for line in page_line("win"), page_line("mac"), readme_line("irm "), readme_line("curl "):
        assert "JOBS_AI" not in line and not re.search(r"\s[123]\s*\"?$", line), line
    assert "data-ai" not in PAGE.read_text(encoding="utf-8")
    for name in "install-windows.ps1", "install-mac.sh":
        script = (INSTALL / name).read_text(encoding="utf-8")
        assert "Which AI do you use?" in script and "--list-extensions" in script, name


def test_short_lines_fetch_exact_copies_of_the_install_scripts():
    # Pages serves docs/ only, no server redirects => docs/<os>/index.html = byte copy of the script
    # (index.html => served as text, so irm hands iex a string); edit app/install, then cp here
    docs = cfg.ROOT / "docs"
    for os, name in ("mac", "install-mac.sh"), ("win", "install-windows.ps1"):
        assert (docs / os / "index.html").read_bytes() == (INSTALL / name).read_bytes(), f"cp app/install/{name} docs/{os}/index.html"
    assert page_line("mac") == readme_line("curl ").replace("https://jobs.enrriquez.com/", "https://x/")
    assert page_line("win") == readme_line("irm ").replace("https://jobs.enrriquez.com/", "https://x/")
    assert (docs / "CNAME").read_text().strip() + "/" in PAGE.read_text(encoding="utf-8")


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


AI_CHOICES = {"claude": "anthropic.claude-code", "chatgpt": "openai.chatgpt", "copilot": ""}


def script(name: str) -> str:
    return (INSTALL / name).read_text(encoding="utf-8")


def mac_pick(tmp_path, answer=None, env=None, extensions="", saved=None, arg=""):
    # mac installer's own ai_word + pick_ai, run in bash w/ a stub `code` and no real install
    body = script("install-mac.sh")
    funcs = body[body.index("ai_word() {"):body.index("printf '\\n\\033[36mInstalling")]
    (tmp_path / "bin").mkdir(exist_ok=True)
    stub = tmp_path / "bin" / "code"
    stub.write_text(f"#!/bin/bash\nprintf '%s' '{extensions}'\n")
    stub.chmod(0o755)
    if saved is not None:
        (tmp_path / ".data").mkdir(exist_ok=True)
        (tmp_path / ".data" / "ai").write_text(saved)
    run = f'DIR="{tmp_path}"\nhave() {{ command -v "$1" >/dev/null 2>&1; }}\n{funcs}\npick_ai "{arg}"\n'
    full_env = {"PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin", **(env or {})}
    # new session => no /dev/tty, as when nothing is there to ask in
    return subprocess.run(["bash", "-c", run], capture_output=True, text=True, env=full_env,
                          stdin=subprocess.DEVNULL, start_new_session=True)


@pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="mac installer runs in bash")
@pytest.mark.parametrize("given,word", [("1", "claude"), ("Claude", "claude"), ("2", "chatgpt"), (" CHATGPT ", "chatgpt"),
                                        ("3", "copilot"), ("copilot", "copilot")])
def test_mac_accepts_number_or_name_any_case(tmp_path, given, word):
    assert mac_pick(tmp_path, env={"JOBS_AI": given}).stdout.strip() == word
    assert mac_pick(tmp_path, arg=given).stdout.strip() == word


@pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="mac installer runs in bash")
def test_mac_order_saved_choice_then_claude_then_chatgpt_never_copilot(tmp_path):
    both = "Anthropic.Claude-Code\nopenai.chatgpt\ngithub.copilot-chat\n"
    assert mac_pick(tmp_path, saved="copilot\n", extensions=both).stdout.strip() == "copilot"
    assert mac_pick(tmp_path, env={"JOBS_AI": "2"}, saved="copilot\n").stdout.strip() == "chatgpt"
    (tmp_path / ".data" / "ai").unlink()
    assert mac_pick(tmp_path, extensions=both).stdout.strip() == "claude"  # extension ids any case
    assert mac_pick(tmp_path, extensions="openai.chatgpt\n").stdout.strip() == "chatgpt"


@pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="mac installer runs in bash")
def test_mac_nothing_known_and_no_window_to_ask_stops_never_silent_claude(tmp_path):
    # Copilot built into VS Code => its extension says nothing; unknown word => not taken either
    out = mac_pick(tmp_path, env={"JOBS_AI": "gemini"}, extensions="github.copilot-chat\n")
    assert out.returncode != 0 and out.stdout.strip() == ""
    assert "Terminal" in out.stderr


@pytest.mark.parametrize("name", ["install-mac.sh", "install-windows.ps1"])
def test_installer_three_way_choice_copilot_installs_nothing_choice_saved(name):
    body = script(name)
    for line in ("1 = Claude (Pro or Max)", "2 = ChatGPT (Plus or Pro)", "3 = GitHub Copilot Pro ($10 a month)",
                 "Type 1, 2 or 3"):
        assert line in body, line
    for number, word in ("1", "claude"), ("2", "chatgpt"), ("3", "copilot"):
        assert re.search(rf"'?{number}'?, '?{word}'?|{number}\|{word}", body), word
    # each AI named on its own => no "anything but 2 = Claude" fallback
    assert "else ai_extension=anthropic.claude-code" not in body and "} else { 'anthropic.claude-code' }" not in body
    mac = name.endswith(".sh")
    for word, extension in AI_CHOICES.items():
        # copilot => empty extension => step 3 skips the install
        assigned = f"{word}) ai_extension={extension or ''}\n" if mac else f"'{word}' {{ '{extension or ''}', "
        assert assigned in body, assigned
    assert ('if [ -n "$ai_extension" ]; then' if mac else "if ($AiExtension) {") in body
    assert "github.copilot" not in body  # never installed, never used to guess
    assert re.search(r"\.data[/\\]ai", body)
    assert "No GitHub account? Make one with your Google or Apple account." in body
    assert "Click the ChatGPT icon at the top left, then Sign in" in body


def test_unknown_answer_asks_again_and_no_window_stops():
    body = script("install-mac.sh")
    loop = body[body.index("  while true; do"):body.index("printf '\\n\\033[36mInstalling")]
    assert 'word=$(ai_word "$answer")' in loop and 'if [ -n "$word" ]; then echo "$word"; return; fi' in loop
    assert "ai=$(pick_ai \"${1:-}\") || exit 1" in body
    body = script("install-windows.ps1")
    pick = body[body.index("function Pick-Ai"):body.index("try {")]
    assert "while ($true)" in pick and "if ($word) { return $word }" in pick
    assert "throw 'Could not ask which AI you use." in pick
    assert "Set-Content -Path (Join-Path $Dir '.data\\ai') -Value $Ai" in body
