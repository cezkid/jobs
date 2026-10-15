"""Maintainer release: zip + SHA256SUMS + signature (+ gh release create).

uv run app/deploy/release.py --notes notes.md --key release.key [--publish]
uv run app/deploy/release.py --new-key ~/keys      (outside the repo)

Key file = 64 hex chars (Ed25519 seed). Design: app/docs/updates.md.
"""

import argparse
import hashlib
import re
import secrets
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
import ed25519  # noqa: E402

REPO = APP.parent
MARKER = "SIGNED_RELEASE_PATH"  # must appear in app/update.py
BANNED = ["config", "yml", "yaml", "json", "api", "repo", "commit", "branch", "pr", "schema", "slug", "params", "facet", "pytest"]


class Refuse(Exception):
    pass


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode:
        raise Refuse(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def for_users(notes: str) -> str | None:
    m = re.search(r"^##\s+For users\s*$(.*?)(?=^##\s|\Z)", notes, re.M | re.S | re.I)
    if not m or not m.group(1).strip():
        return None
    return m.group(1)


def jargon(text: str) -> list[str]:
    return sorted({w for w in BANNED if re.search(rf"\b{w}s?\b", text, re.I)})


def read_key(path: Path) -> bytes:
    try:
        seed = bytes.fromhex(path.read_text().strip())
    except (OSError, ValueError):
        raise Refuse(f"key file {path} is not 64 hex characters")
    if len(seed) != 32:
        raise Refuse(f"key file {path} is not 64 hex characters")
    return seed


def check(root: Path, notes_path: Path, tag: str | None = None) -> tuple[str, str]:
    """All refusals. Returns (version, tag)."""
    if _git(root, "status", "--porcelain").strip():
        raise Refuse("working tree is not clean")
    vfile = root / "app" / "VERSION"
    if not vfile.is_file():
        raise Refuse("app/VERSION missing")
    version = vfile.read_text().strip()
    tag = tag or f"v{version}"
    if tag != f"v{version}":
        raise Refuse(f"tag {tag} does not match app/VERSION ({version})")
    if _git(root, "tag", "--list", tag).strip():
        raise Refuse(f"tag {tag} already exists")
    upd = root / "app" / "update.py"
    if not upd.is_file() or MARKER not in upd.read_text():
        raise Refuse(f"app/update.py lacks the signed-release path ({MARKER})")
    try:
        notes = notes_path.read_text()
    except OSError:
        raise Refuse(f"notes file {notes_path} not readable")
    section = for_users(notes)
    if section is None:
        raise Refuse('notes have no "## For users" section')
    bad = jargon(section)
    if bad:
        raise Refuse("For users section uses jargon: " + ", ".join(bad))
    return version, tag


def build(root: Path, tag: str, seed: bytes, out: Path, users: str | None = None) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    zipf = out / f"jobs-{tag}.zip"
    _git(root, "archive", "--format=zip", f"--prefix=jobs-{tag}/", "-o", str(zipf), "HEAD")
    files = [zipf]
    if users:  # signed with the zip: Today's "What's new" reads this, never the unsigned GitHub body
        news = out / "WHATS-NEW.md"
        news.write_text("## For users\n" + users.strip() + "\n")
        files.append(news)
    sums = out / "SHA256SUMS"
    sums.write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in files))
    sig = out / "SHA256SUMS.sig"
    sig.write_bytes(ed25519.sign(seed, sums.read_bytes()))
    return [*files, sums, sig]


def new_key(dest: Path) -> str:
    dest = dest.expanduser().resolve()
    root = REPO.resolve()
    if dest == root or root in dest.parents:
        raise Refuse("key folder must be outside the repository")
    dest.mkdir(parents=True, exist_ok=True)
    seed = secrets.token_bytes(32)
    keyf = dest / "release.key"
    keyf.write_text(seed.hex() + "\n")
    keyf.chmod(0o600)
    pub = ed25519.public_key(seed).hex()
    (dest / "release.pub").write_text(pub + "\n")
    return pub


def main(argv=None, root: Path = REPO) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--notes", type=Path)
    ap.add_argument("--key", type=Path)
    ap.add_argument("--tag")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--new-key", type=Path, dest="new_key")
    a = ap.parse_args(argv)
    try:
        if a.new_key:
            pub = new_key(a.new_key)
            print(f"Private key saved in {a.new_key} (keep offline, never commit).")
            print("Add this line to app/update-keys.txt:")
            print(pub)
            return 0
        if not a.notes or not a.key:
            raise Refuse("--notes and --key are required")
        version, tag = check(root, a.notes, a.tag)
        seed = read_key(a.key)
        out = a.out or root / ".data" / "release" / tag
        files = build(root, tag, seed, out, for_users(a.notes.read_text()))
        print(f"Release {tag} (version {version}) built in {out}:")
        for f in files:
            print(f"  {f.name}")
        cmd = ["gh", "release", "create", tag, *map(str, files), "--title", tag, "--notes-file", str(a.notes)]
        if not a.publish:
            print("Would run: " + " ".join(cmd))
            print("Add --publish to do it.")
            return 0
        return subprocess.run(cmd, cwd=root).returncode
    except Refuse as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
