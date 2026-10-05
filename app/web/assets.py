# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright", "fonttools", "brotli"]
# ///
"""Build the install site's generated files in docs/.

Makes: docs/fonts/caladea-{regular,bold,italic}.woff2 + OFL.txt (Latin subset of the resume font),
docs/icon.svg (browser tab: the bare bird, app/install/mark-32.svg, pale on a dark tab strip),
icon-192.png, icon-512.png, apple-touch-icon.png, icon-maskable-512.png and favicon.ico (the
Desktop icon, bird on its dark tile: app/install/icon*.svg), and the share images docs/og.png
(from app/web/og.html) and docs/og-research.png (from app/web/og-research.html; both draw the
bare bird). One mark, one home (app/install), so the site shows what the desktop shows. Icons
also rewrite the inline bird (<svg class="bird">: header, hero title bar) in the hand-written
pages from mark-32.svg - rerun app/web/pages.py after, the generated pages copy that header.

Everything it writes in docs/ is generated and committed - never hand-edit those files; change
this script, app/install/{icon,mark}*.svg or app/web/og*.html and rerun. app/web/icon-sync.json
records the art's hashes + every file made from it; test_site_icons_follow_the_app_icon fails
when the art changed and the site didn't follow.

Share image changed => bump its ?v=N in every page's og:image (LinkedIn caches a preview ~7
days, keyed by URL).

Run from repo root: uv run app/web/assets.py [--only fonts|icons|og]
Own deps (inline above), so the project's deps stay untouched. Icons + og use Google Chrome.
"""

import argparse
import base64
import hashlib
import json
import re
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CALADEA = ROOT / "app" / "resume" / "fonts" / "Caladea"
WEB = ROOT / "app" / "web"
APP_ICONS = ROOT / "app" / "install"
# art file -> hash; files made from it -> hash (test_site.py recomputes both)
SYNC = WEB / "icon-sync.json"
ART = ("icon*.svg", "mark*.svg")  # Desktop tile icon + bare bird
MARK_SMALL = APP_ICONS / "mark-32.svg"
# pages w/ a hand-written header + hero window: their inline bird is rewritten from MARK_SMALL
HAND_PAGES = ("index.html", "404.html", "privacy.html")
# dark tab strip: the shared :root's dark --text + --desk (docs/index.html)
PALE, DESK = "#f2f2f2", "#1c1c1e"
MARK_FILL = {"ink": "#000000", "beak": "#ffe433", "eye": "#ffe433"}  # mark-32.svg as drawn (light cut)
INK = "#0c0c0e"  # outer stop of the app tile's ink gradient: plate under full-bleed icons
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


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_sync(made):
    """Merge {docs file: hash} for made files + the art sources' hashes into SYNC."""
    data = json.loads(SYNC.read_text()) if SYNC.exists() else {}
    art = sorted(p for pattern in ART for p in APP_ICONS.glob(pattern))
    data["source"] = {f"app/install/{p.name}": _sha(p) for p in art}
    data["made"] = dict(sorted({**data.get("made", {}), **{f"docs/{p.name}": _sha(p) for p in made}}.items()))
    SYNC.write_text(json.dumps(data, indent=2) + "\n")


def mark_shapes():
    """mark-32.svg's shapes as [(class, element)], per the contract in its <desc>: one shape a
    line, each a direct child w/ class ink | beak | eye and its own fill; nothing else."""
    svg = MARK_SMALL.read_text(encoding="utf-8")
    body = re.sub(r"<desc>.*?</desc>", "", svg, flags=re.S)
    lines = [ln.strip() for ln in body.splitlines()[1:] if ln.strip() and ln.strip() != "</svg>"]
    shape = re.compile(r'<(?:path|circle|rect|ellipse|polygon) class="(ink|beak|eye)" [^<>]*\bfill="(#[0-9a-f]{6})"[^<>]*/>')
    shapes = [(m[1], ln) for ln in lines if (m := shape.fullmatch(ln)) and m[2] == MARK_FILL[m[1]]
              and not re.search(r"\s(?:id|style|transform)=", ln)]
    if 'viewBox="0 0 32 32"' not in svg.split(">", 1)[0] or len(shapes) != len(lines) or {c for c, _ in shapes} != set(MARK_FILL):
        raise SystemExit("icons: app/install/mark-32.svg breaks its contract (viewBox 0 0 32 32; one shape a line - path, "
                         "circle, rect, ellipse or polygon - each w/ class ink | beak | eye first + its fill: ink "
                         f"{MARK_FILL['ink']}, beak + eye {MARK_FILL['beak']}, lowercase; no id, style, transform, defs or group)")
    return shapes


