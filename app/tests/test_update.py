import io
import subprocess
import zipfile
from pathlib import Path

import httpx
import pytest

import update

ROOT = Path(__file__).resolve().parents[2]


def archive(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(f"jobs-main/{name}", text)
    return buf.getvalue()


def write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_zip_replaces_program_keeps_private_folders(tmp_path, monkeypatch):
    write(tmp_path / "app" / "gone.py")
    write(tmp_path / "README.md", "old")
    write(tmp_path / "My Settings" / "Search settings.yml", "mine")
    write(tmp_path / "My Resume" / "Resume details.yml", "mine")
    write(tmp_path / ".data" / "jobs.db", "mine")
    new = archive({"app/jobs.py": "new", "README.md": "new", "My Settings/Search settings.yml": "theirs"})
    monkeypatch.setattr(update, "download", lambda: new)

    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / "app" / "jobs.py").read_text(encoding="utf-8") == "new"
    assert not (tmp_path / "app" / "gone.py").exists()
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "new"
    assert (tmp_path / "My Settings" / "Search settings.yml").read_text(encoding="utf-8") == "mine"
    assert (tmp_path / "My Resume" / "Resume details.yml").read_text(encoding="utf-8") == "mine"
    assert (tmp_path / ".data" / "jobs.db").read_text(encoding="utf-8") == "mine"
    assert [p.name for p in (tmp_path / ".data").iterdir()] == ["jobs.db"]


def test_offline_leaves_old_copy(tmp_path, monkeypatch):
    write(tmp_path / "app" / "jobs.py", "old")

    def offline():
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(update, "download", offline)
    assert update.update(tmp_path) == update.OFFLINE
    assert (tmp_path / "app" / "jobs.py").read_text(encoding="utf-8") == "old"


def test_git_checkout_pulls_instead(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    calls = []
    monkeypatch.setattr(update.subprocess, "run", lambda args, check: calls.append(args) or type("R", (), {"returncode": 0}))
    monkeypatch.setattr(update, "download", lambda: (_ for _ in ()).throw(AssertionError("no zip for git checkout")))
    assert update.update(tmp_path) == "Up to date."
    assert calls == [["git", "-C", str(tmp_path), "pull", "--ff-only", "-q"]]


def test_claude_dont_ask_again_answers_survive_update(tmp_path, monkeypatch):
    write(tmp_path / ".claude" / "settings.json", "old")
    write(tmp_path / ".claude" / "settings.local.json", "mine")
    new = archive({".claude/settings.json": "new", "app/jobs.py": "new"})
    monkeypatch.setattr(update, "download", lambda: new)

    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8") == "new"
    assert (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8") == "mine"


def test_folder_in_use_leaves_whole_old_copy(tmp_path, monkeypatch):
    # Windows refuses renaming folder w/ open file => swap stopped halfway mixed versions
    write(tmp_path / "README.md", "old")
    write(tmp_path / "app" / "jobs.py", "old")
    write(tmp_path / "docs" / "index.html", "old")
    new = archive({"README.md": "new", "app/jobs.py": "new", "brand-new.md": "new", "docs/index.html": "new"})
    monkeypatch.setattr(update, "download", lambda: new)
    rename = update.Path.rename

    def locked(self, target):
        if self == tmp_path / "docs":
            raise PermissionError(5, "Access is denied")
        return rename(self, target)

    monkeypatch.setattr(update.Path, "rename", locked)
    assert update.update(tmp_path) == update.IN_USE
    for name in ("README.md", "app/jobs.py", "docs/index.html"):
        assert (tmp_path / name).read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "brand-new.md").exists()


def test_vscode_settings_survive_update(tmp_path, monkeypatch):
    # gone from an open window => VS Code's own chat back over Claude/ChatGPT, or Copilot shut mid-chat
    write(tmp_path / ".vscode" / "settings.json", "mine")
    monkeypatch.setattr(update, "download", lambda: archive({"app/jobs.py": "new"}))
    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8") == "mine"
    monkeypatch.setattr(update, "download", lambda: archive({".vscode/extensions.json": "new", "app/jobs.py": "new"}))
    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8") == "mine"
    assert Path(".vscode") / "settings.json" in update.KEEP


def test_empty_docs_entry_clears_stale_site_copy(tmp_path, monkeypatch):
    # docs/** export-ignore leaves only an empty jobs-main/docs/ entry => stale site copy goes
    write(tmp_path / "docs" / "index.html", "old site")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("jobs-main/app/jobs.py", "new")
        z.writestr("jobs-main/docs/", "")
    monkeypatch.setattr(update, "download", lambda: buf.getvalue())

    assert update.update(tmp_path) == "Up to date."
    assert (tmp_path / "docs").is_dir()
    assert list((tmp_path / "docs").iterdir()) == []


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="installed copy: no git")
def test_download_leaves_site_out_keeps_program_docs():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--worktree-attributes", "--format=zip", "--prefix=jobs-main/", "HEAD"],
        capture_output=True, check=True,
    ).stdout
    names = zipfile.ZipFile(io.BytesIO(out)).namelist()
    assert [n for n in names if n.startswith("jobs-main/docs/")] == ["jobs-main/docs/"]
    assert "jobs-main/app/docs/site.md" in names
