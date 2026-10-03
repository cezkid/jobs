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

- reduced motion: document.getAnimations() empty, every mark finished (MARK_STATE), every dashed
  SVG stroke drawn (DRAWN: stroke-dashoffset 0)
- full motion: no animation loops forever; once the timed ones end (the opening moment), text
  opacity 1 at every half-screen scroll step; every mark finished once scrolled to mid-screen;
  every dashed stroke drawn after a full scroll; reloaded at the bottom, none above the screen undrawn
- layout boxes (offset rects: transforms don't move them) equal between reduced and full motion
- no JS (CSS still animates: judged once the timed animations end): all text shown
  (opacity 1, visible) + home's Windows install line
- forced colours: every mark still paints something its parent doesn't
- home in print: <= 5 pages (PDF) and the install line shows
- home's opening moment, 1366x641 + 390x844 (full motion): at load only the hero window animates
  (outside it only scroll-driven scene animations may exist),
  every timed animation ends <= 2800 ms; at first paint (each animation at 0) hero text opacity 1
  and no hero box more than 12px from its finished place; the LCP element is outside every
  animated element (its selector reported); a reload in the same tab (html.seen) animates nothing
- page change, 1366x641: /research/ -> home -> /research/ through the header links, full motion:
  pagereveal.viewTransition set both ways, masthead named, home skips its opening (html.seen);
  reduced motion: home -> /research/ with viewTransition null

--engines: WebKit + Firefox (Playwright's own builds), every page at 390x844 + 1366x641: no
sideways scroll, no console errors, finished states (reduced: 0 animations + marks + strokes;
full: marks + strokes after a full scroll + after a reload at the bottom).
--self-test: injects faults into home (Copy below the fold, a hidden mark, a console error, a
wide element, a scene circle stuck half drawn / undrawn in reduced motion, an opening that runs
long / fades text in / moves 40px / animates the LCP element / replays on reload, a page change
w/o crossfade, an opening played after one) and exits 1 unless each one fails its check and clean
home passes.

--perf: home timed in Chrome, docs/ vs a frozen copy of the pre-redesign site (docs/ at
BASELINE_SHA, unpacked once into .data/site-baseline/), new + baseline alternating, median of 3
valid runs, gzip server, keeps the Mac awake (caffeinate -dimsu), never records video. Profiles:
phone 412x915 dpr 2.625, CPU 4x, one raster thread, 150 ms RTT, 1.6 Mbps; desktop 1440x900
(Windows UA, + clicks); the same with a Mac UA; no-GPU desktop (--disable-gpu, CPU 4x) w/ a
raster trace over the scroll. Each run: load, 4 s wait, wheel to the bottom, then (desktop) Copy,
OS switch + a summary clicked at CPU 4x. Gates (perf_gates): phone LCP <= 1.5 s
+ <= baseline + 0.3 s; desktop LCP <= 0.5 s; CLS <= 0.01 every profile; Long Animation Frames
split load / scroll at the first wheel: scroll max < 250 ms + <= baseline + 50, frames >= 50 ms
<= baseline + 2; phone first 4 s max < 300 ms, blocking <= baseline + 100; click -> next paint
(Event Timing) <= 100 ms; Copy -> "Copied" shown <= 150 ms (median of 5); no-GPU frames over
33.4 ms <= 5%. Idle frames > 18 ms apart = busy machine: run invalid, re-run (never a failure);
a run over budget runs once more before failing. --perf --self-test injects a 300 ms busy loop
on scroll + a late layout shift (desktop, 1 run) and exits 1 unless each fails and clean passes.
--lighthouse: npx lighthouse@12.8.2 (system Chrome) against the gzip server, home, research hub,
one article, about, privacy, 404 as phone + desktop, 3 runs each, JSON in .data/site-qa/:
Accessibility + Best Practices 100 every run; Performance median 100 desktop, >= 99 phone; every
SEO audit passes but canonical (names the live host, not localhost) + is-crawlable on the 404.

Mark = <mark>, or any element with class "mark" (SVG circle/check, ::before sweep): new mark
kinds carry class "mark" so these checks see them.

Screenshots go to .data/screens/ (private, gitignored). Exit 1 + one line per failure; lines
starting "report:" are measurements, never failures. Every browser action times out after
ACTION_MS, a whole run after RUN_LIMIT_S (exit 2).

Run from repo root: uv run app/web/qa.py [--engines | --self-test | --perf [--self-test] | --lighthouse]
Own deps (inline above, pinned to the cached webkit-2359 / firefox-1543 builds - no download),
so the project's deps stay untouched.
"""

import gzip
import json
import mimetypes
import os
import re
import shutil
import statistics
import subprocess
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
SEND_AT = (390, 844)        # phone: "Send this page to my computer" ends <= SEND_CAP px (no scroll
SEND_CAP = 675              # for the one thing a phone visitor can do; 675 = 844 minus Safari's bars)
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

# every drawn stroke (SVG circle / path with a dash) not at stroke-dashoffset 0, as "label: why";
# above=true keeps only those wholly above the screen
DRAWN = "(above) => {" + HELPERS + """
  return [...document.querySelectorAll("svg :is(circle, path)")]
    .filter(sh => shown(sh) && getComputedStyle(sh).strokeDasharray !== "none")
    .filter(sh => !above || sh.getBoundingClientRect().bottom < 0)
    .map(sh => [sh, parseFloat(getComputedStyle(sh).strokeDashoffset)]).filter(([, off]) => off > 0.5)
    .map(([sh, off]) => label(sh) + " in " + label(sh.closest("svg").parentElement) + ": stroke-dashoffset " + off);
}"""

# full motion: scroll to the bottom in half-screen steps, let timed animations end
SCROLL_DOWN = "async () => {" + HELPERS + """
  const step = Math.max(1, Math.floor(innerHeight / 2));
  for (let y = 0; y <= document.documentElement.scrollHeight - innerHeight + step; y += step) {
    scrollTo(0, y);
    await frames();
  }
  await Promise.race([Promise.all(document.getAnimations().filter(a => a.timeline === document.timeline)
    .map(a => a.finished.catch(() => {}))), new Promise(r => setTimeout(r, 5000))]);
  await frames();
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

OPENING_MS = 2800          # opening moment ends by then
OPENING_SHIFT = 12         # px a hero object may move during it
OPENING_AT = [((1366, 641), False), ((390, 844), True)]

# load: animations as [target selector, timed?, end ms, inside the hero window?] + the LCP element
OPENING = "async () => {" + HELPERS + """
  const path = el => { const out = []; for (let e = el; e && e !== document.documentElement; e = e.parentElement)
    out.unshift(e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") +
      (typeof e.className === "string" && e.className.trim() ? "." + e.className.trim().split(/\\s+/).join(".") : ""));
    return out.join(" > "); };
  const lcp = await new Promise(done => { new PerformanceObserver(l => { const e = l.getEntries().at(-1);
    done(e && e.element); }).observe({type: "largest-contentful-paint", buffered: true});
    setTimeout(() => done(null), 3000); });
  const all = document.getAnimations(), win = document.querySelector(".hero .window");
  const targets = all.map(a => a.effect.target);
  return {
    animations: all.map(a => [path(a.effect.target), a.timeline === document.timeline,
                              Math.round(a.effect.getComputedTiming().endTime), !!win && win.contains(a.effect.target)]),
    lcp: lcp ? path(lcp) : null,
    lcpAnimated: !!lcp && targets.some(t => t.contains(lcp) || lcp.contains(t)),
  };
}"""

# first paint vs finished: hero text below opacity 1 at time 0, hero boxes moved > OPENING_SHIFT px
FIRST_PAINT = "() => {" + HELPERS + """
  const timed = document.getAnimations().filter(a => a.timeline === document.timeline);
  const hero = [...document.querySelectorAll(".hero *")].filter(el => shown(el));
  timed.forEach(a => { a.pause(); a.currentTime = 0; });
  const at0 = hero.map(el => el.getBoundingClientRect());
  const faded = texts().filter(el => el.closest(".hero") && opacity(el) < 0.99)
    .map(el => label(el) + " opacity " + opacity(el).toFixed(2));
  timed.forEach(a => a.finish());
  const moved = hero.map((el, i) => { const r = el.getBoundingClientRect(), o = at0[i];
    return [el, Math.max(Math.abs(r.left - o.left), Math.abs(r.top - o.top))]; })
    .filter(([, d]) => d > SHIFT).map(([el, d]) => label(el) + " " + Math.round(d) + "px");
  return {faded, moved};
}""".replace("SHIFT", str(OPENING_SHIFT))


# page change: pagereveal recorded from the first script on (true = the page came in through a transition)
REVEAL = 'addEventListener("pagereveal", e => { window.__vt = !!e.viewTransition; });'
ARRIVED = """() => { const win = document.querySelector(".hero .window"), m = document.querySelector(".masthead");
  return {vt: window.__vt, seen: document.documentElement.classList.contains("seen"),
          masthead: m ? getComputedStyle(m).viewTransitionName : null,
          opening: win ? document.getAnimations().filter(a => a.timeline === document.timeline
                                                         && win.contains(a.effect.target)).length : 0}; }"""


# self-test faults: (what, html injected before </body>, check that must fail)
FAULTS = [
    ("Copy below the fold", "<style>#copy { margin-top: 900px; }</style>", "layout"),
    ("phone Send button too low", "<style>.send { margin-top: 400px; }</style>", "phone"),
    ("hidden mark", "<style>mark { opacity: 0; }</style>", "motion"),
    ("console error", "<script>console.error('qa self-test fault')</script>", "layout"),
    ("wide element", '<div style="width: 3000px; height: 1px"></div>', "layout"),
    ("opening runs 4 s", "<style>.today mark { animation-duration: 4s !important; }</style>", "opening"),
    ("opening fades text in", "<style>@keyframes qa-fade { from { opacity: 0; } } "
     "html:not(.seen) .job { animation: qa-fade 1s both; }</style>", "opening"),
    ("opening moves the window 40px", "<style>@keyframes qa-lift { from { transform: translateY(40px); } } "
     "html:not(.seen) .window { animation: qa-lift 1s both; }</style>", "opening"),
    ("LCP element animated", "<style>@keyframes qa-nudge { from { transform: translateY(4px); } } "
     "html:not(.seen) h1 { animation: qa-nudge 1s both; }</style>", "opening"),
    ("scene circle stuck half drawn", "<style>@keyframes qa-stuck { to { stroke-dashoffset: 40; } } "
     "@media (prefers-reduced-motion: no-preference) { .margin.ok .ring { animation: qa-stuck 1s linear both "
     "!important; animation-timeline: view() !important; } }</style>", "motion"),
    ("scene circle undrawn in reduced motion", "<style>.submit svg { stroke-dashoffset: 60 !important; }</style>",
     "motion"),
    ("opening replays on reload", '<script>document.documentElement.classList.remove("seen")</script>', "opening"),
    ("page change w/o crossfade", "<style>@view-transition { navigation: none; }</style>", "transition"),
    ("opening plays after a page change", '<script>addEventListener("pagereveal", () => '
     'document.documentElement.classList.remove("seen"))</script>', "transition"),
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
        page.route(lambda url: url in (base + name, base + name.removesuffix("index.html")), fulfil)
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
            if phone and (width, height) == SEND_AT:
                bottom = page.evaluate("document.querySelector('.send').getBoundingClientRect().bottom")
                reports.append(f"report: {where}: 'Send this page to my computer' ends at {bottom:.0f}px "
                               f"(cap {SEND_CAP})")
                if bottom > SEND_CAP:
                    failed.append(f"{where}: 'Send this page to my computer' ends at {bottom:.0f}px, "
                                  f"cap {SEND_CAP}")
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
        failed += [f"{where}: not drawn: {m}" for m in page.evaluate(DRAWN, False)]
        reduced = dict(page.evaluate(BOXES))

    where = label_for(browser, name, width, height, phone, "full motion")
    with opened(browser, base, name, width, height, phone, failed, where, inject,
                reduced_motion="no-preference") as page:
        failed += [f"{where}: animation never ends: {a}" for a in page.evaluate(SETTLE)]
        moving = dict(page.evaluate(BOXES))
        if full:
            failed += [f"{where}: text not fully shown at {t}" for t in page.evaluate(TEXT_OPACITY)[:10]]
        failed += [f"{where}: mark not finished at mid-screen: {m}" for m in page.evaluate(MARKS_SCROLLED)]
        # scroll-driven draw-ins: all drawn after a full scroll; a reload at the bottom leaves none
        # above the screen unfinished
        page.evaluate(SCROLL_DOWN)
        failed += [f"{where}: not drawn after a full scroll: {m}" for m in page.evaluate(DRAWN, False)]
        page.reload()
        page.wait_for_load_state("load")
        if page.evaluate("scrollY") < 1:  # no scroll restoration: put it at the bottom by hand
            page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
        page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        failed += [f"{where}: reloaded at the bottom, not drawn above the screen: {m}"
                   for m in page.evaluate(DRAWN, True)]
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


def check_opening(browser, base: str, inject: str | None = None) -> tuple[list[str], list[str]]:
    """Home's opening moment (full motion): hero window only, <= OPENING_MS, opaque + in place from
    first paint, LCP element outside it, nothing on a reload in the same tab. (failures, reports)"""
    failed, reports = [], []
    for (w, h), phone in OPENING_AT:
        where = label_for(browser, "index.html", w, h, phone, "opening")
        with opened(browser, base, "index.html", w, h, phone, failed, where, inject,
                    reduced_motion="no-preference") as page:
            result = page.evaluate(OPENING)
            reports.append(f"report: {where}: LCP element {result['lcp']}")
            if not result["lcp"]:
                failed.append(f"{where}: no LCP element reported")
            elif result["lcpAnimated"]:
                failed.append(f"{where}: LCP element {result['lcp']} is inside or around an animated element")
            anims = result["animations"]
            if not phone and not any(timed for _, timed, _, _ in anims):
                failed.append(f"{where}: no opening animation ran (the motion this check guards)")
            # outside the window only scroll-driven scenes may exist: they move when scrolled, not at load
            for target, timed, end, in_window in anims:
                if not in_window and timed:
                    failed.append(f"{where}: animation at load outside the hero window: {target}")
                elif timed and end > OPENING_MS:
                    failed.append(f"{where}: opening animation ends at {end} ms (cap {OPENING_MS}): {target}")
            paint = page.evaluate(FIRST_PAINT)
            failed += [f"{where}: hero text not opaque at first paint: {t}" for t in paint["faded"][:5]]
            failed += [f"{where}: hero object moves over {OPENING_SHIFT}px: {t}" for t in paint["moved"][:5]]
            page.reload()
            page.evaluate("document.fonts.ready")
            again = page.evaluate(OPENING)["animations"]
            failed += [f"{where}: reload in the same tab animates {target}"
                       for target, timed, _, in_window in again if timed or in_window]
    return failed, reports


def check_transition(browser, base: str, inject: str | None = None) -> list[str]:
    """Page change, 1366x641: full motion crossfades both ways (pagereveal.viewTransition set) and
    home arriving through one skips its opening (html.seen, nothing animating in the window);
    reduced motion changes page with no transition (viewTransition null)."""
    failed = []
    for motion, start, hops in (("no-preference", "research/", (("a.brand", ""), ('a[href="/research/"]', "research/"))),
                                ("reduce", "", (('a[href="/research/"]', "research/"),))):
        where = f"page change ({motion})"
        with opened(browser, base, "index.html", 1366, 641, False, failed, where, inject, goto=False,
                    reduced_motion=motion) as page:
            page.add_init_script(REVEAL)
            page.goto(base + start)
            for link, to in hops:
                page.click(f"header {link}")
                page.wait_for_url(base + to)
                page.wait_for_function("window.__vt !== undefined")
                got = page.evaluate(ARRIVED)
                if (motion == "reduce") == got["vt"]:
                    failed.append(f"{where}: /{to} arrived with viewTransition {'set' if got['vt'] else 'null'}")
                if got["masthead"] != ("masthead" if motion != "reduce" else "none"):
                    failed.append(f"{where}: /{to} masthead view-transition-name {got['masthead']!r}")
                if not to and motion != "reduce" and not (got["seen"] and not got["opening"]):
                    failed.append(f"{where}: home arrived through a crossfade plays its opening "
                                  f"(html.seen {got['seen']}, {got['opening']} window animations)")
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
        failed += check_transition(browser, base)
        f, r = check_opening(browser, base)
        failed += f
        reports += r
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
        if kind == "phone":
            return check_layout(browser, base, "index.html", *SEND_AT, True, inject, shots=False)[0]
        if kind == "opening":
            return check_opening(browser, base, inject)[0]
        if kind == "transition":
            return check_transition(browser, base, inject)
        return check_motion(browser, base, "index.html", *FOLD, False, inject)

    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for kind in ("layout", "phone", "motion", "opening", "transition"):
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


# ---- --perf: home timed in Chrome, new docs/ vs the frozen pre-redesign copy ----------------------

BASELINE_SHA = "c7b9a106f7e23fee09a1f6d0bc15b457af00c060"  # site/redesign start (plan-6zp notes)
BASELINE = ROOT / ".data" / "site-baseline"
ANDROID_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36")
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
NOGPU = ["--disable-gpu", "--disable-software-rasterizer"]
# size, device pixel ratio, phone, CPU slowdown, Chrome switches, network (RTT ms, bits/s), UA;
# clicks = Event Timing + Copy -> "Copied"; trace = raster trace over the scroll
PERF_PROFILES = {
    "phone": dict(size=(412, 915), dpr=2.625, phone=True, cpu=4, args=["--num-raster-threads=1"],
                  net=(150, 1.6e6), ua=ANDROID_UA),
    "desktop": dict(size=(1440, 900), dpr=1, phone=False, cpu=1, args=[], net=None, ua=DESKTOP_UA,
                    clicks=True),
    "desktop mac": dict(size=(1440, 900), dpr=1, phone=False, cpu=1, args=[], net=None, ua=MAC_UA),
    "no-GPU desktop": dict(size=(1440, 900), dpr=1, phone=False, cpu=4, args=NOGPU, net=None,
                           ua=DESKTOP_UA, trace=True),
}
PERF_RUNS = 3
PERF_LIMIT_S = 2400
LOAD_WAIT_MS = 4000          # load + opening moment, then the scroll starts
IDLE_MAX_MS = 18             # idle frame interval above this = busy machine, run invalid
INVALID_TRIES = 3            # invalid runs re-run up to this many times each
TRACE = ["devtools.timeline", "disabled-by-default-devtools.timeline", "cc"]

# Web Vitals + Long Animation Frames + Event Timing, collected from the first byte
PERF_JS = """
window.__p = {cls: 0, lcp: 0, loaf: [], events: [], frames: null};
let win = 0, first = 0, last = 0;
new PerformanceObserver(l => { for (const e of l.getEntries()) {
  if (e.hadRecentInput) continue;
  if (win && e.startTime - last < 1000 && e.startTime - first < 5000) win += e.value;
  else { win = e.value; first = e.startTime; }
  last = e.startTime; __p.cls = Math.max(__p.cls, win);
}}).observe({type: "layout-shift", buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries()) __p.lcp = e.startTime; })
  .observe({type: "largest-contentful-paint", buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries())
  __p.loaf.push([e.startTime, e.duration, e.blockingDuration]); })
  .observe({type: "long-animation-frame", buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries())
  if (e.interactionId) __p.events.push([e.startTime, e.duration]); })
  .observe({type: "event", buffered: true, durationThreshold: 16});
"""

# median rAF interval over 60 idle frames
IDLE = """() => new Promise(done => { const f = []; let last;
  const t = n => { if (last !== undefined) f.push(n - last); last = n;
    f.length < 60 ? requestAnimationFrame(t) : done(f.sort((a, b) => a - b)[30]); };
  requestAnimationFrame(t); })"""

# rAF intervals from now on, into __p.frames
FRAMES = """() => { __p.frames = []; let last = performance.now();
  const t = n => { __p.frames.push(n - last); last = n; requestAnimationFrame(t); };
  requestAnimationFrame(t); return last; }"""

# arms one Copy click: resolves to ms from the click to the first frame painted after "Copied"
COPIED = """() => { const b = document.getElementById("copy"), l = document.getElementById("copy-label");
  l.textContent = "Copy";
  window.__copied = new Promise(done => { let t0 = null;
    b.addEventListener("click", e => { t0 = e.timeStamp; }, {once: true, capture: true});
    const mo = new MutationObserver(() => { if (l.textContent !== "Copied") return; mo.disconnect();
      requestAnimationFrame(() => setTimeout(() => done(performance.now() - t0))); });
    mo.observe(l, {childList: true, characterData: true, subtree: true});
    setTimeout(() => done(null), 3000); }); }"""

# self-test faults for --perf: (what, html injected before </body>)
PERF_FAULTS = [
    ("300 ms busy loop on scroll", "<script>addEventListener('scroll', () => { if (window.__busy) return; "
     "window.__busy = 1; const t = performance.now(); while (performance.now() - t < 300); })</script>"),
    ("late layout shift", "<script>setTimeout(() => document.body.insertAdjacentHTML('afterbegin', "
     "'<div style=\"height: 120px\"></div>'), 2500)</script>"),
]


def baseline_docs() -> Path:
    """docs/ as it was at BASELINE_SHA, unpacked once into .data/site-baseline/ (SHA file records it)."""
    stamp = BASELINE / "SHA"
    if stamp.is_file() and stamp.read_text().strip() == BASELINE_SHA and (BASELINE / "docs" / "404.html").is_file():
        return BASELINE / "docs"
    if BASELINE.exists():
        shutil.rmtree(BASELINE)
    BASELINE.mkdir(parents=True)
    # the docs tree itself: "archive SHA docs" drops docs/ (export-ignore in .gitattributes)
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", "--prefix=docs/", f"{BASELINE_SHA}:docs"],
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(BASELINE)], input=archive, check=True)
    stamp.write_text(BASELINE_SHA + "\n")
    return BASELINE / "docs"


