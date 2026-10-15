import hashlib
import io
import subprocess
import zipfile
from pathlib import Path

import httpx
import pytest

import ed25519
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


@pytest.mark.parametrize("said, runs_new", [(update.UP_TO_DATE, True), (update.OFFLINE, False), (update.IN_USE, False)])
def test_update_hands_the_window_extension_to_the_new_program(monkeypatch, capsys, said, runs_new):
    # owner 2026-10-05: update shipped a new window extension, the window never got it until the
    # next cold launch. The NEW program installs it (this process still holds the old modules)
    calls = []
    monkeypatch.setattr(update, "update", lambda root, client=None: said)
    monkeypatch.setattr(update.subprocess, "run", lambda args, check: calls.append(args))
    update.main()
    assert capsys.readouterr().out == f"{said}\n"
    assert calls == ([[update.sys.executable, str(update.cfg.ROOT / "app" / "jobs.py"), "window-update"]] if runs_new else [])


# ---- signed release path (keys file present) ----
SEED = bytes(range(32))
OTHER = bytes(range(1, 33))


def release_zip(version="2.0.0", marker=True):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"jobs-v{version}/app/update.py", "SIGNED_RELEASE_PATH" if marker else "nope")
        z.writestr(f"jobs-v{version}/app/VERSION", version)
        z.writestr(f"jobs-v{version}/README.md", "new")
    return buf.getvalue()


def client_for(version="2.0.0", seed=SEED, marker=True, bad_sha=False, status=200, etag='"e1"'):
    blob = release_zip(version, marker)
    name = f"jobs-v{version}.zip"
    digest = "0" * 64 if bad_sha else hashlib.sha256(blob).hexdigest()
    sums = f"{digest}  {name}\n".encode()
    sig = ed25519.sign(seed, sums)

    def handler(request):
        path = request.url.path
        if path.endswith("/releases/latest"):
            if status != 200:
                return httpx.Response(status)
            body = {"tag_name": f"v{version}", "assets": [
                {"name": n, "browser_download_url": f"https://dl.test/{n}"} for n in (name, "SHA256SUMS", "SHA256SUMS.sig")]}
            return httpx.Response(200, json=body, headers={"etag": etag})
        return httpx.Response(200, content={name: blob, "SHA256SUMS": sums, "SHA256SUMS.sig": sig}[path[1:]])

    return httpx.Client(transport=httpx.MockTransport(handler))


def with_keys(root, *seeds):
    seeds = seeds or (SEED,)
    write(root / "app" / "update-keys.txt", "# keys\n" + "\n".join(ed25519.public_key(s).hex() for s in seeds) + "\n")
    write(root / "app" / "VERSION", "1.0.0")
    write(root / "README.md", "old")


def test_no_keys_means_main_zip_never_touches_releases(tmp_path, monkeypatch):
    write(tmp_path / "README.md", "old")
    monkeypatch.setattr(update, "download", lambda: archive({"README.md": "new"}))

    def boom(request):
        raise AssertionError("no release call")

    assert update.update(tmp_path, httpx.Client(transport=httpx.MockTransport(boom))) == update.UP_TO_DATE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "new"


def test_signed_newer_release_installs_and_keeps_copy(tmp_path):
    with_keys(tmp_path)
    write(tmp_path / "My Settings" / "s.yml", "mine")
    assert update.update(tmp_path, client_for()) == update.UP_TO_DATE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "new"
    assert (tmp_path / ".data" / "previous" / "README.md").read_text(encoding="utf-8") == "old"
    assert (tmp_path / ".data" / "previous" / "app" / "VERSION").read_text(encoding="utf-8") == "1.0.0"
    assert (tmp_path / ".data" / "app-version").read_text(encoding="utf-8").strip() == "2.0.0"
    assert (tmp_path / "My Settings" / "s.yml").read_text(encoding="utf-8") == "mine"


def test_either_key_verifies(tmp_path):
    with_keys(tmp_path, OTHER, SEED)
    assert update.update(tmp_path, client_for()) == update.UP_TO_DATE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "new"


