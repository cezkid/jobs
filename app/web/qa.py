# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
"""Check the install site's pages in a real browser: fit, fold, motion states, colours, print.

Serves docs/ on a local port (gzip, like GitHub Pages; 404.html for a missing path), opens every
page (each docs/**/*.html but the mac/ + win/ install scripts) in Google Chrome as a phone (phone
browser name + touch) at 320x640, 360x780, 375x812, 390x844 and as a desktop at 768x1024,
1366x641, 1440x900, 1920x1080 + the jurors' Mac laptop windows 1440x780, 1512x860, 1728x1000 (a page
that reacts to a Mac - html.is-mac, home - at every desktop size again with a Mac browser name), and checks:

- page no wider than the screen (scrollWidth <= clientWidth; a phone's innerWidth grows to fit a
  too-wide page, so it never fails)
- header on one line from 360px up (brand + links side by side; 320px may wrap); fewer than 2
  header parts found = fail, never a silent pass
- 0 console errors + 0 uncaught errors, in every browser context opened below
- home: Copy button ends within 1366x641 (gate; 1366x768 screen minus Chrome's bars), 1280x593
  reported only; page <= 8 screens at 1366x641, <= 9 at 375x812 (owner decision 4, plan-dxn;
  7.12 + 7.90 at the polish base); home also as a narrow desktop window at the 4 phone sizes
  (install line shown); at every size (COMPOSITION): rules on header, footer + main's rows span the
  window, no section h2 cut by the fold, Job 12's ring box above the salary line and (RING) no point of
  its strokes inside the title's text box, install line
  breaks only at spaces, <= 1 framed object in the first screen; FRAMES at 1366x641 + 1440x900: <= 1 framed
  object (.window, .proof, .sheet-lg) wholly or >= 40% on screen at every half-screen scroll step;
  WINDOW_TEXT at 1440x900: every text in the hero window's body >= 17px (A8);
  SHEET_NOTE at every desktop size >= 760 wide: the resume sheet's approval note top within 4px of the new
  line's, old + new lines at the sheet's bullet size (A10);
  AFTER_RULES: the applications + help pair's top rules (first block under each h2) within 1px at every
  desktop size >= 1080 wide; at 768 the two stacked halves >= 48px apart (A11);
  TYPE_TIERS at 1366x641, 1440x900, 1440x780, 1920x1080: every scene h2 is <= 0.8x or >= 1.2x the h1, never
  between (PICK P-c2 role tiers);
  SPACE_RATIO, every page at 1440x900 + 1920x1080: grid gap >= 0.4x the largest h2, side margin >= 0.75x
  the h1, each display heading (>= 48px) >= 0.5x its size clear of the next column (plan-dxn.37);
  MAC_LINE: Mac browser name at 768, 1366x641, 1440x900, 1920x1080 -> the
  install line is one line box; a check whose selector finds 0 elements fails (missing()), never a
  silent pass; at 1440x900 + 1920x1080 (EMPTY_RIGHT) no row of
  main leaves a band > 400px wide + > 200px tall empty right of its content (hub, about, methods too: main as
  one row, a sticky column counted to its parent's bottom); TOC_BESIDE: an article's On this page column
  <= 120px right of its text, <= 400px empty right of the column (A3)

HIT_BOXES, every page at 390x844 (phone, touch) + 1366x1024 (iPad landscape, touch): every visible link + button
but links inside running text and the skip link is >= 44px tall + wide (Apple HIG 44x44pt); HIT_OVERLAP, same
pages + sizes: every header / footer / nav tap box keeps >= 24px of its height uncovered by its neighbours' boxes
(Lighthouse target-size); SCHEME_LIGHT / SCHEME_DARK, home + an article at 1440x900: desk, a link in the page
(ink, the pen underline), navigation + titles (ink), a research folder + the sticky note's face, the hero window's ground + text + marks + bird; CONTRAST_MORE, same pages,
light + dark w/ prefers-contrast: more: footer text = body text, hairlines #767676; PRINT_DARK, home printed from
a dark screen: the window + desk ink on white; NAV_CURRENT, every page at 1366x641: the header's Research link is
underlined thicker than Install on /research/** and the same elsewhere; FOOTER_BOTTOM, every page at
1440x900: the footer ends within 2px of the window's bottom or the page end (404: no blank band under it).
TOC_NARROW, every page with an On this page column at 390x844 (phone) + 1024x768: a visible 'On this page'
summary starting within 1.25 screens (right after the What to do note, which owns the first screen), opened =
a link to every h2; TOC_WIDE at 1440x900 (also in --engines): the
column's links all visible, the first in the first screen, right of the text column; TOC_CURRENT there: the
3rd h2 scrolled to the top -> its link (both lists, only it) aria-current="true" + bold; CRUMBS_ONE_LINE at
360x780 + 390x844 (phone): an article's visible crumbs share one line. STICKY_FIT, every page w/ a side column
(articles, hub, privacy) at 1280x720, 1366x641, 1440x780 + 1440x900: the column shows all of itself - nothing hidden
in its own scroll box, a stuck one no taller than the window. HUB_FOLD, the hub at 1440x900: >= 4
article titles end above y 900. ARTICLE_H1, research pages at 1440x900: the h1 >= 72px (the home page's display scale); HEADLINE_RAG, research pages at 375 (phone), 768, 1440 + 1920 wide: a
two-part title (h1, hub item) never puts the deck's first word on the question's line; RULES_STACKED on every
article page too (privacy + articles, every size).

Every page again at 1366x641 (desktop) + 390x844 (phone):

- reduced motion: document.getAnimations() empty, every mark + the correction's strike finished (MARK_STATE), every dashed
  SVG stroke drawn (DRAWN: stroke-dashoffset 0)
- full motion: PAINT_CONCURRENT <= 3 animations mid-way on background-size / clip-path /
  stroke-dashoffset at every half-screen scroll step from load on; no animation loops forever; once the timed ones end (the opening moment), text
  opacity 1 at every half-screen scroll step; every mark finished once scrolled to mid-screen;
  every dashed stroke drawn after a full scroll; reloaded at the bottom, none above the screen undrawn
- SHEET_REPLAY (home, full motion, view() timelines): the correction's strike + new-line marks still under
  way at cover 10% of the resume figure, all finished by cover 40% (owner decision 1)
- layout boxes (offset rects: transforms don't move them) equal between reduced and full motion
- no JS (CSS still animates: judged once the timed animations end): all text shown
  (opacity 1, visible) + home's Windows install line; NOJS_SCRIPTING: no visible <button> (nothing
  would run it; Chrome w/o JS matches @media (scripting: none)) + home links to its Mac answer (#mac, inside its question)
- forced colours: every mark still paints something its parent doesn't; FORCED_DEL: every <del> keeps
  a line-through or background image, every .bul dot paints (0 of either on home = fail)
- home in print: <= 5 pages (PDF) and the install line shows
- ZOOM_H1, home at 1366x641, 1440x900, 1920x1080: the h1 at 200% zoom (half the viewport, device scale
  2) is >= its size at 100%, in device px (WCAG 1.4.4)
- HOVER, home + hub + one article at 1366x641 (reduced motion): the mouse on each visible a, button +
  summary changes >= 1 visual style of it and newly paints nothing #FFE433; a research folder pulls up
- STATUS, home at 1366x641: after Copy the role=status text is "Copied to the clipboard" and Copy's
  accessible name holds its visible label; after the OS switch the status names the OS shown
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
full: marks + strokes after a full scroll + after a reload at the bottom); TOC_NARROW + TOC_WIDE.
--self-test: injects each FAULTS entry into its page (+ browser name) and exits 1 unless it adds a
failure line its clean page lacks (a new check's fault: a line of that check) and each clean page
passes its gates. Faults: home (Copy below the fold, a hidden mark, a console error, a
wide element, section rules short of the window edge, the Job 12 ring over the salary line, the
install line broken inside the web address (320px desktop window), the closing list hidden (an empty
right half at 1440x900), a second framed object (a boxed note) in the
first screen (1440x900), a scene circle stuck half drawn / undrawn in reduced motion, an opening that runs
long / fades text in / moves 40px / animates the LCP element / replays on reload, a page change
w/o crossfade, an opening played after one, a check finding 0 elements, paint animations piled up,
the Mac line on more lines, two framed objects at once, Copy + OS switch results unannounced / Copy named
by a fixed label, the strike / bullet dots gone in forced colours, Copy shown / the Mac answer link hidden w/o JS,
the h1's vh cap back below 1080px, footer links back to text height on touch), an article (a wide element, a
console error, the Research link plain, links unchanged on hover, On this page rows too tall for a short window),
the hub (a folder that doesn't lift, the labels stuck + clipped on a short window), the
404 (a blank band under its footer); home also gets a hover rule painting the highlighter.
--capture DIR: every page at 1366x641, 1440x900, 1440x780 (Mac), 1920x1080, 390x844 phone, light +
dark, reduced motion: full-page + per-screen shots and DIR/numbers.md (screens long, print pages, h1 +
h2 px per desktop size) - before/after material.

--perf: home timed in Chrome, docs/ vs a frozen copy of the polish base (docs/ at
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

Run from repo root: uv run app/web/qa.py [--engines | --self-test | --perf [--self-test] | --lighthouse |
--capture DIR]
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
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
PHONES = [(320, 640), (360, 780), (375, 812), (390, 844)]
# jurors' Mac laptops (Chrome window on a 13-16" MacBook): 1440x780, 1512x860, 1728x1000
JURORS = [(1440, 780), (1512, 860), (1728, 1000)]
DESKTOPS = [(768, 1024), (1366, 641), (1440, 900), (1920, 1080)] + JURORS
MOTION_SIZES = [((1366, 641), False), ((390, 844), True)]
FOLD = (1366, 641)          # gate: 1366x768 screen minus Chrome's tab + address bars
FOLD_REPORT = (1280, 593)   # report only: 1280x720 screen, same bars
# page-length caps, owner decision 4 (plan-dxn, 2026-10-03); polish base e704f97 measured
# 7.12 screens at 1366x641 and 7.90 at 375x812
DESKTOP_CAP = 8             # home <= 8 screens at 1366x641
PHONE_CAP = 9.0             # home <= 9 screens at 375x812 (phone UA)
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
// sweeps judged finished: marks + the correction's strike (a background line, owner decision 1)
const SWEPT = MARKS + ", .old del";
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
  return [...document.querySelectorAll(SWEPT)].map(el => [el, markState(el)])
    .filter(([, s]) => s && s !== "ok").map(([el, s]) => label(el) + ": " + s);
}"""

