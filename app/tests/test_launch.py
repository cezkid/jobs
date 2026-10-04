import json
import re
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote

import pytest

import cfg
import launch
import notify

FIXTURES = Path(__file__).parent / "fixtures"
DONE = type("Done", (), {"returncode": 0})  # subprocess.run result of a code call that worked


def test_launch_creates_private_folders_on_fresh_install(tmp_path, monkeypatch):
    # fresh install ships none of them => START HERE.md promised a file list the user never saw
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: False)
    monkeypatch.setattr(launch, "chosen_ai", lambda: None)
    monkeypatch.setattr(launch, "write_workspace", lambda choice: None)
    monkeypatch.setattr(launch, "ensure_extensions", lambda choice: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "ensure_mac_icon", lambda: None)
    monkeypatch.setattr(launch, "ensure_profile", lambda: True)
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: None)
    monkeypatch.setattr(launch.time, "sleep", lambda s: None)
    monkeypatch.setattr(launch, "first_page", lambda: launch.START_PAGE)
    launch.main()
    assert sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith(".")) == ["My Jobs", "My Resume", "My Settings"]
    launch.main()  # second launch leaves what is already there alone


def launch_calls(tmp_path, monkeypatch, running: bool) -> list:
    calls = []
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: True)
    monkeypatch.setattr(launch, "ensure_claude_trust", lambda: None)
    monkeypatch.setattr(launch, "ensure_chat_sidebar", lambda: None)
    monkeypatch.setattr(launch, "chosen_ai", lambda: "claude")
    monkeypatch.setattr(launch, "write_workspace", lambda choice: calls.append(("workspace", choice)))
    monkeypatch.setattr(launch, "ensure_extensions", lambda choice: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "ensure_mac_icon", lambda: None)
    monkeypatch.setattr(launch, "ensure_profile", lambda: True)
    monkeypatch.setattr(launch, "ensure_folder_trusted", lambda: None)
    monkeypatch.setattr(launch, "vscode_running", lambda: running)
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: calls.append(args))
    monkeypatch.setattr(launch.time, "sleep", lambda s: calls.append(("sleep", s)))
    monkeypatch.setattr(launch, "first_page", lambda: tmp_path / "Today.md")
    launch.main()
    return calls


def test_cold_launch_opens_folder_once_and_leaves_the_page_to_the_window(tmp_path, monkeypatch):
    # page named w/ the folder on a cold start opened as plain text; the old fix waited 6 s first.
    # No vscode://...claude link either: it opens chat as a tab over START HERE
    calls = launch_calls(tmp_path, monkeypatch, running=False)
    window = ["--disable-workspace-trust", str(tmp_path)]
    assert calls == [("workspace", "claude"), window]
    assert (tmp_path / ".data" / launch.START_MARKER).read_text(encoding="utf-8") == "Today.md\n"
    assert (tmp_path / ".data" / launch.LAUNCH_STAMP).exists()


def test_launch_with_window_open_brings_the_page_forward_at_once(tmp_path, monkeypatch):
    # double-click on the Desktop icon w/ the window open must still show Today, w/o a 6 s wait;
    # a marker left over would open the page again at the next cold start
    (tmp_path / ".data").mkdir()
    (tmp_path / ".data" / launch.START_MARKER).write_text("START HERE.md\n")
    calls = launch_calls(tmp_path, monkeypatch, running=True)
    window = ["--disable-workspace-trust", str(tmp_path)]
    assert calls == [("workspace", "claude"), window, [*window, str(tmp_path / "Today.md")]]
    assert not (tmp_path / ".data" / launch.START_MARKER).exists()
    assert (tmp_path / ".data" / launch.LAUNCH_STAMP).exists()


def test_launcher_has_no_fixed_wait_for_the_page():
    # the 6 s pause before the page came back => every launch slow again
    assert "sleep" not in Path(launch.__file__).read_text(encoding="utf-8")
    assert not hasattr(launch, "START_PAGE_DELAY_S")


def test_launcher_and_window_rebuild_today_through_one_entry(tmp_path, monkeypatch):
    # two different rebuilds => job folders filed by one, not the other, or both on today.lock
    settings, page = tmp_path / "Search settings.yml", tmp_path / "Today.md"
    settings.write_text("")
    monkeypatch.setattr(launch.cfg, "load", lambda path: {})
    import today
    monkeypatch.setattr(today, "refresh", lambda config, to: (to.write_text("# Today\n"), to)[1])
    assert launch.first_page(settings, page) == page
    js = (cfg.APP / "vscode" / "extension.js").read_text(encoding="utf-8")
    assert '["run", "app/jobs.py", "today", "--refresh"]' in js


def test_first_run_opens_start_here_then_today(tmp_path, monkeypatch):
    # returning users landed on "type set me up" every launch, weeks after setting up
    settings, page = tmp_path / "Search settings.yml", tmp_path / "Today.md"
    written = []

    def write(config, to):
        written.append(to)
        to.write_text("# Today\n")
        return to
    monkeypatch.setattr(launch.cfg, "load", lambda path: {})
    import today
    monkeypatch.setattr(today, "write", write)
    assert launch.first_page(settings, page) == launch.START_PAGE and written == []
    settings.write_text("")
    # rebuilt at launch => never last week's page
    assert launch.first_page(settings, page) == page and written == [page]


def test_launch_files_job_folders_before_building_today(tmp_path, monkeypatch):
    # a folder moved by hand, or one a file kept from moving last time, is back in its stage
    # before the page that points at it is written
    settings, page = tmp_path / "Search settings.yml", tmp_path / "Today.md"
    settings.write_text("")
    calls = []
    monkeypatch.setattr(launch.cfg, "load", lambda path: {})
    import status
    import today
    monkeypatch.setattr(status, "sort_jobs", lambda config: calls.append("sort"))
    monkeypatch.setattr(today, "write", lambda config, to: calls.append("today") or to)
    assert launch.first_page(settings, page) == page and calls == ["sort", "today"]


def test_job_folders_that_fail_to_file_never_stop_the_page(tmp_path, monkeypatch):
    settings, page = tmp_path / "Search settings.yml", tmp_path / "Today.md"
    settings.write_text("")
    monkeypatch.setattr(launch.cfg, "load", lambda path: {})
    import status
    import today
    for failure in (OSError("file in use"), SystemExit("another chat is moving job folders")):
        def broken(config, failure=failure):
            raise failure
        monkeypatch.setattr(status, "sort_jobs", broken)
        monkeypatch.setattr(today, "write", lambda config, to: to)
        assert launch.first_page(settings, page) == page


def test_today_page_that_fails_never_stops_the_launch(tmp_path, monkeypatch):
    settings, page = tmp_path / "Search settings.yml", tmp_path / "Today.md"
    settings.write_text("")

    def broken(config, to):
        raise SystemExit("another chat is updating the Today page - try again in a minute")
    monkeypatch.setattr(launch.cfg, "load", lambda path: {})
    import today
    monkeypatch.setattr(today, "write", broken)
    assert launch.first_page(settings, page) == launch.START_PAGE  # no page yet => setup steps
    page.write_text("# Today\n")
    assert launch.first_page(settings, page) == page  # last page beats setup steps


