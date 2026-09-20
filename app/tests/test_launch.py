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


def test_pdf_opens_in_system_viewer_other_files_in_vscode(tmp_path, monkeypatch):
    import jobs
    pdf, page = tmp_path / "Resume.pdf", tmp_path / "Job posting.md"
    pdf.write_bytes(b"%PDF")
    page.write_text("x", encoding="utf-8")
    viewer, tabs = [], []
    monkeypatch.setattr(jobs.shutil, "which", lambda name: "code")
    monkeypatch.setattr(jobs.webbrowser, "open", viewer.append)
    monkeypatch.setattr(jobs.subprocess, "run", lambda args, check: tabs.append(args[-1]))
    jobs.open_for_user(str(pdf))
    jobs.open_for_user(str(page))
    assert viewer == [pdf.resolve().as_uri()]
    assert tabs == [str(page.resolve())]


def test_workspace_hides_builtin_vscode_chat():
    # without this the built-in Copilot chat owns the right-hand panel on first open
    raw = (cfg.ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    assert settings["chat.disableAIFeatures"] is True
