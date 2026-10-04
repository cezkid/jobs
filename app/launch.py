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
from urllib.parse import quote, unquote, urlparse
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
# page for the window extension (app/vscode/start.js) to open formatted as it starts, then delete.
# Named in the same call as the folder on a cold start, it opens as plain text and stays text on
# every later launch (measured 2026-09-26); the extension opens it formatted at once (probe b)
START_MARKER = "start-page"
# when the launcher last ran: the extension opened from the Dock rebuilds a Today older than this
LAUNCH_STAMP = "launched"
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
    shared: Path  # VS Code's app-wide store shared by its windows (1.140: trusted folders)


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
    # VS Code's appSharedDataHome: ~/.vscode-shared (product.json sharedDataFolderName), every OS
    shared = scratch / "shared" if scratch else home / ".vscode-shared"
    return VSCodePaths(home, data, extensions, user / "settings.json", user / "workspaceStorage",
                       user / "globalStorage", claude_state, home / "Desktop", shared)


def scratch_args() -> list[str]:
    """Added to every code call: without them the call drives the VS Code already running."""
    if not scratch_dir():
        return []
    paths = vscode_paths()
    # w/o --shared-data-dir a scratch VS Code reads + writes the owner's ~/.vscode-shared
    return ["--user-data-dir", str(paths.data), "--extensions-dir", str(paths.extensions),
            "--shared-data-dir", str(paths.shared)]


def has_claude(extensions: Path | None = None) -> bool:
    return has_extension(CLAUDE_EXTENSION, extensions)


def has_pdf_viewer(extensions: Path | None = None) -> bool:
    # any extension already claiming .pdf counts => never replace the viewer the user chose,
    # and never a second one (two defaults => VS Code asks which editor, every single click)
    for folder in installed(extensions).values():
        try:
            manifest = json.loads((folder / "package.json").read_text(encoding="utf-8"))
            contributes = manifest.get("contributes") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for editor in contributes.get("customEditors") or []:
            for selector in editor.get("selector") or []:
                if str(selector.get("filenamePattern", "")).lower().endswith(".pdf"):
                    return True
    return False


def has_extension(name: str, extensions: Path | None = None) -> bool:
    return name.lower() in installed(extensions)


EXTENSION_FOLDER = re.compile(r"^(.+?)-\d")


def installed(extensions: Path | None = None, listing: Path | None = None) -> dict[str, Path]:
    """id (lower case) -> folder of each extension Job Finder's window runs.

    Shared extensions dir holds every profile's => a viewer from another profile read as present
    and resumes showed as binary. So the window's own list: Job Finder's profile once it exists,
    else the dir's `extensions.json` (default profile); folder names only w/o either list.
    """
    if extensions is None:
        paths = vscode_paths()
        extensions, location = paths.extensions, profile_location(paths)
        if location and listing is None:
            listing = paths.data / "User" / "profiles" / location / "extensions.json"
            if not listing.exists():
                return {}  # profile made, nothing installed into it yet
    listing = listing or extensions / "extensions.json"
    try:
        entries = json.loads(listing.read_text(encoding="utf-8"))
    except FileNotFoundError:
        found = {}
        for folder in extensions.glob("*-*"):
            match = EXTENSION_FOLDER.match(folder.name)
            if match and folder.is_dir():
                found[match.group(1).lower()] = folder
        return found
    except (OSError, ValueError):
        return {}
    found = {}
    for entry in entries if isinstance(entries, list) else []:
        try:
            relative = entry.get("relativeLocation")  # older lists: absolute path only
            folder = extensions / relative if relative else Path(entry["location"]["path"])
            found[entry["identifier"]["id"].lower()] = folder
        except (KeyError, TypeError, AttributeError):
            continue
    return found