def test_start_here_content_still_reachable_from_today():
    # START HERE trimmed to first-run steps: what it said moved to guides the Today page links
    import today
    start = (cfg.ROOT / "START HERE.md").read_text(encoding="utf-8")
    guides = {unquote(link) for _, link in today.GUIDES}
    assert {"Guides/What you can ask.md", "Guides/Who sees what.md"} <= guides
    for guide in guides:
        assert (cfg.ROOT / guide).exists()
    moved = "".join((cfg.ROOT / g).read_text(encoding="utf-8") for g in guides)
    for said in ("Why is job 3 on my list?", "freehire.me", "Resume details.yml", "Only you - this computer",
                 "Keep your chats out of AI training", "Only the repaired program code is sent"):
        assert said in moved
    assert "set me up" in start and "## Who sees what" not in start


def test_claude_detected_by_extension_folder(tmp_path):
    assert not launch.has_claude(tmp_path)
    (tmp_path / "anthropic.claude-code-2.1.278-win32-x64").mkdir()
    assert launch.has_claude(tmp_path)


def test_toast_escapes_text_and_opens_job_finder():
    script = notify.windows_script("3 new <jobs> & O'Brien's", notify.HINT)
    assert "&lt;jobs&gt; &amp; O''Brien''s" in script
    assert f'launch="{notify.PROTOCOL}:open"' in script


def test_toast_switched_off_fails_instead_of_vanishing(monkeypatch):
    # measured 2026-09-28: account notifications off => Show() rc 0, toast in no history
    script = notify.windows_script("t", "b")
    assert script.index("$n.Setting -ne 'Enabled'") < script.index("$n.Show(")
    failed = type("R", (), {"returncode": 3, "stderr": f"{notify.OFF_REASON} (DisabledForUser)\n"})
    monkeypatch.setattr(notify.sys, "platform", "win32")
    monkeypatch.setattr(notify.autorun, "powershell", lambda script: failed)
    with pytest.raises(RuntimeError, match="Settings > System > Notifications"):
        notify.notify("t", "b")


def pdf_extension(extensions, name="tomoki1207.pdf-1.2.2", pattern="*.pdf"):
    folder = extensions / name
    folder.mkdir(parents=True)
    (folder / "package.json").write_text(json.dumps(
        {"contributes": {"customEditors": [{"selector": [{"filenamePattern": pattern}]}]}}),
        encoding="utf-8")


def test_pdf_viewer_detected_whoever_provides_it(tmp_path):
    # without one, clicking a resume in the file list shows "binary file" instead of the page
    assert not launch.has_pdf_viewer(tmp_path)
    (tmp_path / "some.extension-1.0.0").mkdir()
    (tmp_path / "some.extension-1.0.0" / "package.json").write_text("not json", encoding="utf-8")
    pdf_extension(tmp_path, "markdown.viewer-2.0.0", "*.md")
    assert not launch.has_pdf_viewer(tmp_path)
    pdf_extension(tmp_path, "someone.elses-pdf-viewer-3.0.0")
    assert launch.has_pdf_viewer(tmp_path)


def test_claude_trusts_this_folder_only(tmp_path):
    # untrusted folder => its permission list ignored, user asked before every step
    state = tmp_path / ".claude.json"
    root = tmp_path / "jobs"
    keys = launch.claude_project_keys(root)
    launch.ensure_claude_trust(root, state)
    assert all(json.loads(state.read_text())["projects"][k] == {"hasTrustDialogAccepted": True} for k in keys)
    state.write_text(json.dumps({"theme": "dark", "projects": {
        "/elsewhere": {"hasTrustDialogAccepted": False}, keys[0]: {"lastCost": 1}}}))
    launch.ensure_claude_trust(root, state)
    written = json.loads(state.read_text())
    assert written["theme"] == "dark" and written["projects"]["/elsewhere"] == {"hasTrustDialogAccepted": False}
    assert written["projects"][keys[0]] == {"lastCost": 1, "hasTrustDialogAccepted": True}
    state.write_text("{broken")
    launch.ensure_claude_trust(root, state)  # a file Claude is mid-way writing stays as it is
    assert state.read_text() == "{broken"


def test_claude_trust_keys_match_claude_lookup():
    # backslash key or one drive case only => VS Code session untrusted, every step asks
    win = PureWindowsPath(r"C:\Users\x\jobs")
    assert launch.claude_project_keys(win) == ["c:/Users/x/jobs", "C:/Users/x/jobs"]
    assert launch.claude_project_keys(PurePosixPath("/Users/x/jobs")) == ["/Users/x/jobs"]


def test_launcher_never_changes_claude_for_other_projects():
    # auto mode is user-wide only => setting it changed Claude in the user's coding projects too
    source = (cfg.APP / "launch.py").read_text(encoding="utf-8")
    assert "defaultMode" not in source and '".claude" / "settings.json"' not in source