def median(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def trace_totals(events: list) -> dict:
    """Raster + paint ms and the compositor's frames (craft-table-kit tools/perf.py method)."""
    spans = [e for e in events if e.get("ph") == "X"]
    ms = lambda n: round(sum(e["dur"] for e in spans if e.get("name") == n) / 1000)
    frames = [e["args"]["frame_reporter"] for e in events if e.get("name") == "PipelineReporter"
              and e.get("ph") == "b" and "frame_reporter" in e.get("args", {})]
    return dict(raster_ms=ms("RasterTask"), paint_ms=ms("Paint"),
                checker=sum(any(r.get(k) for k in ("checkerboarded_needs_raster", "checkerboarded_needs_record",
                                                   "has_missing_content")) for r in frames),
                dropped=sum(r.get("state") == "STATE_DROPPED" for r in frames),
                presented=sum(r.get("state", "").startswith("STATE_PRESENTED") for r in frames))


def perf_run(browser, url: str, prof: dict, inject: str | None = None) -> dict | None:
    """One load + scroll (+ clicks) of url; None = invalid (idle frames slower than IDLE_MAX_MS)."""
    w, h = prof["size"]
    context = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=prof["dpr"],
                                  is_mobile=prof["phone"], has_touch=prof["phone"], user_agent=prof["ua"],
                                  reduced_motion="no-preference")
    context.set_default_timeout(ACTION_MS)
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=url.rstrip("/"))
    context.add_init_script(PERF_JS)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if inject:
        def fulfil(route):
            response = route.fetch()
            route.fulfill(response=response, body=response.text().replace("</body>", inject + "</body>", 1))
        page.route(url, fulfil)
    cdp = context.new_cdp_session(page)
    if prof["net"]:
        rtt, bits = prof["net"]
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", dict(offline=False, latency=rtt, downloadThroughput=bits / 8,
                                                          uploadThroughput=bits / 16))
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": prof["cpu"]})
    try:
        page.goto(url, wait_until="load")
        page.wait_for_timeout(max(0, LOAD_WAIT_MS - page.evaluate("performance.now()")))
        idle = page.evaluate(IDLE)
        if idle > IDLE_MAX_MS:
            print(f"perf: idle frames {idle:.1f} ms apart (> {IDLE_MAX_MS}) - busy machine, run invalid", flush=True)
            return None
        lcp = page.evaluate("__p.lcp")
        tall = page.evaluate("document.documentElement.scrollHeight")
        step = h / 4
        steps = min(80, int((tall - h) / step) + 4)
        page.mouse.move(w / 2, h / 2)
        if prof.get("trace"):
            browser.start_tracing(page=page, categories=TRACE)
        scroll_at = page.evaluate(FRAMES)
        for _ in range(steps):
            page.mouse.wheel(0, step)
            page.wait_for_timeout(120)
        page.wait_for_timeout(1500)
        trace = json.loads(browser.stop_tracing()) if prof.get("trace") else None
        p = page.evaluate("__p")
        frames = [f for f in p["frames"][2:] if f > 0]
        load = [f for f in p["loaf"] if f[0] < min(scroll_at, LOAD_WAIT_MS)]
        scroll = [f for f in p["loaf"] if f[0] >= scroll_at]
        result = dict(idle=idle, lcp=lcp, cls=p["cls"],
                      load_max=max((f[1] for f in load), default=0), load_blocking=sum(f[2] for f in load),
                      scroll_max=max((f[1] for f in scroll), default=0),
                      scroll_long=sum(f[1] >= 50 for f in scroll),
                      over33=100 * sum(f > 33.4 for f in frames) / len(frames) if frames else 0)
        if trace is not None:
            result |= trace_totals(trace["traceEvents"] if isinstance(trace, dict) else trace)
        if prof.get("clicks"):
            page.evaluate("scrollTo(0, 0)")
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            page.wait_for_timeout(300)

            def click(selector: str) -> float:
                t = page.evaluate("performance.now()")
                page.click(selector)
                page.wait_for_timeout(600)
                return page.evaluate("t => Math.max(0, ...__p.events.filter(e => e[0] >= t).map(e => e[1]))", t)

            result["click Copy"] = click("#copy")
            copied = []
            for _ in range(5):
                page.evaluate(COPIED)
                page.click("#copy")
                copied.append(page.evaluate("window.__copied"))
                page.wait_for_timeout(300)
            result["copied"] = None if None in copied else median(copied)
            result["click OS switch"] = click("#switch-os")
            result["click summary"] = click("summary")
        result["errors"] = errors
        return result
    finally:
        context.close()


