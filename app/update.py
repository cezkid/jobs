import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

import cfg

ZIP_URL = "https://github.com/cezkid/jobs/archive/refs/heads/main.zip"
DOWNLOAD_TIMEOUT_S = 60
# gitignored => never in zip; swap must never touch them either
PRIVATE = {*cfg.PRIVATE_DIRS, ".data", ".venv"}
# user's own file inside program folder (Claude's "don't ask again" answers) => carried into new copy
KEEP = (Path(".claude") / "settings.local.json",)
OFFLINE = "Could not check for updates; continuing."
IN_USE = "Could not update now (a program file is open); continuing with this version."


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
        for keep in KEEP:
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


def update(root: Path) -> str:
    if (root / ".git").exists():
        pulled = subprocess.run(["git", "-C", str(root), "pull", "--ff-only", "-q"], check=False)
        return "Up to date." if pulled.returncode == 0 else OFFLINE
    try:
        archive = download()
    except httpx.HTTPError:
        return OFFLINE
    try:
        swap_in(archive, root)
    except OSError:
        return IN_USE
    return "Up to date."


def main() -> None:
    print(update(cfg.ROOT))


if __name__ == "__main__":
    main()
