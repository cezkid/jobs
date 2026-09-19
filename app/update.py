import io
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

import cfg

ZIP_URL = "https://github.com/cezkid/jobs/archive/refs/heads/main.zip"
DOWNLOAD_TIMEOUT_S = 60
# gitignored => never in zip; swap must never touch them either
PRIVATE = {"My Jobs", "My Resume", "My Settings", ".data", ".venv"}
OFFLINE = "Could not check for updates; continuing."


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
        trash = Path(tmp) / "old"
        trash.mkdir()
        # whole top-level entries replaced => files deleted upstream vanish here too
        for new in sorted(src.iterdir()):
            if new.name in PRIVATE:
                continue
            old = root / new.name
            if old.exists():
                old.rename(trash / new.name)
            new.rename(old)


def update(root: Path) -> str:
    if (root / ".git").exists():
        pulled = subprocess.run(["git", "-C", str(root), "pull", "--ff-only", "-q"], check=False)
        return "Up to date." if pulled.returncode == 0 else OFFLINE
    try:
        archive = download()
    except httpx.HTTPError:
        return OFFLINE
    swap_in(archive, root)
    return "Up to date."


def main() -> None:
    print(update(cfg.ROOT))


if __name__ == "__main__":
    main()