def perf_profile(p, name: str, prof: dict, bases: dict, runs: int, inject: str | None = None) -> dict:
    """Medians per site ("new", "baseline") over runs valid runs, sites alternating new/baseline."""
    browser = p.chromium.launch(channel="chrome", args=prof["args"])
    got = {site: [] for site in bases}
    try:
        for i in range(runs):
            for site in (["new", "baseline"] if i % 2 == 0 else ["baseline", "new"]):
                if site not in bases:
                    continue
                for _ in range(INVALID_TRIES):
                    r = perf_run(browser, bases[site], prof, inject if site == "new" else None)
                    if r is not None:
                        got[site].append(r)
                        break
    finally:
        browser.close()
    out = {}
    for site, rs in got.items():
        if not rs:
            out[site] = None
            continue
        keys = [k for k in rs[0] if k != "errors"]
        out[site] = {k: median([r.get(k) for r in rs]) for k in keys} | {
            "runs": len(rs), "errors": sorted({e for r in rs for e in r["errors"]})}
    return out


def perf_gates(name: str, prof: dict, new: dict | None, base: dict | None) -> list[str]:
    """Budgets table (app/docs/site.md, plan-6zp DESIGN) on the medians."""
    where = f"perf {name}"
    if new is None or base is None:
        return [f"{where}: no valid run ({'new' if new is None else 'baseline'}) - machine too busy"]
    failed = [f"{where}: page error: {e[:160]}" for e in new["errors"]]
    if name == "phone":
        if new["lcp"] > 1500 or new["lcp"] > base["lcp"] + 300:
            failed.append(f"{where}: LCP {new['lcp']:.0f} ms (cap 1500 and baseline {base['lcp']:.0f} + 300)")
        if new["load_max"] >= 300:
            failed.append(f"{where}: long frame in the first 4 s {new['load_max']:.0f} ms (cap < 300)")
        if new["load_blocking"] > base["load_blocking"] + 100:
            failed.append(f"{where}: blocking in the first 4 s {new['load_blocking']:.0f} ms "
                          f"(baseline {base['load_blocking']:.0f} + 100)")
    if name == "desktop" and new["lcp"] > 500:
        failed.append(f"{where}: LCP {new['lcp']:.0f} ms (cap 500)")
    if new["cls"] > 0.01:
        failed.append(f"{where}: CLS {new['cls']:.3f} over load + full scroll (cap 0.01)")
    if new["scroll_max"] >= 250 or new["scroll_max"] > base["scroll_max"] + 50:
        failed.append(f"{where}: longest frame while scrolling {new['scroll_max']:.0f} ms "
                      f"(cap < 250 and baseline {base['scroll_max']:.0f} + 50)")
    if new["scroll_long"] > base["scroll_long"] + 2:
        failed.append(f"{where}: {new['scroll_long']:.0f} frames >= 50 ms while scrolling "
                      f"(baseline {base['scroll_long']:.0f} + 2)")
    if prof.get("trace") and new["over33"] > 5:
        failed.append(f"{where}: {new['over33']:.1f}% of frames over 33.4 ms while scrolling (cap 5%)")
    if prof.get("clicks"):
        for k in ("click Copy", "click OS switch", "click summary"):
            if new[k] > 100:
                failed.append(f"{where}: {k} -> next paint {new[k]:.0f} ms (cap 100)")
        if new["copied"] is None or new["copied"] > 150:
            failed.append(f"{where}: Copy click -> \"Copied\" shown {new['copied']} ms (cap 150)")
    return failed


