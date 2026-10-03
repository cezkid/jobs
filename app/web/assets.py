# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright", "fonttools", "brotli"]
# ///
"""Build the install site's generated files in docs/.

Makes: docs/fonts/caladea-{regular,bold,italic}.woff2 + OFL.txt (Latin subset of the resume font),
docs/icon-192.png, icon-512.png, apple-touch-icon.png, icon-maskable-512.png and favicon.ico
(all rendered from docs/icon.svg), and the share images docs/og.png (from app/web/og.html) and
docs/og-research.png (from app/web/og-research.html).

Everything it writes in docs/ is generated and committed - never hand-edit those files; change
this script, docs/icon.svg or app/web/og*.html and rerun. docs/icon.svg itself is hand-drawn.

Share image changed => bump its ?v=N in every page's og:image (LinkedIn caches a preview ~7
days, keyed by URL).

Run from repo root: uv run app/web/assets.py [--only fonts|icons|og]
Own deps (inline above), so the project's deps stay untouched. Icons + og use Google Chrome.
"""

import argparse
import base64
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CALADEA = ROOT / "app" / "resume" / "fonts" / "Caladea"
WEB = ROOT / "app" / "web"
CARDS = [(WEB / "og.html", DOCS / "og.png"), (WEB / "og-research.html", DOCS / "og-research.png")]
SUPPLEMENTAL = Path("/System/Library/Fonts/Supplemental")
# Caladea style -> the Georgia face standing in for it until the web font loads
GEORGIA = {"Regular": SUPPLEMENTAL / "Georgia.ttf", "Italic": SUPPLEMENTAL / "Georgia Italic.ttf"}

UNICODES = [
    *range(0x20, 0x7F), *range(0xA0, 0x100),
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026,
    # combining accents: Caladea's case feature only swaps these, so without them it subsets away
    *range(0x300, 0x305), *range(0x306, 0x309), 0x30A, 0x30B, 0x30C, 0x327, 0x328,
]
FEATURES = ["kern", "liga", "lnum", "onum", "tnum", "case", "frac"]

# English letter frequencies (per cent), space included: weights the average lowercase advance
# the way running text does (capsize's method) - a plain a-z mean overweights q, x, z.
FREQ = {
    " ": 18.0, "e": 10.2, "t": 7.5, "a": 6.5, "o": 6.2, "i": 5.7, "n": 5.7, "s": 5.3, "h": 5.0,
    "r": 5.0, "d": 3.5, "l": 3.3, "u": 2.3, "c": 2.2, "m": 2.0, "w": 1.9, "f": 1.8, "g": 1.6,
    "y": 1.6, "p": 1.5, "b": 1.2, "v": 0.8, "k": 0.6, "j": 0.1, "x": 0.1, "q": 0.1, "z": 0.1,
}


def fonts():
    from fontTools import subset
    from fontTools.ttLib import TTFont

    out = DOCS / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    for weight in ("Regular", "Bold", "Italic"):
        opts = subset.Options()
        # italic unhinted: 13.7 KB instead of 20.7 (hints only touch Windows at small sizes; the
        # italic is never preloaded or in the first viewport)
        opts.hinting = weight != "Italic"
        opts.layout_features = FEATURES
        opts.name_IDs = ["*"]
        opts.name_languages = ["*"]
        opts.flavor = "woff2"
        # keep the source's head.modified: a fresh timestamp would change the file every run
        font = TTFont(CALADEA / f"Caladea-{weight}.ttf", recalcTimestamp=False)
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=UNICODES)
        sub.subset(font)
        dest = out / f"caladea-{weight.lower()}.woff2"
        font.flavor = "woff2"
        font.save(dest)
        print(f"{dest.relative_to(ROOT)}: {dest.stat().st_size / 1024:.1f} KB")
    shutil.copyfile(CALADEA / "OFL.txt", out / "OFL.txt")
    for style, georgia in GEORGIA.items():
        if georgia.exists():
            fallback_metrics(style, georgia)
        else:
            print(f"{georgia} missing - {style} fallback metrics not printed")


def _avg_advance(font):
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    total = sum(w * hmtx[cmap[ord(c)]][0] for c, w in FREQ.items())
    return total / sum(FREQ.values()) / font["head"].unitsPerEm


def fallback_metrics(style, georgia):
    """@font-face overrides that make Georgia take Caladea's space, so the swap moves nothing."""
    from fontTools.ttLib import TTFont

    cal, geo = TTFont(CALADEA / f"Caladea-{style}.ttf"), TTFont(georgia)
    size = _avg_advance(cal) / _avg_advance(geo)
    upm, hhea = cal["head"].unitsPerEm, cal["hhea"]
    pct = lambda v: f"{v / upm / size * 100:.2f}%"
    print(f"{georgia.stem} fallback for Caladea {style} (Cambria is metric-compatible: no overrides):")
    print(f"  size-adjust: {size * 100:.2f}%;")
    print(f"  ascent-override: {pct(hhea.ascent)};")
    print(f"  descent-override: {pct(abs(hhea.descent))};")
    print(f"  line-gap-override: {pct(hhea.lineGap)};")