def favicon_svg():
    """docs/icon.svg = the bare bird's small cut (whole pixels: sharp in a tab), <desc> cut; on a
    dark tab strip the ink turns the page's text tone and the eye the page colour (the dark cut),
    the beak stays. Only the tab uses the file: the pages carry the bird inline (inline_bird)."""
    svg = re.sub(r"<desc>.*?</desc>\n?", "", MARK_SMALL.read_text(encoding="utf-8"), flags=re.S)
    mark_shapes()
    dark = f"<style>@media (prefers-color-scheme:dark){{.ink{{fill:{PALE}}}.eye{{fill:{DESK}}}}}</style>\n"
    return re.sub(r"(<svg[^>]*>\n)", lambda m: m[1] + dark, svg, count=1)


def inline_bird():
    """The bird as the pages carry it inline (header brand, hero title bar): mark-32.svg's shapes
    w/ their fills cut - the shared CSS colours them (.bird: ink = currentColor, so the page's
    text tone, black in print, CanvasText in forced colours; beak + eye = --mark). An <img> can't:
    its own dark cut prints pale on white paper. No id (the header is copied to every page)."""
    shapes = "".join(re.sub(r' fill="[^"]*"', "", el).replace(' class="ink"', "") for _, el in mark_shapes())
    return f'<svg class="bird" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" focusable="false">{shapes}</svg>'


def inline_birds():
    """Rewrite every <svg class="bird"> in the hand-written pages w/ inline_bird()."""
    bird = inline_bird()
    for name in HAND_PAGES:
        page = DOCS / name
        html, n = re.subn(r'<svg class="bird"[^>]*>.*?</svg>', lambda m: bird, page.read_text(encoding="utf-8"), flags=re.S)
        if not n:
            raise SystemExit(f'icons: docs/{name} has no <svg class="bird"> to redraw')
        page.write_text(html, encoding="utf-8", newline="\n")
        print(f"docs/{name}: {n} inline bird(s) (app/install/mark-32.svg)")


def _b64(path):
    return base64.b64encode(path.read_bytes()).decode()


def _render(browser, svg_b64, size, art=1.0, bg=None):
    """Return PNG bytes of an svg at size px; art = mark's side / canvas side (> 1 bleeds off).
    Own page per shot: on a reused page a later size sometimes came out a few levels off in ~4% of
    its pixels (apple-touch 3 runs of 16, measured) => files changed w/ no art change."""
    inner = round(size * art)
    pad = (size - inner) / 2
    body = f"background:{bg}" if bg else "background:transparent"
    page = browser.new_page(device_scale_factor=1, color_scheme="light", viewport={"width": size, "height": size})
    page.set_content(
        f'<html><body style="margin:0;overflow:hidden;{body}">'
        f'<img src="data:image/svg+xml;base64,{svg_b64}" width="{inner}" height="{inner}"'
        f' style="display:block;position:absolute;left:{pad}px;top:{pad}px"></body></html>'
    )
    # decoded + two frames painted before the shot
    page.evaluate("async () => { await document.images[0].decode();"
                  " await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }")
    png = page.screenshot(omit_background=bg is None)
    page.close()
    return png


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