def perf_report(name: str, result: dict) -> list[str]:
    def fmt(r: dict | None) -> str:
        if r is None:
            return "no valid run"
        parts = [f"LCP {r['lcp']:.0f}", f"CLS {r['cls']:.3f}", f"load LoAF max {r['load_max']:.0f}",
                 f"blocking {r['load_blocking']:.0f}", f"scroll LoAF max {r['scroll_max']:.0f}",
                 f">=50ms {r['scroll_long']:.0f}", f"idle {r['idle']:.1f}"]
        if "raster_ms" in r:
            parts += [f">33.4ms {r['over33']:.1f}%", f"raster {r['raster_ms']:.0f}", f"paint {r['paint_ms']:.0f}",
                      f"dropped {r['dropped']:.0f}", f"checker {r['checker']:.0f}"]
        if "copied" in r:
            ms = lambda v: "<16" if v < 16 else f"{v:.0f}"  # Event Timing reports from 16 ms
            parts += [f"click->paint Copy {ms(r['click Copy'])}", f"OS switch {ms(r['click OS switch'])}",
                      f"summary {ms(r['click summary'])}",
                      f"Copied shown {'never' if r['copied'] is None else round(r['copied'])}"]
        return ", ".join(parts) + f" ms (median of {r['runs']})"
    return [f"report: perf {name} {site}: {fmt(result.get(site))}" for site in ("new", "baseline") if site in result]