def test_workspace_lets_the_ai_write_only_job_finder_folders():
    allow = json.loads((cfg.ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    edits = {rule for rule in allow if rule.startswith(("Edit", "Write"))}
    assert edits == {"Edit(/My Jobs/**)", "Edit(/My Resume/**)", "Edit(/My Settings/**)", "Edit(/.data/**)"}


def test_workspace_never_sets_a_permission_mode_of_its_own():
    # this folder's own mode outranks the user's, and "auto" is ignored from here => every
    # mode named here is a mode that costs the user prompts
    settings = json.loads((cfg.ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "defaultMode" not in settings.get("permissions", {})


def test_pdf_opens_as_tab_with_viewer_system_viewer_without(tmp_path, monkeypatch):
    import jobs
    pdf, page = tmp_path / "Resume.pdf", tmp_path / "Job posting.md"
    pdf.write_bytes(b"%PDF")
    page.write_text("x", encoding="utf-8")
    viewer, tabs = [], []
    monkeypatch.setattr(launch.shutil, "which", lambda name: "code")
    monkeypatch.setattr(jobs.webbrowser, "open", viewer.append)
    monkeypatch.setattr(jobs.subprocess, "run", lambda args, check: tabs.append(args[-1]))
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    jobs.open_for_user(str(pdf))
    jobs.open_for_user(str(page))
    assert (viewer, tabs) == ([], [str(pdf.resolve()), str(page.resolve())])
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: False)
    jobs.open_for_user(str(pdf))
    assert viewer == [pdf.resolve().as_uri()]


def test_vscode_started_on_its_own_hidden_console(monkeypatch):
    # shared launcher console => its terminal window stayed open while VS Code ran
    runs = []
    monkeypatch.setattr(launch.shutil, "which", lambda name: "code")
    monkeypatch.setattr(launch.sys, "platform", "win32")
    monkeypatch.setattr(launch.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(kw["creationflags"]) or DONE)
    launch.code(["folder"])
    assert runs == [0x08000000]


def test_yaml_telemetry_answered_once(tmp_path, monkeypatch):
    # user is asked to decide about Red Hat telemetry on first activation otherwise, mid job search
    settings = tmp_path / "User" / "settings.json"
    launch.ensure_yaml_checker(settings)
    assert launch.TELEMETRY in settings.read_text(encoding="utf-8")
    launch.ensure_yaml_checker(settings)
    assert settings.read_text(encoding="utf-8").count("redhat.telemetry.enabled") == 1


def test_vscode_settings_keep_comments_and_trailing_commas():
    # developers' own settings files carry both; a JSON round-trip would silently delete them
    jsonc = '{\n  // mine\n  "editor.tabSize": 2,\n}\n'
    merged = launch.add_setting(jsonc, launch.TELEMETRY)
    assert "// mine" in merged and merged.count("\"editor.tabSize\": 2") == 1
    assert re.sub(r",(\s*})", r"\1", merged).strip().endswith(launch.TELEMETRY + "\n}")
    assert launch.add_setting("", launch.TELEMETRY) == "{\n  " + launch.TELEMETRY + "\n}\n"
    assert launch.add_setting("{}", launch.TELEMETRY) == "{\n  " + launch.TELEMETRY + "\n}"
    assert json.loads(launch.add_setting('{\n  "a": 1\n}\n', launch.TELEMETRY)) == {"a": 1, "redhat.telemetry.enabled": False}


QUIET_LINES = ['"update.showReleaseNotes": false', '"workbench.enableExperiments": false',
               '"telemetry.telemetryLevel": "off"', '"workbench.welcomePage.walkthroughs.openOnInstall": false']


# VS Code it installed: Release Notes tab over Today after each update, usage reports to Microsoft
def test_quiet_settings_added_when_installer_put_vscode_there(tmp_path, monkeypatch):
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    marker, settings = tmp_path / "vscode-ours", tmp_path / "User" / "settings.json"
    marker.touch()
    launch.ensure_quiet_vscode(settings, marker)
    text = settings.read_text(encoding="utf-8")
    assert all(line in text for line in QUIET_LINES) and "menuBarVisibility" not in text
    launch.ensure_quiet_vscode(settings, marker)
    assert settings.read_text(encoding="utf-8") == text


# a developer's VS Code (owner's own) changed app-wide = their editor stops behaving as they set it
def test_quiet_settings_never_touch_a_developers_vscode(tmp_path):
    settings = tmp_path / "settings.json"
    shutil.copy(FIXTURES / "vscode-dev-settings.jsonc", settings)
    before = settings.read_bytes()
    launch.ensure_quiet_vscode(settings, tmp_path / "no-marker")
    assert settings.read_bytes() == before
    assert len(launch.settings_keys(before.decode())) >= 20


# installs from before the marker: still quiet when only Job Finder ever wrote the file
@pytest.mark.parametrize("text", [None, "", "{}", '{\n  "redhat.telemetry.enabled": false\n}\n'])
def test_quiet_settings_on_old_installs_only_job_finder_wrote(tmp_path, text):
    settings = tmp_path / "settings.json"
    if text is not None:
        settings.write_text(text, encoding="utf-8")
    launch.ensure_quiet_vscode(settings, tmp_path / "no-marker")
    assert all(line in settings.read_text(encoding="utf-8") for line in QUIET_LINES)


# a user's own choice overwritten = their setting flips back at every launch
def test_quiet_settings_keep_the_users_value_and_comments(tmp_path):
    marker, settings = tmp_path / "vscode-ours", tmp_path / "settings.json"
    marker.touch()
    settings.write_text('{\n  // keep me\n  "telemetry.telemetryLevel": "error",\n}\n', encoding="utf-8")
    launch.ensure_quiet_vscode(settings, marker)
    text = settings.read_text(encoding="utf-8")
    assert "// keep me" in text and text.count("telemetry.telemetryLevel") == 1
    assert '"telemetry.telemetryLevel": "error"' in text and '"update.showReleaseNotes": false' in text
    assert launch.settings_keys(text) >= {"telemetry.telemetryLevel", "update.showReleaseNotes"}


# full File/Edit/.../Help bar is Windows-only; the key on a Mac is noise in their settings
@pytest.mark.parametrize("platform, menu", [("win32", True), ("darwin", False), ("linux", False)])
def test_quiet_menu_bar_only_on_windows(tmp_path, monkeypatch, platform, menu):
    monkeypatch.setattr(launch.sys, "platform", platform)
    settings = tmp_path / "settings.json"
    launch.ensure_quiet_vscode(settings, tmp_path / "no-marker")
    assert ('"window.menuBarVisibility": "compact"' in settings.read_text(encoding="utf-8")) is menu


def test_start_page_leads_with_the_first_step():
    # users read the whole page and still did not know what to do
    page = (cfg.ROOT / "START HERE.md").read_text(encoding="utf-8")
    assert page.split("\n## ")[1].startswith("Do this now") and "set me up" in page


def test_old_mac_icon_swapped_for_app_once(tmp_path, monkeypatch):
    # .command icon leaves a Terminal window open after every launch
    runs = []
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args) or DONE)
    old, app = tmp_path / "CEZ Job Finder.command", tmp_path / "CEZ Job Finder.app"
    launch.ensure_mac_icon(old, app)
    assert runs == []  # no old icon => nothing made, a deleted icon stays deleted
    old.write_text("")
    launch.ensure_mac_icon(old, app)
    assert runs == [["bash", str(launch.MAC_ICON_MAKER), str(app)]]


def test_mac_app_icon_gets_brand_picture_once(tmp_path, monkeypatch):
    # app icons made before the brand icon kept the generic script picture on the Desktop
    runs = []
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args) or DONE)
    app = tmp_path / "CEZ Job Finder.app"
    icns = app / "Contents" / "Resources" / "applet.icns"
    icns.parent.mkdir(parents=True)
    icns.write_bytes(b"generic script icon")
    launch.ensure_mac_icon(tmp_path / "none.command", app)
    assert runs == [["bash", str(launch.MAC_ICON_MAKER), str(app)]]
    icns.write_bytes(launch.MAC_ICON.read_bytes())
    launch.ensure_mac_icon(tmp_path / "none.command", app)
    assert len(runs) == 1  # brand icon in place => left alone, no re-sign every launch


def test_mac_icon_is_an_app_not_a_terminal_script():
    maker = (launch.MAC_ICON_MAKER).read_text(encoding="utf-8")
    assert "osacompile" in maker and ".app" in maker
    installer = (cfg.APP / "install" / "install-mac.sh").read_text(encoding="utf-8")
    assert "make-icon-mac.sh" in installer and ".command\"" not in installer


def test_chat_sidebar_shown_again_after_user_closed_it(tmp_path):
    # VS Code remembers a closed sidebar per folder => next launch showed only START HERE
    import sqlite3
    root = tmp_path / "jobs folder"
    root.mkdir()
    other, mine = tmp_path / "ws" / "a", tmp_path / "ws" / "b"
    for folder, target in ((other, tmp_path / "elsewhere"), (mine, root)):
        folder.mkdir(parents=True)
        (folder / "workspace.json").write_text(json.dumps({"folder": target.as_uri()}))
        with sqlite3.connect(folder / "state.vscdb") as db:
            db.execute("CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)")
            db.execute("INSERT INTO ItemTable VALUES ('workbench.auxiliaryBar.hidden', 'true')")
        db.close()
    launch.ensure_chat_sidebar(root, tmp_path / "ws")

    def hidden(folder):
        with sqlite3.connect(folder / "state.vscdb") as db:
            value = db.execute("SELECT value FROM ItemTable WHERE key = ?",
                               ("workbench.auxiliaryBar.hidden",)).fetchone()[0]
        db.close()
        return value
    assert hidden(mine) == "false"
    assert hidden(other) == "true"  # another folder's layout left alone


