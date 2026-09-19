import io
import zipfile

import httpx

import update


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