def run_perf(base: str, baseline: str) -> tuple[list[str], list[str]]:
    from playwright.sync_api import sync_playwright

    failed, reports = [], []
    with sync_playwright() as p:
        for name, prof in PERF_PROFILES.items():
            result = perf_profile(p, name, prof, {"new": base, "baseline": baseline}, PERF_RUNS)
            reports += perf_report(name, result)
            failed += perf_gates(name, prof, result["new"], result["baseline"])
    return failed, reports


def run_perf_self_test(base: str, baseline: str) -> list[str]:
    """Clean home passes the desktop gates, each PERF_FAULTS entry fails them (1 run each)."""
    from playwright.sync_api import sync_playwright

    failed = []
    name, prof = "desktop", PERF_PROFILES["desktop"]
    with sync_playwright() as p:
        ref = perf_profile(p, name, prof, {"baseline": baseline}, 1)["baseline"]
        clean = perf_gates(name, prof, perf_profile(p, name, prof, {"new": base}, 1)["new"], ref)
        print(f"self-test: clean home: {'FAILS - ' + clean[0] if clean else 'passes'}")
        if clean:
            failed.append(f"self-test: clean home fails its perf checks: {clean[0]}")
        for what, html in PERF_FAULTS:
            caught = perf_gates(name, prof, perf_profile(p, name, prof, {"new": base}, 1, html)["new"], ref)
            print(f"self-test: {what}: {'caught - ' + caught[0] if caught else 'NOT CAUGHT'}")
            if not caught:
                failed.append(f"self-test: injected fault not caught: {what}")
    return failed


