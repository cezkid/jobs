"""Desktop icon files from the brand art (blackbird on the dark tile): icon.icns (Mac app),
icon.ico (Windows shortcut). icon.svg = master (64 px up), icon-32.svg + icon-16.svg =
hand-tuned small rungs (master blurs there). Rendered by headless Chrome, packed by Pillow.
Dev-only, output committed - Pillow + Chrome are never runtime dependencies.

    uv run --with pillow python app/install/icons.py
"""
import io
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
MASTER, SMALL = HERE / "icon.svg", {16: HERE / "icon-16.svg", 32: HERE / "icon-32.svg"}
CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium",
]
# icns type per pixel size; 2x types share a size w/ the 1x one so each size is listed once.
# 64 (32@2x) = master: compared side by side, 32 rung doubled is sharper but flat; master keeps
# depth => matches the 128+ rungs on Retina
ICNS_TYPES = {16: [b"icp4"], 32: [b"icp5", b"ic11"], 64: [b"ic12"], 128: [b"ic07"],
              256: [b"ic08", b"ic13"], 512: [b"ic09", b"ic14"], 1024: [b"ic10"]}
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
# Windows has no Mac safe margin => crop master to the tile + its shadow (tile ~93% of canvas)
ICO_VIEWBOX = "70 70 884 884"


def chrome() -> str:
    for c in CHROME:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("Chrome not found - needed to draw the icons")


def render(svg: str, size: int, tmp: Path) -> Image.Image:
    # headless Chrome writes the PNG then hangs on exit (measured) => wait for file, kill
    n = len(list(tmp.glob("*.svg")))
    src, page, shot = tmp / f"{n}.svg", tmp / f"{n}.html", tmp / f"{n}.png"
    src.write_text(svg, encoding="utf-8")
    page.write_text(f'<html><body style="margin:0;background:transparent"><img src="{src.name}" '
                    f'width="{size}" height="{size}" style="display:block"></body></html>',
                    encoding="utf-8")
    proc = subprocess.Popen(
        [chrome(), "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--user-data-dir={tmp / f'profile{n}'}", "--default-background-color=00000000",
         "--force-device-scale-factor=1", f"--window-size={size},{size}",
         f"--screenshot={shot}", page.as_uri()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        for _ in range(300):
            if shot.exists() and shot.stat().st_size:
                time.sleep(0.3)  # let the write finish
                break
            time.sleep(0.1)
        else:
            sys.exit(f"Chrome made no picture for {size} px")
    finally:
        kill(proc)
    im = Image.open(shot).convert("RGBA")
    im.load()
    assert im.size == (size, size), im.size
    return im


def kill(proc: subprocess.Popen) -> None:
    # whole group: Chrome's helper processes otherwise linger + hold the profile
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (AttributeError, OSError):  # Windows, or group already gone
        proc.kill()
    proc.wait()


def windows_small(svg: str, size: int) -> str:
    # small rung's tile grown to 1 px from the edge (Windows: no Mac margin), bird stays centred
    r = round((size - 2) * 0.23)
    return re.sub(r'<rect id="tile"[^>]*/>',
                  f'<rect id="tile" x="1" y="1" width="{size - 2}" height="{size - 2}" rx="{r}" '
                  'fill="#1c1c1e"/>', svg)


def mac_rung(size: int, tmp: Path) -> Image.Image:
    src = SMALL.get(size, MASTER).read_text(encoding="utf-8")
    return render(src, size, tmp)


def ico_rung(size: int, tmp: Path) -> Image.Image:
    if size in SMALL:
        return render(windows_small(SMALL[size].read_text(encoding="utf-8"), size), size, tmp)
    master = MASTER.read_text(encoding="utf-8").replace('viewBox="0 0 1024 1024"',
                                                         f'viewBox="{ICO_VIEWBOX}"', 1)
    return render(master, size, tmp)


def png(im: Image.Image) -> bytes:
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def icns(tmp: Path) -> bytes:
    body = b""
    for size, types in ICNS_TYPES.items():
        data = png(mac_rung(size, tmp))
        for t in types:
            body += t + struct.pack(">I", len(data) + 8) + data
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def ico(tmp: Path) -> bytes:
    images = [ico_rung(s, tmp) for s in ICO_SIZES]
    out = io.BytesIO()
    images[-1].save(out, "ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    return out.getvalue()


def main() -> None:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (HERE / "icon.icns").write_bytes(icns(tmp))
        (HERE / "icon.ico").write_bytes(ico(tmp))
    if os.environ.get("ICON_PREVIEW"):
        preview(Path(os.environ["ICON_PREVIEW"]))


def preview(out: Path) -> None:
    # owner's look: 1024 master + 128/64/32/16 Mac rungs on a light and a dark strip
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        rungs = [mac_rung(s, tmp) for s in (1024, 128, 64, 32, 16)]
    w, h = sum(im.width + 40 for im in rungs) + 40, 1024 + 80
    sheet = Image.new("RGBA", (w, 2 * h), (0, 0, 0, 0))
    for row, bg in enumerate([(0xE9, 0xE9, 0xEC, 255), (0x1E, 0x1E, 0x20, 255)]):
        strip = Image.new("RGBA", (w, h), bg)
        x = 40
        for im in rungs:
            strip.alpha_composite(im, (x, (h - im.height) // 2))
            x += im.width + 40
        sheet.paste(strip, (0, row * h))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


if __name__ == "__main__":
    main()
