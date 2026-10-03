import plistlib
import shutil
import struct
import subprocess
import sys

import pytest

import cfg

INSTALL = cfg.APP / "install"
ICNS, ICO = INSTALL / "icon.icns", INSTALL / "icon.ico"


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