# ---- --lighthouse: pinned Lighthouse against the gzip server ---------------------------------------

LIGHTHOUSE = "lighthouse@12.8.2"
LH_PAGES = [("home", ""), ("research", "research/"), ("article", "research/what-makes-a-good-resume/"),
            ("about", "about/"), ("privacy", "privacy.html"), ("404", "404.html")]
LH_RUNS = 3
LH_PERF = {"mobile": 99, "desktop": 100}   # Performance, median of LH_RUNS
LH_EVERY_RUN = ("accessibility", "best-practices")  # 100 on every run
SEO_EXEMPT = {"canonical"}                  # canonical names https://jobs.enrriquez.com, not localhost
SEO_EXEMPT_404 = {"is-crawlable"}           # 404 is noindex on purpose
LH_OUT = ROOT / ".data" / "site-qa"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def lighthouse_once(url: str, preset: str, out: Path) -> dict | str:
    """One Lighthouse run; the report, or a one-line error."""
    out.unlink(missing_ok=True)
    cmd = ["npx", "-y", LIGHTHOUSE, url, "--quiet", "--output=json", f"--output-path={out}",
           "--chrome-flags=--headless=new",
           "--only-categories=performance,accessibility,best-practices,seo"]
    if preset == "desktop":
        cmd.append("--preset=desktop")
    env = os.environ | ({"CHROME_PATH": CHROME} if Path(CHROME).is_file() else {})
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    if r.returncode or not out.is_file():
        return "lighthouse failed: " + (r.stderr or r.stdout).strip()[-300:]
    report = json.loads(out.read_text())
    if report.get("runtimeError"):
        return "lighthouse: " + report["runtimeError"].get("message", "")[:300]
    return report