def _render(page, svg_b64, size, art=1.0, bg=None):
    """Return PNG bytes of icon.svg at size px; art = share of the side the mark fills."""
    inner = round(size * art)
    pad = (size - inner) / 2
    body = f"background:{bg}" if bg else "background:transparent"
    page.set_viewport_size({"width": size, "height": size})
    page.set_content(
        f'<html><body style="margin:0;{body}">'
        f'<img src="data:image/svg+xml;base64,{svg_b64}" width="{inner}" height="{inner}"'
        f' style="display:block;position:absolute;left:{pad}px;top:{pad}px"></body></html>'
    )
    page.wait_for_function("document.images[0].complete")
    return page.screenshot(omit_background=bg is None)


def ico(frames):
    """Pack PNG frames {size: bytes} into a .ico: ICONDIR, one ICONDIRENTRY each, payloads."""
    head = struct.pack("<HHH", 0, 1, len(frames))
    offset = len(head) + 16 * len(frames)
    entries, payloads = b"", b""
    for size, png in frames.items():
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        payloads += png
        offset += len(png)
    return head + entries + payloads


def icons(qa=None):
    from playwright.sync_api import sync_playwright

    svg_b64 = base64.b64encode((DOCS / "icon.svg").read_bytes()).decode()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(device_scale_factor=1, color_scheme="light")
        made = {
            "icon-192.png": _render(page, svg_b64, 192),
            "icon-512.png": _render(page, svg_b64, 512),
            "apple-touch-icon.png": _render(page, svg_b64, 180, bg="#FFFFFF"),
            "icon-maskable-512.png": _render(page, svg_b64, 512, art=0.8, bg="#FFFFFF"),
        }
        frames = {s: _render(page, svg_b64, s) for s in (16, 32, 48)}
        browser.close()
    for name, png in made.items():
        (DOCS / name).write_bytes(png)
        print(f"docs/{name}")
    (DOCS / "favicon.ico").write_bytes(ico(frames))
    print("docs/favicon.ico (16, 32, 48)")
    if qa:
        qa.mkdir(parents=True, exist_ok=True)
        for s, png in frames.items():
            (qa / f"icon-{s}.png").write_bytes(png)


# Fails the render when anything leaves the 1200x630 card or lands in its bottom 90px (X lays
# its headline there), or when a box w/ overflow hidden clips its content: either would cut text off silently.
OVERFLOW_JS = """() => {
  const bad = [];
  for (const el of document.body.querySelectorAll("*")) {
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    const cls = el.getAttribute("class"), name = el.tagName.toLowerCase() + (cls ? "." + cls : "");
    if (r.left < 0 || r.top < 0 || r.right > 1200 || r.bottom > 630 - 90) bad.push(`${name} at ${[r.left, r.top, r.right, r.bottom].map(Math.round)}`);
    else if (getComputedStyle(el).overflow !== "visible" && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) bad.push(`${name} clips its content`);
  }
  return bad;
}"""


def render_card(template, out):
    """One share card: template (HTML, fonts inlined - Chrome blocks file:// fonts) -> out PNG,
    1200x630 exactly, clipped; fails on unloaded fonts or overflow (OVERFLOW_JS)."""
    import re
    from playwright.sync_api import sync_playwright

    def inline(m):
        b64 = base64.b64encode((DOCS / "fonts" / m[1]).read_bytes()).decode()
        return f'url("data:font/woff2;base64,{b64}")'

    name = template.name
    html, n = re.subn(r'url\("/fonts/([\w.-]+\.woff2)"\)', inline, template.read_text(encoding="utf-8"))
    if not n:
        raise SystemExit(f"og: no /fonts/*.woff2 url() in {name} to inline")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        try:
            page = browser.new_page(
                viewport={"width": 1200, "height": 630}, device_scale_factor=1, color_scheme="light"
            )
            page.set_content(html)
            page.evaluate("document.fonts.ready")
            faces = page.evaluate(
                "[...document.fonts].map(f => `${f.family} ${f.weight}: ${f.status}`)"
            )
            bad = [f for f in faces if not f.endswith(": loaded")]
            if not faces or bad:
                raise SystemExit(f"og: {name}: font faces not loaded: {bad or 'none declared'}")
            overflow = page.evaluate(OVERFLOW_JS)
            if overflow:
                raise SystemExit(f"og: {name}: outside the card or its bottom 90px: " + "; ".join(overflow))
            png = page.screenshot(clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        finally:
            browser.close()
    out.write_bytes(png)
    print(f"docs/{out.name}: {len(png) / 1024:.1f} KB ({', '.join(faces)})")


def og():
    """docs/og.png (home) + docs/og-research.png (research + about pages), 1200x630 each."""
    for template, out in CARDS:
        render_card(template, out)


def main():
    ap = argparse.ArgumentParser(description="Build the install site's generated files in docs/.")
    ap.add_argument("--only", choices=["fonts", "icons", "og"])
    ap.add_argument("--qa", type=Path, help="also write the 16/32/48 favicon frames here")
    args = ap.parse_args()
    steps = {"fonts": fonts, "icons": lambda: icons(args.qa), "og": og}
    for name, step in steps.items():
        if args.only in (None, name):
            step()


if __name__ == "__main__":
    sys.exit(main())