# Job Finder's own VS Code profile: its extensions, settings + chat model, apart from the user's
# other work. Created on a cold start only: a running VS Code holds that list in memory
# (app/docs/app-window.md "Measured")
PROFILE_LOCATION = "cez-job-finder"
PROFILE_ICON = "briefcase"
# app-wide or machine keys a workspace can't set; the default profile's copy doesn't reach this one
PROFILE_SETTINGS = {
    "workbench.welcomePage.walkthroughs.openOnInstall": "false",
    "redhat.telemetry.enabled": "false",
}


def storage_file(paths: VSCodePaths | None = None) -> Path:
    return (paths or vscode_paths()).global_storage / "storage.json"


def read_storage(paths: VSCodePaths | None = None) -> dict | None:
    """VS Code's own state file (plain JSON); {} before its first start, None if unreadable."""
    try:
        data = json.loads(storage_file(paths).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def profile_location(paths: VSCodePaths | None = None) -> str | None:
    for profile in (read_storage(paths) or {}).get("userDataProfiles") or []:
        if isinstance(profile, dict) and profile.get("name") == cfg.NAME and profile.get("location"):
            return str(profile["location"])
    return None


def folder_uri(folder: str, windows: bool | None = None) -> str:
    """Folder as VS Code's URI.file writes it: storage.json keys on it.

    Mac file:///Users/Your%20Name/jobs; Windows file:///c%3A/Users/... (drive lower-cased,
    `:` escaped; vscode-uri 3.2.0, app/docs/app-window/measure/1-windows-key.txt).
    """
    windows = sys.platform == "win32" if windows is None else windows
    path = str(folder)
    if windows:
        path = path.replace("\\", "/")
        if re.match(r"^[A-Za-z]:", path):
            path = "/" + path[0].lower() + path[1:]
    return "file://" + quote(path, safe="/")


def same_folder(uri: str, folder: str, windows: bool | None = None) -> bool:
    # VS Code parses keys => file:///C:/x and file:///c%3A/x name one folder; one key per folder
    windows = sys.platform == "win32" if windows is None else windows
    norm = (lambda p: p.lower()) if windows else (lambda p: p)
    return norm(unquote(uri)) == norm(unquote(folder_uri(folder, windows)))


def process_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes  # os.kill(pid, 0) on Windows ends the process
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code_ = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code_))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code_.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # someone else's process: alive
    return True


def vscode_running(paths: VSCodePaths | None = None) -> bool:
    """VS Code holds this data dir: code.lock names its main process."""
    lock = (paths or vscode_paths()).data / "code.lock"
    try:
        text = lock.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return False
    except OSError:
        return True  # can't tell => as if running: change nothing
    try:
        return process_alive(int(text.split()[0]))
    except (ValueError, IndexError):
        return True


def ensure_profile(root: Path | None = None, paths: VSCodePaths | None = None) -> bool:
    """Job Finder's profile + this folder opening in it. Cold start only; True once in place.

    Running VS Code => nothing now, next cold start does it. Every other profile, association
    and key in storage.json kept.
    """
    paths, root = paths or vscode_paths(), root or cfg.ROOT
    if vscode_running(paths):
        return False
    storage = read_storage(paths)
    if storage is None:
        return False  # unreadable: never overwrite VS Code's own state
    profiles = storage.get("userDataProfiles")
    profiles = profiles if isinstance(profiles, list) else []
    location = profile_location(paths)
    if not location:
        taken = {str(p.get("location")) for p in profiles if isinstance(p, dict)}
        location, n = PROFILE_LOCATION, 2
        while location in taken:
            location, n = f"{PROFILE_LOCATION}-{n}", n + 1
        profiles = [*profiles, {"location": location, "name": cfg.NAME, "icon": PROFILE_ICON}]
    associations = storage.get("profileAssociations")
    associations = dict(associations) if isinstance(associations, dict) else {}
    workspaces = associations.get("workspaces")
    workspaces = workspaces if isinstance(workspaces, dict) else {}
    key = folder_uri(str(root))
    workspaces = {k: v for k, v in workspaces.items() if k == key or not same_folder(k, str(root))}
    workspaces[key] = location
    associations["workspaces"] = workspaces
    updated = {**storage, "userDataProfiles": profiles, "profileAssociations": associations}
    folder = paths.data / "User" / "profiles" / location
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if updated != storage:
            target = storage_file(paths)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".jobfinder")
            temp.write_text(json.dumps(updated, indent=4), encoding="utf-8")
            os.replace(temp, target)
        ensure_profile_settings(folder / "settings.json")
    except OSError:
        return False
    return True