def run_lighthouse(base: str) -> tuple[list[str], list[str]]:
    failed, reports = [], []
    LH_OUT.mkdir(parents=True, exist_ok=True)
    for slug, path in LH_PAGES:
        for preset in ("mobile", "desktop"):
            where = f"lighthouse {slug} ({preset})"
            perf = []
            for i in range(LH_RUNS):
                rep = lighthouse_once(base + path, preset, LH_OUT / f"lh-{slug}-{preset}-{i + 1}.json")
                if isinstance(rep, str):
                    failed.append(f"{where}: {rep}")
                    continue
                cats = rep["categories"]
                score = lambda k: round((cats[k]["score"] or 0) * 100)
                perf.append(score("performance"))
                for k in LH_EVERY_RUN:
                    if score(k) < 100:
                        low = [a["id"] for a in cats[k]["auditRefs"] if a["weight"]
                               and (rep["audits"][a["id"]]["score"] or 0) < 1]
                        failed.append(f"{where} run {i + 1}: {k} {score(k)} ({', '.join(low[:6])})")
                exempt = SEO_EXEMPT | (SEO_EXEMPT_404 if slug == "404" else set())
                for a in cats["seo"]["auditRefs"]:
                    audit = rep["audits"][a["id"]]
                    if (audit["scoreDisplayMode"] in ("binary", "numeric") and audit["score"] is not None
                            and audit["score"] < 1 and a["id"] not in exempt):
                        failed.append(f"{where} run {i + 1}: SEO audit {a['id']} fails")
                if i == 0:
                    tbt = rep["audits"]["total-blocking-time"].get("displayValue", "?")
                    reports.append(f"report: {where}: accessibility {score('accessibility')}, best practices "
                                   f"{score('best-practices')}, SEO {score('seo')}, TBT {tbt}")
            if perf:
                mid = median(perf)
                reports.append(f"report: {where}: performance median {mid:g} of {', '.join(map(str, perf))}")
                if mid < LH_PERF[preset]:
                    failed.append(f"{where}: performance median {mid:g} (need {LH_PERF[preset]})")
    return failed, reports


