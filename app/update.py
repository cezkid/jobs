import hashlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

import cfg
import ed25519

ZIP_URL = "https://github.com/cezkid/jobs/archive/refs/heads/main.zip"
RELEASE_URL = "https://api.github.com/repos/cezkid/jobs/releases/latest"
MARKER = "SIGNED_RELEASE_PATH"  # a release zip must carry it in app/update.py (loop prevention)
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
BAD_PACK = "Could not update: the new version is not packed as expected; continuing with this version."
UNVERIFIED = "Could not verify the update; continuing with this version."


def download(url: str = ZIP_URL) -> bytes:
    response = httpx.get(url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_S)
    response.raise_for_status()
    return response.content


def swap_in(archive: bytes, root: Path, keep_copy: bool = False) -> None:
    # unzip fully before touching root => bad download leaves old copy intact
    staging = root / ".data"
    staging.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging, ignore_cleanup_errors=True) as tmp:
        zipfile.ZipFile(io.BytesIO(archive)).extractall(tmp)
        (src,) = Path(tmp).iterdir()
        for keep in KEEP:
            # folder absent from the zip (.vscode is never shipped) => swap leaves it alone, file and all
            if (root / keep).is_file() and (src / keep.parent).is_dir():
                shutil.copy2(root / keep, src / keep)
        if keep_copy:
            # a release w/o the keys file must not silently switch this install back to unsigned main.zip
            keys = Path("app") / "update-keys.txt"
            if (root / keys).is_file() and (src / keys.parent).is_dir() and not (src / keys).exists():
                shutil.copy2(root / keys, src / keys)
            save_previous(src, root, staging, Path(tmp))
        swap_entries(src, root, Path(tmp))


def swap_entries(src: Path, root: Path, tmp: Path) -> None:
    trash = tmp / "old"
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


UNDONE = "Went back to the version before the last update. Close and reopen CEZ Job Finder."
NO_UNDO = "Nothing to undo: there is no earlier version saved."


def undo(root: Path) -> str:
    previous = root / ".data" / "previous"
    if not previous.is_dir() or not any(previous.iterdir()):
        return NO_UNDO
    bad = installed_version(root)
    try:
        with tempfile.TemporaryDirectory(dir=root / ".data", ignore_cleanup_errors=True) as tmp:
            src = Path(tmp) / "back"
            shutil.copytree(previous, src, symlinks=True)  # previous stays => a failed swap loses nothing
            swap_entries(src, root, Path(tmp))
    except OSError:
        return IN_USE
    data = root / ".data"
    # bad version remembered => next launch skips it until a newer release
    (data / "undone-version").write_text(bad + "\n", encoding="utf-8")
    (data / "update-etag").unlink(missing_ok=True)
    restored = root / "app" / "VERSION"
    if restored.is_file():
        (data / "app-version").write_text(restored.read_text(encoding="utf-8").strip() + "\n", encoding="utf-8")
    else:
        (data / "app-version").unlink(missing_ok=True)
    return UNDONE


def save_previous(src: Path, root: Path, staging: Path, tmp: Path) -> None:
    # copy every entry about to be replaced; staged => a failed copy never loses the last good copy
    stage = tmp / "previous"
    stage.mkdir()
    for new in src.iterdir():
        old = root / new.name
        if new.name in PRIVATE or not old.exists():
            continue
        if old.is_dir():
            shutil.copytree(old, stage / new.name, symlinks=True)
        else:
            shutil.copy2(old, stage / new.name)
    final = staging / "previous"
    aside = staging / "previous-old"
    shutil.rmtree(aside, ignore_errors=True)
    if final.exists():
        final.rename(aside)
    try:
        shutil.move(str(stage), str(final))
    except OSError:
        # earlier copy goes back => a failed move never loses it
        shutil.rmtree(final, ignore_errors=True)
        if aside.exists():
            aside.rename(final)
        raise
    shutil.rmtree(aside, ignore_errors=True)


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(n) for n in text.strip().lstrip("v").split("."))


def installed_version(root: Path) -> str:
    for f in (root / ".data" / "app-version", root / "app" / "VERSION"):
        try:
            return f.read_text(encoding="utf-8").strip() or "0"
        except OSError:
            continue
    return "0"


def read_keys(path: Path) -> list[bytes]:
    keys = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            keys.append(bytes.fromhex(line))
    return keys


def for_users(body: object) -> list[str]:
    """The release notes' "## For users" lines, plain text: bullets and markup stripped, no links."""
    out, inside = [], False
    for line in (body if isinstance(body, str) else "").splitlines():
        if line.startswith("#"):
            inside = line.lstrip("#").strip().lower() == "for users"
        elif inside and (text := line.strip().lstrip("-*").strip()):
            text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
            text = re.sub(r"https?://\S+", "", text)
            text = re.sub(r"[\x00-\x1f\x7f-\x9f`*_<>\[\]]", "", text).strip()[:200].strip()
            if text:
                out.append(text)
    return out[:8]


