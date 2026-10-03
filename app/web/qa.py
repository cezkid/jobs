# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
"""Check the install site's pages in a real browser: fit, fold, motion states, colours, print.

Serves docs/ on a local port (gzip, like GitHub Pages; 404.html for a missing path), opens every
page (each docs/**/*.html but the mac/ + win/ install scripts) in Google Chrome as a phone (phone
browser name + touch) at 320x640, 360x780, 375x812, 390x844 and as a desktop at 768x1024,
1366x641, 1440x900, 1920x1080, and checks:

- page no wider than the screen (scrollWidth <= clientWidth; a phone's innerWidth grows to fit a
  too-wide page, so it never fails)
- header on one line from 360px up (brand + links side by side; 320px may wrap); fewer than 2
  header parts found = fail, never a silent pass
- 0 console errors + 0 uncaught errors, in every browser context opened below
- home: Copy button ends within 1366x641 (gate; 1366x768 screen minus Chrome's bars), 1280x593
  reported only; page <= 8 screens at 1366x641 (3.88 on 2026-10-03), <= 2x 3.84 screens at
  375x812 (2x the 2026-10-03 length)

Every page again at 1366x641 (desktop) + 390x844 (phone):

- reduced motion: document.getAnimations() empty, every mark finished (MARK_STATE)
- full motion: no animation loops forever; once the timed ones end (the opening moment), text
  opacity 1 at every half-screen scroll step; every mark finished once scrolled to mid-screen
- layout boxes (offset rects: transforms don't move them) equal between reduced and full motion
- no JS (CSS still animates: judged once the timed animations end): all text shown
  (opacity 1, visible) + home's Windows install line
- forced colours: every mark still paints something its parent doesn't
- home in print: <= 5 pages (PDF) and the install line shows

--engines: WebKit + Firefox (Playwright's own builds), every page at 390x844 + 1366x641: no
sideways scroll, no console errors, finished states (reduced: 0 animations + marks; full: marks).
--self-test: injects faults into home (Copy below the fold, a hidden mark, a console error, a
wide element) and exits 1 unless each one fails its check and clean home passes.

Mark = <mark>, or any element with class "mark" (SVG circle/check, ::before sweep): new mark
kinds carry class "mark" so these checks see them.

Screenshots go to .data/screens/ (private, gitignored). Exit 1 + one line per failure; lines
starting "report:" are measurements, never failures. Every browser action times out after
ACTION_MS, a whole run after RUN_LIMIT_S (exit 2).

Run from repo root: uv run app/web/qa.py [--engines | --self-test]
Own deps (inline above, pinned to the cached webkit-2359 / firefox-1543 builds - no download),
so the project's deps stay untouched.
"""

import gzip
import mimetypes
import os
import re
import sys
import threading
from contextlib import contextmanager
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
DESKTOPS = [(768, 1024), (1366, 641), (1440, 900), (1920, 1080)]
MOTION_SIZES = [((1366, 641), False), ((390, 844), True)]
FOLD = (1366, 641)          # gate: 1366x768 screen minus Chrome's tab + address bars
FOLD_REPORT = (1280, 593)   # report only: 1280x720 screen, same bars
DESKTOP_CAP = 8             # home <= 8 screens at 1366x641 (3.88 on 2026-10-03, pre-redesign)
PHONE_TODAY = 3.84          # home at 375x812 (phone UA), measured 2026-10-03 (pre-redesign)
PHONE_CAP = 2 * PHONE_TODAY
PRINT_CAP = 5               # home prints in <= 5 pages
WIN_LINE = "irm https://jobs.enrriquez.com/win | iex"
ACTION_MS = 20_000
RUN_LIMIT_S = 900
GZIP_TYPES = (".html", ".css", ".js", ".svg", ".xml", ".json", ".webmanifest", ".txt", ".ico")

# visible header parts (brand + shown links) overlap vertically <=> one line; null = < 2 found
ONE_LINE = """() => {
  const parts = [...document.querySelectorAll("header .brand, header .links a")]
    .map(e => e.getBoundingClientRect()).filter(r => r.width > 0);
  if (parts.length < 2) return null;
  return Math.max(...parts.map(r => r.top)) < Math.min(...parts.map(r => r.bottom));
}"""