def test_chat_sidebar_first_window_left_to_setting(tmp_path):
    launch.ensure_chat_sidebar(tmp_path, tmp_path / "no-storage-yet")  # nothing to fix, no error


def test_mac_notification_says_how_to_open(monkeypatch):
    # click opens Script Editor (notification belongs to osascript) => the text carries the way in
    calls = []
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(notify.subprocess, "run", lambda args, **kw: calls.append((args, kw)))
    notify.notify("3 new jobs", "Engineer; Designer")
    args, kw = calls[0]
    assert args[0] == "osascript" and kw["check"]
    assert args[-3:] == ["3 new jobs", "Engineer; Designer", notify.MAC_SUBTITLE]
    assert "subtitle (item 3 of argv)" in " ".join(args)
    assert "Desktop" in notify.MAC_SUBTITLE and notify.cfg.NAME in notify.MAC_SUBTITLE


def test_copilot_window_gets_its_chat_sidebar_without_claude(tmp_path, monkeypatch):
    # Copilot's chat lives in the same right-hand sidebar => closed once, it must come back too
    calls = []
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: False)
    monkeypatch.setattr(launch, "chosen_ai", lambda: "copilot")
    monkeypatch.setattr(launch, "write_workspace", lambda choice: calls.append(("workspace", choice)))
    monkeypatch.setattr(launch, "ensure_claude_trust", lambda: calls.append("trust"))
    monkeypatch.setattr(launch, "ensure_chat_sidebar", lambda: calls.append("sidebar"))
    monkeypatch.setattr(launch, "ensure_extensions", lambda choice: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "ensure_mac_icon", lambda: None)
    monkeypatch.setattr(launch, "ensure_profile", lambda: True)
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: calls.append("code"))
    monkeypatch.setattr(launch.time, "sleep", lambda s: None)
    monkeypatch.setattr(launch, "first_page", lambda: launch.START_PAGE)
    launch.main()
    assert calls[:3] == [("workspace", "copilot"), "sidebar", "code"] and "trust" not in calls


def test_windows_shortcut_refresh_only_touches_this_installs_shortcut():
    # re-pointing a shortcut to another copy (or making a new one) would leave two icons / wrong app
    script = launch.windows_shortcut_script(launch.WINDOWS_LAUNCHER, launch.WINDOWS_ICON)
    guard = f"if ($l.TargetPath -ne '{launch.WINDOWS_LAUNCHER}') {{ exit 0 }}"
    assert "if (-not (Test-Path -LiteralPath $p)) { exit 0 }" in script
    assert guard in script
    assert script.index("Test-Path") < script.index(guard) < script.index("IconLocation") < script.index("$l.Save()")
    assert f"$l.IconLocation = '{launch.WINDOWS_ICON},0'" in script
    assert "$l.WindowStyle = 7" in script
    assert f"'{cfg.NAME}.lnk'" in script
    assert "TargetPath =" not in script and "CreateShortcut($p)" in script


def test_windows_shortcut_path_with_apostrophe_stays_quoted():
    # user folder "O'Brien" => unescaped quote breaks the script, icon never refreshed
    script = launch.windows_shortcut_script(PureWindowsPath(r"C:\Users\O'Brien\jobs\start.bat"),
                                            PureWindowsPath(r"C:\Users\O'Brien\jobs\icon.ico"))
    assert r"'C:\Users\O''Brien\jobs\start.bat'" in script
    assert r"'C:\Users\O''Brien\jobs\icon.ico,0'" in script


def test_windows_icon_refreshed_once_retried_after_failure(tmp_path):
    # powershell every launch slows each start; a failed run must not be marked done
    runs = []
    result = type("R", (), {"returncode": 1})
    def run(script):
        runs.append(script)
        return result
    done = tmp_path / ".data" / "desktop-icon-refreshed"
    launch.ensure_windows_icon(done, run)
    assert not done.exists() and len(runs) == 1
    result.returncode = 0
    launch.ensure_windows_icon(done, run)
    launch.ensure_windows_icon(done, run)
    assert done.exists() and len(runs) == 2
    assert runs[0] == launch.windows_shortcut_script()


def test_scratch_vscode_keeps_every_path_and_call_off_the_owners(tmp_path, monkeypatch):
    # live looks drove the owner's open VS Code and rewrote their Claude trust + Desktop icon
    scratch = tmp_path / "scratch"
    monkeypatch.setenv(launch.SCRATCH_ENV, str(scratch))
    paths = launch.vscode_paths()
    assert all(p.is_relative_to(scratch.resolve()) for p in paths)
    assert launch.vscode_settings() == paths.settings
    runs = []
    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/code")
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args) or DONE)
    launch.code(["--install-extension", launch.PDF_EXTENSION])
    assert runs == [["/bin/code", "--user-data-dir", str(paths.data), "--extensions-dir", str(paths.extensions),
                     "--shared-data-dir", str(paths.shared),
                     "--install-extension", launch.PDF_EXTENSION]]
    launch.ensure_claude_trust(tmp_path / "jobs")
    assert paths.claude_state.exists()
    (paths.extensions / "anthropic.claude-code-2.0.0").mkdir(parents=True)
    assert launch.has_claude()


def test_without_scratch_paths_follow_the_home_folder(tmp_path, monkeypatch):
    # paths fixed at import => a home folder changed later (tests, another user) still hit the old one
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    paths = launch.vscode_paths()
    assert paths.claude_state == tmp_path / ".claude.json" and paths.extensions == tmp_path / ".vscode" / "extensions"
    assert paths.settings == tmp_path / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    assert launch.scratch_args() == []


def test_open_for_user_lands_in_the_scratch_vscode(tmp_path, monkeypatch):
    # jobs.py open during a live look put the file in the owner's window
    import jobs
    page = tmp_path / "Job posting.md"
    page.write_text("x", encoding="utf-8")
    monkeypatch.setenv(launch.SCRATCH_ENV, str(tmp_path / "scratch"))
    runs = []
    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/code")
    monkeypatch.setattr(jobs.subprocess, "run", lambda args, check: runs.append(args))
    jobs.open_for_user(str(page))
    assert runs[0][1:3] == ["--user-data-dir", str(launch.vscode_paths().data)] and runs[0][-1] == str(page.resolve())


def test_test_guard_stops_real_code_calls():
    # one unguarded test drove the owner's running VS Code window
    import conftest
    assert conftest.reaches_real_vscode(["/usr/local/bin/code", "--version"])
    assert conftest.reaches_real_vscode("code -r x")
    assert conftest.reaches_real_vscode(["open", "vscode://anthropic.claude-code/open"])
    assert not conftest.reaches_real_vscode(["code", "--user-data-dir", "/tmp/x", "--version"])
    assert not conftest.reaches_real_vscode(["bash", "-c", "code --list-extensions"])


