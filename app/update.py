import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

import cfg

ZIP_URL = "https://github.com/cezkid/jobs/archive/refs/heads/main.zip"
DOWNLOAD_TIMEOUT_S = 60
# gitignored => never in zip; swap must never touch them either
PRIVATE = {*cfg.PRIVATE_DIRS, ".data", ".venv"}
# user's own files inside program folder => carried into new copy: Claude's "don't ask again"
# answers; this user's VS Code settings (app/workspace.py) - gone from an open window, VS Code's
# own chat comes back over Claude/ChatGPT, or Copilot's shuts mid-chat
KEEP = (Path(".claude") / "settings.local.json", Path(".vscode") / "settings.json")
OFFLINE = "Could not check for updates; continuing."
IN_USE = "Could not update now (a program file is open); continuing with this version."
UP_TO_DATE = "Up to date."
KEPT = ("Update skipped: {n} program {files} changed on this computer would be replaced ({first}). "
        "Send the change to the maintainer, or ask your AI to undo it, and the next start updates.")
# each shipped file's hash as last swapped in: a file differing from it AND from the new copy = an edit made
# here that the swap would wipe (2026-10-29: a Today feature built + tested in an install vanished at the next
# start; AGENTS.md "leave fix local" lost the same way). Runtime files (not in the zip) never count
RECORD = Path(".data") / "program-files.json"
# skipped => its files, one per line, for `jobs.py doctor` (the start script's own line goes unseen); gone once updated
SKIPPED = Path(".data") / "update-skipped"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shipped(src: Path) -> dict[str, str]:
    """Hash of every file the swap would put in place, by its path in root."""
    return {p.relative_to(src).as_posix(): digest(p) for p in sorted(src.rglob("*"))
            if p.is_file() and p.relative_to(src).parts[0] not in PRIVATE}


def local_edits(root: Path, new: dict[str, str]) -> list[str]:
    """Files changed here since the last swap that the new copy doesn't carry as they are now. No record
    (first update w/ this check) => none known."""
    try:
        was = json.loads((root / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for rel, h in was.items():
        here = root / rel
        if here.is_file() and Path(rel) not in KEEP:
            now = digest(here)
            if now != h and now != new.get(rel):
                out.append(rel)
    return out


class Kept(Exception):
    def __init__(self, files: list[str]):
        self.files = files


def download(url: str = ZIP_URL) -> bytes:
    response = httpx.get(url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_S)
    response.raise_for_status()
    return response.content


def swap_in(archive: bytes, root: Path) -> None:
    # unzip fully before touching root => bad download leaves old copy intact
    staging = root / ".data"
    staging.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging, ignore_cleanup_errors=True) as tmp:
        zipfile.ZipFile(io.BytesIO(archive)).extractall(tmp)
        (src,) = Path(tmp).iterdir()
        files = shipped(src)
        edits = local_edits(root, files)
        if edits:
            raise Kept(edits)
        for keep in KEEP:
            # folder absent from the zip (.vscode is never shipped) => swap leaves it alone, file and all
            if (root / keep).is_file() and (src / keep.parent).is_dir():
                shutil.copy2(root / keep, src / keep)
        trash = Path(tmp) / "old"
        trash.mkdir()
        moved_out, moved_in = [], []
        try:
            # whole top-level entries replaced => files deleted upstream vanish here too
            for new in sorted(src.iterdir()):
                if new.name in PRIVATE:
                    continue
                old = root / new.name
                if old.exists():
                    old.rename(trash / new.name)
                    moved_out.append(new.name)
                new.rename(old)
                moved_in.append(new.name)
        except OSError:
            # Windows refuses renaming folder w/ open file (antivirus scan, editor) => half-swapped
            # copy mixes versions or loses app/ => every entry goes back
            for name in reversed(moved_in):
                (root / name).rename(src / name)
            for name in reversed(moved_out):
                (trash / name).rename(root / name)
            raise
    (root / RECORD).write_text(json.dumps(files, indent=0, sort_keys=True), encoding="utf-8")
    (root / SKIPPED).unlink(missing_ok=True)


def update(root: Path) -> str:
    if (root / ".git").exists():
        pulled = subprocess.run(["git", "-C", str(root), "pull", "--ff-only", "-q"], check=False)
        return UP_TO_DATE if pulled.returncode == 0 else OFFLINE
    try:
        archive = download()
    except httpx.HTTPError:
        return OFFLINE
    try:
        swap_in(archive, root)
    except Kept as kept:
        (root / SKIPPED).write_text("\n".join(kept.files) + "\n", encoding="utf-8")
        n = len(kept.files)
        return KEPT.format(n=n, files="file" if n == 1 else "files", first=", ".join(kept.files[:3]) + (" ..." if n > 3 else ""))
    except OSError:
        return IN_USE
    return UP_TO_DATE


def main() -> None:
    said = update(cfg.ROOT)
    print(said)
    if said == UP_TO_DATE:
        # new window extension into the profile now, by the NEW program (this process still holds
        # the old modules); an open window on the old one gets a plain restart line
        subprocess.run([sys.executable, str(cfg.ROOT / "app" / "jobs.py"), "window-update"], check=False)


if __name__ == "__main__":
    main()
