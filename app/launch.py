import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import cfg
import notify

CLAUDE_EXTENSION = "anthropic.claude-code"
VSCODE_EXTENSIONS = Path.home() / ".vscode" / "extensions"
START_PAGE = cfg.ROOT / "START HERE.md"
WINDOWS_LAUNCHER = cfg.APP / "install" / "start-windows.bat"
FIRST_PROMPT = "set me up"
RETURN_PROMPT = "any new jobs?"


def prompt() -> str:
    return RETURN_PROMPT if cfg.SETTINGS.exists() else FIRST_PROMPT


def claude_uri(text: str) -> str:
    return f"vscode://{CLAUDE_EXTENSION}/open?prompt={quote(text)}"


def has_claude(extensions: Path = VSCODE_EXTENSIONS) -> bool:
    return any(extensions.glob(f"{CLAUDE_EXTENSION}-*"))


def register_protocol() -> None:
    # toast click -> jobfinder: URL -> Desktop launcher; per-user key, no admin
    import winreg
    key = rf"Software\Classes\{notify.PROTOCOL}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:Job Finder")
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{key}\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{WINDOWS_LAUNCHER}"')


def code(args: list[str]) -> None:
    exe = shutil.which("code")
    if not exe:
        sys.exit("VS Code not found; run the Job Finder installer again")
    subprocess.run([exe, *args], check=False)


def main() -> None:
    if sys.platform == "win32":
        register_protocol()
    # trust off for this window only => no "trust the authors?" dialog
    code(["--disable-workspace-trust", str(cfg.ROOT), str(START_PAGE)])
    # separate call: --open-url beside folder args drops the folder (measured 2026-09-19)
    if has_claude():
        code(["--open-url", claude_uri(prompt())])


if __name__ == "__main__":
    main()