@pytest.mark.parametrize("kw, said", [
    ({"seed": OTHER}, update.UNVERIFIED),
    ({"bad_sha": True}, update.UNVERIFIED),
    ({"marker": False}, update.UNVERIFIED),
    ({"version": "1.0.0"}, update.UP_TO_DATE),
    ({"version": "0.9.0"}, update.UP_TO_DATE),
    ({"status": 403}, update.OFFLINE),
    ({"status": 404}, update.OFFLINE),
])
def test_bad_release_keeps_this_version(tmp_path, kw, said):
    with_keys(tmp_path)
    assert update.update(tmp_path, client_for(**kw)) == said
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"
    assert not (tmp_path / ".data" / "previous").exists()


def test_offline_release_keeps_this_version(tmp_path):
    with_keys(tmp_path)

    def down(request):
        raise httpx.ConnectError("no network")

    assert update.update(tmp_path, httpx.Client(transport=httpx.MockTransport(down))) == update.OFFLINE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"


def test_etag_cached_and_sent_back(tmp_path):
    with_keys(tmp_path)
    assert update.update(tmp_path, client_for()) == update.UP_TO_DATE
    seen = []
    c = httpx.Client(transport=httpx.MockTransport(lambda r: seen.append(r) or httpx.Response(304)))
    assert update.update(tmp_path, c) == update.UP_TO_DATE
    assert seen[0].headers["if-none-match"] == '"e1"'
    assert len(seen) == 1


def raw_release_client(files: dict[str, str], skip: str = ""):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, t in files.items():
            z.writestr(n, t)
    blob = buf.getvalue()
    sums = f"{hashlib.sha256(blob).hexdigest()}  jobs-v2.0.0.zip\n".encode()
    sig = ed25519.sign(SEED, sums)
    served = {"jobs-v2.0.0.zip": blob, "SHA256SUMS": sums, "SHA256SUMS.sig": sig}

    def handler(request):
        path = request.url.path
        if path.endswith("/releases/latest"):
            return httpx.Response(200, json={"tag_name": "v2.0.0", "assets": [
                {"name": n, "browser_download_url": f"https://dl.test/{n}"} for n in served if n != skip]})
        return httpx.Response(200, content=served[path[1:]])

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_update_release_gap_etag_write_error_keeps_version(tmp_path, monkeypatch):
    with_keys(tmp_path)

    def boom(self, *a, **k):
        raise OSError("read-only")

    monkeypatch.setattr(update.Path, "write_text", boom)
    assert update.update(tmp_path, client_for(version="1.0.0")) == update.UP_TO_DATE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"


def test_update_release_gap_marker_needs_exact_app_segment(tmp_path):
    with_keys(tmp_path)
    client = raw_release_client({"jobs-v2.0.0/xapp/update.py": "SIGNED_RELEASE_PATH", "jobs-v2.0.0/README.md": "new"})
    assert update.update(tmp_path, client) == update.UNVERIFIED
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"


@pytest.mark.parametrize("missing", ["jobs-v2.0.0.zip", "SHA256SUMS", "SHA256SUMS.sig"])
def test_update_release_gap_missing_asset_keeps_version(tmp_path, missing):
    with_keys(tmp_path)
    client = raw_release_client({"jobs-v2.0.0/app/update.py": "SIGNED_RELEASE_PATH"}, skip=missing)
    assert update.update(tmp_path, client) == update.UNVERIFIED
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"


def test_update_release_gap_failed_move_keeps_earlier_copy(tmp_path, monkeypatch):
    write(tmp_path / "README.md", "current")
    write(tmp_path / ".data" / "previous" / "README.md", "earlier")
    src = tmp_path / "src"
    write(src / "README.md", "new")
    (tmp_path / "tmp").mkdir()

    def boom(a, b):
        raise OSError("disk full")

    monkeypatch.setattr(update.shutil, "move", boom)
    with pytest.raises(OSError):
        update.save_previous(src, tmp_path, tmp_path / ".data", tmp_path / "tmp")
    assert (tmp_path / ".data" / "previous" / "README.md").read_text(encoding="utf-8") == "earlier"


def test_update_release_gap_odd_zip_layout_is_not_file_in_use(tmp_path):
    with_keys(tmp_path)
    client = raw_release_client({"a/app/update.py": "SIGNED_RELEASE_PATH", "b/README.md": "new"})
    said = update.update(tmp_path, client)
    assert said == update.BAD_PACK
    assert said != update.IN_USE
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "old"
