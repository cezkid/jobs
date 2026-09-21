import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import cfg
import notify

CLAUDE_EXTENSION = "anthropic.claude-code"
# VS Code ships no PDF viewer: clicking a resume shows "binary ... unsupported text encoding"
# instead of the page. Installed once at launch, so copies installed before this fix get it too.
PDF_EXTENSION = "tomoki1207.pdf"
VSCODE_EXTENSIONS = Path.home() / ".vscode" / "extensions"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
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


def has_pdf_viewer(extensions: Path = VSCODE_EXTENSIONS) -> bool:
    # any extension already claiming .pdf counts => never replace the viewer the user chose,
    # and never a second one (two defaults => VS Code asks which editor, every single click)
    for manifest in extensions.glob("*/package.json"):
        try:
            contributes = json.loads(manifest.read_text(encoding="utf-8")).get("contributes") or {}
        except (OSError, ValueError):
            continue
        for editor in contributes.get("customEditors") or []:
            for selector in editor.get("selector") or []:
                if str(selector.get("filenamePattern", "")).lower().endswith(".pdf"):
                    return True
    return False


def ensure_pdf_viewer() -> None:
    if not has_pdf_viewer():
        code(["--install-extension", PDF_EXTENSION, "--force"], quiet=True)


def register_protocol() -> None:
    # toast click -> jobfinder: URL -> Desktop launcher; per-user key, no admin
    import winreg
    key = rf"Software\Classes\{notify.PROTOCOL}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:Job Finder")
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{key}\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{WINDOWS_LAUNCHER}"')


def ensure_auto_mode(settings: Path = CLAUDE_SETTINGS) -> None:
    # Auto mode lets the AI panel answer its own permission questions. Only the user's own
    # Claude settings can turn it on: the same key in this folder's .claude/settings.json is
    # ignored as repo-controlled, and would also outrank the user file (measured 2026-09-21).
    # Without it the user is asked to approve nearly every step Job Finder takes.
    try:
        current = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
    except (OSError, ValueError):
        return
    if not isinstance(current, dict):
        return
    permissions = current.get("permissions") or {}
    if permissions.get("defaultMode"):  # a mode the user picked themselves => leave it alone
        return
    current["permissions"] = {**permissions, "defaultMode": "auto"}
    current["skipAutoPermissionPrompt"] = True  # else first launch asks to opt in to auto mode
    try:
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def code(args: list[str], quiet: bool = False) -> None:
    exe = shutil.which("code")
    if not exe:
        sys.exit("VS Code not found; run the Job Finder installer again")
    subprocess.run([exe, *args], check=False, capture_output=quiet)


def main() -> None:
    if sys.platform == "win32":
        register_protocol()
    # before VS Code opens => file list shows the private folders even on a brand-new install
    cfg.ensure_private_dirs()
    # before VS Code opens => the first click on a resume already shows the page
    ensure_pdf_viewer()
    # trust off for this window only => no "trust the authors?" dialog
    code(["--disable-workspace-trust", str(cfg.ROOT), str(START_PAGE)])
    # separate call: --open-url beside folder args drops the folder (measured 2026-09-19)
    if has_claude():
        ensure_auto_mode()
        code(["--open-url", claude_uri(prompt())])


if __name__ == "__main__":
    main()