# full motion: scroll each mark to mid-screen, let its timed animations end, then judge it
MARKS_SCROLLED = "async () => {" + HELPERS + """
  const bad = [];
  for (const el of document.querySelectorAll(SWEPT)) {
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

# forced colours (B4): every <del> keeps a strike (line-through or a background image), every resume
# bullet dot still paints (a border, or a background other than Canvas); counts for the 0-match rule
FORCED_DEL = "() => {" + HELPERS + """
  const probe = document.createElement("div"); probe.style.background = "Canvas"; document.body.append(probe);
  const canvas = getComputedStyle(probe).backgroundColor; probe.remove();
  const clear = c => /rgba\\(.*, 0\\)$/.test(c) || c === "transparent";
  const dels = [...document.querySelectorAll("del")], buls = [...document.querySelectorAll(".bul")], bad = [];
  for (const el of dels) {
    const s = getComputedStyle(el);
    if (!s.textDecorationLine.includes("line-through") && s.backgroundImage === "none") bad.push("strike gone: " + label(el));
  }
  for (const el of buls) {
    const b = getComputedStyle(el, "::before");
    const border = ["Top", "Right", "Bottom", "Left"].some(k => parseFloat(b["border" + k + "Width"]) > 0 &&
                                                              b["border" + k + "Style"] !== "none");
    if (!border && b.backgroundImage === "none" && (clear(b.backgroundColor) || b.backgroundColor === canvas))
      bad.push("bullet dot gone: " + label(el));
  }
  return {dels: dels.length, buls: buls.length, bad};
}"""

# no JS (B6): visible buttons (none may show: nothing would run them); home's link to the Mac answer
NOJS_SCRIPTING = """() => {
  const shown = el => el.checkVisibility() && el.getBoundingClientRect().width > 0;
  const buttons = [...document.querySelectorAll("button")].filter(shown)
    .map(b => "button" + (b.id ? "#" + b.id : "") + " " + JSON.stringify(b.textContent.trim().replace(/\\s+/g, " ").slice(0, 30)));
  const mac = document.getElementById("mac");
  const answer = !!mac && !!mac.closest("details") && mac.textContent.includes("curl -fsSL");
  return {buttons, answer, link: [...document.querySelectorAll('a[href="#mac"]')].some(shown)};
}"""

# home's composition (critique C1, C3, C4, C5, C10, plan-6zp.30), one line per fault:
# - rules on header, footer + main's rows span the whole window (full-bleed hairlines)
# - no section h2 cut by the fold (wholly inside the first screen or wholly below it)
# - the Job 12 ring's box ends above the salary line's letters
# - the install line breaks only at spaces (never inside the web address)
# - at most one framed object (bordered box > 250x150, layout box: transforms ignored) in the first screen
COMPOSITION = """() => {
  const W = document.documentElement.clientWidth, H = innerHeight, bad = [];
  const ruled = s => ["Top", "Bottom"].some(k => parseFloat(s["border" + k + "Width"]) > 0 &&
    s["border" + k + "Style"] !== "none" && s["border" + k + "Color"] !== "rgba(0, 0, 0, 0)");
  for (const el of document.querySelectorAll("header, footer, main > *")) {
    const r = el.getBoundingClientRect();
    if (r.width && ruled(getComputedStyle(el)) && (r.left > 0.5 || r.right < W - 0.5))
      bad.push(`rule on ${el.tagName.toLowerCase()}.${el.className} spans ${Math.round(r.left)}-${Math.round(r.right)}, window 0-${W}`);
  }
  for (const h of document.querySelectorAll("main section h2")) {
    const r = h.getBoundingClientRect(), top = r.top + scrollY, bottom = r.bottom + scrollY;
    if (top < H && bottom > H) bad.push(`h2 "${h.textContent.trim().slice(0, 30)}" cut by the fold (${Math.round(top)}-${Math.round(bottom)}px, screen ${H}px)`);
  }
  const ring = document.querySelector(".picked svg.ring"), meta = document.querySelector(".picked .meta");
  if (ring && meta && ring.getBoundingClientRect().width) {
    const range = document.createRange(); range.selectNodeContents(meta);
    const over = ring.getBoundingClientRect().bottom - range.getClientRects()[0].top;
    if (over > 0.5) bad.push(`Job 12 ring runs ${over.toFixed(1)}px into the salary line`);
  }
  const line = document.getElementById("line"), text = line && line.firstChild;
  if (text && line.getClientRects().length) {
    let last = null;
    for (let i = 0; i < text.length; i++) {
      const range = document.createRange(); range.setStart(text, i); range.setEnd(text, i + 1);
      const c = range.getClientRects()[0]; if (!c) continue;
      if (last !== null && c.top > last + 2 && text.data[i - 1] !== " " && text.data[i] !== " ")
        bad.push(`install line breaks inside a word: "${text.data.slice(Math.max(0, i - 8), i)}|${text.data.slice(i, i + 8)}"`);
      last = c.top;
    }
  }
  const layoutTop = el => { let y = 0; for (let e = el; e; e = e.offsetParent) y += e.offsetTop; return y; };
  const framed = [...document.querySelectorAll("main *")].filter(el => {
    if (!(el instanceof HTMLElement) || !el.offsetWidth) return false;
    const s = getComputedStyle(el);
    return ["Top", "Right", "Bottom", "Left"].every(k => parseFloat(s["border" + k + "Width"]) >= 1) &&
      el.offsetWidth > 250 && el.offsetHeight > 150;
  }).filter(el => layoutTop(el) < H && layoutTop(el) + el.offsetHeight > 0);
  if (framed.length > 1) bad.push(`${framed.length} framed objects in the first screen: ` +
    framed.map(el => el.tagName.toLowerCase() + "." + el.className + " at " + layoutTop(el) + "px").join(", "));
  return bad;
}"""

# RING (A8, every home size): the Job 12 ring is drawn round the title, never through it - each of 200 points
# along each ring path, widened by half its stroke on each axis (the svg stretches it), lies outside the title's
# text box ("Job 12 - Customer Support Lead"); null = no ring or title found
RING = """() => { const c = document.querySelector(".picked .circled"), paths = [...document.querySelectorAll(".picked svg.ring path")];
  const b = c && c.querySelector("b"); if (!b || !paths.length) return null;
  const range = document.createRange(); range.setStartBefore(b); range.setEnd(c, c.childNodes.length - 1);
  const t = range.getBoundingClientRect(), bad = [];
  for (const p of paths) { const m = p.getScreenCTM(), len = p.getTotalLength(), w = parseFloat(getComputedStyle(p).strokeWidth) / 2;
    const hx = w * Math.hypot(m.a, m.b), hy = w * Math.hypot(m.c, m.d);
    for (let i = 0; i <= 200; i++) { const q = p.getPointAtLength(len * i / 200);
      const x = m.a * q.x + m.c * q.y + m.e, y = m.b * q.x + m.d * q.y + m.f;
      if (x + hx > t.left && x - hx < t.right && y + hy > t.top && y - hy < t.bottom) {
        bad.push(`ring stroke${p.classList.length ? " ." + p.classList[0] : ""} crosses the Job 12 title at ${Math.round(x)},${Math.round(y)}px (title ${Math.round(t.left)}-${Math.round(t.right)} x ${Math.round(t.top)}-${Math.round(t.bottom)})`);
        break; } } }
  return bad; }"""

# WINDOW_TEXT (A8, home at 1440x900): the hero window read at a glance - every text in its body >= 17px
WINDOW_TEXT_AT = (1440, 900)
WINDOW_TEXT_MIN = 17
WINDOW_TEXT = """() => [...document.querySelectorAll(".hero .window .today *")].filter(el =>
  [...el.childNodes].some(n => n.nodeType === 3 && n.data.trim()) && el.getClientRects().length)
  .map(el => [el.tagName.toLowerCase() + (el.className ? "." + el.className : ""), parseFloat(getComputedStyle(el).fontSize)])"""

# SHEET_NOTE (A10, home >= 760 wide): the approval note sits on the corrected line's row (tops within 4px) and
# the old + new lines are set at the sheet's bullet size; [note top, new top, new px, old px, bullet px] or null
SHEET_NOTE_W = 760
SHEET_NOTE_PX = 4
SHEET_NOTE = """() => { const q = s => document.querySelector(".sheet-lg " + s);
  const ok = q(".margin.ok"), nw = q(".new"), od = q(".old"), bul = q(".bul:not(.old):not(.new)");
  if (!ok || !nw || !od || !bul) return null;
  const px = el => parseFloat(getComputedStyle(el).fontSize);
  return [ok.getBoundingClientRect().top, nw.getBoundingClientRect().top, px(nw), px(od), px(bul)]; }"""

# SHEET_REPLAY (owner decision 1, full motion where view() timelines run): the correction (strike + the new
# line's marks) replays on the .proof view timeline - at cover SHEET_REPLAY_EARLY one of them is still
# under way, by cover SHEET_REPLAY_DONE every one is finished; [early unfinished, late unfinished] or null
SHEET_REPLAY_EARLY = 0.10
SHEET_REPLAY_DONE = 0.40
SHEET_REPLAY = "async () => {" + HELPERS + """
  if (!CSS.supports("animation-timeline: view()")) return [[], []];
  const fig = document.querySelector(".proof"), els = [...document.querySelectorAll(".sheet-lg .old del, .sheet-lg .new mark")];
  if (!fig || els.length < 3) return null;
  const top = fig.getBoundingClientRect().top + scrollY, span = innerHeight + fig.offsetHeight;
  const at = async p => { scrollTo(0, Math.ceil(top - innerHeight + p * span) + 1); await frames();
    return els.filter(el => el.getAnimations().some(a => { const t = a.effect.getComputedTiming();
      return t.progress === null || t.progress < 0.999; }) || markState(el) !== "ok").map(label); };
  const out = [await at(""" + str(SHEET_REPLAY_EARLY) + """), await at(""" + str(SHEET_REPLAY_DONE) + """)];
  scrollTo(0, 0);
  return out;
}"""

# AFTER_RULES (A11, home): the two halves' first block under the h2 (its top rule) shares one line at >= 1080;
# at tablet width the stacked halves keep a gap; [[rule top per half], gap from half 1's foot to half 2] or null
AFTER_RULES_W = 1080
AFTER_RULES_PX = 1
AFTER_GAP_AT = (768, 1024)
AFTER_GAP_MIN = 48
AFTER_RULES = """() => { const h = [...document.querySelectorAll(".after .half")];
  const r = h.map(el => el.querySelector(":scope > :not(h2)")).filter(Boolean);
  if (h.length !== 2 || r.length !== 2) return null;
  return [r.map(el => el.getBoundingClientRect().top),
          h[1].getBoundingClientRect().top - h[0].getBoundingClientRect().bottom]; }"""

# TYPE_TIERS (PICK P-c2, home): each scene h2's size over the h1's is a tier - statements <= 0.8x, labels >= 1.2x,
# nothing in between; [[h2 text, ratio]] or null (no h1 / no scene h2)
TYPE_TIERS_AT = [(1366, 641), (1440, 900), (1440, 780), (1920, 1080)]
TYPE_TIERS_LOW, TYPE_TIERS_HIGH = 0.8, 1.2
TYPE_TIERS = """() => { const h1 = document.querySelector("h1"), h2s = [...document.querySelectorAll("main section.scene h2")];
  if (!h1 || !h2s.length) return null;
  const px = el => parseFloat(getComputedStyle(el).fontSize);
  return h2s.map(h => [h.textContent.trim().slice(0, 30), px(h) / px(h1)]); }"""

# SPACE_RATIO (plan-dxn.37, owner at S1: "such large font and tiny gutter"), every page at SPACE_AT: the
# grid gap (--gutter, read off a probe) >= 0.4x the page's largest h2, the page's side margin (main's content
# box) >= 0.75x the h1, and each display heading (>= 48px) keeps >= 0.5x its size clear to the next column
# (a sibling grid item level with one of its line boxes). [gap, h2, side, h1, [[text, px, clear]]] or null
SPACE_AT = [(1440, 900), (1920, 1080)]
SPACE_GAP, SPACE_SIDE, SPACE_CLEAR, SPACE_DISPLAY = 0.4, 0.75, 0.5, 48
SPACE_RATIO = """() => {
  const main = document.querySelector("main"), h1 = document.querySelector("main h1");
  if (!main || !h1) return null;
  const px = el => parseFloat(getComputedStyle(el).fontSize), shown = el => el.getBoundingClientRect().width > 0;
  const probe = document.createElement("div"); probe.style.cssText = "display: grid; column-gap: var(--gutter)";
  document.body.append(probe); const gap = parseFloat(getComputedStyle(probe).columnGap); probe.remove();
  const h2s = [...main.querySelectorAll("h2")].filter(shown), h2 = Math.max(0, ...h2s.map(px));
  const box = main.matches(".grid, .wrap") ? main : main.querySelector(".grid, .wrap");
  if (!box) return null;
  const r = box.getBoundingClientRect(), s = getComputedStyle(box);
  const side = Math.min(r.left + parseFloat(s.paddingLeft), innerWidth - r.right + parseFloat(s.paddingRight));
  const near = [];
  for (const h of [h1, ...h2s].filter(h => px(h) >= """ + str(SPACE_DISPLAY) + """)) {
    let item = h;
    while (item.parentElement && item.parentElement !== document.body) {
      const g = getComputedStyle(item.parentElement);
      if (g.display.includes("grid") && g.gridTemplateColumns.split(" ").length > 1) break;
      item = item.parentElement;
    }
    if (!item.parentElement || item.parentElement === document.body) continue;
    const range = document.createRange(); range.selectNodeContents(h);
    const lines = [...range.getClientRects()].filter(l => l.width > 1);
    let clear = Infinity;
    for (const sib of item.parentElement.children) {
      if (sib === item || !shown(sib) || getComputedStyle(sib).position === "absolute") continue;
      const b = sib.getBoundingClientRect();
      for (const l of lines) {
        if (Math.min(l.bottom, b.bottom) - Math.max(l.top, b.top) < 2) continue;
        clear = Math.min(clear, b.left >= l.left ? b.left - l.right : l.left - b.right);
      }
    }
    if (clear < Infinity) near.push([h.textContent.trim().slice(0, 30), px(h), clear]);
  }
  return [gap, h2, side, px(h1), near]; }"""

# empty right halves (BAND_AT): per row of main, 4px slices from its first content line to its last; a run
# of slices whose rightmost content (text line boxes, svg/img/button, boxes with a border or background)
# ends more than BAND_W px short of the row's content edge, taller than BAND_H px = a band left empty
BAND_AT = [(1440, 900), (1920, 1080)]  # 1920 too: bigger display type wraps to more lines
BAND_W, BAND_H = 400, 200
# hub, about, methods: main itself is the one row (their columns are main's children); a sticky element
# (methods' On this page) stays beside the text, so it counts down to its parent's bottom
WIDE_PAGES = {"research/index.html", "about/index.html", "research/methods/index.html", "privacy.html", "terms.html", "404.html"}
EMPTY_RIGHT = """(rows) => {
  const out = [];
  for (const row of document.querySelectorAll(rows)) {
    const box = row.getBoundingClientRect(); if (!box.height) continue;
    const s = getComputedStyle(row), left = box.left + parseFloat(s.paddingLeft), right = box.right - parseFloat(s.paddingRight);
    const rects = [];
    for (const el of row.querySelectorAll("*")) {
      const c = getComputedStyle(el);
      if (c.visibility === "hidden" || parseFloat(c.opacity) === 0) continue;
      // a display heading (>= 48px) counts as its whole block: the rag of its last line is type, not an
      // empty half (closing line at 1920, 2026-10-04)
      if (/^h[1-3]$/.test(el.localName) && parseFloat(c.fontSize) >= 48) {
        rects.push(el.getBoundingClientRect()); continue;
      }
      if ([...el.childNodes].some(n => n.nodeType === 3 && n.data.trim())) {
        const r = document.createRange(); r.selectNodeContents(el);
        rects.push(...[...r.getClientRects()].filter(q => q.width > 2 && q.height > 2));
      }
      if (["svg", "img", "button"].includes(el.localName) || parseFloat(c.borderLeftWidth) > 0 ||
          parseFloat(c.borderRightWidth) > 0 || c.backgroundColor !== "rgba(0, 0, 0, 0)" || c.position === "sticky") {
        const q = el.getBoundingClientRect(); if (!(q.width > 2 && q.height > 2)) continue;
        rects.push(c.position === "sticky" ? {top: q.top, right: q.right, bottom: el.parentElement.getBoundingClientRect().bottom} : q);
      }
    }
    if (!rects.length) continue;
    const top = Math.min(...rects.map(q => q.top)), bottom = Math.max(...rects.map(q => q.bottom));
    let run = 0, start = 0, narrow = Infinity, worst = null;
    for (let y = top; y < bottom; y += 4) {
      const hit = rects.filter(q => q.top < y + 4 && q.bottom > y);
      const empty = right - (hit.length ? Math.max(...hit.map(q => q.right)) : left);
      if (empty <= BAND_W) { run = 0; continue; }
      if (!run) { start = y; narrow = Infinity; }
      run += 4; narrow = Math.min(narrow, empty);
      if (run > BAND_H && (!worst || run > worst[1])) worst = [Math.round(narrow), run, Math.round(start + scrollY)];
    }
    if (worst) out.push(`${row.localName}.${row.className.trim().split(/\\s+/).join(".")}: ${worst[0]}x${worst[1]}px ` +
                        `left empty right of its content at y ${worst[2]} (cap BAND_WxBAND_H)`);
  }
  return out;
}""".replace("BAND_W", str(BAND_W)).replace("BAND_H", str(BAND_H))
# RULES_STACKED (privacy, every size): two horizontal rules (a border edge > 100px wide) overlapping side by
# side, <= RULE_GAP px apart with no text line between them = a double rule (A19); every article page too
# (a top note's rule over On this page or the next h2)
RULES_PAGES = {"privacy.html"}
RULE_GAP = 60
RULES_STACKED = """() => {
  const main = document.querySelector("main"); if (!main) return null;
  const rules = [], lines = [];
  for (const el of main.querySelectorAll("*")) {
    const c = getComputedStyle(el), q = el.getBoundingClientRect();
    if (c.display === "none" || c.visibility === "hidden") continue;
    // rules: border edges over 100px wide; text: any line, a short link's included
    if (q.width > 100 && parseFloat(c.borderTopWidth) > 0 && c.borderTopStyle !== "none") rules.push({y: q.top, l: q.left, r: q.right, el});
    if (q.width > 100 && parseFloat(c.borderBottomWidth) > 0 && c.borderBottomStyle !== "none") rules.push({y: q.bottom, l: q.left, r: q.right, el});
    if ([...el.childNodes].some(n => n.nodeType === 3 && n.data.trim())) {
      const r = document.createRange(); r.selectNodeContents(el);
      lines.push(...[...r.getClientRects()].filter(q => q.width > 2 && q.height > 2));
    }
  }
  const name = el => el.localName + (el.className ? "." + String(el.className).trim().split(/\\s+/).join(".") : "");
  const out = [];
  for (const a of rules) for (const b of rules) {
    const gap = b.y - a.y, l = Math.max(a.l, b.l), r = Math.min(a.r, b.r);
    if (gap <= 2 || gap > RULE_GAP || r - l <= 100) continue;
    if (lines.some(t => t.left < r && t.right > l && (t.top + t.bottom) / 2 > a.y && (t.top + t.bottom) / 2 < b.y)) continue;
    out.push(`${name(a.el)} rule at y ${Math.round(a.y + scrollY)} then ${name(b.el)} rule ${Math.round(gap)}px below, ` +
             `no text between`);
  }
  return out;
}""".replace("RULE_GAP", str(RULE_GAP))
# ARTICLE_H1 (A3), research pages at 1440x900: the h1 on the home page's display scale, >= H1_MIN px
H1_MIN = 72
H1_SIZE = "() => { const h = document.querySelector('main h1'); return h ? parseFloat(getComputedStyle(h).fontSize) : null; }"
# HUB_FOLD (A16), the hub at 1440x900: >= HUB_FOLD_MIN article titles (link boxes, deck included) end above the
# window's bottom - the method lines + labels beside them, not over the list
HUB_FOLD_MIN = 4
HUB_FOLD = "() => [...document.querySelectorAll('main .list li > h2 > a')].map(a => a.getBoundingClientRect().bottom)"
# STICKY_FIT, every page w/ a side column at laptop sizes (>= 1280 wide: the columns show): each visible side
# column shows all of itself - nothing hidden in its own scroll box (the longest On this page hid 88px at
# 1366x641: on a Mac the last entries just weren't there, Windows drew a 2nd scrollbar), and a stuck one is no
# taller than the window below its top offset (its end out of reach). [class, position, px hidden, px over]
STICKY_AT = [(1280, 720), (1366, 641), (1440, 780), (1440, 900)]
STICKY_SIDES = "main .toc, main .labels, main .summary"
STICKY_FIT = """() => [...document.querySelectorAll("STICKY_SIDES")].filter(el => el.checkVisibility()
    && el.getBoundingClientRect().height > 0).map(el => { const cs = getComputedStyle(el);
  return [el.className.split(" ").pop(), cs.position, el.scrollHeight - el.clientHeight,
          Math.round(el.getBoundingClientRect().height + (parseFloat(cs.top) || 0) - innerHeight)]; })""".replace(
    "STICKY_SIDES", STICKY_SIDES)
# HEADLINE_RAG (A4), research pages at 375/768/1440/1920: in a two-part title (the h1, a hub item) split at the
# first "? " / ": ", the deck's first word never shares a line with the question's last word
RAG_AT = [((375, 812), True), ((768, 1024), False), ((1440, 900), False), ((1920, 1080), False)]
HEADLINE_RAG = """() => {
  if (!document.querySelector("main h1")) return null;
  const out = [];
  for (const el of document.querySelectorAll("main h1, main .list a")) {
    const text = el.textContent, m = /[?:] (?=\\S)/.exec(text); if (!m) continue;
    const at = i => { const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n, seen = 0;
      while ((n = w.nextNode())) { if (i < seen + n.data.length) { const r = document.createRange();
        r.setStart(n, i - seen); r.setEnd(n, i - seen + 1); return r.getBoundingClientRect(); } seen += n.data.length; } };
    const end = at(m.index), start = at(m.index + 2);
    // same line: either glyph's middle inside the other's box (a smaller deck sits lower on a shared line)
    const mid = q => (q.top + q.bottom) / 2, inside = (y, q) => y > q.top && y < q.bottom;
    if (end && start && (inside(mid(start), end) || inside(mid(end), start)))
      out.push(`${el.localName}: "${text.slice(m.index + 2).split(" ")[0]}" ends the line "${text.slice(0, m.index + 1)}" sits on`);
  }
  return out;
}"""
# TOC_BESIDE (A3, critique K6), wide article: the On this page column sits <= TOC_GAP px right of the text
# (pushed to the window's edge it was 297px off at 1440) and leaves <= BAND_W px empty right of itself
# (not one 68ch column alone); null = no visible column
TOC_GAP = 120
TOC_BESIDE = """() => { const t = document.querySelector("main nav.toc"), p = document.querySelector("main article p");
  if (!t || !p || !t.getBoundingClientRect().width) return null;
  const m = document.querySelector("main"), s = getComputedStyle(m), edge = m.getBoundingClientRect().right - parseFloat(s.paddingRight);
  const r = t.getBoundingClientRect(); return [r.left - p.getBoundingClientRect().right, edge - r.right]; }"""

# MAC_LINE (A6, a gate since plan-dxn.3): home under MAC_UA shows the Mac line
# as ONE line box at these sizes; null = no #line
MAC_LINE_AT = [(768, 1024), (1366, 641), (1440, 900), (1920, 1080)]
LINE_BOXES = """() => { const l = document.getElementById("line"); if (!l) return null;
  const r = document.createRange(); r.selectNodeContents(l);
  return [l.textContent.trim(), new Set([...r.getClientRects()].filter(q => q.width > 0)
    .map(q => Math.round(q.top))).size]; }"""

# PAINT_CONCURRENT (gate, full motion): at every half-screen scroll step, animations mid-way (0 < progress
# < 1) on a paint property (background-size, clip-path, stroke-dashoffset) - <= PAINT_CAP at once
# HIT_BOXES (B9): phone at 390x844 (touch => pointer: coarse), every visible link + button but links inside
# running text (WCAG 2.5.8 exempts those) and the skip link (shown on keyboard focus only): >= 44px tall and, since
# the Apple HIG review (2026-10-07: 44x44pt), >= 44px wide; again on a wide touch screen (TOUCH_WIDE, iPad landscape)
HIT_MIN = 44
TOUCH_WIDE = (1366, 1024)
HIT_BOXES = """() => { const out = [];
  for (const el of document.querySelectorAll("a, button")) {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (!r.width || !r.height || cs.visibility !== "visible" || el.classList.contains("skip")) continue;
    const inText = !el.closest("header, footer, nav") && el.tagName === "A"
      && [...el.parentElement.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!inText) out.push([el.tagName.toLowerCase() + " " + JSON.stringify(el.textContent.trim().slice(0, 40)), r.height, r.width]);
  }
  return out; }"""
# HIT_OVERLAP (G1): same pages + size, the links + buttons in header, footer and nav: each keeps >= 24px of its
# height (WCAG 2.5.8 floor) not covered by its neighbours' boxes (Lighthouse target-size reads a covered strip as
# obscured: footer rows 35px apart w/ 53px hit boxes left Research 20.4px -> accessibility 95 on phones)
HIT_FREE = 24
HIT_OVERLAP = """() => { const els = [...document.querySelectorAll("header a, header button, footer a, nav a")]
    .filter(el => el.checkVisibility({visibilityProperty: true}) && !el.classList.contains("skip"))
    .map(el => [el.textContent.trim().slice(0, 30), el.getBoundingClientRect()]), out = [];
  for (const [name, r] of els) {
    const cut = els.filter(([, q]) => q !== r && Math.min(r.right, q.right) - Math.max(r.left, q.left) > 1)
      .map(([n, q]) => [n, Math.max(r.top, q.top), Math.min(r.bottom, q.bottom)]).filter(([, t, b]) => b - t > 1)
      .sort((x, y) => x[1] - y[1]);
    let covered = 0, end = r.top;
    for (const [, t, b] of cut) { if (b > end) { covered += b - Math.max(t, end); end = b; } }
    if (r.height - covered < HIT_FREE) out.push([name, cut.map(c => c[0]), r.height - covered]);
  }
  return [els.length, out]; }""".replace("HIT_FREE", str(HIT_FREE))
# NAV_CURRENT (B12): the header's Research link is thicker-underlined on /research/** only (vs Install)
NAV_CURRENT = """() => { const t = s => { const a = document.querySelector(s);
    return a ? parseFloat(getComputedStyle(a).textDecorationThickness) || 0 : null; };
  return [t('.links a[href="/research/"]'), t('.links a[href="/#install"]')]; }"""
# TOC_NARROW (B2): every page with an On this page column, at 390x844 (phone) + 1024x768: a visible summary
# "On this page" starting within TOC_NARROW_SCREENS screens - right after the What to do note, which holds the
# first screen w/ the answer (owner 2026-10-07, plan-ngk; was: inside the first screen); opened, its visible
# links = every h2 of the page, in order.
# TOC_WIDE (B2/D21), 1440x900, Chrome + WebKit + Firefox: the column's links all visible, the first in the
# first screen, right of the text column, and again = every h2
TOC_NARROW_AT = [((390, 844), True), ((1024, 768), False)]
TOC_NARROW_SCREENS = 1.25
TOC_WIDE_AT = (1440, 900)
TOC_HEADS = """() => [...document.querySelectorAll("main article h2[id]")].map(h => "#" + h.id)"""
# sel -> null (none) or {text, shown, top, bottom, left of first link?} for the first match
TOC_BOX = """sel => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect();
  return {text: el.textContent.trim().split("\\n")[0], shown: el.checkVisibility({visibilityProperty: true}) && r.width > 0
          && r.height > 0, top: r.top, bottom: r.bottom, left: r.left}; }"""
TOC_LINKS = """sel => [...document.querySelectorAll(sel)].filter(a => { const r = a.getBoundingClientRect();
  return a.checkVisibility({visibilityProperty: true}) && r.width > 0 && r.height > 0 && r.right <= innerWidth; })
  .map(a => a.getAttribute("href"))"""
# TOC_CURRENT (A23), with TOC_WIDE: the 3rd h2 scrolled to the top -> its link, and only it, aria-current="true"
# in both lists, set in ink (bold, not the other links' weight). Read 400 ms after the scroll (IO calls back next frame)
TOC_CURRENT = """i => { const h = document.querySelectorAll("main article h2[id]")[i]; if (!h) return null;
  h.scrollIntoView(); return new Promise(r => setTimeout(() => r({want: "#" + h.id,
    got: [...document.querySelectorAll(".toc a[aria-current=true], .toc-mini a[aria-current=true]")]
      .map(a => [a.closest("nav").className, a.getAttribute("href"), getComputedStyle(a).fontWeight]),
    plain: getComputedStyle(document.querySelector(".toc a:not([aria-current])")).fontWeight}), 400)); }"""
# CRUMBS_ONE_LINE (A20), articles at 360 + 390 wide: the breadcrumb's visible crumbs share one line
CRUMBS_AT = [(360, 780), (390, 844)]
CRUMBS_TOPS = """() => [...document.querySelectorAll("article .crumbs li")].filter(li => li.getBoundingClientRect().width > 1)
  .map(li => Math.round(li.getBoundingClientRect().top))"""
# FOOTER_BOTTOM (C2/short pages): at 1440x900 the footer ends within 2px of the window's bottom or the page end
FOOTER_BOTTOM_AT = (1440, 900)
FOOTER_BOTTOM = """() => { const f = document.querySelector("footer"); if (!f) return null;
  return [f.getBoundingClientRect().bottom + scrollY,
          Math.max(innerHeight, document.documentElement.scrollHeight)]; }"""
# HOVER (A5): home, hub + one article at 1366x641, reduced motion (hover changes land at once): the mouse on
# each visible a / button / summary changes >= 1 visual style of it (an underline thickness on a box with no
# underline doesn't count) and newly paints nothing #FFE433 (hover is ink, never the highlighter); a research
# folder (home pick, hub item, Keep reading) pulls up. Elements above the page (the skip link) are keyboard-only: skipped
HOVER_PAGES = ["index.html", "research/index.html", "research/what-makes-a-good-resume/index.html"]
HOVER_SELECTOR = "a, button, summary"
HOVER_MARK = "rgb(255, 228, 51)"
# [i] -> null (hidden / above the page) or {what, x, y (client point on its first line box), style, rule}
HOVER_STATE = """i => { const el = document.querySelectorAll("a, button, summary")[i];
  if (!el.checkVisibility({visibilityProperty: true}) || el.getBoundingClientRect().bottom + scrollY <= 0) return null;
  const cs = getComputedStyle(el), style = {};
  for (const p of ["textDecorationLine", "textDecorationThickness", "textDecorationColor", "textUnderlineOffset",
                   "borderTopWidth", "borderTopColor", "borderBottomWidth", "borderBottomColor", "outlineStyle",
                   "outlineWidth", "outlineColor", "color", "backgroundColor", "backgroundImage", "backgroundSize",
                   "transform", "opacity", "boxShadow"]) style[p] = cs[p];
  const li = el.closest(".picks > li, .list > li, .more li:has(> p)");
  const q = el.getClientRects()[0];
  return {what: el.tagName.toLowerCase() + " " + JSON.stringify(el.textContent.trim().slice(0, 40)),
          x: q.left + q.width / 2, y: q.top + q.height / 2, style,
          rule: li && li.querySelector("a") === el ? getComputedStyle(li).transform : null}; }"""
PAINT_CAP = 3
PAINT_CONCURRENT ="async () => {" + HELPERS + """
  const PAINT = ["backgroundSize", "clipPath", "strokeDashoffset"];
  const paints = a => { try { return a.effect.getKeyframes().some(k => PAINT.some(p => p in k)); }
                        catch { return false; } };
  const midway = a => { if (a.playState !== "running" || !a.effect) return false;
    const t = a.effect.getComputedTiming(); return t.progress !== null && t.progress > 0 && t.progress < 1; };
  let worst = [0, 0, []];
  const step = Math.max(1, Math.floor(innerHeight / 2));
  for (let y = 0; y <= document.documentElement.scrollHeight - innerHeight + step; y += step) {
    scrollTo(0, y);
    await frames();
    const now = document.getAnimations().filter(a => paints(a) && midway(a));
    if (now.length > worst[0]) worst = [now.length, scrollY,
      now.map(a => (a.animationName || "animation") + " on " + label(a.effect.target)).slice(0, 6)];
  }
  scrollTo(0, 0);
  return worst;
}"""

# FRAMES (gate; passed at the polish base): framed objects (outermost .window, .proof,
# .sheet-lg) wholly or >= 40% inside the screen at every half-screen step - <= 1 at once; null = none found
FRAMES_AT = [(1366, 641), (1440, 900)]
ZOOM_AT = [(1366, 641), (1440, 900), (1920, 1080)]  # ZOOM_H1: 200% zoom = half the viewport at 2x
FRAMED = "async () => {" + HELPERS + """
  const all = [...document.querySelectorAll(".window, .proof, .sheet-lg")];
  const objs = all.filter(el => !all.some(o => o !== el && o.contains(el)));
  if (!objs.length) return null;
  const bad = [];
  const step = Math.max(1, Math.floor(innerHeight / 2));
  for (let y = 0; y <= document.documentElement.scrollHeight - innerHeight + step; y += step) {
    scrollTo(0, y);
    await frames();
    const inside = objs.filter(el => { const r = el.getBoundingClientRect();
      const seen = Math.min(r.bottom, innerHeight) - Math.max(r.top, 0);
      return r.height > 0 && (seen >= r.height - 0.5 || seen >= 0.4 * r.height); });
    if (inside.length > 1) bad.push("y=" + scrollY + " " + inside.length + " framed objects: " +
      inside.map(el => el.tagName.toLowerCase() + "." + el.className).join(", "));
  }
  scrollTo(0, 0);
  return bad;
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


