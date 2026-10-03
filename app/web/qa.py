# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Check the install site's pages in a real browser: nothing scrolls sideways, header fits.

Serves docs/ on a local port, opens every page (each docs/**/*.html but the mac/ + win/ install
scripts) in Google Chrome as a phone (phone browser name + touch) at 320, 360, 375 and 390px wide
and as a desktop at 768 and 1366px, and checks:

- page no wider than the screen (scrollWidth <= clientWidth; a phone's innerWidth grows to fit a
  too-wide page, so it never fails)
- header on one line from 360px up (brand + links side by side; 320px may wrap)
- home page at 1366x768: the Copy button shows without scrolling

Screenshots go to .data/screens/ (private, gitignored). Exit 1 + one line per failure.
The pytest site tests can't see layout; run this after changing a page's header, CSS or width.

Run from repo root: uv run app/web/qa.py
Own deps (inline above), so the project's deps stay untouched.
"""

import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SCREENS = ROOT / ".data" / "screens"

PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
PHONES = [(320, 640), (360, 780), (375, 812), (390, 844)]
DESKTOPS = [(768, 1024), (1366, 768)]

# visible header parts (brand + shown links) overlap vertically <=> one line
ONE_LINE = """() => {
  const parts = [...document.querySelectorAll("header .brand, header .links a")]
    .map(e => e.getBoundingClientRect()).filter(r => r.width > 0);
  return Math.max(...parts.map(r => r.top)) < Math.min(...parts.map(r => r.bottom));
}"""


def pages() -> list[str]:
    return sorted(p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.html")
                  if p.relative_to(DOCS).parts[0] not in ("mac", "win"))


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(browser, base: str, name: str, width: int, height: int, phone: bool) -> list[str]:
    context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=phone,
                                  has_touch=phone, user_agent=PHONE_UA if phone else DESKTOP_UA)
    page = context.new_page()
    page.goto(base + name)
    page.evaluate("document.fonts.ready")
    where = f"{name} at {width}x{height} ({'phone' if phone else 'desktop'})"
    failed = []
    scroll, inner = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    if scroll > inner:
        failed.append(f"{where}: page {scroll}px wide, screen {inner}px - scrolls sideways")
    if width >= 360 and not page.evaluate(ONE_LINE):
        failed.append(f"{where}: header wraps to a second line")
    if name == "index.html" and (width, height) == (1366, 768):
        bottom = page.evaluate("document.getElementById('copy').getBoundingClientRect().bottom")
        if bottom > height:
            failed.append(f"{where}: Copy button ends at {bottom:.0f}px, below the {height}px screen")
    SCREENS.mkdir(parents=True, exist_ok=True)
    shot = name.removesuffix(".html").replace("/", "-")
    page.screenshot(path=SCREENS / f"{shot}-{width}{'-phone' if phone else ''}.png", full_page=True)
    context.close()
    return failed


def main() -> int:
    from playwright.sync_api import sync_playwright

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    failed = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            for name in pages():
                for (w, h), phone in [(s, True) for s in PHONES] + [(s, False) for s in DESKTOPS]:
                    failed += check(browser, base, name, w, h, phone)
            browser.close()
    finally:
        server.shutdown()
    for line in failed:
        print(line)
    print(f"{len(failed)} problem(s); screenshots in {SCREENS.relative_to(ROOT)}/" if failed
          else f"all pages fit; screenshots in {SCREENS.relative_to(ROOT)}/")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
