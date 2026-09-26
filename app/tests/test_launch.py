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
    monkeypatch.setattr(launch, "ensure_auto_mode", lambda: None)
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


def test_auto_mode_turned_on_for_the_user_once(tmp_path):
    # without it the user is asked to approve nearly every step, which reads like an error
    settings = tmp_path / ".claude" / "settings.json"
    launch.ensure_auto_mode(settings)
    written = json.loads(settings.read_text(encoding="utf-8"))
    assert written["permissions"]["defaultMode"] == "auto"
    assert written["skipAutoPermissionPrompt"] is True
    settings.write_text(json.dumps(
        {"theme": "dark", "permissions": {"defaultMode": "plan", "allow": ["Read"]}}),
        encoding="utf-8")
    launch.ensure_auto_mode(settings)  # a mode the user chose themselves stays untouched
    assert json.loads(settings.read_text(encoding="utf-8"))["permissions"]["defaultMode"] == "plan"


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


def test_window_shows_job_finder_not_a_code_editor():
    # users saw a developer tool: search box, layout buttons, breadcrumbs
    raw = (cfg.ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    assert settings["window.title"] == cfg.NAME
    assert not settings["window.commandCenter"]
    assert settings["workbench.activityBar.location"] != "hidden"  # ChatGPT's icon is there
    # hiding tab buttons / status bar hid Claude's new-chat and open-chat buttons with them
    assert settings.get("workbench.editor.editorActionsLocation", "default") != "hidden"
    assert settings.get("workbench.statusBar.visible", True)


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