# shared helpers, prepended to the snippets below
HELPERS = """
const MARKS = "mark, .mark";
const opacity = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement)
  o *= parseFloat(getComputedStyle(e).opacity); return o; };
const shown = el => el.checkVisibility({contentVisibilityAuto: true});
const label = el => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") +
  (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\\s+/).join(".") : "") +
  ' "' + (el.textContent || "").trim().slice(0, 30) + '"';
const texts = () => [...document.body.querySelectorAll("*")].filter(el =>
  !["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName) &&
  [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && shown(el));
const markState = el => {
  const s = getComputedStyle(el);
  if (!shown(el)) return null;
  if (opacity(el) < 0.99 || s.visibility !== "visible") return "hidden";
  const size = s.backgroundSize.split(/\\s+/)[0];
  if (s.backgroundImage !== "none" && /^0(px|%)?$/.test(size)) return "not swept (background-size 0)";
  const before = getComputedStyle(el, "::before");
  const m = before.transform.match(/^matrix\\(([-\\d.e]+)/);
  if (before.content !== "none" && m && Math.abs(parseFloat(m[1])) < 0.99) return "not swept (::before scaleX)";
  const shapes = el instanceof SVGElement ? [el, ...el.querySelectorAll("*")] : [...el.querySelectorAll("svg *")];
  for (const sh of shapes) {
    const off = parseFloat(getComputedStyle(sh).strokeDashoffset);
    if (off > 0.5) return "not drawn (stroke-dashoffset " + off + ")";
  }
  return "ok";
};
const frames = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""

# every mark not finished, as "label: why"
MARK_STATE = "() => {" + HELPERS + """
  return [...document.querySelectorAll(MARKS)].map(el => [el, markState(el)])
    .filter(([, s]) => s && s !== "ok").map(([el, s]) => label(el) + ": " + s);
}"""

# full motion: scroll each mark to mid-screen, let its timed animations end, then judge it
MARKS_SCROLLED = "async () => {" + HELPERS + """
  const bad = [];
  for (const el of document.querySelectorAll(MARKS)) {
    el.scrollIntoView({block: "center"});
    await frames();
    await Promise.race([Promise.all(el.getAnimations({subtree: true})
      .filter(a => !(a.timeline instanceof (window.ScrollTimeline || class {})) &&
                   !(a.timeline instanceof (window.ViewTimeline || class {})))
      .map(a => a.finished.catch(() => {}))), new Promise(r => setTimeout(r, 5000))]);
    await frames();
    const s = markState(el);
    if (s && s !== "ok") bad.push(label(el) + ": " + s);
  }
  scrollTo(0, 0);
  return bad;
}"""

# animations that never end + wait (<= 5 s) for the timed ones to finish
SETTLE = "async () => {" + HELPERS + """
  const timed = document.getAnimations().filter(a => a.timeline === document.timeline);
  const loops = timed.filter(a => a.effect.getComputedTiming().iterations === Infinity)
    .map(a => (a.animationName || "animation") + " on " + label(a.effect.target));
  await Promise.race([Promise.all(timed.filter(a => a.effect.getComputedTiming().iterations !== Infinity)
    .map(a => a.finished.catch(() => {}))), new Promise(r => setTimeout(r, 5000))]);
  await frames();
  return loops;
}"""

# ms until the last timed (finite) animation ends; sync, so it works with JS off
REMAINING = """() => Math.max(0, ...document.getAnimations()
  .filter(a => a.timeline === document.timeline && a.effect.getComputedTiming().iterations !== Infinity)
  .map(a => a.effect.getComputedTiming().endTime - (a.currentTime || 0)))"""

# text below opacity 1 at each half-screen scroll step, as "y=N label"
TEXT_OPACITY = "async () => {" + HELPERS + """
  const bad = new Set();
  const step = Math.max(1, Math.floor(innerHeight / 2));
  for (let y = 0; y <= document.documentElement.scrollHeight - innerHeight + step; y += step) {
    scrollTo(0, y);
    await frames();
    for (const el of texts()) {
      const r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > innerHeight) continue;
      const o = opacity(el);
      if (o < 0.99 || getComputedStyle(el).visibility !== "visible")
        bad.add("y=" + scrollY + " " + label(el) + " opacity " + o.toFixed(2));
    }
  }
  scrollTo(0, 0);
  return [...bad];
}"""

# offset boxes of every HTML element in body (transforms + opacity leave them alone)
BOXES = """() => [...document.body.querySelectorAll("*")].filter(el => el instanceof HTMLElement)
  .map((el, i) => [i + " " + el.tagName.toLowerCase() + (el.id ? "#" + el.id : ""),
                   [el.offsetLeft, el.offsetTop, el.offsetWidth, el.offsetHeight].join(",")])"""

# no JS: text not shown in full (opacity / visibility), Windows line text + shown
NO_JS = "() => {" + HELPERS + """
  const bad = texts().filter(el => opacity(el) < 0.99 || getComputedStyle(el).visibility !== "visible")
    .map(el => label(el) + " opacity " + opacity(el).toFixed(2));
  const line = document.getElementById("line");
  return {bad, line: line ? [line.textContent.trim(), shown(line) && opacity(line) > 0.99] : null};
}"""

# forced colours: marks that paint nothing their parent doesn't
FORCED = "() => {" + HELPERS + """
  const paints = el => {
    const s = getComputedStyle(el), p = getComputedStyle(el.parentElement);
    const clear = c => /rgba\\(.*, 0\\)$/.test(c) || c === "transparent";
    if (s.backgroundImage !== "none") return true;
    if (!clear(s.backgroundColor) && s.backgroundColor !== p.backgroundColor) return true;
    if (s.textDecorationLine !== "none" || parseFloat(s.outlineWidth) > 0 && s.outlineStyle !== "none") return true;
    if (["Top", "Right", "Bottom", "Left"].some(k => parseFloat(s["border" + k + "Width"]) > 0 &&
                                                   s["border" + k + "Style"] !== "none")) return true;
    const before = getComputedStyle(el, "::before");
    if (before.content !== "none" && (!clear(before.backgroundColor) || before.backgroundImage !== "none")) return true;
    const shapes = el instanceof SVGElement ? [el, ...el.querySelectorAll("*")] : [...el.querySelectorAll("svg *")];
    return shapes.some(sh => { const c = getComputedStyle(sh); return (c.stroke !== "none" && !clear(c.stroke)) ||
                                                                   (c.fill !== "none" && !clear(c.fill)); });
  };
  return [...document.querySelectorAll(MARKS)].filter(el => shown(el) && !paints(el)).map(label);
}"""

# self-test faults: (what, html injected before </body>, check that must fail)
FAULTS = [
    ("Copy below the fold", "<style>#copy { margin-top: 900px; }</style>", "layout"),
    ("hidden mark", "<style>mark { opacity: 0; }</style>", "motion"),
    ("console error", "<script>console.error('qa self-test fault')</script>", "layout"),
    ("wide element", '<div style="width: 3000px; height: 1px"></div>', "layout"),
]


def pages() -> list[str]:
    return sorted(p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.html")
                  if p.relative_to(DOCS).parts[0] not in ("mac", "win"))


class Handler(SimpleHTTPRequestHandler):
    """docs/ like GitHub Pages: gzip for text when asked, 404.html (status 404) for a missing path."""

    def log_message(self, *args):
        pass

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir() and self.path.split("?")[0].endswith("/"):
            path = path / "index.html"
        if path.is_dir():
            return super().send_head()  # redirect to the folder with a slash
        status = 200
        if not path.is_file():
            path, status = Path(self.directory) / "404.html", 404
        body = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        if path.suffix in GZIP_TYPES and "gzip" in self.headers.get("Accept-Encoding", ""):
            body = gzip.compress(body, 6)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return _Body(body)


class _Body:
    """File-like body for SimpleHTTPRequestHandler.do_GET (copyfile + close)."""

    def __init__(self, data: bytes):
        self.data, self.done = data, False

    def read(self, n: int = -1) -> bytes:
        if self.done:
            return b""
        self.done = True
        return self.data

    def close(self):
        pass


def serve(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    """Start the gzip server on a free local port; returns (server, base URL ending in /)."""
    mimetypes.add_type("application/manifest+json", ".webmanifest")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def watchdog(seconds: int) -> threading.Timer:
    """Whole-run limit: a hung browser ends the run (exit 2) instead of the loop."""
    def stop():
        print(f"qa.py: run took over {seconds}s - stopped (a browser hung?)", flush=True)
        os._exit(2)
    timer = threading.Timer(seconds, stop)
    timer.daemon = True
    timer.start()
    return timer


@contextmanager
def opened(browser, base: str, name: str, width: int, height: int, phone: bool, failed: list,
           where: str, inject: str | None = None, goto: bool = True, **options):
    """A fresh context + page; console errors + uncaught errors land in failed on close."""
    mobile = {"is_mobile": phone} if browser.browser_type.name != "firefox" else {}
    context = browser.new_context(viewport={"width": width, "height": height}, has_touch=phone,
                                  user_agent=PHONE_UA if phone else DESKTOP_UA, **mobile, **options)
    context.set_default_timeout(ACTION_MS)
    page = context.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    if inject:
        def fulfil(route):
            response = route.fetch()
            route.fulfill(response=response, body=response.text().replace("</body>", inject + "</body>", 1))
        page.route(base + name, fulfil)
    try:
        if goto:
            page.goto(base + name)
            page.evaluate("document.fonts.ready")
        yield page
    finally:
        context.close()
        failed += [f"{where}: console error: {e[:160]}" for e in errors]


def label_for(browser, name: str, width: int, height: int, phone: bool, extra: str = "") -> str:
    engine = browser.browser_type.name
    kind = "phone" if phone else "desktop"
    return (f"{name} at {width}x{height} ({kind}{', ' + engine if engine != 'chromium' else ''}"
            f"{', ' + extra if extra else ''})")


def check_layout(browser, base: str, name: str, width: int, height: int, phone: bool,
                 inject: str | None = None, shots: bool = True) -> tuple[list[str], list[str]]:
    """Fit, header, fold, page length, console errors. Returns (failures, reports)."""
    where = label_for(browser, name, width, height, phone)
    failed, reports = [], []
    with opened(browser, base, name, width, height, phone, failed, where, inject) as page:
        scroll, inner, tall = page.evaluate("[document.documentElement.scrollWidth, "
                                            "document.documentElement.clientWidth, "
                                            "document.documentElement.scrollHeight]")
        if scroll > inner:
            failed.append(f"{where}: page {scroll}px wide, screen {inner}px - scrolls sideways")
        if width >= 360:
            one = page.evaluate(ONE_LINE)
            if one is None:
                failed.append(f"{where}: header check found fewer than 2 parts (brand + links)")
            elif not one:
                failed.append(f"{where}: header wraps to a second line")
        if name == "index.html":
            if (width, height) in (FOLD, FOLD_REPORT):
                bottom = page.evaluate("document.getElementById('copy').getBoundingClientRect().bottom")
                if bottom > height and (width, height) == FOLD:
                    failed.append(f"{where}: Copy button ends at {bottom:.0f}px, below the {height}px screen")
                if (width, height) == FOLD_REPORT:
                    reports.append(f"report: {where}: Copy button ends at {bottom:.0f}px of {height}px")
            screens = tall / height
            if (width, height) == FOLD and screens > DESKTOP_CAP:
                failed.append(f"{where}: page is {screens:.1f} screens long, cap {DESKTOP_CAP}")
            if (width, height) == (375, 812):
                reports.append(f"report: {where}: page is {screens:.2f} screens (today {PHONE_TODAY}, "
                               f"cap {PHONE_CAP:.1f})")
                if screens > PHONE_CAP:
                    failed.append(f"{where}: page is {screens:.1f} screens long, cap {PHONE_CAP:.1f}")
        if shots:
            SCREENS.mkdir(parents=True, exist_ok=True)
            shot = name.removesuffix(".html").replace("/", "-")
            engine = browser.browser_type.name
            page.screenshot(path=SCREENS / f"{shot}-{width}{'-phone' if phone else ''}"
                                           f"{'' if engine == 'chromium' else '-' + engine}.png",
                            full_page=True)
    return failed, reports


def check_motion(browser, base: str, name: str, width: int, height: int, phone: bool,
                 inject: str | None = None, full: bool = True) -> list[str]:
    """Reduced vs full motion; full=True adds no-JS, forced colours (Chrome) + text-opacity steps."""
    failed = []
    where = label_for(browser, name, width, height, phone, "reduced motion")
    with opened(browser, base, name, width, height, phone, failed, where, inject,
                reduced_motion="reduce") as page:
        running = page.evaluate("document.getAnimations().map(a => (a.animationName || a.constructor.name)"
                                " + ' on ' + (a.effect && a.effect.target ? a.effect.target.tagName : '?'))")
        failed += [f"{where}: animation runs: {a}" for a in running]
        failed += [f"{where}: mark not finished: {m}" for m in page.evaluate(MARK_STATE)]
        reduced = dict(page.evaluate(BOXES))

    where = label_for(browser, name, width, height, phone, "full motion")
    with opened(browser, base, name, width, height, phone, failed, where, inject,
                reduced_motion="no-preference") as page:
        failed += [f"{where}: animation never ends: {a}" for a in page.evaluate(SETTLE)]
        moving = dict(page.evaluate(BOXES))
        if full:
            failed += [f"{where}: text not fully shown at {t}" for t in page.evaluate(TEXT_OPACITY)[:10]]
        failed += [f"{where}: mark not finished at mid-screen: {m}" for m in page.evaluate(MARKS_SCROLLED)]
    diff = [k for k in reduced.keys() | moving.keys() if reduced.get(k) != moving.get(k)]
    if diff:
        first = sorted(diff, key=lambda k: int(k.split()[0]))[:5]
        failed.append(f"{where}: {len(diff)} layout box(es) differ from reduced motion: " +
                      "; ".join(f"{k} {reduced.get(k)} vs {moving.get(k)}" for k in first))
    if not full:
        return failed

    where = label_for(browser, name, width, height, phone, "no JS")
    with opened(browser, base, name, width, height, phone, failed, where, inject,
                java_script_enabled=False) as page:
        # CSS still animates without JS (but timers + frames never fire): sleep out the timed ones
        page.wait_for_timeout(min(5000, page.evaluate(REMAINING)) + 100)
        result = page.evaluate(NO_JS)
        failed += [f"{where}: text not fully shown: {t}" for t in result["bad"][:10]]
        if name == "index.html":
            line = result["line"]
            if not line or line[0] != WIN_LINE or not line[1]:
                failed.append(f"{where}: Windows install line missing or hidden ({line})")

    if browser.browser_type.name == "chromium":
        where = label_for(browser, name, width, height, phone, "forced colours")
        with opened(browser, base, name, width, height, phone, failed, where, inject,
                    forced_colors="active") as page:
            failed += [f"{where}: mark paints nothing: {m}" for m in page.evaluate(FORCED)]
    return failed


def check_print(browser, base: str, inject: str | None = None) -> list[str]:
    """Home as printed: <= PRINT_CAP pages (Chrome PDF), install line shown."""
    failed = []
    where = "index.html in print"
    with opened(browser, base, "index.html", 1366, 641, False, failed, where, inject) as page:
        page.emulate_media(media="print")
        line = page.evaluate("(() => { const l = document.getElementById('line');"
                             " return l && l.checkVisibility() ? l.textContent.trim() : null; })()")
        if line != WIN_LINE:
            failed.append(f"{where}: install line not printed ({line!r})")
        pdf = page.pdf(format="Letter", print_background=True)
        count = len(re.findall(rb"/Type\s*/Page\b", pdf))
        if not count or count > PRINT_CAP:
            failed.append(f"{where}: {count} pages, cap {PRINT_CAP}")
    return failed


def run_chrome(base: str) -> tuple[list[str], list[str]]:
    from playwright.sync_api import sync_playwright

    failed, reports = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name in pages():
            sizes = [(s, True) for s in PHONES] + [(s, False) for s in DESKTOPS]
            if name == "index.html":
                sizes.append((FOLD_REPORT, False))
            for (w, h), phone in sizes:
                f, r = check_layout(browser, base, name, w, h, phone)
                failed += f
                reports += r
            for (w, h), phone in MOTION_SIZES:
                failed += check_motion(browser, base, name, w, h, phone)
        failed += check_print(browser, base)
        browser.close()
    return failed, reports


def run_engines(base: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    failed = []
    with sync_playwright() as p:
        for engine in (p.webkit, p.firefox):
            browser = engine.launch()
            for name in pages():
                for (w, h), phone in MOTION_SIZES:
                    f, _ = check_layout(browser, base, name, w, h, phone)
                    failed += [line for line in f if "header" not in line and "Copy button" not in line]
                    failed += check_motion(browser, base, name, w, h, phone, full=False)
            browser.close()
    return failed


def run_self_test(base: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    def home(browser, kind: str, inject: str | None) -> list[str]:
        if kind == "layout":
            return check_layout(browser, base, "index.html", *FOLD, False, inject, shots=False)[0]
        return check_motion(browser, base, "index.html", *FOLD, False, inject)

    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for kind in ("layout", "motion"):
            clean = home(browser, kind, None)
            if clean:
                failed.append(f"self-test: clean home fails its {kind} checks: {clean[0]}")
        for what, html, kind in FAULTS:
            caught = home(browser, kind, html)
            print(f"self-test: {what}: {'caught - ' + caught[0] if caught else 'NOT CAUGHT'}")
            if not caught:
                failed.append(f"self-test: injected fault not caught: {what}")
        browser.close()
    return failed


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("", "--engines", "--self-test"):
        print("usage: uv run app/web/qa.py [--engines | --self-test]")
        return 2
    watchdog(RUN_LIMIT_S)
    server, base = serve(DOCS)
    reports = []
    try:
        if mode == "--engines":
            failed = run_engines(base)
        elif mode == "--self-test":
            failed = run_self_test(base)
        else:
            failed, reports = run_chrome(base)
    finally:
        server.shutdown()
    for line in reports + failed:
        print(line)
    done = {"": "all pages pass", "--engines": "WebKit + Firefox pass",
            "--self-test": "every injected fault caught"}[mode]
    print(f"{len(failed)} problem(s)" if failed else done,
          f"; screenshots in {SCREENS.relative_to(ROOT)}/" if mode != "--self-test" else "", sep="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