# what the user set in their default profile that a new profile starts without: Copilot's model
# pick (Auto instead of the one they chose, app/docs/app-window.md #6), zoom + text size (a
# smaller window than they set). Copied once, cold start, marker here; never overwrites the profile's
PROFILE_MIGRATED = cfg.DATA / "profile-migrated"
MODEL_KEYS = "chat.currentLanguageModel.%"
CARRIED_SETTINGS = ("window.zoomLevel", "editor.fontSize")
ITEM_TABLE = "CREATE TABLE IF NOT EXISTS ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)"


def migrate_profile(paths: VSCodePaths | None = None, marker: Path | None = None) -> None:
    """Once, after `ensure_profile` (cold): default profile's model pick, zoom + text size into Job
    Finder's. Nothing to copy or a copy fails => no error, marker still written: the setup skill's
    pick-Claude-Sonnet line covers a lost model pick (Copilot)."""
    paths, marker = paths or vscode_paths(), marker or PROFILE_MIGRATED
    location = profile_location(paths)
    if not location or marker.exists() or vscode_running(paths):
        return
    profile = paths.data / "User" / "profiles" / location
    copied = copy_model_pick(paths.global_storage / "state.vscdb", profile / "globalStorage" / "state.vscdb")
    copy_settings(paths.settings, profile / "settings.json")
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"model: {'copied' if copied else 'not copied'}\n", encoding="utf-8")
    except OSError:
        pass


def copy_model_pick(source: Path, target: Path) -> bool:
    """Chat model keys from VS Code's own state db (read-only) into the profile's; True if any copied."""
    if not source.exists():
        return False
    try:
        db = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=2)
        try:
            rows = db.execute("SELECT key, value FROM ItemTable WHERE key LIKE ?", (MODEL_KEYS,)).fetchall()
        finally:
            db.close()
        if not rows:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(target, timeout=2)
        try:
            with db:
                db.execute(ITEM_TABLE)
                # OR IGNORE: a pick already made in the profile wins
                db.executemany("INSERT OR IGNORE INTO ItemTable (key, value) VALUES (?, ?)", rows)
        finally:
            db.close()
    except (sqlite3.Error, OSError):
        return False
    return True


# Outline + Timeline under the file list = code-editor tells. No setting hides a view: VS Code keeps
# the Explorer's hidden views in the profile's state db, this key (app/docs/app-window.md #m)
VIEWS_KEY = "workbench.explorer.views.state.hidden"
HIDDEN_VIEWS = ("outline", "timeline")
# our own row in the same db: once per profile => a view the user shows again stays shown
VIEWS_DONE_KEY = "cez-job-finder.views-hidden"


