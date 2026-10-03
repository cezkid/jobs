import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import autorun
import cfg
import notify

CLAUDE_EXTENSION = "anthropic.claude-code"
# VS Code ships no PDF viewer: clicking a resume shows "binary ... unsupported text encoding"
# instead of the page. Installed once at launch, so copies installed before this fix get it too.
PDF_EXTENSION = "tomoki1207.pdf"
# marks a mistyped resume fact in red while the user types it (app/workspace.py #yaml.schemas);
# without it the mistake surfaces later as a render error they cannot read
YAML_EXTENSION = "redhat.vscode-yaml"
START_PAGE = cfg.ROOT / "START HERE.md"
# once set up, START HERE ("type set me up") is the wrong page: Today (waiting on you, new jobs)
TODAY_PAGE = cfg.ROOT / "Today.md"
# file named in the same call as the folder opens before VS Code knows its formatted view =>
# plain text, and the tab stays text on every later launch. Opened 6 s after the window it
# comes up formatted (fresh window each way, measured 2026-09-26: 0 s text, 6 s formatted)
START_PAGE_DELAY_S = 6
WINDOWS_LAUNCHER = cfg.APP / "install" / "start-windows.bat"
MAC_ICON_MAKER = cfg.APP / "install" / "make-icon-mac.sh"
MAC_ICON = cfg.APP / "install" / "icon.icns"
WINDOWS_ICON = cfg.APP / "install" / "icon.ico"
WINDOWS_ICON_DONE = cfg.DATA / "desktop-icon-refreshed"
# set => every VS Code call starts a separate VS Code w/ its data + extensions under this dir,
# and Claude trust / Desktop icon land there too: tests + live looks never touch the owner's own
SCRATCH_ENV = "JOBS_VSCODE_DIR"


class VSCodePaths(NamedTuple):
    home: Path  # Desktop icon maker's $HOME
    data: Path  # VS Code user data dir (User/ inside)
    extensions: Path
    settings: Path
    workspace_storage: Path
    global_storage: Path
    claude_state: Path
    desktop: Path


def scratch_dir() -> Path | None:
    value = os.environ.get(SCRATCH_ENV, "").strip()
    return Path(value).resolve() if value else None


def vscode_paths() -> VSCodePaths:
    """Every machine-wide file the launcher reads or writes; read per call, never at import."""
    scratch = scratch_dir()
    if scratch:
        home, data, extensions, claude_state = scratch, scratch / "data", scratch / "ext", scratch / "claude.json"
    else:
        home = Path.home()
        if sys.platform == "win32":
            data = Path(os.environ.get("APPDATA", home)) / "Code"
        elif sys.platform == "darwin":
            data = home / "Library" / "Application Support" / "Code"
        else:
            data = home / ".config" / "Code"
        extensions, claude_state = home / ".vscode" / "extensions", home / ".claude.json"
    user = data / "User"
    return VSCodePaths(home, data, extensions, user / "settings.json", user / "workspaceStorage",
                       user / "globalStorage", claude_state, home / "Desktop")


def scratch_args() -> list[str]:
    """Added to every code call: without them the call drives the VS Code already running."""
    if not scratch_dir():
        return []
    paths = vscode_paths()
    return ["--user-data-dir", str(paths.data), "--extensions-dir", str(paths.extensions)]


def has_claude(extensions: Path | None = None) -> bool:
    return has_extension(CLAUDE_EXTENSION, extensions)


def has_pdf_viewer(extensions: Path | None = None) -> bool:
    # any extension already claiming .pdf counts => never replace the viewer the user chose,
    # and never a second one (two defaults => VS Code asks which editor, every single click)
    for manifest in (extensions or vscode_paths().extensions).glob("*/package.json"):
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


def has_extension(name: str, extensions: Path | None = None) -> bool:
    return any((extensions or vscode_paths().extensions).glob(f"{name}-*"))


def vscode_settings() -> Path:
    return vscode_paths().settings


def workspace_state(root: Path, storage: Path | None = None) -> Path | None:
    """VS Code's remembered layout for this folder; None before its first window."""
    storage = storage or vscode_paths().workspace_storage
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


def ensure_mac_icon(old: Path | None = None, app: Path | None = None) -> None:
    # installs before 2026-09-26 got a .command icon: its Terminal window stays open after VS
    # Code is up. Swapped once for the app icon; this launch's window still shows, later ones don't.
    # App icons before 2026-10-03 show the generic script picture => brand icon swapped in once
    # (maker edits in place: the icon keeps its spot on the Desktop)
    paths = vscode_paths()
    old = old or paths.desktop / f"{cfg.NAME}.command"
    app = app or paths.desktop / f"{cfg.NAME}.app"
    current = app / "Contents" / "Resources" / "applet.icns"
    stale = app.exists() and (not current.exists() or current.read_bytes() != MAC_ICON.read_bytes())
    if old.exists() or stale:
        # maker writes $HOME/Desktop => scratch run rebuilds a scratch icon, never the owner's
        subprocess.run(["bash", str(MAC_ICON_MAKER), str(app)], check=False, capture_output=True,
                       env={**os.environ, "HOME": str(paths.home)})


def windows_shortcut_script(launcher: Path = WINDOWS_LAUNCHER, icon: Path = WINDOWS_ICON) -> str:
    launcher, icon = (str(v).replace("'", "''") for v in (launcher, icon))
    # missing shortcut stays missing; one aimed elsewhere (another copy) is not ours
    return f"""$ErrorActionPreference = 'Stop'
$p = Join-Path ([Environment]::GetFolderPath('Desktop')) '{cfg.NAME}.lnk'
if (-not (Test-Path -LiteralPath $p)) {{ exit 0 }}
$l = (New-Object -ComObject WScript.Shell).CreateShortcut($p)
if ($l.TargetPath -ne '{launcher}') {{ exit 0 }}
$l.IconLocation = '{icon},0'
$l.WindowStyle = 7
$l.Save()
"""