# tile = 824 of the master's 1024 (Apple grid): 1024 / 824 fills the canvas w/ the tile (iOS rounds
# its own corners). Maskable: launchers crop to a circle SAFE of the side from centre; the bird's
# farthest point (beak tip) is 0.292 at art 1 => the full-bleed tile keeps it at 0.363, no tile
# corner left to show. icons() measures #bird (REACH_JS) and fails when new art reaches past SAFE.
BLEED = 1024 / 824
MASKABLE, SAFE = BLEED, 0.40

# farthest point of the master's <g id="bird"> from the canvas centre, as a share of the side
REACH_JS = """() => {
  const side = document.querySelector("svg").viewBox.baseVal.width;
  let far = 0;
  for (const el of document.querySelectorAll("#bird *")) {
    if (!el.getTotalLength) continue;
    const m = el.getCTM(), n = el.getTotalLength();
    for (let i = 0; i <= 2000; i++) {
      const p = el.getPointAtLength(n * i / 2000).matrixTransform(m);
      far = Math.max(far, Math.hypot(p.x - side / 2, p.y - side / 2));
    }
  }
  return far / side;
}"""


def icons(qa=None):
    from playwright.sync_api import sync_playwright

    (DOCS / "icon.svg").write_text(favicon_svg(), encoding="utf-8", newline="\n")
    print("docs/icon.svg (app/install/mark-32.svg)")
    inline_birds()
    master, s32, s16 = (_b64(APP_ICONS / f) for f in ("icon.svg", "icon-32.svg", "icon-16.svg"))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(device_scale_factor=1, color_scheme="light")
        page.set_viewport_size({"width": 1024, "height": 1024})
        page.set_content((APP_ICONS / "icon.svg").read_text(encoding="utf-8"))
        reach = page.evaluate(REACH_JS)
        if not 0 < reach * MASKABLE <= SAFE:
            raise SystemExit(f'icons: app/install/icon.svg: <g id="bird"> reaches {reach:.3f} of the side from centre '
                             f"(x {MASKABLE:.3f} = {reach * MASKABLE:.3f}): none found, or outside the maskable safe circle {SAFE}")
        made = {
            "icon-192.png": _render(browser, master, 192),
            "icon-512.png": _render(browser, master, 512),
            "apple-touch-icon.png": _render(browser, master, 180, art=BLEED, bg=INK),
            "icon-maskable-512.png": _render(browser, master, 512, art=MASKABLE, bg=INK),
        }
        # hand-tuned rungs at their own sizes: sharper than the master scaled down
        frames = {16: _render(browser, s16, 16), 32: _render(browser, s32, 32), 48: _render(browser, master, 48)}
        browser.close()
    for name, png in made.items():
        (DOCS / name).write_bytes(png)
        print(f"docs/{name}")
    (DOCS / "favicon.ico").write_bytes(ico(frames))
    print("docs/favicon.ico (16, 32, 48)")
    record_sync([DOCS / n for n in ("icon.svg", *made, "favicon.ico")])
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
    """One share card: template (HTML, fonts + app art inlined - Chrome blocks file:// fonts) ->
    out PNG, 1200x630 exactly, clipped; fails on unloaded fonts or overflow (OVERFLOW_JS)."""
    from playwright.sync_api import sync_playwright

    def inline(m):
        b64 = base64.b64encode((DOCS / "fonts" / m[1]).read_bytes()).decode()
        return f'url("data:font/woff2;base64,{b64}")'

    name = template.name
    html, n = re.subn(r'url\("/fonts/([\w.-]+\.woff2)"\)', inline, template.read_text(encoding="utf-8"))
    if not n:
        raise SystemExit(f"og: no /fonts/*.woff2 url() in {name} to inline")
    # the app's own art files, never a copy of the mark: the card follows the desktop icon
    html, n = re.subn(
        r'src="/app/install/((?:icon|mark)[\w-]*\.svg)"',
        lambda m: f'src="data:image/svg+xml;base64,{_b64(APP_ICONS / m[1])}"', html,
    )
    if not n:
        raise SystemExit(f"og: no /app/install/ mark in {name} to inline")
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
    record_sync([out for _, out in CARDS])


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
