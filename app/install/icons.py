"""Desktop icon files from the brand mark (docs/icon.svg geometry): icon.icns (Mac app), icon.ico
(Windows shortcut). Dev-only, output committed - Pillow is never a runtime dependency.

    uv run --with pillow python app/install/icons.py
"""
import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
INK, PAGE, MARK = (0, 0, 0, 255), (255, 255, 255, 255), (0xFF, 0xE4, 0x33, 255)
# docs/icon.svg, 32-unit box: body 0.5..31.5 rx 7, page, highlight, 3 lines (y, x1, x2), stroke 2.4
BODY, RADIUS = (0.5, 0.5, 31.5, 31.5), 7
SHEET, HIGHLIGHT = (8, 4, 24, 28), (10, 13, 22, 19)
LINES, STROKE = ((9.5, 11, 21), (16, 11, 21), (22.5, 11, 18)), 2.4
# Mac grid (macOS 11+ template): body 824 of 1024, 100 margin => sits level w/ other Desktop apps
MAC_MARGIN = 100 / 1024
# icns type per pixel size; 2x types share a size w/ the 1x one so each size is listed once
ICNS_TYPES = {16: [b"icp4"], 32: [b"icp5", b"ic11"], 64: [b"ic12"], 128: [b"ic07"],
              256: [b"ic08", b"ic13"], 512: [b"ic09", b"ic14"], 1024: [b"ic10"]}
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw(size: int, margin: float = 0.0) -> Image.Image:
    # drawn 4x then shrunk => smooth edges at 16 px; margin = share of the canvas left clear
    scale = 4 if size <= 256 else 2
    big = size * scale
    pad = margin * big
    unit = (big - 2 * pad) / 31  # body spans 31 units
    origin = pad - 0.5 * unit

    def box(x1, y1, x2, y2):
        return [origin + x1 * unit, origin + y1 * unit, origin + x2 * unit - 1, origin + y2 * unit - 1]

    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box(*BODY), radius=RADIUS * unit, fill=INK)
    d.rectangle(box(*SHEET), fill=PAGE)
    d.rectangle(box(*HIGHLIGHT), fill=MARK)
    for y, x1, x2 in LINES:
        d.rectangle(box(x1, y - STROKE / 2, x2, y + STROKE / 2), fill=INK)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def png(im: Image.Image) -> bytes:
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def icns() -> bytes:
    body = b""
    for size, types in ICNS_TYPES.items():
        data = png(draw(size, MAC_MARGIN))
        for t in types:
            body += t + struct.pack(">I", len(data) + 8) + data
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def ico() -> bytes:
    # Windows draws shortcuts edge to edge => no Mac margin
    images = [draw(s) for s in ICO_SIZES]
    out = io.BytesIO()
    images[-1].save(out, "ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    return out.getvalue()


def main() -> None:
    (HERE / "icon.icns").write_bytes(icns())
    (HERE / "icon.ico").write_bytes(ico())


if __name__ == "__main__":
    main()