def hide_side_views(paths: VSCodePaths | None = None) -> None:
    """Cold start, once per profile: Outline + Timeline hidden in Job Finder's profile. Never the
    file list; every other view's entry kept as VS Code wrote it."""
    paths = paths or vscode_paths()
    location = profile_location(paths)
    if not location or vscode_running(paths):
        return
    state = paths.data / "User" / "profiles" / location / "globalStorage" / "state.vscdb"
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(state, timeout=2)
        try:
            with db:
                db.execute(ITEM_TABLE)
                rows = dict(db.execute("SELECT key, value FROM ItemTable WHERE key IN (?, ?)", (VIEWS_KEY, VIEWS_DONE_KEY)).fetchall())
                if VIEWS_DONE_KEY in rows:
                    return
                try:
                    views = json.loads(rows.get(VIEWS_KEY) or "[]")
                except ValueError:
                    return  # VS Code's own value unreadable: never overwrite it
                if not isinstance(views, list):
                    return
                # VS Code reads a bare id as hidden too; ours become objects (order kept), the rest as is
                ours = {v["id"]: v for v in views if isinstance(v, dict) and v.get("id") in HIDDEN_VIEWS}
                views = [v for v in views if (v.get("id") if isinstance(v, dict) else v) not in HIDDEN_VIEWS]
                views += [{**ours.get(view, {"id": view}), "isHidden": True} for view in HIDDEN_VIEWS]
                db.executemany("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                               [(VIEWS_KEY, json.dumps(views, separators=(",", ":"))), (VIEWS_DONE_KEY, "1")])
        finally:
            db.close()
    except (sqlite3.Error, OSError):
        pass


# trusted folders: VS Code 1.140 keeps them app-wide in the shared store, under this key; older
# ones (+ 1.140 before its first read) in the default state db, moved over on first read
# (app/docs/app-window.md #n)
TRUST_KEY = "content.trust.model.key"
# shared store's list of keys already moved over: listed => the default db's copy is ignored
MIGRATED_KEY = "__$__migratedStorageMarker"


def trust_uri(folder: str, windows: bool | None = None) -> dict:
    """Folder as VS Code saves a URI in JSON ($mid 1 = URI; revived from scheme + path)."""
    windows = sys.platform == "win32" if windows is None else windows
    path = str(folder).replace("\\", "/") if windows else str(folder)
    path = path.rstrip("/") or "/"
    if not path.startswith("/"):
        path = "/" + path
    return {"$mid": 1, "path": path, "scheme": "file"}


def ensure_folder_trusted(root: Path | None = None, paths: VSCodePaths | None = None) -> None:
    """Cold start: Job Finder's folder on VS Code's trusted list => opened from the Dock, recent
    folders or File > Open it still runs the AI panel + PDF viewer (no Restricted Mode). This
    folder only, never `security.workspace.trust.enabled`; every other entry kept."""
    paths, root = paths or vscode_paths(), root or cfg.ROOT
    if vscode_running(paths):
        return  # VS Code holds the store + writes its own copy back on quit
    shared = paths.shared / "sharedStorage" / "state.vscdb"
    try:
        target = paths.global_storage / "state.vscdb"
        if shared.exists():
            rows = state_values(shared, (TRUST_KEY, MIGRATED_KEY))
            try:
                moved = TRUST_KEY in json.loads(rows.get(MIGRATED_KEY) or "[]")
            except (ValueError, TypeError):
                return  # VS Code's own value unreadable: never guess where it reads trust
            if TRUST_KEY in rows or moved:
                target = shared
        add_trusted(target, trust_uri(str(root)))
    except (sqlite3.Error, OSError):
        pass


def state_values(state: Path, keys: tuple[str, ...]) -> dict:
    db = sqlite3.connect(f"{state.as_uri()}?mode=ro", uri=True, timeout=2)
    try:
        marks = ",".join("?" * len(keys))
        return dict(db.execute(f"SELECT key, value FROM ItemTable WHERE key IN ({marks})", keys).fetchall())
    finally:
        db.close()


def add_trusted(state: Path, uri: dict) -> None:
    windows = re.match(r"^/[A-Za-z]:", uri["path"]) is not None
    norm = (lambda p: p.lower()) if windows else (lambda p: p)
    state.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(state, timeout=2)
    try:
        with db:
            db.execute(ITEM_TABLE)
            row = db.execute("SELECT value FROM ItemTable WHERE key = ?", (TRUST_KEY,)).fetchone()
            try:
                info = json.loads(row[0]) if row else {}
            except (ValueError, TypeError):
                return  # VS Code's own value unreadable: never overwrite it
            entries = info.get("uriTrustInfo") if isinstance(info, dict) else None
            if row and not isinstance(entries, list):
                return
            entries = entries or []
            for entry in entries:
                seen = entry.get("uri") if isinstance(entry, dict) else None
                if (isinstance(seen, dict) and seen.get("scheme") == "file" and entry.get("trusted")
                        and norm(str(seen.get("path", "")).rstrip("/")) == norm(uri["path"])):
                    return
            info = {**(info if isinstance(info, dict) else {}), "uriTrustInfo": [*entries, {"uri": uri, "trusted": True}]}
            db.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                       (TRUST_KEY, json.dumps(info, separators=(",", ":"))))
    finally:
        db.close()


