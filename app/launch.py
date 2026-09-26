import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

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
CLAUDE_STATE = Path.home() / ".claude.json"
START_PAGE = cfg.ROOT / "START HERE.md"
# file named in the same call as the folder opens before VS Code knows its formatted view =>
# plain text, and the tab stays text on every later launch. Opened 6 s after the window it
# comes up formatted (fresh window each way, measured 2026-09-26: 0 s text, 6 s formatted)
START_PAGE_DELAY_S = 6
WINDOWS_LAUNCHER = cfg.APP / "install" / "start-windows.bat"
MAC_ICON_MAKER = cfg.APP / "install" / "make-icon-mac.sh"
OLD_MAC_ICON = Path.home() / "Desktop" / f"{cfg.NAME}.command"

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


def workspace_state(root: Path, storage: Path | None = None) -> Path | None:
    """VS Code's remembered layout for this folder; None before its first window."""
    storage = storage or vscode_settings().parent / "workspaceStorage"
    for marker in storage.glob("*/workspace.json"):
        try:
            uri = json.loads(marker.read_text(encoding="utf-8")).get("folder") or ""
        except (OSError, ValueError):
            continue
        folder = Path(url2pathname(unquote(urlparse(uri).path)))
        if os.path.normcase(folder) == os.path.normcase(root) and (marker.parent / "state.vscdb").exists():
            return marker.parent / "state.vscdb"
    return None


def ensure_chat_sidebar(root: Path | None = None, storage: Path | None = None) -> None:
    # workspace setting secondarySideBar.defaultVisibility only counts in a folder's first window;
    # after the user closes the sidebar once VS Code keeps it closed => only START HERE, no chat
    # (measured 2026-09-26). The one remembered flag is set back before the window opens.
    state = workspace_state(root or cfg.ROOT, storage)
    if not state:
        return
    try:
        with sqlite3.connect(state, timeout=2) as db:
            db.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                       ("workbench.auxiliaryBar.hidden", "false"))
        db.close()
    except sqlite3.Error:
        pass


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


def ensure_mac_icon(old: Path = OLD_MAC_ICON) -> None:
    # installs before 2026-09-26 got a .command icon: its Terminal window stays open after VS
    # Code is up. Swapped once for the app icon; this launch's window still shows, later ones don't
    if old.exists():
        subprocess.run(["bash", str(MAC_ICON_MAKER)], check=False, capture_output=True)


def ensure_claude_trust(root: Path | None = None, state: Path = CLAUDE_STATE) -> None:
    # this folder's .claude/settings.json lets the AI run Job Finder's own steps and write only
    # inside My Jobs / My Resume / My Settings / .data without asking. Claude ignores that list
    # until the folder is trusted (measured 2026-09-26: untrusted => every write blocked; trusted
    # => those folders written, a file beside them still blocked). Trust is kept per folder, so
    # nothing changes in the user's other projects - unlike auto mode, which is user-wide only.
    folder = str(root or cfg.ROOT)
    try:
        current = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
    except (OSError, ValueError):
        return
    if not isinstance(current, dict):
        return
    projects = current.setdefault("projects", {})
    if not isinstance(projects, dict) or (projects.get(folder) or {}).get("hasTrustDialogAccepted"):
        return
    projects[folder] = {**(projects.get(folder) or {}), "hasTrustDialogAccepted": True}
    try:
        state.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
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
    if sys.platform == "darwin":
        ensure_mac_icon()
    # before VS Code opens => file list shows the private folders even on a brand-new install
    cfg.ensure_private_dirs()
    # before VS Code opens => the first click on a resume already shows the page
    ensure_pdf_viewer()
    # before VS Code opens => a typo in the resume facts is underlined on the first edit
    ensure_yaml_checker()
    if has_claude():
        ensure_claude_trust()
        ensure_chat_sidebar()
    # trust off for this window only => no "trust the authors?" dialog. Chat comes up in the
    # right-hand sidebar beside this page (.vscode/settings.json #secondarySideBar). No
    # vscode://anthropic.claude-code/open link: it always opens chat as a tab in the active
    # group, on top of START HERE, and every file the AI then opens lands on top of the chat
    # (extension 2.1.283, measured 2026-09-26)
    window = ["--disable-workspace-trust", str(cfg.ROOT)]
    code(window)
    time.sleep(START_PAGE_DELAY_S)
    code([*window, str(START_PAGE)])  # folder again => lands in this window, not the last used


if __name__ == "__main__":
    main()