def keep_awake():
    """caffeinate -dimsu for as long as this process lives (macOS); a sleeping screen skews timing."""
    if shutil.which("caffeinate"):
        subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])

def main() -> int:
    args = sys.argv[1:]
    modes = {(): "", ("--engines",): "--engines", ("--self-test",): "--self-test", ("--perf",): "--perf",
             ("--perf", "--self-test"): "--perf --self-test", ("--lighthouse",): "--lighthouse"}
    mode = modes.get(tuple(sorted(args, key=lambda a: a != "--perf")))
    if mode is None:
        print("usage: uv run app/web/qa.py [--engines | --self-test | --perf [--self-test] | --lighthouse]")
        return 2
    timed = mode.startswith("--perf") or mode == "--lighthouse"
    if timed:
        keep_awake()
    watchdog(PERF_LIMIT_S if timed else RUN_LIMIT_S)
    server, base = serve(DOCS)
    servers = [server]
    reports = []
    try:
        if mode.startswith("--perf"):
            old, baseline = serve(baseline_docs())
            servers.append(old)
            if mode == "--perf":
                failed, reports = run_perf(base, baseline)
                if failed:  # retry once before failing: one slow moment on the machine is not the page
                    print(f"perf: {len(failed)} over budget ({failed[0]}) - running once more", flush=True)
                    failed, reports = run_perf(base, baseline)
            else:
                failed = run_perf_self_test(base, baseline)
        elif mode == "--lighthouse":
            failed, reports = run_lighthouse(base)
        elif mode == "--engines":
            failed = run_engines(base)
        elif mode == "--self-test":
            failed = run_self_test(base)
        else:
            failed, reports = run_chrome(base)
    finally:
        for s in servers:
            s.shutdown()
    for line in reports + failed:
        print(line)
    done = {"": "all pages pass", "--engines": "WebKit + Firefox pass", "--self-test": "every injected fault caught",
            "--perf": "perf within budget", "--perf --self-test": "every injected perf fault caught",
            "--lighthouse": f"Lighthouse within budget; reports in {LH_OUT.relative_to(ROOT)}/"}[mode]
    shots = mode in ("", "--engines")
    print(f"{len(failed)} problem(s)" if failed else done,
          f"; screenshots in {SCREENS.relative_to(ROOT)}/" if shots else "", sep="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