def copy_settings(source: Path, target: Path) -> None:
    try:
        values = settings_values(source.read_text(encoding="utf-8")) if source.exists() else None
        text = target.read_text(encoding="utf-8") if target.exists() else ""
    except OSError:
        return
    merged = text
    for key in CARRIED_SETTINGS:
        if values and key in values and f'"{key}"' not in merged:
            merged = add_setting(merged, f'"{key}": {json.dumps(values[key])}')
    if merged != text:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(merged, encoding="utf-8")
        except OSError:
            pass


# Settings Sync sends every extension in a profile, ours too (pinned + version) => another computer
# signed in to the same account asks the Marketplace for an id that isn't there, or later someone
# else's under that id (app/docs/app-window.md #5). Sync skips machine-scoped ones + ignored ids
SYNC_IGNORED = "settingsSync.ignoredExtensions"


def keep_out_of_sync(paths: VSCodePaths | None = None) -> None:
    """After installs, cold start only: ours marked machine-scoped in the profile's list (each
    install rewrites the entry); sync on => its id in `ignoredExtensions` too (app-wide key, default
    profile's settings only; that one id added, the rest of the file byte for byte)."""
    paths = paths or vscode_paths()
    location = profile_location(paths)
    if not location or vscode_running(paths):
        return
    import vscode_ext
    try:
        ours = vscode_ext.extension_id().lower()
    except (OSError, ValueError, KeyError):
        return
    mark_machine_scoped(paths.data / "User" / "profiles" / location / "extensions.json", ours)
    if sync_on(paths):
        try:
            text = paths.settings.read_text(encoding="utf-8") if paths.settings.exists() else ""
            merged = add_to_list_setting(text, SYNC_IGNORED, ours)
            if merged != text:
                paths.settings.parent.mkdir(parents=True, exist_ok=True)
                paths.settings.write_text(merged, encoding="utf-8")
        except OSError:
            pass


def mark_machine_scoped(listing: Path, ident: str) -> None:
    try:
        entries = json.loads(listing.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(entries, list):
        return
    changed = False
    for entry in entries:
        try:
            if entry["identifier"]["id"].lower() != ident:
                continue
            metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        except (KeyError, TypeError, AttributeError):
            continue
        if metadata.get("isMachineScoped") is not True:
            entry["metadata"] = {**metadata, "isMachineScoped": True}
            changed = True
    if changed:
        try:
            temp = listing.with_name(listing.name + ".jobfinder")
            temp.write_text(json.dumps(entries), encoding="utf-8")
            os.replace(temp, listing)
        except OSError:
            pass


def sync_on(paths: VSCodePaths) -> bool:
    # VS Code keeps "sync.enable" app-wide in the default state db (1.140 bundle: storage scope -1)
    state = paths.global_storage / "state.vscdb"
    if not state.exists():
        return False
    try:
        db = sqlite3.connect(f"{state.as_uri()}?mode=ro", uri=True, timeout=2)
        try:
            row = db.execute("SELECT value FROM ItemTable WHERE key = 'sync.enable'").fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        return False
    return bool(row) and str(row[0]).strip() == "true"


def ensure_profile_settings(settings: Path) -> None:
    text = settings.read_text(encoding="utf-8") if settings.exists() else ""
    merged = text
    for key, value in PROFILE_SETTINGS.items():
        if f'"{key}"' not in merged:
            merged = add_setting(merged, f'"{key}": {value}')
    if merged != text:
        settings.write_text(merged, encoding="utf-8")


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


# app-wide in VS Code: only the default profile's user settings change them, never a workspace.
# Release Notes tab over Today after VS Code updates itself, experiments flipping the UI, Microsoft
# usage reports on a program sold as private, walkthrough tabs when an extension installs, and
# Windows' full File/Edit/.../Help menu bar. Set only on a VS Code Job Finder owns - a
# developer's settings stay byte for byte
QUIET = {
    "update.showReleaseNotes": "false",
    "workbench.enableExperiments": "false",
    "telemetry.telemetryLevel": '"off"',
    "workbench.welcomePage.walkthroughs.openOnInstall": "false",
}
QUIET_WINDOWS = {"window.menuBarVisibility": '"compact"'}
# installers write it only in the branch that downloads VS Code itself
VSCODE_OURS = cfg.DATA / "vscode-ours"
JSONC_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.S)


