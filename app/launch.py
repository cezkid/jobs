import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cfg
import notify

CLAUDE_EXTENSION = "anthropic.claude-code"
# VS Code ships no PDF viewer: clicking a resume shows "binary ... unsupported text encoding"
# instead of the page. Installed once at launch, so copies installed before this fix get it too.
PDF_EXTENSION = "tomoki1207.pdf"
# marks a mistyped resume fact in red while the user types it (.vscode/settings.json #yaml.schemas);
# without it the mistake surfaces later as a render error they cannot read
YAML_EXTENSION = "redhat.vscode-yaml"
VSCODE_EXTENSIONS = Path.home() / ".vscode" / "extensions"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
START_PAGE = cfg.ROOT / "START HERE.md"
WINDOWS_LAUNCHER = cfg.APP / "install" / "start-windows.bat"

def has_claude(extensions: Path = VSCODE_EXTENSIONS) -> bool:
    return has_extension(CLAUDE_EXTENSION, extensions)


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


def has_extension(name: str, extensions: Path = VSCODE_EXTENSIONS) -> bool:
    return any(extensions.glob(f"{name}-*"))


def vscode_settings() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "Code" / "User" / "settings.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    return Path.home() / ".config" / "Code" / "User" / "settings.json"


def add_setting(text: str, line: str) -> str:
    """One more setting into VS Code's own settings file, left otherwise byte for byte.

    That file is JSON with comments and trailing commas allowed, and developers' copies use both;
    reading it as JSON and writing it back drops every comment they wrote, so the text is edited
    in place instead.
    """
    if "}" not in text:
        return "{\n  " + line + "\n}\n"
    end = text.rindex("}")
    head = text[:end].rstrip()
    separator = "" if head.endswith(("{", ",")) else ","
    return f"{head}{separator}\n  {line}\n" + text[end:]


TELEMETRY = '"redhat.telemetry.enabled": false'


def ensure_yaml_checker(settings: Path | None = None) -> None:
    # the extension asks each new user to decide about telemetry in a popup. Answering that is no
    # part of looking for a job, so it is answered here first - only when they have not answered.
    settings = settings or vscode_settings()
    try:
        text = settings.read_text(encoding="utf-8") if settings.exists() else ""
        if "redhat.telemetry.enabled" not in text:
            settings.parent.mkdir(parents=True, exist_ok=True)
            settings.write_text(add_setting(text, TELEMETRY), encoding="utf-8")
    except OSError:
        pass
    if not has_extension(YAML_EXTENSION):
        code(["--install-extension", YAML_EXTENSION, "--force"], quiet=True)


def register_protocol() -> None:
    # toast click -> jobfinder: URL -> Desktop launcher; per-user key, no admin
    import winreg
    key = rf"Software\Classes\{notify.PROTOCOL}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"URL:{cfg.NAME}")
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
        sys.exit(f"VS Code not found; run the {cfg.NAME} installer again")
    subprocess.run([exe, *args], check=False, capture_output=quiet)


def main() -> None:
    if sys.platform == "win32":
        register_protocol()
    # before VS Code opens => file list shows the private folders even on a brand-new install
    cfg.ensure_private_dirs()
    # before VS Code opens => the first click on a resume already shows the page
    ensure_pdf_viewer()
    # before VS Code opens => a typo in the resume facts is underlined on the first edit
    ensure_yaml_checker()
    if has_claude():
        ensure_auto_mode()
    # trust off for this window only => no "trust the authors?" dialog. Chat comes up in the
    # right-hand sidebar beside this page (.vscode/settings.json #secondarySideBar). No
    # vscode://anthropic.claude-code/open link: it always opens chat as a tab in the active
    # group, on top of START HERE, and every file the AI then opens lands on top of the chat
    # (extension 2.1.283, measured 2026-09-26)
    code(["--disable-workspace-trust", str(cfg.ROOT), str(START_PAGE)])


if __name__ == "__main__":
    main()