def test_open_names_job_finders_folder_with_the_file(tmp_path, monkeypatch):
    # code -r <file> alone landed in whichever VS Code window was used last
    import jobs
    page = tmp_path / "Job posting.md"
    page.write_text("x", encoding="utf-8")
    runs = []
    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/code")
    monkeypatch.setattr(jobs.subprocess, "run", lambda args, check: runs.append(args))
    jobs.open_for_user(str(page))
    assert runs[0][-2:] == [str(cfg.ROOT), str(page.resolve())] and "-r" not in runs[0]


def profile_paths(tmp_path, monkeypatch):
    monkeypatch.setenv(launch.SCRATCH_ENV, str(tmp_path / "scratch"))
    return launch.vscode_paths()


def write_storage(paths, data):
    target = launch.storage_file(paths)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data), encoding="utf-8")


def test_cold_start_creates_profile_and_opens_folder_in_it(tmp_path, monkeypatch):
    # without the profile the window ran the user's own extensions + settings, not Job Finder's
    paths, root = profile_paths(tmp_path, monkeypatch), tmp_path / "Your Name" / "jobs"
    assert launch.ensure_profile(root, paths)
    storage = json.loads(launch.storage_file(paths).read_text(encoding="utf-8"))
    assert storage["userDataProfiles"] == [{"location": "cez-job-finder", "name": cfg.NAME, "icon": "briefcase"}]
    assert storage["profileAssociations"]["workspaces"] == {launch.folder_uri(str(root)): "cez-job-finder"}
    settings = paths.data / "User" / "profiles" / "cez-job-finder" / "settings.json"
    assert json.loads(settings.read_text(encoding="utf-8"))["workbench.welcomePage.walkthroughs.openOnInstall"] is False
    before = launch.storage_file(paths).stat().st_mtime_ns
    assert launch.ensure_profile(root, paths)  # next launch: nothing to change, nothing written
    assert launch.storage_file(paths).stat().st_mtime_ns == before
    assert launch.profile_location(paths) == "cez-job-finder"


def test_running_vscode_leaves_its_state_alone(tmp_path, monkeypatch):
    # VS Code running holds storage.json in memory => a write now is lost or fights it
    paths = profile_paths(tmp_path, monkeypatch)
    write_storage(paths, {"theme": "dark"})
    (paths.data / "code.lock").write_text(str(launch.os.getpid()), encoding="utf-8")
    before = launch.storage_file(paths).read_bytes()
    assert not launch.ensure_profile(tmp_path / "jobs", paths)
    assert launch.storage_file(paths).read_bytes() == before
    assert not (paths.data / "User" / "profiles").exists()
    (paths.data / "code.lock").write_text("999999999", encoding="utf-8")  # crashed: stale lock
    assert launch.ensure_profile(tmp_path / "jobs", paths)


def test_users_other_profiles_and_folders_kept(tmp_path, monkeypatch):
    # dropping the user's own profiles or folder links would lose their setup in VS Code
    paths, root = profile_paths(tmp_path, monkeypatch), tmp_path / "jobs"
    theirs = {"location": "-5a1b2c", "name": "Work", "icon": "code"}
    other = launch.folder_uri(str(tmp_path / "work"))
    write_storage(paths, {"userDataProfiles": [theirs],
                          "profileAssociations": {"workspaces": {other: "-5a1b2c"}, "emptyWindows": {}},
                          "windowsState": {"lastActiveWindow": {"folder": other}}})
    assert launch.ensure_profile(root, paths)
    storage = json.loads(launch.storage_file(paths).read_text(encoding="utf-8"))
    assert storage["userDataProfiles"][0] == theirs and len(storage["userDataProfiles"]) == 2
    assert storage["profileAssociations"] == {"workspaces": {other: "-5a1b2c", launch.folder_uri(str(root)): "cez-job-finder"},
                                              "emptyWindows": {}}
    assert storage["windowsState"] == {"lastActiveWindow": {"folder": other}}


def test_unreadable_vscode_state_never_overwritten(tmp_path, monkeypatch):
    # rewriting a file we could not read would wipe every window + profile VS Code remembers
    paths = profile_paths(tmp_path, monkeypatch)
    launch.storage_file(paths).parent.mkdir(parents=True)
    launch.storage_file(paths).write_text("{half", encoding="utf-8")
    assert not launch.ensure_profile(tmp_path / "jobs", paths)
    assert launch.storage_file(paths).read_text(encoding="utf-8") == "{half"


def test_folder_key_matches_vscode_on_windows_and_mac():
    # key spelled differently from VS Code's => folder opens in the default profile
    assert launch.folder_uri("C:\\Home\\Your Name\\jobs", windows=True) == "file:///c%3A/Home/Your%20Name/jobs"
    assert launch.folder_uri("D:/Jobs \u00d1", windows=True) == "file:///d%3A/Jobs%20%C3%91"
    assert launch.folder_uri("/Users/Your Name/CEZ Job Finder", windows=False) == "file:///Users/Your%20Name/CEZ%20Job%20Finder"
    assert launch.same_folder("file:///C:/Home/Your%20Name/jobs", "C:\\Home\\Your Name\\jobs", windows=True)


def test_old_spelling_of_folder_key_replaced_not_doubled(tmp_path, monkeypatch):
    # two keys for one folder => VS Code picks either profile
    paths = profile_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(launch.sys, "platform", "win32")
    monkeypatch.setattr(launch, "vscode_running", lambda paths=None: False)
    write_storage(paths, {"profileAssociations": {"workspaces": {"file:///C:/Home/jobs": "__default__profile__"}}})
    assert launch.ensure_profile(Path("C:\\Home\\jobs"), paths)
    storage = json.loads(launch.storage_file(paths).read_text(encoding="utf-8"))
    assert storage["profileAssociations"]["workspaces"] == {"file:///c%3A/Home/jobs": "cez-job-finder"}


def listed(ext_dir, *ids):
    entries = []
    for ident in ids:
        (ext_dir / f"{ident}-1.0.0").mkdir(parents=True, exist_ok=True)
        entries.append({"identifier": {"id": ident}, "version": "1.0.0", "relativeLocation": f"{ident}-1.0.0",
                        "location": {"$mid": 1, "path": str(ext_dir / f"{ident}-1.0.0"), "scheme": "file"}})
    return entries


def test_extension_in_another_profile_does_not_count(tmp_path, monkeypatch):
    # shared extensions folder holds every profile's => a PDF viewer from another profile read as
    # present, never installed into Job Finder's, and resumes showed as binary
    paths = profile_paths(tmp_path, monkeypatch)
    viewer = paths.extensions / "tomoki1207.pdf-1.0.0"
    viewer.mkdir(parents=True)
    (viewer / "package.json").write_text(json.dumps({"contributes": {"customEditors": [
        {"selector": [{"filenamePattern": "*.pdf"}]}]}}), encoding="utf-8")
    (paths.extensions / "extensions.json").write_text(json.dumps(
        listed(paths.extensions, "tomoki1207.pdf", "anthropic.claude-code")), encoding="utf-8")
    assert launch.has_pdf_viewer() and launch.has_claude()  # default profile: its own list
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    assert not launch.has_pdf_viewer() and not launch.has_claude()  # new profile: nothing in it yet
    own = paths.data / "User" / "profiles" / "cez-job-finder" / "extensions.json"
    own.write_text(json.dumps(listed(paths.extensions, "anthropic.claude-code")), encoding="utf-8")
    assert launch.has_claude() and not launch.has_pdf_viewer()
    import ai
    assert ai.current(tmp_path / "no-choice") == "claude"