def settings_values(text: str) -> dict | None:
    """VS Code's settings file read (comments + trailing commas allowed); None if unreadable."""
    plain = JSONC_TOKEN.sub(lambda m: m.group(0) if m.group(0).startswith('"') else "", text)
    plain = re.sub(r",(\s*[}\]])", r"\1", plain).strip()
    if not plain:
        return {}
    try:
        data = json.loads(plain)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def settings_keys(text: str) -> set[str] | None:
    values = settings_values(text)
    return None if values is None else set(values)


def add_to_list_setting(text: str, key: str, item: str) -> str:
    """`item` into list setting `key`, rest of the file byte for byte (see `add_setting`).

    Key missing => added; already listed (any case) or not a list => unchanged.
    """
    # comments blanked, same length => offsets in `bare` are offsets in `text`
    bare = JSONC_TOKEN.sub(lambda m: m.group(0) if m.group(0).startswith('"') else " " * len(m.group(0)), text)
    if f'"{key}"' not in bare:
        return add_setting(text, f'"{key}": [{json.dumps(item)}]')
    found = re.search(rf'"{re.escape(key)}"\s*:\s*\[', bare)
    end = bare.find("]", found.end()) if found else -1
    if end < 0:
        return text
    inside = bare[found.end():end]
    if json.dumps(item).lower() in inside.lower():
        return text
    separator = ", " if inside.strip() else ""
    return text[:found.end()] + json.dumps(item) + separator + text[found.end():]


def quiet_keys() -> dict[str, str]:
    return {**QUIET, **(QUIET_WINDOWS if sys.platform == "win32" else {})}


def vscode_is_ours(text: str, marker: Path | None = None) -> bool:
    # installs from before the marker: a settings file holding nothing but what Job Finder writes
    # is one nobody else set up. Anything more (or a comment's worth of hand edits) = theirs
    if (marker or VSCODE_OURS).exists():
        return True
    keys = settings_keys(text)
    own = {"redhat.telemetry.enabled", *QUIET, *QUIET_WINDOWS}
    return keys is not None and keys <= own and "//" not in text and "/*" not in text


def ensure_quiet_vscode(settings: Path | None = None, marker: Path | None = None) -> None:
    settings = settings or vscode_settings()
    try:
        text = settings.read_text(encoding="utf-8") if settings.exists() else ""
        if not vscode_is_ours(text, marker):
            return
        merged = text
        for key, value in quiet_keys().items():
            if f'"{key}"' not in merged:
                merged = add_setting(merged, f'"{key}": {value}')
        if merged != text:
            settings.parent.mkdir(parents=True, exist_ok=True)
            settings.write_text(merged, encoding="utf-8")
    except OSError:
        pass


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

# launcher: VS Code was running, profile waits for a cold start; the window extension reads it
PROFILE_PENDING = cfg.DATA / "profile-pending"


def mark_profile_pending(path: Path | None = None) -> None:
    path = path or PROFILE_PENDING
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("quit VS Code once, then open CEZ Job Finder\n", encoding="utf-8")
    except OSError:
        pass


