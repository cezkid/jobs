import json
import re
from urllib.parse import parse_qs, urlparse

import cfg
import launch
import notify


def test_first_run_prompts_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(launch.cfg, "SETTINGS", tmp_path / "missing.yml")
    assert launch.prompt() == launch.FIRST_PROMPT
    (tmp_path / "missing.yml").write_text("x")
    assert launch.prompt() == launch.RETURN_PROMPT


def test_launch_creates_private_folders_on_fresh_install(tmp_path, monkeypatch):
    # fresh install ships none of them => START HERE.md promised a file list the user never saw
    monkeypatch.setattr(launch.cfg, "ROOT", tmp_path)
    monkeypatch.setattr(launch, "has_claude", lambda: False)
    monkeypatch.setattr(launch, "has_pdf_viewer", lambda: True)
    monkeypatch.setattr(launch.sys, "platform", "darwin")
    monkeypatch.setattr(launch, "code", lambda args, quiet=False: None)
    launch.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["My Jobs", "My Resume", "My Settings"]
    launch.main()  # second launch leaves what is already there alone


def test_claude_uri_carries_prompt():
    uri = urlparse(launch.claude_uri("any new jobs?"))
    assert (uri.scheme, uri.netloc, uri.path) == ("vscode", "anthropic.claude-code", "/open")
    assert parse_qs(uri.query) == {"prompt": ["any new jobs?"]}


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
    launch.ensure_pdf_viewer()
    assert len(installed) == 1


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