def profile_extension(paths, ident, version="1.0.0", manifest=None):
    """List `ident` in Job Finder's profile w/ its package.json, as VS Code leaves it."""
    folder = paths.extensions / f"{ident}-{version}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "package.json").write_text(json.dumps({"version": version, **(manifest or {})}), encoding="utf-8")
    own = paths.data / "User" / "profiles" / "cez-job-finder" / "extensions.json"
    entries = json.loads(own.read_text(encoding="utf-8")) if own.exists() else []
    entries = [e for e in entries if e["identifier"]["id"] != ident]
    entries.append({"identifier": {"id": ident}, "version": version, "relativeLocation": folder.name})
    own.write_text(json.dumps(entries), encoding="utf-8")


PDF_MANIFEST = {"contributes": {"customEditors": [{"selector": [{"filenamePattern": "*.pdf"}]}]}}


@pytest.mark.parametrize("choice, ai_ext", [("claude", "anthropic.claude-code"), ("chatgpt", "openai.chatgpt"),
                                            ("copilot", None)])
def test_one_install_call_for_only_what_the_profile_lacks(tmp_path, monkeypatch, choice, ai_ext):
    # one call per extension = ~3 s each at every launch (one batched call: 3.0 s for all four);
    # one already listed reinstalled = slower launch for nothing; Copilot's chat is built in
    import vscode_ext
    paths = profile_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(vscode_ext, "OUT", tmp_path / "vsix")
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    calls = []
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: calls.append(args) or 0)
    assert launch.ensure_extensions(choice)
    ours, version = vscode_ext.extension_id(), vscode_ext.manifest()["version"]
    vsix = str(tmp_path / "vsix" / f"{ours}-{version}.vsix")
    wanted = [*([ai_ext] if ai_ext else []), launch.PDF_EXTENSION, launch.YAML_EXTENSION, vsix]
    assert calls == [[*(a for ext in wanted for a in ("--install-extension", ext)), "--force"]]
    assert Path(vsix).exists()
    if ai_ext:
        profile_extension(paths, ai_ext)
    profile_extension(paths, launch.PDF_EXTENSION, manifest=PDF_MANIFEST)
    profile_extension(paths, launch.YAML_EXTENSION)
    profile_extension(paths, ours, version)
    calls.clear()
    assert launch.ensure_extensions(choice) and calls == []  # all listed => no code call at all
    profile_extension(paths, ours, "0.0.1")  # last release's copy => this one, nothing else
    assert launch.ensure_extensions(choice) and calls == [["--install-extension", vsix, "--force"]]


def test_users_own_pdf_viewer_in_the_profile_kept(tmp_path, monkeypatch):
    # two viewers claiming .pdf => VS Code asks which editor on every single click
    paths = profile_paths(tmp_path, monkeypatch)
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    profile_extension(paths, "someone.elses-pdf-viewer", manifest=PDF_MANIFEST)
    assert launch.PDF_EXTENSION not in [ext for ext, _ in launch.missing_extensions(None)]


def test_every_code_call_lands_in_job_finders_profile_once_made(tmp_path, monkeypatch):
    # w/o --profile, installs went to the default profile (reinstalled at every launch, never
    # seen by the window) and an opened file could land in a default-profile window
    import jobs
    paths = profile_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/code")
    scratch = ["/bin/code", "--user-data-dir", str(paths.data), "--extensions-dir", str(paths.extensions),
               "--shared-data-dir", str(paths.shared)]
    assert launch.code_command(["x"]) == [*scratch, "x"]  # not made yet: an unknown name fails the call
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    assert launch.code_command(["x"]) == [*scratch, "--profile", "CEZ Job Finder", "x"]
    runs = []
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args) or type("R", (), {"returncode": 0}))
    launch.code(["--install-extension", launch.YAML_EXTENSION])
    page = tmp_path / "Job posting.md"
    page.write_text("x", encoding="utf-8")
    jobs.open_for_user(str(page))
    assert [r[7:9] for r in runs] == [["--profile", "CEZ Job Finder"]] * 2


def test_code_calls_built_in_one_place():
    # a call site building its own command skipped --profile => installed into or opened in the
    # default profile; every call site named here so a new one is a deliberate choice
    import ast
    sites = {}
    for name in "jobs.py", "ai.py", "launch.py":
        tree = ast.parse((cfg.APP / name).read_text(encoding="utf-8"))
        for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            for call in (c for c in ast.walk(func) if isinstance(c, ast.Call)):
                callee = ast.unparse(call.func)
                if callee in ("code", "launch.code", "code_command", "launch.code_command"):
                    sites.setdefault(name, set()).add(func.name)
                if callee == "shutil.which" and ast.unparse(call.args[0]) in ("'code'", '"code"'):
                    sites.setdefault(name, set()).add(f"which:{func.name}")
    assert sites == {"jobs.py": {"open_for_user"},
                     "launch.py": {"which:code_command", "code", "ensure_extensions", "main"}}


def test_window_setup_says_what_it_does_and_falls_back_while_vscode_runs(tmp_path, monkeypatch, capsys):
    # installer terminal is the only place an install failure shows (launcher output goes nowhere)
    import vscode_ext
    paths = profile_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(vscode_ext, "OUT", tmp_path / "vsix")
    monkeypatch.setattr(launch.cfg, "ensure_private_dirs", lambda: None)
    monkeypatch.setattr(launch, "chosen_ai", lambda: "claude")
    monkeypatch.setattr(launch, "vscode_running", lambda paths=None: True)
    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/code")
    runs = []
    result = type("R", (), {"returncode": 0})
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args) or result)
    launch.window_setup()  # VS Code open => default profile, as installers did before
    out = capsys.readouterr().out
    assert "next time it starts" in out and "the Claude chat panel" in out and "VS Code is ready." in out
    assert "--profile" not in runs[0] and "anthropic.claude-code" in runs[0]
    for jargon in "profile", "extension", "vsix", "yaml":
        assert jargon not in out.lower(), jargon
    result.returncode = 1
    with pytest.raises(SystemExit):  # installer then installs the AI panel the old way
        launch.window_setup()
    monkeypatch.setattr(launch, "vscode_running", lambda paths=None: False)
    monkeypatch.setattr(launch, "PROFILE_MIGRATED", tmp_path / "profile-migrated")
    result.returncode = 0
    runs.clear()
    launch.window_setup()
    assert "own space" in capsys.readouterr().out and runs[0][7:9] == ["--profile", "CEZ Job Finder"]


def state_db(path, rows):
    """VS Code's state.vscdb, same table as VS Code makes it."""
    import sqlite3
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    with db:
        db.execute(launch.ITEM_TABLE)
        db.executemany("INSERT INTO ItemTable (key, value) VALUES (?, ?)", rows)
    db.close()


def state_rows(path):
    import sqlite3
    db = sqlite3.connect(path)
    try:
        return dict(db.execute("SELECT key, value FROM ItemTable").fetchall())
    finally:
        db.close()


MODEL = "chat.currentLanguageModel.panel"