def chosen_ai() -> str | None:
    import ai  # here, not on top: ai imports this module
    name = ai.current()
    # installs before the choice file (or a repaired one) => the AI found from its extension is
    # written down: the window extension reads only the file, and w/o it every button copied
    if name and not ai.CHOICE_FILE.is_file():
        try:
            ai.set(name)
        except (OSError, ValueError):
            pass
    return name


def write_workspace(choice: str | None) -> None:
    import workspace
    try:
        # search settings saved => START HERE leaves the file list (it only says "type set me up")
        workspace.write(choice, set_up=cfg.config_path().exists())
    except OSError:
        pass  # last launch's file still opens the window


def code_command(args: list[str]) -> list[str] | None:
    """The one place a code call is built (launcher, `jobs.py open`, `window-setup`); None w/o VS Code.

    Job Finder's profile made => `--profile` on every call: installs land in its list, not the
    default profile's, and a file opens in its window. Not made yet => no flag (an unknown name
    fails: "Profile ... not found.", exit 1).
    """
    exe = shutil.which("code")
    if not exe:
        return None
    profile = ["--profile", cfg.NAME] if profile_location() else []
    return [exe, *scratch_args(), *profile, *args]


def code(args: list[str], quiet: bool = False) -> int:
    command = code_command(args)
    if not command:
        sys.exit(f"VS Code not found; run the {cfg.NAME} installer again")
    # VS Code started cold inherits console => launcher's terminal window stays up until VS Code
    # quits, and closing it can take VS Code down (measured 2026-09-28, Windows Terminal)
    own_hidden_console = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.run(command, check=False, capture_output=quiet, creationflags=own_hidden_console).returncode


# AI chat panel per choice; Copilot's chat is built into VS Code => nothing to add
AI_EXTENSIONS = {"claude": CLAUDE_EXTENSION, "chatgpt": "openai.chatgpt"}
AI_PANEL_NAMES = {"claude": "the Claude chat panel", "chatgpt": "the ChatGPT chat panel"}


def installed_version(name: str) -> str | None:
    folder = installed().get(name.lower())
    try:
        return str(json.loads((folder / "package.json").read_text(encoding="utf-8"))["version"])
    except (TypeError, OSError, ValueError, KeyError):
        return None


def missing_extensions(choice: str | None) -> list[tuple[str, str]]:
    """(install arg, plain name) of each one Job Finder's window lacks; read off its list, no code call."""
    import vscode_ext
    missing = []
    if choice in AI_EXTENSIONS and not has_extension(AI_EXTENSIONS[choice]):
        missing.append((AI_EXTENSIONS[choice], AI_PANEL_NAMES[choice]))
    if not has_pdf_viewer():
        missing.append((PDF_EXTENSION, "the PDF viewer"))
    if not has_extension(YAML_EXTENSION):
        missing.append((YAML_EXTENSION, "the resume typo checker"))
    try:
        # other version listed (older or newer) => this release's copy; VS Code refuses an older
        # one w/o --force yet exits 0 (app/docs/app-window.md #4)
        if installed_version(vscode_ext.extension_id()) != vscode_ext.manifest()["version"]:
            missing.append((str(vscode_ext.build()), f"{cfg.NAME}'s window"))
    except (OSError, ValueError, KeyError):
        pass  # can't build it => the window still opens, just w/o it
    return missing


def ensure_extensions(choice: str | None, quiet: bool = True) -> bool:
    """Everything missing in ONE code call: 3 gallery + vsix = 3.0 s vs ~3 s each (measured)."""
    missing = missing_extensions(choice)
    if not missing:
        return True
    if not quiet:
        print("Adding " + ", ".join(name for _, name in missing) + "...")
    args = [a for ext, _ in missing for a in ("--install-extension", ext)]
    return code([*args, "--force"], quiet=True) == 0


