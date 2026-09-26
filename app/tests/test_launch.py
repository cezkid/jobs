import json
import re

import cfg
import launch
import notify


def test_launch_creates_private_folders_on_fresh_install(tmp_path, monkeypatch):
    # fresh install ships none of them => START HERE.md promised a file list the user never saw
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: False)
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "ensure_mac_icon", lambda: None)
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: None)
    monkeypatch.setattr(launch.time, "sleep", lambda s: None)
    launch.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["My Jobs", "My Resume", "My Settings"]
    launch.main()  # second launch leaves what is already there alone


def test_launch_never_opens_chat_as_a_tab_over_start_here(tmp_path, monkeypatch):
    # the extension's open link always makes a tab in the active group => START HERE hidden
    calls = []
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: True)
    monkeypatch.setattr(launch, "ensure_claude_trust", lambda: None)
    monkeypatch.setattr(launch, "ensure_chat_sidebar", lambda: None)
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "ensure_mac_icon", lambda: None)
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: calls.append(args))
    monkeypatch.setattr(launch.time, "sleep", lambda s: calls.append(s))
    launch.main()
    window = ["--disable-workspace-trust", str(tmp_path)]
    # START HERE after the window is up => formatted, not plain text
    assert calls == [window, launch.START_PAGE_DELAY_S, [*window, str(launch.START_PAGE)]]


def test_claude_detected_by_extension_folder(tmp_path):
    assert not launch.has_claude(tmp_path)
    (tmp_path / "anthropic.claude-code-2.1.278-win32-x64").mkdir()
    assert launch.has_claude(tmp_path)


def test_toast_escapes_text_and_opens_job_finder():
    script = notify.windows_script("3 new <jobs> & O'Brien's", notify.HINT)
    assert "&lt;jobs&gt; &amp; O''Brien''s" in script
    assert f'launch="{notify.PROTOCOL}:open"' in script


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


def test_pdf_viewer_installed_once_and_never_over_the_users_own(tmp_path, monkeypatch):
    installed = []
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: installed.append(args))
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: False)
    launch.ensure_pdf_viewer()
    assert installed == [["--install-extension", launch.PDF_EXTENSION, "--force"]]
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: True)
    monkeypatch.setattr(launch, "ensure_yaml_checker", lambda: None)
    launch.ensure_pdf_viewer()
    assert len(installed) == 1


def test_claude_trusts_this_folder_only(tmp_path):
    # untrusted folder => its permission list ignored, user asked before every step
    state = tmp_path / ".claude.json"
    root = tmp_path / "jobs"
    launch.ensure_claude_trust(root, state)
    assert json.loads(state.read_text())["projects"][str(root)] == {"hasTrustDialogAccepted": True}
    state.write_text(json.dumps({"theme": "dark", "projects": {
        "/elsewhere": {"hasTrustDialogAccepted": False}, str(root): {"lastCost": 1}}}))
    launch.ensure_claude_trust(root, state)
    written = json.loads(state.read_text())
    assert written["theme"] == "dark" and written["projects"]["/elsewhere"] == {"hasTrustDialogAccepted": False}
    assert written["projects"][str(root)] == {"lastCost": 1, "hasTrustDialogAccepted": True}
    state.write_text("{broken")
    launch.ensure_claude_trust(root, state)  # a file Claude is mid-way writing stays as it is
    assert state.read_text() == "{broken"


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
    monkeypatch.setattr(jobs.shutil, "which", lambda name: "code")
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


def test_workspace_hides_builtin_vscode_chat():
    # without this the built-in Copilot chat owns the right-hand panel on first open
    raw = (cfg.ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    assert settings["chat.disableAIFeatures"] is True


def test_yaml_checker_installed_once_and_telemetry_answered(tmp_path, monkeypatch):
    # user is asked to decide about Red Hat telemetry on first activation otherwise, mid job search
    installed = []
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: installed.append(args))
    monkeypatch.setattr(launch, "has_extension", lambda name: False)
    settings = tmp_path / "User" / "settings.json"
    launch.ensure_yaml_checker(settings)
    assert launch.TELEMETRY in settings.read_text(encoding="utf-8")
    assert installed == [["--install-extension", launch.YAML_EXTENSION, "--force"]]
    monkeypatch.setattr(launch, "has_extension", lambda name: True)
    launch.ensure_yaml_checker(settings)
    assert settings.read_text(encoding="utf-8").count("redhat.telemetry.enabled") == 1
    assert len(installed) == 1


def test_vscode_settings_keep_comments_and_trailing_commas():
    # developers' own settings files carry both; a JSON round-trip would silently delete them
    jsonc = '{\n  // mine\n  "editor.tabSize": 2,\n}\n'
    merged = launch.add_setting(jsonc, launch.TELEMETRY)
    assert "// mine" in merged and merged.count("\"editor.tabSize\": 2") == 1
    assert re.sub(r",(\s*})", r"\1", merged).strip().endswith(launch.TELEMETRY + "\n}")
    assert launch.add_setting("", launch.TELEMETRY) == "{\n  " + launch.TELEMETRY + "\n}\n"
    assert launch.add_setting("{}", launch.TELEMETRY) == "{\n  " + launch.TELEMETRY + "\n}"
    assert json.loads(launch.add_setting('{\n  "a": 1\n}\n', launch.TELEMETRY)) == {"a": 1, "redhat.telemetry.enabled": False}


def test_chat_opens_in_the_right_sidebar_not_a_tab():
    # default puts the chat in a tab and leaves Claude's right-hand sidebar empty, doing nothing
    raw = (cfg.ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    assert settings["claudeCode.preferredLocation"] == "sidebar"
    # sidebar shown on open => START HERE in the middle, chat beside it
    assert settings["workbench.secondarySideBar.defaultVisibility"] == "visible"
    assert settings["claudeCode.hideOnboarding"] is True


def test_start_page_leads_with_the_first_step():
    # users read the whole page and still did not know what to do
    page = (cfg.ROOT / "START HERE.md").read_text(encoding="utf-8")
    assert page.split("\n## ")[1].startswith("Do this now") and "set me up" in page


def test_old_mac_icon_swapped_for_app_once(tmp_path, monkeypatch):
    # .command icon leaves a Terminal window open after every launch
    runs = []
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **kw: runs.append(args))
    launch.ensure_mac_icon(tmp_path / "CEZ Job Finder.command")
    assert runs == []  # no old icon => nothing made, a deleted icon stays deleted
    (tmp_path / "CEZ Job Finder.command").write_text("")
    launch.ensure_mac_icon(tmp_path / "CEZ Job Finder.command")
    assert runs == [["bash", str(launch.MAC_ICON_MAKER)]]


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