# self-test faults: (page, what, html injected before </body>, check kind that must fail[, browser name])
HOME = "index.html"
ARTICLE = "research/what-makes-a-good-resume/index.html"
FAULTS = [
    (HOME, "Copy below the fold", "<style>#copy { margin-top: 900px; }</style>", "layout"),
    (HOME, "phone Send button too low", "<style>.send { margin-top: 400px; }</style>", "phone"),
    (HOME, "hidden mark", "<style>mark { opacity: 0; }</style>", "motion"),
    (HOME, "console error", "<script>console.error('qa self-test fault')</script>", "layout"),
    (HOME, "wide element", '<div style="width: 3000px; height: 1px"></div>', "layout"),
    (HOME, "section rules stop at the column edge", "<style>.grid { max-width: 1320px; margin: 0 auto; }</style>",
     "layout"),
    (HOME, "Job 12 ring over the salary line", "<style>.slip .ring { bottom: -20px; height: calc(100% + 27px); }"
     "</style>", "layout"),
    (HOME, "install line broken inside the web address", "<style>.command code { overflow-wrap: anywhere "
     "!important; font-size: 0.9375rem !important; }</style>", "narrow"),
    (HOME, "closing list gone: right half empty", "<style>.next { display: none !important; }</style>", "wide"),
    (HOME, "second framed object in the first screen", "<style>.need { border: 1px solid; min-height: 160px; }</style>",
     "wide"),
    (HOME, "opening runs 4 s", "<style>.today mark { animation-duration: 4s !important; }</style>", "opening"),
    (HOME, "opening fades text in", "<style>@keyframes qa-fade { from { opacity: 0; } } "
     "html:not(.seen) .job { animation: qa-fade 1s both; }</style>", "opening"),
    (HOME, "opening moves the window 40px", "<style>@keyframes qa-lift { from { transform: translateY(40px); } } "
     "html:not(.seen) .window { animation: qa-lift 1s both; }</style>", "opening"),
    (HOME, "LCP element animated", "<style>@keyframes qa-nudge { from { transform: translateY(4px); } } "
     "html:not(.seen) h1 { animation: qa-nudge 1s both; }</style>", "opening"),
    (HOME, "scene circle stuck half drawn", "<style>@keyframes qa-stuck { to { stroke-dashoffset: 40; } } "
     "@media (prefers-reduced-motion: no-preference) { .margin.ok .ring { animation: qa-stuck 1s linear both "
     "!important; animation-timeline: view() !important; } }</style>", "motion"),
    (HOME, "scene circle undrawn in reduced motion", "<style>.submit svg { stroke-dashoffset: 60 !important; }</style>",
     "motion"),
    (HOME, "opening replays on reload", '<script>document.documentElement.classList.remove("seen")</script>', "opening"),
    (HOME, "page change w/o crossfade", "<style>@view-transition { navigation: none; }</style>", "transition"),
    (HOME, "opening plays after a page change", '<script>addEventListener("pagereveal", () => '
     'document.documentElement.classList.remove("seen"))</script>', "transition"),
    (ARTICLE, "wide element on an article", '<div style="width: 3000px; height: 1px"></div>', "layout"),
    (ARTICLE, "console error on an article", "<script>console.error('qa self-test fault')</script>", "layout"),
    (HOME, "0 matches: Job 12 no longer picked (ring check would see nothing)",
     "<script>document.querySelector('.picked').classList.remove('picked')</script>", "layout"),
    (HOME, "RING: the Job 12 ring slid onto the title", "<style>.slip .ring { left: 6px !important; }</style>", "layout"),
    (HOME, "WINDOW_TEXT: the window's why lines back to 15px", "<style>.why { font-size: 0.9375rem !important; }</style>",
     "wide"),
    (HOME, "SHEET_NOTE: approval note back beside the struck line", "<style>.sheet-lg .margin.ok { position: relative; "
     "top: -2.4em; }</style>", "layout"),
    (HOME, "AFTER_RULES: the help table's rule drops below the names' rule", "<style>.half { display: block "
     "!important; } .half + .half h2 { margin-bottom: 1.2em !important; }</style>", "wide"),
    (HOME, "AFTER_RULES: stacked halves jammed together at tablet width", "<style>.after { row-gap: 20px !important; }"
     "</style>", "tablet"),
    (HOME, "SHEET_NOTE: the new line back at 15px", "<style>.sheet-lg .new { font-size: 0.9375rem !important; }</style>",
     "layout"),
    (HOME, "SPACE_RATIO: gap forced back to 32px", "<style>:root { --gutter: 32px !important; }</style>", "wide"),
    (HOME, "SPACE_RATIO: side margin back to the --max centring alone (60px at 1440)", "<style>:root { --side: 32px "
     "!important; }</style>", "wide"),
    (HOME, "TYPE_TIERS: Questions back at the h1's size", "<style>.questions h2 { font-size: var(--h1) !important; }"
     "</style>", "wide"),
    (HOME, "TYPE_TIERS: the help subhead a step under the h1", "<style>.half + .half h2 { font-size: "
     "calc(var(--h1) * 0.92) !important; }</style>", "layout"),
    (HOME, "SHEET_REPLAY: correction finishes at cover 60%", "<style>.sheet-lg .new mark:last-of-type "
     "{ animation-range: cover 50% cover 60% !important; }</style>", "motion"),
    (HOME, "SHEET_REPLAY: correction shown finished from the start", "<style>.sheet-lg :is(.old del, .new mark) "
     "{ animation: none !important; }</style>", "motion"),
    (HOME, "strike undrawn in reduced motion", "<style>.sheet-lg .old del { background-size: 0 2px !important; }</style>",
     "motion"),
    (HOME, "PAINT_CONCURRENT: every paragraph sweeps its background at load", "<style>@keyframes qa-paint "
     "{ from { background-size: 0 100%; } } @media (prefers-reduced-motion: no-preference) { main p "
     "{ animation: qa-paint 30s linear both; } }</style>", "motion"),
    (HOME, "MAC_LINE: Mac install line on more lines", "<style>.command { max-width: 16rem !important; }</style>",
     "mac", MAC_UA),
    (HOME, "FRAMES: the resume sheet pinned over the window", "<style>.proof { position: fixed !important; "
     "top: 0; left: 0; width: 520px; }</style>", "frames"),
    (HOME, "STATUS: Copy result never announced", "<script>document.getElementById('install-status')"
     ".removeAttribute('role')</script>", "status"),
    (HOME, "STATUS: Copy named by a fixed label", "<script>document.getElementById('copy')"
     ".setAttribute('aria-label', 'Copy the line')</script>", "status"),
    (HOME, "STATUS: OS switch silent", "<script>document.getElementById('switch-os').addEventListener('click', "
     "() => setTimeout(() => { document.getElementById('install-status').textContent = 'Copied to the clipboard'; "
     "}))</script>", "status"),
    (HOME, "FORCED_DEL: strike gone in forced colours", "<style>@media (forced-colors: active) { .old del "
     "{ text-decoration-line: none !important; } }</style>", "motion"),
    (HOME, "FORCED_DEL: bullet dots gone in forced colours", "<style>@media (forced-colors: active) { .bul::before "
     "{ border: 0 !important; } }</style>", "motion"),
    (HOME, "NOJS_SCRIPTING: Copy shown without JS", "<style>#copy { display: inline-flex !important; }</style>", "motion"),
    (HOME, "NOJS_SCRIPTING: Mac answer link hidden without JS", "<style>.nojs-mac { display: none !important; }</style>",
     "motion"),
    (HOME, "HIT_BOXES: footer links back to their text height on touch", "<style>@media (pointer: coarse) "
     "{ footer a { padding-block: 0 !important; margin-block: 0 !important; } }</style>", "phone"),
    (ARTICLE, "HIT_BOXES: crumb Home back to its text width on touch", "<style>@media (pointer: coarse) { .crumbs a "
     "{ padding-inline: 0 !important; margin-inline: 0 !important; } }</style>", "phone"),
    (ARTICLE, "HIT_BOXES: Sources links back inline, 18px tall", "<style>.src-links { display: inline !important; } "
     ".src-links a { padding: 0 !important; margin: 0 !important; }</style>", "phone"),
    (ARTICLE, "HIT_BOXES: On this page rows overprint on an iPad (before 2026-10-07)", "<style>@media (pointer: coarse) "
     "{ .toc a { padding-block: 8px 9px !important; margin-block: -12px !important; } }</style>", "touch"),
    (HOME, "SCHEME_DARK: marks in the window turn pale", "<style>@media (prefers-color-scheme: dark) { .window mark "
     "{ color: #f2f2f2 !important; } }</style>", "schemes"),
    (HOME, "SCHEME_DARK: the window white again in dark mode", "<style>.window { background: #ffffff !important; }"
     "</style>", "schemes"),
    (HOME, "SCHEME_LIGHT: links in the page lose the pen's underline", "<style>main a { text-decoration-color: "
     "var(--text) !important; }</style>",
     "schemes"),
    (HOME, "CONTRAST_MORE: grey text kept under Increase Contrast", "<style>@media (prefers-contrast: more) { :root "
     "{ --text-2: #767676 !important; } }</style>", "schemes"),
    (HOME, "PRINT_DARK: the window prints pale from a dark screen", "<style>@media print { body { --win-ink: #f2f2f2 "
     "!important; } }</style>", "schemes"),
    (ARTICLE, "HIT_OVERLAP: footer rows 8px apart w/ 53px tap boxes on touch (before G1)", "<style>@media (pointer: "
     "coarse) { footer nav { row-gap: 8px !important; } footer nav a { padding-block: calc((45px - 1.1em) / 2) "
     "!important; margin-block: calc((1.1em - 45px) / 2) !important; } }</style>", "phone"),
    (ARTICLE, "NAV_CURRENT: Research link plain on an article", "<style>.links a { text-decoration-thickness: 1px "
     "!important; }</style>", "layout"),
    ("privacy.html", "EMPTY_RIGHT: Short version back in the text column, right half empty",
     "<style>.page { display: block !important; max-width: 68ch !important; }</style>", "wide"),
    ("404.html", "EMPTY_RIGHT: drawing back to its small size", "<style>.cut { width: 200px !important; "
     "justify-self: start !important; }</style>", "wide"),
    ("privacy.html", "RULES_STACKED: a hairline under the Short version, over the next heading's",
     "<style>.short { border-bottom: 1px solid; padding-bottom: 30px; }</style>", "narrow"),
    (ARTICLE, "ARTICLE_H1: article h1 back to 64px", "<style>h1 { font-size: 4rem !important; }</style>", "wide"),
    ("research/index.html", "ARTICLE_H1: hub h1 below the display scale", "<style>h1 { font-size: clamp(2.25rem, "
     "1.4rem + 2.6vw, 4rem) !important; }</style>", "wide"),
    ("research/ai-resume-screening-bias/index.html", "HEADLINE_RAG: the title in one run at the old h1 size (as audited)",
     "<style>h1 { font-size: clamp(2.25rem, 1.4rem + 2.6vw, 4rem) !important; }</style><script>document.querySelector("
     "'h1 .deck').replaceWith(document.querySelector('h1 .deck').textContent)</script>", "wide"),
    ("research/index.html", "HUB_FOLD: articles back in one column", "<style>.list { display: block "
     "!important; }</style>", "wide"),
    ("research/index.html", "HEADLINE_RAG: hub titles back in one run", "<script>document.querySelectorAll('.deck')"
     ".forEach(d => d.replaceWith(d.textContent))</script>", "wide"),
    ("404.html", "FOOTER_BOTTOM: blank band under the 404's footer", "<style>body { min-height: 0 !important; }"
     "</style>", "wide"),
    (HOME, "ZOOM_H1: vh cap back below 1080px", "<style>@media (max-width: 1079px) { h1 { font-size: "
     "min(clamp(2.5rem, 1.2rem + 3vw, 6rem), 8.6vh + 0.5rem) !important; } }</style>", "zoom"),
    (HOME, "HOVER: a hover rule paints the highlighter", "<style>a:hover { background: var(--mark) "
     "!important; }</style>", "hover"),
    (ARTICLE, "HOVER: links look the same on hover", "<style>a:hover { text-decoration-thickness: 1px !important; }"
     "</style>", "hover"),
    (ARTICLE, "TOC_NARROW: no On this page below 1280px", "<style>.toc-mini { display: none !important; }</style>",
     "toc"),
    (ARTICLE, "TOC_NARROW: the opened list drops a heading", "<script>document.querySelector('.toc-mini li:last-child')"
     ".remove()</script>", "toc"),
    # the longest list (19 rows since 2026-10-06) scrolls w/ the page on a short window, so the fault sticks it again
    (ARTICLE, "STICKY_FIT: On this page rows back to full height on a short window", "<style>@media (max-height: "
     "819px) { .toc a { padding: 8px 0 9px !important; } .toc:has(li:nth-child(19)) { position: sticky !important; "
     "max-height: calc(100vh - 48px) !important; overflow-y: auto !important; } }</style>", "sticky"),
    ("research/index.html", "STICKY_FIT: evidence labels stuck + clipped on a short window", "<style>@media "
     "(min-width: 1280px) { .labels { position: sticky !important; max-height: calc(100vh - 48px) !important; "
     "overflow-y: auto !important; } }</style>", "sticky"),
    (ARTICLE, "TOC_BESIDE: On this page back at the window's edge", "<style>.toc { justify-self: end !important; }"
     "</style>", "wide"),
    (ARTICLE, "TOC_BESIDE: a thin column, the right half empty again", "<style>.toc { width: 6rem !important; }"
     "</style>", "wide"),
    (ARTICLE, "TOC_WIDE: On this page column hidden on wide screens", "<style>@media (min-width: 1280px) "
     "{ .toc { display: none !important; } }</style>", "toc"),
    (ARTICLE, "TOC_CURRENT: the section in view never marked", "<script>new MutationObserver(() => document"
     ".querySelectorAll('[aria-current=true]').forEach(a => a.removeAttribute('aria-current'))).observe("
     "document.body, {subtree: true, attributes: true, attributeFilter: ['aria-current']})</script>", "toc"),
    (ARTICLE, "TOC_CURRENT: current link looks like the rest", "<style>:is(.toc, .toc-mini) a[aria-current] "
     "{ font-weight: 400 !important; }</style>", "toc"),
    (ARTICLE, "CRUMBS_ONE_LINE: current crumb shown on phones", "<style>article .crumbs [aria-current] "
     "{ position: static !important; width: auto !important; height: auto !important; clip-path: none !important; "
     "white-space: normal !important; }</style>", "toc"),
    ("research/index.html", "HOVER: a hub folder stays put", "<style>.list > li:hover "
     "{ transform: none !important; }</style>", "hover"),
]
# a fault whose what starts with one of these must be caught by that check's own line
CAUGHT_BY = {"PAINT_CONCURRENT": "PAINT_CONCURRENT", "MAC_LINE": "MAC_LINE", "FRAMES": "FRAMES", "STATUS": "STATUS",
             "RING": "RING", "WINDOW_TEXT": "WINDOW_TEXT", "SHEET_NOTE": "SHEET_NOTE", "AFTER_RULES": "AFTER_RULES", "TYPE_TIERS": "TYPE_TIERS", "SHEET_REPLAY": "SHEET_REPLAY",
             "FORCED_DEL": "FORCED_DEL", "NOJS_SCRIPTING": "NOJS_SCRIPTING", "ZOOM_H1": "ZOOM_H1",
             "HIT_BOXES": "HIT_BOXES", "NAV_CURRENT": "NAV_CURRENT", "EMPTY_RIGHT": "left empty right of its content",
             "RULES_STACKED": "RULES_STACKED", "ARTICLE_H1": "ARTICLE_H1", "HEADLINE_RAG": "HEADLINE_RAG", "HUB_FOLD": "HUB_FOLD", "TOC_BESIDE": "TOC_BESIDE", "TOC_NARROW": "TOC_NARROW", "TOC_WIDE": "TOC_WIDE", "TOC_CURRENT": "TOC_CURRENT", "CRUMBS_ONE_LINE": "CRUMBS_ONE_LINE", "FOOTER_BOTTOM": "FOOTER_BOTTOM", "HOVER": "HOVER",
             "HIT_OVERLAP": "HIT_OVERLAP", "SCHEME_DARK": "SCHEME_DARK", "SCHEME_LIGHT": "SCHEME_LIGHT",
             "CONTRAST_MORE": "CONTRAST_MORE", "PRINT_DARK": "PRINT_DARK", "SPACE_RATIO": "SPACE_RATIO", "STICKY_FIT": "STICKY_FIT", "0 matches": "found 0 elements"}


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
           where: str, inject: str | None = None, goto: bool = True, ua: str | None = None, **options):
    """A fresh context + page; console errors + uncaught errors land in failed on close.
    ua: browser name, default PHONE_UA / DESKTOP_UA (Windows)."""
    mobile = {"is_mobile": phone} if browser.browser_type.name != "firefox" else {}
    context = browser.new_context(viewport={"width": width, "height": height}, has_touch=options.pop("has_touch", phone),
                                  user_agent=ua or (PHONE_UA if phone else DESKTOP_UA), **mobile, **options)
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