def window_setup() -> None:
    """Installer step: profile (cold start only) + every extension, w/ plain progress lines.

    VS Code running => no profile yet: installs land in the default profile as before, the
    launcher makes the profile at its next cold start. Fails (exit 1) => installer falls back to
    its plain AI install.
    """
    cfg.ensure_private_dirs()
    if ensure_profile():
        migrate_profile()
        hide_side_views()
        print(f"{cfg.NAME} has its own space in VS Code, apart from anything else you use it for.")
    else:
        print(f"VS Code is open, so {cfg.NAME} gets its own space the next time it starts.")
    if not ensure_extensions(chosen_ai(), quiet=False):
        sys.exit("Could not add everything to VS Code.")
    keep_out_of_sync()
    print("VS Code is ready.")


def first_page(settings: Path | None = None, page: Path | None = None) -> Path:
    """START HERE until search settings exist, then Today, rebuilt now so a page last written days
    ago never shows old news. Rebuild fails => the last Today page still beats setup steps; none
    yet => START HERE. The launcher itself must never fail on it."""
    settings, page = settings or cfg.config_path(), page or TODAY_PAGE
    if not settings.exists():
        return START_PAGE
    try:
        import today  # here, not on top: a broken page module must not stop VS Code opening
        # same entry as the window extension's (`today --refresh`): job folders filed, then the page
        return today.refresh(cfg.load(settings), page)
    except (Exception, SystemExit):
        return page if page.exists() else START_PAGE


def mark_start_page(page: Path | None, data: Path | None = None) -> None:
    """Launch stamp always; `page` => marker naming it for the extension, None => no marker left.
    Read per call (cfg.ROOT), never cfg.DATA: tests point ROOT at a throwaway folder."""
    data = data or cfg.ROOT / ".data"
    try:
        data.mkdir(parents=True, exist_ok=True)
        (data / LAUNCH_STAMP).write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n", encoding="utf-8")
        marker = data / START_MARKER
        if page:
            marker.write_text(page.name + "\n", encoding="utf-8")  # both pages sit in the folder root
        else:
            marker.unlink(missing_ok=True)
    except OSError:
        pass  # no marker => the extension still opens a page, just its own pick


def main() -> None:
    if sys.platform == "win32":
        register_protocol()
        ensure_windows_icon()
    if sys.platform == "darwin":
        ensure_mac_icon()
    # before VS Code opens => file list shows the private folders even on a brand-new install
    cfg.ensure_private_dirs()
    # before any install + before VS Code opens => this folder's window comes up in Job Finder's
    # profile; VS Code already running => next cold start
    if ensure_profile():
        # their model pick, zoom + text size come along, once
        migrate_profile()
        # no Outline + Timeline under the file list (code-editor tells), once
        hide_side_views()
        PROFILE_PENDING.unlink(missing_ok=True)
    elif not profile_location():
        # VS Code left open => no profile yet; the window extension says how to finish (quit once)
        mark_profile_pending()
    # opened later w/o the Desktop icon (Dock, recent folders) => still trusted: AI panel runs
    ensure_folder_trusted()
    choice = chosen_ai()
    # before VS Code opens, into its profile once made => the window comes up with the chat panel,
    # the first click on a resume shows the page, a typo in the resume facts is underlined
    ensure_extensions(choice)
    # our window extension never synced to another computer (the Marketplace has no such id)
    keep_out_of_sync()
    # before VS Code opens => no Release Notes tab over Today, no usage reports (ours only)
    ensure_quiet_vscode()
    # before VS Code opens => Red Hat's telemetry popup never asks mid job search
    ensure_yaml_checker()
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
    cold = not vscode_running()
    # before the window => the page is fresh when the extension opens it
    page = first_page()
    if cold:
        # ONE call, folder only: the window extension opens the page formatted as it starts
        mark_start_page(page)
        code(window)
        return
    mark_start_page(None)
    code(window)
    # window already up => the page lands formatted at once, no wait; double-click on the Desktop
    # icon brings it forward. Folder again => lands in this window, not the last used
    code([*window, str(page)])


if __name__ == "__main__":
    main()
