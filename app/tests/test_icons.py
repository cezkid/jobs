import plistlib
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

import cfg

INSTALL = cfg.APP / "install"
ICNS, ICO = INSTALL / "icon.icns", INSTALL / "icon.ico"
YELLOW = (0xFF, 0xE4, 0x33)


def pixels(png: bytes) -> tuple[int, list[list[tuple[int, int, int, int]]]]:
    # stdlib PNG reader: 8-bit RGBA, not interlaced (what icons.py writes)
    w, h, depth, kind, _, _, lace = struct.unpack(">IIBBBBB", png[16:29])
    assert (depth, kind, lace) == (8, 6, 0)
    data, at = b"", 8
    while at < len(png):
        length, tag = struct.unpack(">I4s", png[at:at + 8])
        if tag == b"IDAT":
            data += png[at + 8:at + 8 + length]
        at += 12 + length
    raw, stride, prev, rows = zlib.decompress(data), w * 4, bytearray(w * 4), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b, c = prev[i], prev[i - 4] if i >= 4 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[i:i + 4]) for i in range(0, stride, 4)])
        prev = line
    return w, rows


def icns_png(data: bytes, size: int) -> bytes:
    at = 8
    while at < len(data):
        length = struct.unpack(">I", data[at + 4:at + 8])[0]
        png = data[at + 8:at + length]
        if struct.unpack(">I", png[16:20])[0] == size:
            return png
        at += length
    raise AssertionError(size)


def ico_png(data: bytes, size: int) -> bytes:
    for i in range(struct.unpack("<H", data[4:6])[0]):
        entry = data[6 + 16 * i:22 + 16 * i]
        if (entry[0] or 256) == size:
            length, offset = struct.unpack("<II", entry[8:16])
            return data[offset:offset + length]
    raise AssertionError(size)


def icns_sizes(data: bytes) -> set[int]:
    sizes, at = set(), 8
    while at < len(data):
        kind, length = data[at:at + 4], struct.unpack(">I", data[at + 4:at + 8])[0]
        png = data[at + 8:at + length]
        assert png[:8] == b"\x89PNG\r\n\x1a\n", kind
        sizes.add(struct.unpack(">I", png[16:20])[0])
        at += length
    return sizes


def test_mac_icon_has_every_size():
    # missing size => blurry or blank Desktop icon at some Finder zoom / Retina screen
    data = ICNS.read_bytes()
    assert data[:4] == b"icns" and struct.unpack(">I", data[4:8])[0] == len(data)
    assert icns_sizes(data) == {16, 32, 64, 128, 256, 512, 1024}


def test_windows_icon_has_every_size():
    # missing size => Windows stretches a small one => blurry shortcut on the Desktop
    data = ICO.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    sizes = {data[6 + 16 * i] or 256 for i in range(count)}
    assert sizes == {16, 24, 32, 48, 64, 128, 256}


def test_icon_art_sources_kept():
    # master or hand-tuned small art missing => next redraw can't rebuild the same icon
    for name in ("icon.svg", "icon-32.svg", "icon-16.svg"):
        assert (INSTALL / name).read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_mac_icon_is_dark_tile_with_highlighter():
    # light or flat tile => icon lost among the light third-party tiles on the Desktop
    w, rows = pixels(icns_png(ICNS.read_bytes(), 512))
    # tile left of the page, below its rounded corner (512 px: tile 50..462, r 92)
    corner = [p for row in rows[100:160] for p in row[75:135]]
    assert all(p[3] == 255 for p in corner)
    assert sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _ in corner) / len(corner) < 60
    assert any(all(abs(p[i] - YELLOW[i]) < 30 for i in range(3)) for row in rows for p in row)


def test_windows_icon_fills_canvas():
    # Mac-style margin on Windows => shortcut looks smaller than the ones beside it
    w, rows = pixels(ico_png(ICO.read_bytes(), 256))
    solid = [x for row in rows for x, p in enumerate(row) if p[3] > 200]
    assert min(solid) <= 0.08 * w and max(solid) >= 0.92 * w


def test_icon_drawing_not_a_runtime_dependency():
    # Pillow only draws the icons (dev step) => an install never needs it
    assert "pillow" not in (cfg.ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("osacompile"), reason="Mac only")
def test_mac_app_icon_shows_brand_picture(tmp_path):
    # generic script picture on the Desktop instead of the brand icon, or an app macOS calls damaged
    app = tmp_path / "T.app"
    maker = INSTALL / "make-icon-mac.sh"
    subprocess.run(["bash", str(maker), str(app)], check=True, capture_output=True)
    assert subprocess.run(["codesign", "-v", str(app)], capture_output=True).returncode == 0
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert "CFBundleIconName" not in info
    res = app / "Contents" / "Resources"
    assert (res / "applet.icns").read_bytes() == ICNS.read_bytes()
    assert not (res / "Assets.car").exists()
    # second run edits in place => icon keeps its spot on the Desktop
    inode = app.stat().st_ino
    subprocess.run(["bash", str(maker), str(app)], check=True, capture_output=True)
    assert app.stat().st_ino == inode
    assert subprocess.run(["codesign", "-v", str(app)], capture_output=True).returncode == 0