def ensure_windows_icon(done: Path = WINDOWS_ICON_DONE, run=autorun.powershell) -> None:
    # installs before 2026-10-03 got VS Code's icon + a console window over the screen during
    # launch. Shortcut re-pointed once (brand icon, minimized); hidden powershell, never a 2nd icon
    if done.exists():
        return
    if run(windows_shortcut_script()).returncode == 0:
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("")


def claude_project_keys(folder: Path) -> list[str]:
    # Claude looks folder up by forward-slash path, drive letter case-sensitive; VS Code starts it
    # on `c:/...`, terminal on `C:/...` (measured 2026-09-28: backslash or other-case key => untrusted)
    posix = folder.as_posix()
    if len(posix) < 2 or posix[1] != ":":
        return [posix]
    return [posix[0].lower() + posix[1:], posix[0].upper() + posix[1:]]


def ensure_claude_trust(root: Path | None = None, state: Path | None = None) -> None:
    # this folder's .claude/settings.json lets the AI run Job Finder's own steps and write only
    # inside My Jobs / My Resume / My Settings / .data without asking. Claude ignores that list
    # until the folder is trusted (measured 2026-09-26: untrusted => every write blocked; trusted
    # => those folders written, a file beside them still blocked). Trust is kept per folder, so
    # nothing changes in the user's other projects - unlike auto mode, which is user-wide only.
    state = state or vscode_paths().claude_state
    try:
        current = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
    except (OSError, ValueError):
        return
    if not isinstance(current, dict):
        return
    projects = current.setdefault("projects", {})
    if not isinstance(projects, dict):
        return
    untrusted = [k for k in claude_project_keys(root or cfg.ROOT)
                 if not (projects.get(k) or {}).get("hasTrustDialogAccepted")]
    if not untrusted:
        return
    for key in untrusted:
        projects[key] = {**(projects.get(key) or {}), "hasTrustDialogAccepted": True}
    try:
        state.parent.mkdir(parents=True, exist_ok=True)  # scratch dir may not exist yet
        state.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass

def chosen_ai() -> str | None:
    import ai  # here, not on top: ai imports this module
    return ai.current()


def write_workspace(choice: str | None) -> None:
    import workspace
    try:
        workspace.write(choice)
    except OSError:
        pass  # last launch's file still opens the window


def code(args: list[str], quiet: bool = False) -> None:
    exe = shutil.which("code")
    if not exe:
        sys.exit(f"VS Code not found; run the {cfg.NAME} installer again")
    # VS Code started cold inherits console => launcher's terminal window stays up until VS Code
    # quits, and closing it can take VS Code down (measured 2026-09-28, Windows Terminal)
    own_hidden_console = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.run([exe, *scratch_args(), *args], check=False, capture_output=quiet, creationflags=own_hidden_console)


def first_page(settings: Path | None = None, page: Path | None = None) -> Path:
    """START HERE until search settings exist, then Today, rebuilt now so a page last written days
    ago never shows old news. Rebuild fails => the last Today page still beats setup steps; none
    yet => START HERE. The launcher itself must never fail on it."""
    settings, page = settings or cfg.config_path(), page or TODAY_PAGE
    if not settings.exists():
        return START_PAGE
    try:
        import today  # here, not on top: a broken page module must not stop VS Code opening
        config = cfg.load(settings)
        file_jobs(config)
        return today.write(config, page)
    except (Exception, SystemExit):
        return page if page.exists() else START_PAGE


def file_jobs(config: dict) -> None:
    """Every job folder under the stage its status names (one moved by hand, one a file kept from
    moving last time) before the page is built. Never stops the launch: what can't move now
    waits for the next one."""
    try:
        import status
        status.sort_jobs(config)
    except (Exception, SystemExit):
        pass


def main() -> None:
    if sys.platform == "win32":
        register_protocol()
        ensure_windows_icon()
    if sys.platform == "darwin":
        ensure_mac_icon()
    # before VS Code opens => file list shows the private folders even on a brand-new install
    cfg.ensure_private_dirs()
    # before VS Code opens => the first click on a resume already shows the page
    ensure_pdf_viewer()
    # before VS Code opens => a typo in the resume facts is underlined on the first edit
    ensure_yaml_checker()
    choice = chosen_ai()
    # before VS Code opens => the window comes up with this user's chat (Copilot's built-in one
    # shown, or hidden for Claude/ChatGPT), never reloading mid-chat
    write_workspace(choice)
    claude = has_claude()
    if claude:
        ensure_claude_trust()
    if claude or choice == "copilot":
        ensure_chat_sidebar()
    # trust off for this window only => no "trust the authors?" dialog. Chat comes up in the
    # right-hand sidebar beside this page (app/workspace.py #secondarySideBar). No
    # vscode://anthropic.claude-code/open link: it always opens chat as a tab in the active
    # group, on top of START HERE, and every file the AI then opens lands on top of the chat
    # (extension 2.1.283, measured 2026-09-26)
    window = ["--disable-workspace-trust", str(cfg.ROOT)]
    code(window)
    page = first_page()  # while the window comes up
    time.sleep(START_PAGE_DELAY_S)
    code([*window, str(page)])  # folder again => lands in this window, not the last used


if __name__ == "__main__":
    main()