def save_whats_new(root: Path, version: str, body: object) -> None:
    """Cache this release's user lines for Today (first line = version); best effort."""
    lines = for_users(body)
    target = root / ".data" / "whats-new.md"
    try:
        if lines:
            target.write_text(version + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
        else:
            target.unlink(missing_ok=True)
    except OSError:
        pass  # only a note; the update is in


def signed_news(client: httpx.Client, assets: dict, listed: dict) -> str:
    """WHATS-NEW.md text, only when its sha256 is in the signed SHA256SUMS; else "" (no What's new)."""
    try:
        part = client.get(assets["WHATS-NEW.md"])
        part.raise_for_status()
        if listed.get("WHATS-NEW.md") == hashlib.sha256(part.content).hexdigest():
            return part.content.decode("utf-8", "replace")
    except (httpx.HTTPError, KeyError):
        pass
    return ""


def update_release(root: Path, keys: list[bytes], client: httpx.Client) -> str:
    etag_file = root / ".data" / "update-etag"
    headers = {"Accept": "application/vnd.github+json"}
    try:
        cached = etag_file.read_text(encoding="utf-8").strip()
    except OSError:
        cached = ""
    if cached:
        headers["If-None-Match"] = cached
    try:
        response = client.get(RELEASE_URL, headers=headers)
        if response.status_code == 304:
            return UP_TO_DATE
        if response.status_code != 200:  # 403 rate limit, 404 no release yet
            return OFFLINE
        release = response.json()
        assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
        tag = release["tag_name"]
        try:
            undone = (root / ".data" / "undone-version").read_text(encoding="utf-8")
            if version_tuple(tag) <= version_tuple(undone):
                return UP_TO_DATE
        except (OSError, ValueError):
            pass
        zip_name = f"jobs-{tag}.zip"
        fetched = {}
        for name in ("SHA256SUMS", "SHA256SUMS.sig", zip_name):
            part = client.get(assets[name])
            part.raise_for_status()
            fetched[name] = part.content
    except httpx.HTTPError:
        return OFFLINE
    except (KeyError, TypeError, ValueError):
        return UNVERIFIED
    sums, sig, archive = fetched["SHA256SUMS"], fetched["SHA256SUMS.sig"], fetched[zip_name]
    if not any(ed25519.verify(k, sums, sig) for k in keys):
        return UNVERIFIED
    listed = {}
    for line in sums.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 2:
            listed[parts[1].lstrip("*")] = parts[0].lower()
    if listed.get(zip_name) != hashlib.sha256(archive).hexdigest():
        return UNVERIFIED
    etag = response.headers.get("etag", "")
    try:
        version = tag.lstrip("v")
        if version_tuple(version) <= version_tuple(installed_version(root)):
            try:
                etag_file.parent.mkdir(exist_ok=True)
                etag_file.write_text(etag, encoding="utf-8")
            except OSError:
                pass  # only a cache; this version stays
            return UP_TO_DATE
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            carries = any(n.split("/")[-2:] == ["app", "update.py"] and MARKER.encode() in z.read(n) for n in z.namelist())
    except (ValueError, zipfile.BadZipFile):
        return UNVERIFIED
    if not carries:
        return UNVERIFIED
    try:
        swap_in(archive, root, keep_copy=True)
        (root / ".data").mkdir(exist_ok=True)
        (root / ".data" / "app-version").write_text(version + "\n", encoding="utf-8")
        save_whats_new(root, version, signed_news(client, assets, listed))
    except OSError:
        return IN_USE
    except (zipfile.BadZipFile, ValueError):
        return BAD_PACK
    try:
        etag_file.write_text(etag, encoding="utf-8")
    except OSError:
        pass  # only a cache; the update is in
    return UP_TO_DATE


def update(root: Path, client: httpx.Client | None = None) -> str:
    if (root / ".git").exists():
        pulled = subprocess.run(["git", "-C", str(root), "pull", "--ff-only", "-q"], check=False)
        return UP_TO_DATE if pulled.returncode == 0 else OFFLINE
    keys_file = root / "app" / "update-keys.txt"
    if keys_file.is_file():
        try:
            keys = read_keys(keys_file)
        except (OSError, ValueError):
            keys = []
        if not keys:
            return UNVERIFIED
        with client or httpx.Client(follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_S) as c:
            return update_release(root, keys, c)
    try:
        archive = download()
    except httpx.HTTPError:
        return OFFLINE
    try:
        swap_in(archive, root)
    except OSError:
        return IN_USE
    return UP_TO_DATE


def main() -> None:
    if "--undo" in sys.argv[1:]:
        print(undo(cfg.ROOT))
        return
    said = update(cfg.ROOT)
    print(said)
    if said == UP_TO_DATE:
        # new window extension into the profile now, by the NEW program (this process still holds
        # the old modules); an open window on the old one gets a plain restart line
        subprocess.run([sys.executable, str(cfg.ROOT / "app" / "jobs.py"), "window-update"], check=False)


if __name__ == "__main__":
    main()
