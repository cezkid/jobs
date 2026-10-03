import pytest

import ai
import jobs
import update
from test_update import archive, write


def extension(folder, name):
    (folder / f"{name}-1.0.0").mkdir(parents=True)


def test_saved_choice_first_then_claude_then_chatgpt(tmp_path):
    saved, exts = tmp_path / ".data" / "ai", tmp_path / "ext"
    exts.mkdir()
    assert ai.current(saved, exts) is None
    extension(exts, "openai.chatgpt")
    assert ai.current(saved, exts) == "chatgpt"
    extension(exts, "anthropic.claude-code")
    assert ai.current(saved, exts) == "claude"
    write(saved, "Copilot\r\n")  # Windows installer writes a CRLF line
    assert ai.current(saved, exts) == "copilot"
    write(saved, "gemini")  # unknown word => as if not saved
    assert ai.current(saved, exts) == "claude"


def test_never_infers_copilot(tmp_path):
    # Copilot Chat ships inside VS Code => an extension folder says nothing about the user's AI
    exts = tmp_path / "ext"
    extension(exts, "github.copilot-chat")
    extension(exts, "github.copilot")
    assert ai.current(tmp_path / "none", exts) is None


def test_set_validates_and_saves_one_word(tmp_path):
    saved = tmp_path / ".data" / "ai"
    assert ai.set(" COPILOT ", saved) == "copilot"
    assert saved.read_text(encoding="utf-8") == "copilot\n"
    with pytest.raises(ValueError):
        ai.set("gemini", saved)
    assert saved.read_text(encoding="utf-8") == "copilot\n"


def test_command_prints_and_saves(tmp_path, monkeypatch, capsys):
    saved = tmp_path / ".data" / "ai"
    monkeypatch.setattr(ai, "CHOICE_FILE", saved)
    monkeypatch.setenv(ai.launch.SCRATCH_ENV, str(tmp_path / "vscode"))
    monkeypatch.setattr("sys.argv", ["jobs.py", "ai"])
    jobs.main()
    assert "not chosen yet" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["jobs.py", "ai", "copilot"])
    jobs.main()
    out = capsys.readouterr().out
    assert "GitHub Copilot" in out and "reopen CEZ Job Finder" in out
    assert saved.read_text(encoding="utf-8") == "copilot\n"
    monkeypatch.setattr("sys.argv", ["jobs.py", "ai"])
    jobs.main()
    assert capsys.readouterr().out.strip() == "AI: GitHub Copilot (copilot)"
    monkeypatch.setattr("sys.argv", ["jobs.py", "ai", "gemini"])
    with pytest.raises(SystemExit):
        jobs.main()
    assert "ai" in jobs.COMMANDS


def test_update_keeps_saved_ai(tmp_path, monkeypatch):
    write(tmp_path / ".data" / "ai", "copilot\n")
    write(tmp_path / "app" / "jobs.py", "old")
    monkeypatch.setattr(update, "download", lambda: archive({"app/jobs.py": "new"}))
    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / ".data" / "ai").read_text(encoding="utf-8") == "copilot\n"
