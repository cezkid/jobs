import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP))
_spec = importlib.util.spec_from_file_location("release", _APP / "deploy" / "release.py")
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)
import ed25519  # noqa: E402

NOTES = "# v1\n\n## For users\nFaster start.\n\n## For maintainers\nChanged the config.\n"


def _git(root, *a):
    subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "r"
    (root / "app").mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "a@b.c")
    _git(root, "config", "user.name", "t")
    (root / "app" / "VERSION").write_text("1.2.3\n")
    (root / "app" / "update.py").write_text("# SIGNED_RELEASE_PATH\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "x")
    notes = tmp_path / "n.md"
    notes.write_text(NOTES)
    keydir = tmp_path / "keys"
    release.new_key(keydir)
    return root, notes, keydir / "release.key", tmp_path / "out"


def run(env, *extra, notes=None):
    root, n, key, out = env
    return release.main(["--notes", str(notes or n), "--key", str(key), "--out", str(out), *extra], root=root)


def test_builds_and_signs(env, capsys):
    assert run(env) == 0
    out = env[3]
    assert (out / "jobs-v1.2.3.zip").is_file()
    sums = (out / "SHA256SUMS").read_bytes()
    sig = (out / "SHA256SUMS.sig").read_bytes()
    pub = bytes.fromhex((env[2].parent / "release.pub").read_text().strip())
    assert ed25519.verify(pub, sums, sig)
    assert b"jobs-v1.2.3.zip" in sums
    assert "Would run: gh release create v1.2.3" in capsys.readouterr().out


def test_publish_calls_gh(env, monkeypatch):
    calls = []
    real = subprocess.run

    def fake(cmd, *a, **k):
        if cmd[0] == "gh":
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)
        return real(cmd, *a, **k)

    monkeypatch.setattr(release.subprocess, "run", fake)
    assert run(env, "--publish") == 0
    assert calls and calls[0][:4] == ["gh", "release", "create", "v1.2.3"]


def test_dirty_tree(env):
    (env[0] / "app" / "VERSION").write_text("9\n")
    assert run(env) == 1


def test_tag_exists(env):
    _git(env[0], "tag", "v1.2.3")
    assert run(env) == 1


def test_tag_mismatch(env):
    assert run(env, "--tag", "v9.9.9") == 1


def test_no_for_users(env, tmp_path):
    n = tmp_path / "bad.md"
    n.write_text("## Other\nhi\n")
    assert run(env, notes=n) == 1


@pytest.mark.parametrize("word", ["config", "JSON", "API", "repo", "commit", "branch", "PR", "yml"])
def test_jargon(env, tmp_path, word):
    n = tmp_path / "j.md"
    n.write_text(f"## For users\nFixed the {word} thing.\n")
    assert run(env, notes=n) == 1


def test_missing_marker(env):
    root = env[0]
    (root / "app" / "update.py").write_text("old\n")
    _git(root, "commit", "-qam", "y")
    assert run(env) == 1


def test_new_key_refuses_inside_repo():
    with pytest.raises(release.Refuse):
        release.new_key(release.REPO / "keys-here")


def test_new_key_pub_matches(tmp_path):
    pub = release.new_key(tmp_path / "k")
    seed = release.read_key(tmp_path / "k" / "release.key")
    assert ed25519.public_key(seed).hex() == pub