def test_model_pick_zoom_and_text_size_follow_into_the_profile_once(tmp_path, monkeypatch):
    # new profile starts on Copilot's automatic model (fails tailored resumes) and at default zoom
    paths, marker = profile_paths(tmp_path, monkeypatch), tmp_path / "data" / "profile-migrated"
    state_db(paths.global_storage / "state.vscdb", [(MODEL, "copilot/claude-sonnet"), (f"{MODEL}.isDefault", "false"),
                                                     ("sync.enable", "true"), ("other.key", "x")])
    paths.settings.write_text('{\n  // mine\n  "window.zoomLevel": 1.5,\n  "editor.fontSize": 16,\n  "editor.tabSize": 8,\n}\n',
                              encoding="utf-8")
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    launch.migrate_profile(paths, marker)
    profile = paths.data / "User" / "profiles" / "cez-job-finder"
    assert state_rows(profile / "globalStorage" / "state.vscdb") == {MODEL: "copilot/claude-sonnet", f"{MODEL}.isDefault": "false"}
    settings = launch.settings_values((profile / "settings.json").read_text(encoding="utf-8"))
    assert settings["window.zoomLevel"] == 1.5 and settings["editor.fontSize"] == 16 and "editor.tabSize" not in settings
    assert marker.read_text(encoding="utf-8") == "model: copied\n"
    # run once: a pick changed later in the default profile never overwrites the profile's
    state_db(paths.global_storage / "state.vscdb", [(MODEL, "copilot/gpt-auto")])
    launch.migrate_profile(paths, marker)
    assert state_rows(profile / "globalStorage" / "state.vscdb")[MODEL] == "copilot/claude-sonnet"


def test_pick_already_made_in_the_profile_kept(tmp_path, monkeypatch):
    # the user's choice inside Job Finder overwritten by an older one from their other work
    paths = profile_paths(tmp_path, monkeypatch)
    state_db(paths.global_storage / "state.vscdb", [(MODEL, "copilot/gpt-auto")])
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    own = paths.data / "User" / "profiles" / "cez-job-finder" / "globalStorage" / "state.vscdb"
    state_db(own, [(MODEL, "copilot/claude-sonnet")])
    settings = paths.data / "User" / "profiles" / "cez-job-finder" / "settings.json"
    settings.write_text('{"editor.fontSize": 20}', encoding="utf-8")
    paths.settings.write_text('{"editor.fontSize": 12}', encoding="utf-8")
    launch.migrate_profile(paths, tmp_path / "marker")
    assert state_rows(own)[MODEL] == "copilot/claude-sonnet"
    assert launch.settings_values(settings.read_text(encoding="utf-8")) == {"editor.fontSize": 20}


def test_nothing_to_copy_or_unreadable_state_is_no_error(tmp_path, monkeypatch):
    # a launch that stops on a broken VS Code state file never opens the window at all
    paths, marker = profile_paths(tmp_path, monkeypatch), tmp_path / "marker"
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    launch.migrate_profile(paths, marker)  # fresh VS Code: no state db, no settings
    assert marker.read_text(encoding="utf-8") == "model: not copied\n"
    marker.unlink()
    paths.global_storage.joinpath("state.vscdb").write_bytes(b"not a database")
    launch.migrate_profile(paths, marker)
    assert marker.read_text(encoding="utf-8") == "model: not copied\n"
    assert not (paths.data / "User" / "profiles" / "cez-job-finder" / "globalStorage").exists()


def test_running_vscode_profile_state_untouched(tmp_path, monkeypatch):
    # VS Code running holds the state db open => our write lost or the user's pick clobbered
    paths, marker = profile_paths(tmp_path, monkeypatch), tmp_path / "marker"
    state_db(paths.global_storage / "state.vscdb", [(MODEL, "copilot/claude-sonnet"), ("sync.enable", "true")])
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    (paths.data / "code.lock").write_text(str(launch.os.getpid()), encoding="utf-8")
    launch.migrate_profile(paths, marker)
    launch.keep_out_of_sync(paths)
    assert not marker.exists() and not (paths.data / "User" / "profiles" / "cez-job-finder" / "globalStorage").exists()
    assert not paths.settings.exists()


def test_window_extension_kept_out_of_settings_sync(tmp_path, monkeypatch):
    # synced, another computer asks the Marketplace for an id that isn't there (or someone else's)
    import vscode_ext
    paths = profile_paths(tmp_path, monkeypatch)
    ours = vscode_ext.extension_id()
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    profile_extension(paths, launch.PDF_EXTENSION)
    profile_extension(paths, ours)
    listing = paths.data / "User" / "profiles" / "cez-job-finder" / "extensions.json"
    entries = json.loads(listing.read_text(encoding="utf-8"))
    entries[-1]["metadata"] = {"source": "vsix", "pinned": True, "isMachineScoped": False}
    listing.write_text(json.dumps(entries), encoding="utf-8")
    paths.settings.write_text('{"editor.tabSize": 8}', encoding="utf-8")
    launch.keep_out_of_sync(paths)  # sync off: their settings file untouched
    entries = {e["identifier"]["id"]: e for e in json.loads(listing.read_text(encoding="utf-8"))}
    assert entries[ours]["metadata"] == {"source": "vsix", "pinned": True, "isMachineScoped": True}
    assert "metadata" not in entries[launch.PDF_EXTENSION]
    assert paths.settings.read_text(encoding="utf-8") == '{"editor.tabSize": 8}'
    state_db(paths.global_storage / "state.vscdb", [("sync.enable", "true")])
    launch.keep_out_of_sync(paths)
    launch.keep_out_of_sync(paths)  # once only
    assert launch.settings_values(paths.settings.read_text(encoding="utf-8")) == {
        "editor.tabSize": 8, launch.SYNC_IGNORED: [ours]}


def test_sync_ignore_list_edited_in_place():
    # rewriting the settings file as JSON drops every comment the user wrote in it
    text = '{\n  // keep\n  "settingsSync.ignoredExtensions": [\n    "a.b", // theirs\n  ],\n}\n'
    out = launch.add_to_list_setting(text, launch.SYNC_IGNORED, "cez-job-finder.window")
    assert out == text.replace('[\n', '["cez-job-finder.window", \n', 1)
    assert launch.settings_values(out)[launch.SYNC_IGNORED] == ["cez-job-finder.window", "a.b"]
    assert launch.add_to_list_setting(out, launch.SYNC_IGNORED, "CEZ-Job-Finder.window") == out
    empty = '{"settingsSync.ignoredExtensions": []}'
    assert launch.add_to_list_setting(empty, launch.SYNC_IGNORED, "x.y") == '{"settingsSync.ignoredExtensions": ["x.y"]}'
    commented = '{\n  // "settingsSync.ignoredExtensions": ["old"]\n}'
    assert launch.settings_values(launch.add_to_list_setting(commented, launch.SYNC_IGNORED, "x.y")) == {
        launch.SYNC_IGNORED: ["x.y"]}


def test_ai_found_from_its_extension_is_written_down(tmp_path, monkeypatch):
    # installs before the choice file: the window extension saw no AI and every Today button copied
    import ai
    choice = tmp_path / "ai"
    monkeypatch.setattr(ai, "CHOICE_FILE", choice)
    monkeypatch.setattr(ai, "current", lambda: "claude")
    assert launch.chosen_ai() == "claude"
    assert choice.read_text(encoding="utf-8").strip() == "claude"