def missing(page, where: str, *selectors: str) -> list[str]:
    """A check whose selector matches 0 elements fails - never a silent pass."""
    return [f"{where}: check found 0 elements for {s!r}" for s in selectors
            if not page.evaluate("s => document.querySelectorAll(s).length", s)]


REPORT_ONLY = "report-only: "  # failure lines of a check not yet a gate: printed as reports, self-test counts them


def label_for(browser, name: str, width: int, height: int, phone: bool, extra: str = "") -> str:
    engine = browser.browser_type.name
    kind = "phone" if phone else "desktop"
    return (f"{name} at {width}x{height} ({kind}{', ' + engine if engine != 'chromium' else ''}"
            f"{', ' + extra if extra else ''})")


def toc_pages() -> list[str]:
    return [name for name in pages() if '<nav class="toc"' in (DOCS / name).read_text(encoding="utf-8")]


def check_toc(browser, base: str, inject: str | None = None, names: list[str] | None = None,
              narrow: bool = True) -> list[str]:
    """TOC_NARROW + TOC_WIDE (B2, D21): On this page reachable at every width."""
    failed = []
    names = names or toc_pages()
    if not names:
        return ["TOC: check found 0 pages with an On this page column"]
    for name in names:
        for (w, h), phone in TOC_NARROW_AT if narrow else []:
            where = f"TOC_NARROW {label_for(browser, name, w, h, phone)}"
            with opened(browser, base, name, w, h, phone, failed, where, inject) as page:
                heads, box = page.evaluate(TOC_HEADS), page.evaluate(TOC_BOX, ".toc-mini summary")
                if not heads or box is None:
                    failed.append(f"{where}: check found 0 elements for {'h2' if not heads else '.toc-mini summary'}")
                    continue
                if not box["shown"] or box["text"] != "On this page" or box["top"] > h * TOC_NARROW_SCREENS:
                    failed.append(f"{where}: no visible 'On this page' within {TOC_NARROW_SCREENS} screens ({box})")
                    continue
                page.click(".toc-mini summary")
                got = page.evaluate(TOC_LINKS, ".toc-mini a")
                if got != heads:
                    failed.append(f"{where}: opened list shows {len(got)} links, page has {len(heads)} h2s "
                                  f"(first missing: {next((x for x in heads if x not in got), None)})")
        for w, h in CRUMBS_AT if narrow else []:
            where = f"CRUMBS_ONE_LINE {label_for(browser, name, w, h, True)}"
            with opened(browser, base, name, w, h, True, failed, where, inject) as page:
                tops = page.evaluate(CRUMBS_TOPS)
                if not tops:
                    failed.append(f"{where}: check found 0 elements for article .crumbs li")
                elif len(set(tops)) > 1:
                    failed.append(f"{where}: breadcrumb runs to {len(set(tops))} lines")
        w, h = TOC_WIDE_AT
        where = f"TOC_WIDE {label_for(browser, name, w, h, False)}"
        with opened(browser, base, name, w, h, False, failed, where, inject) as page:
            heads, first = page.evaluate(TOC_HEADS), page.evaluate(TOC_BOX, ".toc a")
            if not heads or first is None:
                failed.append(f"{where}: check found 0 elements for {'h2' if not heads else '.toc a'}")
                continue
            got = page.evaluate(TOC_LINKS, ".toc a")
            text = page.evaluate("document.querySelector('main article h1').getBoundingClientRect().right")
            if got != heads or not first["shown"] or first["bottom"] > h or first["left"] < text:
                spot = f"at x {first['left']:.0f}, bottom {first['bottom']:.0f}" if first["shown"] else "hidden"
                failed.append(f"{where}: On this page column shows {len(got)} of {len(heads)} links, first {spot}"
                              f" (text column ends at x {text:.0f}, screen {h}px)")
            cur = page.evaluate(TOC_CURRENT, 2)
            where = f"TOC_CURRENT {label_for(browser, name, w, h, False)}"
            if cur is None:
                failed.append(f"{where}: check found 0 elements for a 3rd h2")
            elif sorted(c[:2] for c in cur["got"]) != [["toc", cur["want"]], ["toc-mini", cur["want"]]]:
                failed.append(f"{where}: 3rd h2 {cur['want']} at the top, links marked current: {cur['got']}")
            elif any(int(c[2]) < 700 or c[2] == cur["plain"] for c in cur["got"]):
                failed.append(f"{where}: current link weight {cur['got'][0][2]}, others {cur['plain']} - not set apart")
    return failed


def sticky_pages() -> list[str]:
    return [name for name in pages()
            if re.search(r'class="(?:toc|side labels|summary)"', (DOCS / name).read_text(encoding="utf-8"))]


def check_sticky(browser, base: str, inject: str | None = None, names: list[str] | None = None) -> list[str]:
    """STICKY_FIT: every side column shows all of itself at laptop sizes."""
    failed = []
    names = names or sticky_pages()
    if not names:
        return ["STICKY_FIT: check found 0 pages with a side column"]
    for name in names:
        for w, h in STICKY_AT:
            where = f"STICKY_FIT {label_for(browser, name, w, h, False)}"
            with opened(browser, base, name, w, h, False, failed, where, inject) as page:
                sides = page.evaluate(STICKY_FIT)
                if not sides:
                    failed.append(f"{where}: check found 0 elements for {STICKY_SIDES!r}")
                for cls, position, hidden, over in sides:
                    if hidden > 1:
                        failed.append(f"{where}: .{cls} hides {hidden}px of itself (scrolls inside its own box)")
                    elif position == "sticky" and over > 1:
                        failed.append(f"{where}: .{cls} stuck {over}px taller than the window (its end out of reach)")
    return failed


def check_layout(browser, base: str, name: str, width: int, height: int, phone: bool,
                 inject: str | None = None, shots: bool = True, ua: str | None = None) -> tuple[list[str], list[str]]:
    """Fit, header, fold, page length, console errors. Returns (failures, reports); failures starting
    REPORT_ONLY come from checks not yet gating."""
    mac = ua == MAC_UA
    where = label_for(browser, name, width, height, phone, "Mac" if mac else "")
    failed, reports = [], []
    with opened(browser, base, name, width, height, phone, failed, where, inject, ua=ua) as page:
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
        if phone and (width, height) == SEND_AT:
            boxes = page.evaluate(HIT_BOXES)
            if not boxes:
                failed.append(f"HIT_BOXES {where}: check found 0 links or buttons")
            failed += hit_problems(page, where)
        if (width, height) == FOLD and not phone and not mac:
            research, other = page.evaluate(NAV_CURRENT)
            if research is None or other is None:
                failed.append(f"NAV_CURRENT {where}: check found 0 header Research / Install links")
            elif name.startswith("research/") and research <= other:
                failed.append(f"NAV_CURRENT {where}: Research link underline {research}px, not thicker than "
                              f"Install's {other}px on a research page")
            elif not name.startswith("research/") and research != other:
                failed.append(f"NAV_CURRENT {where}: Research link marked current ({research}px vs {other}px) "
                              f"off the research pages")
        if (width, height) == FOOTER_BOTTOM_AT and not phone:
            got = page.evaluate(FOOTER_BOTTOM)
            if got is None:
                failed.append(f"FOOTER_BOTTOM {where}: check found 0 footers")
            elif got[0] < got[1] - 2:
                failed.append(f"FOOTER_BOTTOM {where}: footer ends at {got[0]:.0f}px, page/window at "
                              f"{got[1]:.0f}px - a blank band under it")
        if name.startswith("research/") and not phone and (width, height) == (1440, 900):
            size = page.evaluate(H1_SIZE)
            if size is None:
                failed.append(f"ARTICLE_H1 {where}: check found 0 h1")
            elif size < H1_MIN:
                failed.append(f"ARTICLE_H1 {where}: h1 {size:.1f}px, under {H1_MIN}px")
        if name == "research/index.html" and not phone and (width, height) == (1440, 900):
            ends = page.evaluate(HUB_FOLD)
            if not ends:
                failed.append(f"HUB_FOLD {where}: check found 0 elements (article titles)")
            elif sum(y <= height for y in ends) < HUB_FOLD_MIN:
                failed.append(f"HUB_FOLD {where}: {sum(y <= height for y in ends)} article titles end above y "
                              f"{height}, under {HUB_FOLD_MIN} (title ends {[round(y) for y in ends]})")
        if name.startswith("research/") and ((width, height), phone) in RAG_AT:
            got = page.evaluate(HEADLINE_RAG)
            if got is None:
                failed.append(f"HEADLINE_RAG {where}: check found 0 h1")
            failed += [f"HEADLINE_RAG {where}: {line}" for line in got or []]
        if name in RULES_PAGES or page.evaluate("!!document.querySelector('main article')"):
            got = page.evaluate(RULES_STACKED)
            if got is None:
                failed.append(f"RULES_STACKED {where}: check found 0 main elements")
            failed += [f"RULES_STACKED {where}: {line}" for line in got or []]
        if (width, height) in SPACE_AT and not phone and not mac:
            got = page.evaluate(SPACE_RATIO)
            if got is None:
                failed.append(f"SPACE_RATIO {where}: check found 0 elements (main, h1, content box)")
            else:
                gap, h2, side, h1, near = got
                reports.append(f"report: SPACE_RATIO {where}: gap {gap:.0f}px, largest h2 {h2:.0f}px, side {side:.0f}px, "
                               f"h1 {h1:.0f}px, clear {', '.join(f'{c:.0f}/{f:.0f}' for _, f, c in near) or '-'}")
                if gap < SPACE_GAP * h2:
                    failed.append(f"SPACE_RATIO {where}: grid gap {gap:.0f}px, under {SPACE_GAP}x the {h2:.0f}px h2")
                if side < SPACE_SIDE * h1:
                    failed.append(f"SPACE_RATIO {where}: side margin {side:.0f}px, under {SPACE_SIDE}x the {h1:.0f}px h1")
                failed += [f"SPACE_RATIO {where}: \"{text}\" ({f:.0f}px) {c:.0f}px from the next column, under "
                           f"{SPACE_CLEAR}x its size" for text, f, c in near if c < SPACE_CLEAR * f]
        if (width, height) in BAND_AT and not phone:
            if name == "index.html" or name in WIDE_PAGES:
                rows = "main > *" if name == "index.html" else "main"
                failed += [f"{where}: {line}" for line in page.evaluate(EMPTY_RIGHT, rows)]
            if page.evaluate("!!document.querySelector('main article')"):
                got = page.evaluate(TOC_BESIDE)
                if got is None:
                    failed.append(f"TOC_BESIDE {where}: check found 0 elements (On this page column)")
                elif got[0] > TOC_GAP or got[1] > BAND_W:
                    failed.append(f"TOC_BESIDE {where}: On this page {got[0]:.0f}px right of the text (cap {TOC_GAP}), "
                                  f"{got[1]:.0f}px empty right of it (cap {BAND_W})")
        if name == "index.html":
            failed += missing(page, where, "#copy", "#line", "main section h2", ".picked svg.ring", ".picked .meta")
            failed += [f"{where}: {line}" for line in page.evaluate(COMPOSITION)]
            ring = page.evaluate(RING)
            if ring is None:
                failed.append(f"RING {where}: check found 0 elements (Job 12 ring paths + title)")
            failed += [f"RING {where}: {line}" for line in ring or []]
            if not phone and (width, height) == WINDOW_TEXT_AT:
                sizes = page.evaluate(WINDOW_TEXT)
                if not sizes:
                    failed.append(f"WINDOW_TEXT {where}: check found 0 elements (hero window text)")
                failed += [f"WINDOW_TEXT {where}: {what} text {px:.1f}px, under {WINDOW_TEXT_MIN}px"
                           for what, px in sizes if px < WINDOW_TEXT_MIN]
            if not phone and width >= SHEET_NOTE_W:
                got = page.evaluate(SHEET_NOTE)
                if got is None:
                    failed.append(f"SHEET_NOTE {where}: check found 0 elements (sheet note, old/new line, bullet)")
                else:
                    note, top, new_px, old_px, bul_px = got
                    if abs(note - top) > SHEET_NOTE_PX:
                        failed.append(f"SHEET_NOTE {where}: approval note top {note:.0f}px vs new line top {top:.0f}px "
                                      f"(over {SHEET_NOTE_PX}px apart)")
                    if not new_px == old_px == bul_px:
                        failed.append(f"SHEET_NOTE {where}: old/new lines {old_px:g}/{new_px:g}px, "
                                      f"the sheet's bullets {bul_px:g}px")
            if not phone and name == HOME and (width >= AFTER_RULES_W or (width, height) == AFTER_GAP_AT):
                got = page.evaluate(AFTER_RULES)
                if got is None:
                    failed.append(f"AFTER_RULES {where}: check found 0 elements (.after .half pair)")
                elif width >= AFTER_RULES_W and abs(got[0][0] - got[0][1]) > AFTER_RULES_PX:
                    failed.append(f"AFTER_RULES {where}: top rules at y {got[0][0]:.0f} vs {got[0][1]:.0f} "
                                  f"(over {AFTER_RULES_PX}px apart)")
                elif width < AFTER_RULES_W and got[1] < AFTER_GAP_MIN:
                    failed.append(f"AFTER_RULES {where}: halves {got[1]:.0f}px apart, under {AFTER_GAP_MIN}px")
            if not phone and not mac and (width, height) in TYPE_TIERS_AT:
                got = page.evaluate(TYPE_TIERS)
                if not got:
                    failed.append(f"TYPE_TIERS {where}: check found 0 elements (h1 + scene h2s)")
                failed += [f"TYPE_TIERS {where}: h2 \"{text}\" is {ratio:.2f}x the h1, between "
                           f"{TYPE_TIERS_LOW} and {TYPE_TIERS_HIGH}" for text, ratio in got or []
                           if TYPE_TIERS_LOW < ratio < TYPE_TIERS_HIGH]
            if mac and not phone and (width, height) in MAC_LINE_AT:
                got = page.evaluate(LINE_BOXES)
                if not got or not got[0].startswith("curl ") or got[1] != 1:
                    failed.append(f"MAC_LINE {where}: Mac install line is "
                                  f"{got[1] if got else 0} line boxes, not 1 ({got[0] if got else 'no #line'!r})")
            if not phone and (width, height) in FRAMES_AT:
                frames = page.evaluate(FRAMED)
                if frames is None:
                    failed.append(f"{where}: FRAMES found 0 framed objects (.window, .proof, .sheet-lg)")
                else:
                    failed += [f"{where}: FRAMES {line}" for line in frames[:3]]
            if (width, height) in (FOLD, FOLD_REPORT) and page.evaluate("!!document.getElementById('copy')"):
                bottom = page.evaluate("document.getElementById('copy').getBoundingClientRect().bottom")
                if bottom > height and (width, height) == FOLD:
                    failed.append(f"{where}: Copy button ends at {bottom:.0f}px, below the {height}px screen")
                if (width, height) == FOLD_REPORT:
                    reports.append(f"report: {where}: Copy button ends at {bottom:.0f}px of {height}px")
            screens = tall / height
            if (width, height) == FOLD and not phone and not mac:
                reports.append(f"report: {where}: page is {screens:.2f} screens (cap {DESKTOP_CAP})")
            if (width, height) == FOLD and screens > DESKTOP_CAP:
                failed.append(f"{where}: page is {screens:.1f} screens long, cap {DESKTOP_CAP}")
            if phone and (width, height) == SEND_AT and not (gone := missing(page, where, ".send")):
                bottom = page.evaluate("document.querySelector('.send').getBoundingClientRect().bottom")
                reports.append(f"report: {where}: 'Send this page to my computer' ends at {bottom:.0f}px "
                               f"(cap {SEND_CAP})")
                if bottom > SEND_CAP:
                    failed.append(f"{where}: 'Send this page to my computer' ends at {bottom:.0f}px, "
                                  f"cap {SEND_CAP}")
            elif phone and (width, height) == SEND_AT:
                failed += gone
            if phone and (width, height) == (375, 812):
                reports.append(f"report: {where}: page is {screens:.2f} screens (cap {PHONE_CAP:.1f})")
                if screens > PHONE_CAP:
                    failed.append(f"{where}: page is {screens:.1f} screens long, cap {PHONE_CAP:.1f}")
        if shots:
            SCREENS.mkdir(parents=True, exist_ok=True)
            shot = name.removesuffix(".html").replace("/", "-")
            engine = browser.browser_type.name
            page.screenshot(path=SCREENS / f"{shot}-{width}x{height}{'-phone' if phone else ''}{'-mac' if mac else ''}"
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
        # from load on (the opening's timed ones count), before anything settles
        count, y, which = page.evaluate(PAINT_CONCURRENT)
        if count > PAINT_CAP:
            failed.append(f"{where}: PAINT_CONCURRENT {count} paint animations at once at y={y} "
                          f"(cap {PAINT_CAP}): {'; '.join(which)}")
        failed += [f"{where}: animation never ends: {a}" for a in page.evaluate(SETTLE)]
        if name == HOME:
            got = page.evaluate(SHEET_REPLAY)
            if got is None:
                failed.append(f"SHEET_REPLAY {where}: check found 0 elements (.proof, strike + new line's marks)")
            elif page.evaluate('CSS.supports("animation-timeline: view()")'):
                early, late = got
                if not early:
                    failed.append(f"SHEET_REPLAY {where}: correction already finished at cover "
                                  f"{SHEET_REPLAY_EARLY:.0%} (no replay)")
                failed += [f"SHEET_REPLAY {where}: {m} not finished by cover {SHEET_REPLAY_DONE:.0%}" for m in late]
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
        nojs = page.evaluate(NOJS_SCRIPTING)
        failed += [f"NOJS_SCRIPTING {where}: {b} shown, but nothing runs it" for b in nojs["buttons"]]
        if name == "index.html":
            line = result["line"]
            if not line or line[0] != WIN_LINE or not line[1]:
                failed.append(f"{where}: Windows install line missing or hidden ({line})")
            if not nojs["answer"]:
                failed.append(f"NOJS_SCRIPTING {where}: no #mac answer inside a details holding the Mac install line")
            elif not nojs["link"]:
                failed.append(f"NOJS_SCRIPTING {where}: no visible link to the Mac answer (#mac)")

    if browser.browser_type.name == "chromium":
        where = label_for(browser, name, width, height, phone, "forced colours")
        with opened(browser, base, name, width, height, phone, failed, where, inject,
                    forced_colors="active") as page:
            failed += [f"{where}: mark paints nothing: {m}" for m in page.evaluate(FORCED)]
            got = page.evaluate(FORCED_DEL)
            failed += [f"FORCED_DEL {where}: {b}" for b in got["bad"]]
            if name == "index.html" and not (got["dels"] and got["buls"]):
                failed.append(f"FORCED_DEL {where}: check found 0 elements ({got['dels']} del, {got['buls']} .bul)")
    return failed


def check_zoom(browser, base: str, inject: str | None = None) -> tuple[list[str], list[str]]:
    """ZOOM_H1 (B8, WCAG 1.4.4): home's h1 at 200% browser zoom (half the viewport, 2 device px per CSS px)
    renders at least as large as at 100%. (failures, reports)"""
    failed, reports = [], []
    size = "parseFloat(getComputedStyle(document.querySelector('h1')).fontSize)"
    for w, h in ZOOM_AT:
        where = f"ZOOM_H1 index.html at {w}x{h}"
        with opened(browser, base, "index.html", w, h, False, failed, where, inject) as page:
            if gone := missing(page, where, "h1"):
                failed += gone
                continue
            full = page.evaluate(size)
        with opened(browser, base, "index.html", w // 2, h // 2, False, failed, where + " at 200%", inject,
                    device_scale_factor=2) as page:
            zoomed = page.evaluate(size) * 2
        reports.append(f"report: {where}: h1 {full:.1f}px, at 200% zoom {zoomed:.1f} device px (x{zoomed / full:.2f})")
        if zoomed < full - 0.5:
            failed.append(f"{where}: h1 at 200% zoom {zoomed:.1f} device px, smaller than {full:.1f}px at 100%")
    return failed, reports


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


def hit_problems(page, where: str) -> list[str]:
    """HIT_BOXES + HIT_OVERLAP on an open touch page."""
    failed = []
    boxes = page.evaluate(HIT_BOXES)
    if not boxes:
        failed.append(f"HIT_BOXES {where}: check found 0 links or buttons")
    failed += [f"HIT_BOXES {where}: {what} hit box {h:.1f}px tall, under {HIT_MIN}px" for what, h, w in boxes if h < HIT_MIN]
    failed += [f"HIT_BOXES {where}: {what} hit box {w:.1f}px wide, under {HIT_MIN}px" for what, h, w in boxes if w < HIT_MIN]
    n, overlaps = page.evaluate(HIT_OVERLAP)
    if not n:
        failed.append(f"HIT_OVERLAP {where}: check found 0 elements")
    failed += [f"HIT_OVERLAP {where}: {a!r} keeps {h:.1f}px of its tap box (under {HIT_FREE}px), "
               f"covered by {', '.join(map(repr, b))}" for a, b, h in overlaps]
    return failed


def check_touch(browser, base: str, inject: str | None = None, names: list[str] | None = None) -> list[str]:
    """HIT_BOXES + HIT_OVERLAP on a wide touch screen (iPad landscape, TOUCH_WIDE): the phone run missed On this
    page's rows overprinting there (2026-10-07)."""
    failed = []
    for name in names or pages():
        where = label_for(browser, name, *TOUCH_WIDE, False, "touch")
        with opened(browser, base, name, *TOUCH_WIDE, False, failed, where, inject, has_touch=True) as page:
            if not page.evaluate("matchMedia('(pointer: coarse)').matches"):
                failed.append(f"HIT_BOXES {where}: touch emulation off (pointer: coarse not matched)")
                continue
            failed += hit_problems(page, where)
    return failed


# SCHEME_* (Apple HIG review, 2026-10-07): the colours each scheme must paint, read off computed styles - the static
# contrast check can't see the hero window's own tokens, nor print. Home + an article; light, dark, both w/ Increase
# Contrast (prefers-contrast: more), and print from a dark screen (Chrome keeps the scheme when printing).
SCHEME_JS = """() => { const c = (s, p = "color") => { const e = document.querySelector(s); return e ? getComputedStyle(e)[p] : null; };
  return {desk: c("body", "backgroundColor"), text: c("body"), win: c(".window", "backgroundColor"), winText: c(".window"),
    winMark: c(".window mark"), bird: c(".window .bird", "fill"), disc: c(".window .bird .disc", "fill"),
    link: c("main .research-head a, main .box-more a"), linkLine: c("main .research-head a, main .box-more a", "textDecorationColor"),
    nav: c(".links a"), title: c("main .picks a, main .crumbs a"), cite: c("main small a"),
    folder: c("main .picks > li", "backgroundColor"), note: c("main .box", "backgroundColor"),
    foot: c("footer p"), footLine: c("footer", "borderTopColor")}; }"""
# the job-search desk (plan-h14): a link in the page keeps the text's ink, the blue pen draws its underline; the
# objects' faces (a home research folder, an article's sticky note) dim in dark
SCHEME_WANT = {
    "light": {"desk": "rgb(246, 241, 231)", "link": "rgb(0, 0, 0)", "linkLine": "rgb(42, 81, 184)",
              "nav": "rgb(0, 0, 0)", "title": "rgb(0, 0, 0)", "win": "rgb(255, 255, 255)", "winMark": "rgb(0, 0, 0)",
              "cite": "rgb(0, 0, 0)", "folder": "rgb(238, 220, 185)", "note": "rgb(251, 241, 174)"},
    "dark": {"desk": "rgb(26, 23, 18)", "link": "rgb(234, 230, 221)", "linkLine": "rgb(129, 180, 246)",
             "nav": "rgb(234, 230, 221)", "title": "rgb(234, 230, 221)", "win": "rgb(35, 32, 28)",
             "winText": "rgb(234, 230, 221)", "winMark": "rgb(0, 0, 0)", "bird": "rgb(0, 0, 0)",
             "cite": "rgb(234, 230, 221)", "folder": "rgb(40, 34, 23)", "note": "rgb(37, 35, 23)"},
}
MORE_LINE = "rgb(118, 118, 118)"
# what each page must have for its colours to be checked at all (a renamed class would skip them silently)
SCHEME_NEEDS = {"index.html": ("desk", "link", "linkLine", "nav", "title", "win", "winText", "winMark", "bird", "disc",
                               "folder", "foot"),
                "ARTICLE": ("desk", "link", "linkLine", "nav", "title", "cite", "note", "foot")}


def check_schemes(browser, base: str, inject: str | None = None) -> list[str]:
    """SCHEME_LIGHT / SCHEME_DARK colours, CONTRAST_MORE (footer text = body text, hairline #767676) and PRINT_DARK
    (the window + desk print ink on white from a dark screen), home + ARTICLE at 1440x900."""
    failed = []
    for name in ("index.html", ARTICLE):
        for scheme in ("light", "dark"):
            where = f"{name} at 1440x900 ({scheme})"
            with opened(browser, base, name, 1440, 900, False, failed, where, inject, color_scheme=scheme) as page:
                got = page.evaluate(SCHEME_JS)
                gone = [k for k in SCHEME_NEEDS["index.html" if name == "index.html" else "ARTICLE"] if got[k] is None]
                if gone:
                    failed.append(f"SCHEME_{scheme.upper()} {where}: check found 0 elements for {', '.join(gone)}")
                for key, want in SCHEME_WANT[scheme].items():
                    if got[key] is None:
                        continue  # not on this page (window: home only, citations: articles only) - SCHEME_NEEDS
                    if got[key] != want:
                        failed.append(f"SCHEME_{scheme.upper()} {where}: {key} {got[key]}, want {want}")
                if name == "index.html" and scheme == "dark" and got["disc"] == got["win"]:
                    failed.append(f"SCHEME_DARK {where}: the window bird's disc is the window's own grey (a black "
                                  f"bird lost on it)")
                page.emulate_media(contrast="more")
                more = page.evaluate(SCHEME_JS)
                if more["foot"] != more["text"] or more["footLine"] != MORE_LINE:
                    failed.append(f"CONTRAST_MORE {where}: footer text {more['foot']} vs body {more['text']}, "
                                  f"hairline {more['footLine']} (want the body colour + {MORE_LINE})")
                if name == "index.html" and scheme == "dark":
                    page.emulate_media(contrast="no-preference", media="print")
                    printed = page.evaluate(SCHEME_JS)
                    if (printed["win"], printed["winText"], printed["desk"]) != \
                            ("rgb(255, 255, 255)", "rgb(0, 0, 0)", "rgb(255, 255, 255)"):
                        failed.append(f"PRINT_DARK {where}: prints window {printed['win']} / {printed['winText']} "
                                      f"on {printed['desk']} (want ink on white)")
    return failed


STATUS_TEXT = "() => [...document.querySelectorAll('[role=status]')].map(e => e.textContent.trim()).join(' | ')"


def check_status(browser, base: str, inject: str | None = None) -> list[str]:
    """Copy + OS switch results reach screen readers (B5): one role=status, written on click only."""
    failed = []
    where = "index.html at 1366x641"
    with opened(browser, base, "index.html", 1366, 641, False, failed, where, inject,
                permissions=["clipboard-read", "clipboard-write"]) as page:
        gone = missing(page, where, "[role=status]", "#copy", "#copy-label", "#switch-os")
        if gone:
            return failed + [f"STATUS {line}" for line in gone]
        if (got := page.evaluate(STATUS_TEXT)):
            failed.append(f"STATUS {where}: status says {got!r} at load (announced before any click)")
        page.click("#copy")
        page.wait_for_timeout(300)
        visible = page.inner_text("#copy-label").strip()
        name = re.match(r'- button "([^"]*)"', page.locator("#copy").aria_snapshot())
        if not name or visible.lower() not in name[1].lower():
            failed.append(f"STATUS {where}: Copy's accessible name {name[1] if name else None!r} lacks its "
                          f"visible label {visible!r}")
        if (got := page.evaluate(STATUS_TEXT)) != "Copied to the clipboard":
            failed.append(f"STATUS {where}: after Copy the status says {got!r}, not 'Copied to the clipboard'")
        for _ in range(2):
            page.click("#switch-os")
            page.wait_for_timeout(100)
            shown = "Mac" if page.evaluate("document.documentElement.classList.contains('is-mac')") else "Windows"
            if (got := page.evaluate(STATUS_TEXT)) != f"Showing {shown} steps":
                failed.append(f"STATUS {where}: after the OS switch ({shown} shown) the status says {got!r}")
    return failed


def check_hover(browser, base: str, inject: str | None = None, names: list[str] | None = None) -> list[str]:
    """HOVER (A5): the mouse on each visible link, button + summary changes how it looks, in ink only."""
    failed = []
    for name in names or HOVER_PAGES:
        where = f"HOVER {name} at {FOLD[0]}x{FOLD[1]}"
        with opened(browser, base, name, *FOLD, False, failed, where, inject, reduced_motion="reduce") as page:
            count, seen = page.evaluate("s => document.querySelectorAll(s).length", HOVER_SELECTOR), 0
            for i in range(count):
                page.evaluate("i => document.querySelectorAll('a, button, summary')[i]"
                              ".scrollIntoView({block: 'center'})", i)
                before = page.evaluate(HOVER_STATE, i)
                if before is None:
                    continue
                seen += 1
                away = (1, 1) if abs(before["x"] - 1) + abs(before["y"] - 1) > 40 else (FOLD[0] - 2, FOLD[1] - 2)
                page.mouse.move(*away)
                before = page.evaluate(HOVER_STATE, i)
                page.mouse.move(before["x"], before["y"])
                after = page.evaluate(HOVER_STATE, i)
                page.mouse.move(*away)
                b, a = before["style"], after["style"]
                plain = b["textDecorationLine"] == a["textDecorationLine"] == "none"
                changed = [p for p in b if b[p] != a[p] and not (plain and p.startswith("text"))]
                if not changed:
                    failed.append(f"{where}: {before['what']} looks the same on hover")
                failed += [f"{where}: {before['what']} paints the highlighter on hover ({p}: {a[p]})"
                           for p in a if HOVER_MARK in a[p] and a[p] != b[p]]
                if before["rule"] is not None and before["rule"] == after["rule"]:
                    failed.append(f"{where}: {before['what']}'s folder doesn't lift on hover ({after['rule']})")
            if not seen:
                failed.append(f"{where}: check found 0 elements for {HOVER_SELECTOR!r}")
    return failed


def run_chrome(base: str) -> tuple[list[str], list[str]]:
    from playwright.sync_api import sync_playwright

    failed, reports = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name in pages():
            sizes = [(s, True) for s in PHONES] + [(s, False) for s in DESKTOPS]
            if name == "index.html":
                sizes += [(FOLD_REPORT, False)] + [(s, False) for s in PHONES]
            # jurors browse on Macs: a page that reacts to one (html.is-mac: home's Mac install line) gets
            # every desktop size again with a Mac browser name; the others render the same either way
            mac = [(s, False, MAC_UA) for s in DESKTOPS] if "is-mac" in (DOCS / name).read_text() else []
            sizes = [(s, phone, None) for s, phone in sizes] + mac
            for (w, h), phone, ua in sizes:
                f, r = check_layout(browser, base, name, w, h, phone, ua=ua)
                failed += f
                reports += r
            for (w, h), phone in MOTION_SIZES:
                failed += check_motion(browser, base, name, w, h, phone)
        failed += check_print(browser, base)
        failed += check_schemes(browser, base)
        failed += check_touch(browser, base)
        failed += check_status(browser, base)
        failed += check_hover(browser, base)
        failed += check_toc(browser, base)
        failed += check_sticky(browser, base)
        f, r = check_zoom(browser, base)
        failed += f
        reports += r
        failed += check_transition(browser, base)
        f, r = check_opening(browser, base)
        failed += f
        reports += r
        browser.close()
    reports += ["report: " + line for line in failed if line.startswith(REPORT_ONLY)]
    return [line for line in failed if not line.startswith(REPORT_ONLY)], reports


def run_engines(base: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    failed = []
    with sync_playwright() as p:
        for engine in (p.webkit, p.firefox):
            browser = engine.launch()
            for name in pages():
                for (w, h), phone in MOTION_SIZES:
                    f, _ = check_layout(browser, base, name, w, h, phone)
                    failed += [line for line in f if "header" not in line and "Copy button" not in line
                               and not line.startswith(REPORT_ONLY)]
                    failed += check_motion(browser, base, name, w, h, phone, full=False)
            failed += check_toc(browser, base)
            browser.close()
    return failed


def run_self_test(base: str) -> list[str]:
    """Each FAULTS entry, injected into its page (+ browser name), must add a failure line its clean page
    lacks; each clean page passes its gates (REPORT_ONLY lines aside: those checks fail today)."""
    from playwright.sync_api import sync_playwright

    def check(browser, name: str, kind: str, inject: str | None, ua: str | None) -> list[str]:
        if kind == "layout":
            return check_layout(browser, base, name, *FOLD, False, inject, shots=False, ua=ua)[0]
        if kind == "phone":
            return check_layout(browser, base, name, *SEND_AT, True, inject, shots=False, ua=ua)[0]
        if kind in ("narrow", "wide", "frames", "mac", "tablet"):
            size = {"narrow": PHONES[0], "mac": FOLD, "tablet": AFTER_GAP_AT}.get(kind, (1440, 900))
            return check_layout(browser, base, name, *size, False, inject, shots=False, ua=ua)[0]
        if kind == "opening":
            return check_opening(browser, base, inject)[0]
        if kind == "transition":
            return check_transition(browser, base, inject)
        if kind == "status":
            return check_status(browser, base, inject)
        if kind == "schemes":
            return check_schemes(browser, base, inject)
        if kind == "touch":
            return check_touch(browser, base, inject, [name])
        if kind == "hover":
            return check_hover(browser, base, inject, [name])
        if kind == "toc":
            return check_toc(browser, base, inject, [name])
        if kind == "sticky":
            return check_sticky(browser, base, inject, [name])
        if kind == "zoom":
            return check_zoom(browser, base, inject)[0]
        return check_motion(browser, base, name, *FOLD, False, inject)

    failed, clean = [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name, what, html, kind, *ua in FAULTS:
            ua = ua[0] if ua else None
            if (name, kind, ua) not in clean:
                got = clean[name, kind, ua] = check(browser, name, kind, None, ua)
                gate = [line for line in got if not line.startswith(REPORT_ONLY)]
                if gate:
                    failed.append(f"self-test: clean {name} fails its {kind} checks: {gate[0]}")
            caught = [line for line in check(browser, name, kind, html, ua) if line not in clean[name, kind, ua]]
            needle = CAUGHT_BY.get(what.split(":")[0])
            caught = [line for line in caught if not needle or needle in line]
            print(f"self-test: {name}: {what}: {'caught - ' + caught[0] if caught else 'NOT CAUGHT'}")
            if not caught:
                failed.append(f"self-test: injected fault not caught: {name}: {what}")
        browser.close()
    return failed


# ---- --perf: home timed in Chrome, new docs/ vs the frozen polish-base copy ----------------------

BASELINE_SHA = "e704f973b2303671e1f30b4a6bae200e1e2f43b2"  # polish base (plan-dxn notes; was c7b9a106, site/redesign start)
BASELINE = ROOT / ".data" / "site-baseline"
ANDROID_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36")
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
            ("about", "about/"), ("privacy", "privacy.html"), ("terms", "terms.html"), ("404", "404.html")]
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


# ---- --capture DIR: before/after material (plan-dxn) -------------------------------------------------

# name, size, phone, browser name (None = Windows / phone default)
CAPTURE_SIZES = [("1366x641", (1366, 641), False, None), ("1440x900", (1440, 900), False, None),
                 ("1440x780-mac", (1440, 780), False, MAC_UA), ("1920x1080", (1920, 1080), False, None),
                 ("390x844-phone", (390, 844), True, None)]
CAPTURE_SCREENS = 40        # per-screen shots per page + size, at most
HEADINGS = """() => { const px = el => parseFloat(getComputedStyle(el).fontSize);
  const h1 = document.querySelector("h1"), sizes = {};
  for (const h of document.querySelectorAll("h2")) if (h.checkVisibility()) { const k = px(h); sizes[k] = (sizes[k] || 0) + 1; }
  return {h1: h1 ? px(h1) : null, h2: Object.entries(sizes).sort((a, b) => b[0] - a[0])}; }"""


def run_capture(base: str, out: Path) -> list[str]:
    """Every page at CAPTURE_SIZES, light + dark (reduced motion = finished state): a full-page shot
    and one shot per screen, plus numbers.md - length in screens, h1 + h2 px per desktop size, print pages."""
    from playwright.sync_api import sync_playwright

    failed, length, heads, printed = [], {}, {}, {}
    (out / "screens").mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name in pages():
            slug = name.removesuffix(".html").removesuffix("/index").replace("/", "-")
            for size, (w, h), phone, ua in CAPTURE_SIZES:
                for scheme in ("light", "dark"):
                    where = f"capture {name} {size} {scheme}"
                    with opened(browser, base, name, w, h, phone, failed, where, ua=ua, reduced_motion="reduce",
                                color_scheme=scheme) as page:
                        page.screenshot(path=out / f"{slug}-{size}-{scheme}.png", full_page=True)
                        tall = page.evaluate("document.documentElement.scrollHeight")
                        for i in range(min(CAPTURE_SCREENS, -(-tall // h))):
                            page.evaluate(f"scrollTo(0, {i * h})")
                            page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                            page.screenshot(path=out / "screens" / f"{slug}-{size}-{scheme}-{i + 1:02d}.png")
                        if scheme == "light":
                            length[name, size] = tall / h
                            if not phone:
                                heads[name, size] = page.evaluate(HEADINGS)
            with opened(browser, base, name, 1366, 641, False, failed, f"capture {name} print") as page:
                page.emulate_media(media="print")
                printed[name] = len(re.findall(rb"/Type\s*/Page\b", page.pdf(format="Letter", print_background=True)))
        browser.close()
    sizes = [size for size, *_ in CAPTURE_SIZES]
    desk = [size for size, _, phone, _ in CAPTURE_SIZES if not phone]
    head = lambda d: (f"{d['h1']:g}" if d["h1"] else "-") + " / " + (", ".join(
        f"{float(px):g}" + (f" x{n}" if n > 1 else "") for px, n in d["h2"]) or "-")
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    lines = [f"# Site numbers at {sha}", "", "Made by `uv run app/web/qa.py --capture DIR` (reduced motion, Chrome). "
             "Shots: `<page>-<size>-<light|dark>.png` (full page) + `screens/` (one per screen).", "",
             "## Page length (screens)", "", "| page | " + " | ".join(sizes) + " | print pages |",
             "|---" * (len(sizes) + 2) + "|"]
    lines += [f"| {name} | " + " | ".join(f"{length[name, s]:.2f}" for s in sizes) + f" | {printed[name]} |"
              for name in pages()]
    lines += ["", "## h1 / h2 computed px (h2: size xcount, largest first)", "",
              "| page | " + " | ".join(desk) + " |", "|---" * (len(desk) + 1) + "|"]
    lines += [f"| {name} | " + " | ".join(head(heads[name, s]) for s in desk) + " |" for name in pages()]
    (out / "numbers.md").write_text("\n".join(lines) + "\n")
    return failed


def keep_awake():
    """caffeinate -dimsu for as long as this process lives (macOS); a sleeping screen skews timing."""
    if shutil.which("caffeinate"):
        subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])

def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--capture"] and len(args) == 2:
        out = Path(args[1]).expanduser().resolve()
        watchdog(PERF_LIMIT_S)
        server, base = serve(DOCS)
        try:
            failed = run_capture(base, out)
        finally:
            server.shutdown()
        for line in failed:
            print(line)
        print(f"{len(failed)} problem(s)" if failed else f"captured; numbers in {out / 'numbers.md'}")
        return 1 if failed else 0
    modes = {(): "", ("--engines",): "--engines", ("--self-test",): "--self-test", ("--perf",): "--perf",
             ("--perf", "--self-test"): "--perf --self-test", ("--lighthouse",): "--lighthouse"}
    mode = modes.get(tuple(sorted(args, key=lambda a: a != "--perf")))
    if mode is None:
        print("usage: uv run app/web/qa.py [--engines | --self-test | --perf [--self-test] | --lighthouse | --capture DIR]")
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