def test_profile_waiting_on_a_cold_start_is_flagged_for_the_window(tmp_path):
    # VS Code left open => no profile, and nothing told the user to quit it once
    flag = tmp_path / "profile-pending"
    launch.mark_profile_pending(flag)
    assert "quit VS Code" in flag.read_text(encoding="utf-8")


def views_state(paths):
    return paths.data / "User" / "profiles" / "cez-job-finder" / "globalStorage" / "state.vscdb"


def test_outline_and_timeline_hidden_under_the_file_list_once(tmp_path, monkeypatch):
    # Outline + Timeline under the file list made the window read as a code editor
    paths = profile_paths(tmp_path, monkeypatch)
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    launch.hide_side_views(paths)
    views = json.loads(state_rows(views_state(paths))[launch.VIEWS_KEY])
    assert views == [{"id": "outline", "isHidden": True}, {"id": "timeline", "isHidden": True}]
    assert "workbench.explorer.fileView" not in str(views)  # file list never hidden
    # user shows Outline again later => next cold start leaves it shown
    state_db(views_state(paths), [(launch.VIEWS_KEY, '[{"id":"outline","isHidden":false}]')])
    launch.hide_side_views(paths)
    assert json.loads(state_rows(views_state(paths))[launch.VIEWS_KEY]) == [{"id": "outline", "isHidden": False}]


def test_hiding_views_keeps_what_vscode_wrote(tmp_path, monkeypatch):
    # rewriting VS Code's own list lost the file list's place or another view the user hid
    paths = profile_paths(tmp_path, monkeypatch)
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    written = [{"id": "workbench.explorer.fileView", "isHidden": False, "order": 0},
               {"id": "outline", "isHidden": False, "order": 2}, "npm"]
    state_db(views_state(paths), [(launch.VIEWS_KEY, json.dumps(written)), (MODEL, "copilot/claude-sonnet")])
    launch.hide_side_views(paths)
    rows = state_rows(views_state(paths))
    assert json.loads(rows[launch.VIEWS_KEY]) == [written[0], "npm", {"id": "outline", "isHidden": True, "order": 2},
                                                  {"id": "timeline", "isHidden": True}]
    assert rows[MODEL] == "copilot/claude-sonnet"


def test_hiding_views_never_touches_a_running_or_unreadable_state(tmp_path, monkeypatch):
    # VS Code running holds the db open; a value it wrote we can't read must never be replaced
    paths = profile_paths(tmp_path, monkeypatch)
    launch.hide_side_views(paths)  # no profile yet: nothing, no error
    assert launch.ensure_profile(tmp_path / "jobs", paths)
    state_db(views_state(paths), [(launch.VIEWS_KEY, "not json")])
    launch.hide_side_views(paths)
    assert state_rows(views_state(paths)) == {launch.VIEWS_KEY: "not json"}
    views_state(paths).unlink()
    (paths.data / "code.lock").write_text(str(launch.os.getpid()), encoding="utf-8")
    launch.hide_side_views(paths)
    assert not views_state(paths).exists()
    views_state(paths).write_bytes(b"not a database")
    (paths.data / "code.lock").unlink()
    launch.hide_side_views(paths)  # broken db: launch carries on


def trust_list(state):
    return json.loads(state_rows(state)[launch.TRUST_KEY])["uriTrustInfo"]


def shared_state(paths):
    return paths.shared / "sharedStorage" / "state.vscdb"


def test_folder_trusted_so_a_dock_open_still_runs_the_ai_panel(tmp_path, monkeypatch):
    # opened from the Dock / recent folders => Restricted Mode: Claude + PDF viewer never ran
    paths = profile_paths(tmp_path, monkeypatch)
    root = tmp_path / "jobs"
    launch.ensure_folder_trusted(root, paths)
    # VS Code never started: default db, VS Code moves it to its shared store on first read
    default = paths.global_storage / "state.vscdb"
    assert trust_list(default) == [{"uri": {"$mid": 1, "path": str(root), "scheme": "file"}, "trusted": True}]
    launch.ensure_folder_trusted(root, paths)  # once only
    assert len(trust_list(default)) == 1
    # VS Code already moved the key into the shared store => written there, other folders kept
    other = {"uri": {"$mid": 1, "path": "/Users/Your Name/code", "scheme": "file"}, "trusted": True}
    state_db(shared_state(paths), [(launch.MIGRATED_KEY, json.dumps([launch.TRUST_KEY])),
                                   (launch.TRUST_KEY, json.dumps({"uriTrustInfo": [other]}))])
    launch.ensure_folder_trusted(root, paths)
    assert trust_list(shared_state(paths)) == [other, {"uri": {"$mid": 1, "path": str(root), "scheme": "file"}, "trusted": True}]


def test_trust_written_where_vscode_reads_it(tmp_path, monkeypatch):
    # written to the default db after VS Code moved the key => ignored, folder stayed untrusted
    paths = profile_paths(tmp_path, monkeypatch)
    root = tmp_path / "jobs"
    state_db(shared_state(paths), [(launch.MIGRATED_KEY, json.dumps([launch.TRUST_KEY]))])
    launch.ensure_folder_trusted(root, paths)
    assert trust_list(shared_state(paths))[0]["uri"]["path"] == str(root)
    assert not (paths.global_storage / "state.vscdb").exists()
    # shared store there but key not moved yet => default db, so the folders it holds move together
    shared_state(paths).unlink()
    state_db(shared_state(paths), [(launch.MIGRATED_KEY, "[]")])
    launch.ensure_folder_trusted(root, paths)
    assert launch.TRUST_KEY not in state_rows(shared_state(paths))
    assert trust_list(paths.global_storage / "state.vscdb")[0]["uri"]["path"] == str(root)


def test_trust_never_touches_a_running_or_unreadable_store(tmp_path, monkeypatch):
    # VS Code running writes its own copy back on quit; a value we can't read must never be replaced
    paths = profile_paths(tmp_path, monkeypatch)
    root = tmp_path / "jobs"
    state_db(shared_state(paths), [(launch.TRUST_KEY, "not json")])
    launch.ensure_folder_trusted(root, paths)
    assert state_rows(shared_state(paths)) == {launch.TRUST_KEY: "not json"}
    shared_state(paths).unlink()
    paths.data.mkdir(parents=True, exist_ok=True)
    (paths.data / "code.lock").write_text(str(launch.os.getpid()), encoding="utf-8")
    launch.ensure_folder_trusted(root, paths)
    assert not (paths.global_storage / "state.vscdb").exists()
    (paths.data / "code.lock").unlink()
    shared_state(paths).write_bytes(b"not a database")
    launch.ensure_folder_trusted(root, paths)  # broken store: launch carries on


def test_trust_uri_matches_vscode_on_windows():
    # backslash path never matched the open folder => untrusted on Windows
    assert launch.trust_uri("C:\\Users\\Your Name\\jobs", windows=True) == {
        "$mid": 1, "path": "/C:/Users/Your Name/jobs", "scheme": "file"}
    assert launch.trust_uri("/Users/Your Name/jobs/", windows=False)["path"] == "/Users/Your Name/jobs"
