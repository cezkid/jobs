"""A safe look at a live employer form, for developers adding a system: `apply-form measure <link>`.

Throwaway Chrome (fresh profile per run, deleted after; never `.data/apply-browser`, the user's
application window), every write blocked at context level before the page loads, a canary
self-test proving the block first. Reads the form twice (ids a framework makes per load show up
as changed), keeps the JSON it fetched (form definitions), records employer names + prefilled
values in `.data/measure/tenants.txt` for the anonymity grep. Never reads the user's settings or
resume: worktrees have none, and nothing typed here is ever theirs.
Rules + why: app/docs/apply/apply-systems.md (Add a system).
"""
import contextlib
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import cfg
from apply import browser, dom

RUNS = cfg.DATA / "measure-browser"
OUT = cfg.DATA / "measure"
# reads only. A GET still carries what the page puts in its link (measured 2026-10-03: an image
# pixel w/ typed text went through) - tolerated because measure types nothing, try types only
# synthetic values
READS = ("GET", "HEAD", "OPTIONS")
# a click that could send the application or sign something: the applicant's own act, never ours.
# "Apply", "Apply without an Account" only navigate to the form
REFUSE_CLICK = re.compile(r"\b(?:submit|send|save|finish|complete|sign)", re.I)
IDLE_MS = 20000
JSON_KEEP = 2048
DATA_KEEP = 500_000
# a form defined in the page itself, not fetched: `window.pageData = {...}` in an inline script
# (Paylocity, 2026-10-03) - each such global kept whole, JSON only
PAGE_DATA = """() => { const out = {};
  for (const s of document.querySelectorAll('script:not([src])'))
    for (const m of s.textContent.matchAll(/window\\.([A-Za-z_$][\\w$]*)\\s*=\\s*[{[]/g))
      try { const j = JSON.stringify(window[m[1]]); if (j && j.length <= %d) out[m[1]] = JSON.parse(j); } catch (e) {}
  return out; }""" % DATA_KEEP
# where a multi-page form says it is and how it moves on: "Step 1 of 5", headings, button words,
# links + the page's opening text (Dayforce's "apply without an account" choice is neither a
# button nor a heading, 2026-10-03)
OUTLINE = """() => { const vis = e => e.checkVisibility ? e.checkVisibility({checkVisibilityCSS: true}) : !!e.getClientRects().length;
  const text = e => (e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120);
  const step = (document.body.innerText.match(/\\bstep \\d+ of \\d+\\b/gi) || []);
  return {steps: [...new Set(step)],
    headings: [...document.querySelectorAll('h1, h2, h3, h4, legend, [role=heading]')].filter(vis).map(text).filter(Boolean),
    buttons: [...document.querySelectorAll('button, [role=button], input[type=submit], input[type=button], a.button, a.btn')]
      .filter(vis).map(e => text(e) || e.value || e.getAttribute('aria-label') || '').filter(Boolean),
    links: [...new Set([...document.querySelectorAll('a[href]')].filter(vis).map(text).filter(Boolean))].slice(0, 60),
    text: (document.body.innerText || '').slice(0, 3000)}; }"""
# boxes with no name a reader finds: the markup around each, to see where the page puts its words
AROUND = """() => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
  .filter(e => !e.labels?.length && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby'))
  .map(e => ({id: e.id, name: e.name || '', around: (e.parentElement?.parentElement || e).outerHTML.slice(0, 800)}))"""
TEXT_KEEP = 4096
# host labels + path parts every tenant shares: not a tenant name, would hit the anonymity grep
GENERIC = {"www", "jobs", "job", "careers", "career", "apply", "boards", "board", "job-boards", "embed", "job_app",
           "greenhouse", "lever", "ashbyhq", "workable", "smartrecruiters", "applytojob", "bamboohr", "paylocity",
           "dayforcehcm", "paycomonline", "workforcenow", "oraclecloud", "icims", "myworkdayjobs", "myworkday",
           "ultipro", "candidateportal", "mascsr", "recruiting", "recruitment", "hiring", "posting", "postings", "opening", "openings",
           "en-us", "en_us", "en", "us", "com", "net", "org", "io", "co"}


class Refused(Exception):
    """Page not measured: the block can't vouch for it."""


class Block:
    """Every non-read request + every WebSocket aborted and logged, w/ the step that set it off."""

    def __init__(self):
        self.log: list[dict] = []
        self.step = "start"

    def install(self, page) -> None:
        context = page.context
        context.route("**/*", self.request)
        context.route_web_socket(re.compile(".*"), self.socket)
        # requests a service worker makes never reach the page's route: bypass it, and
        # check_page refuses a page one controls anyway
        session = context.new_cdp_session(page)
        session.send("Network.enable")
        session.send("Network.setBypassServiceWorker", {"bypass": True})
        self.session = session  # detaching drops the bypass

    def request(self, route) -> None:
        r = route.request
        if r.method in READS:
            return route.continue_()
        self.log.append({"method": r.method, "url": r.url[:300], "type": r.resource_type, "after": self.step})
        route.abort()

    def socket(self, ws) -> None:
        # never connect_to_server: the page talks to a stub, nothing it sends leaves Chrome.
        # ws.close() here deadlocks the sync API (measured 2026-10-03, Playwright 1.63)
        self.log.append({"method": "WEBSOCKET", "url": ws.url[:300], "type": "websocket", "after": self.step})


class Listener:
    """Local server for the canary (+ tests): serves `pages`, records every write that arrives."""

    def __init__(self, pages: dict[str, tuple[str, str]]):
        self.pages, self.writes, self.gets = pages, [], []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.headers.get("Upgrade", "").lower() == "websocket":
                    outer.writes.append(("WEBSOCKET", self.path))
                    return self.send_error(400)
                outer.gets.append(self.path)
                kind, body = outer.pages.get(self.path.split("?")[0], ("text/plain", None))
                if body is None:
                    return self.send_error(404)
                data = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def write(self):
                outer.writes.append((self.command, self.path))
                self.send_response(204)
                self.end_headers()

            do_POST = do_PUT = do_PATCH = do_DELETE = write

        self.servers = [ThreadingHTTPServer(("127.0.0.1", 0), Handler) for _ in range(2)]
        for s in self.servers:
            threading.Thread(target=s.serve_forever, daemon=True).start()
        # two hosts as well as two ports: 127.0.0.1 vs localhost is another site, so its frame
        # runs in its own process (Chrome isolates by site, ports don't count)
        self.home = f"http://127.0.0.1:{self.servers[0].server_port}"
        self.other = f"http://localhost:{self.servers[1].server_port}"

    def close(self) -> None:
        for s in self.servers:
            s.shutdown()
            s.server_close()


# every way a page can send without the user: same origin, keepalive, beacon, native form,
# a worker, another site's frame, a WebSocket. Path /w/<kind> names each in the listener's record
CANARY = """<!doctype html><title>canary</title>
<form id=f method=post action="/w/form" target=sink><input name=c value=canary></form>
<iframe name=sink></iframe><iframe id=x src="%(other)s/frame.html"></iframe>
<script>
const x = new XMLHttpRequest(); x.open('POST', '/w/xhr'); x.send('canary');
fetch('/w/keepalive', {method: 'POST', body: 'canary', keepalive: true}).catch(() => {});
navigator.sendBeacon('/w/beacon', 'canary');
fetch('%(other)s/w/cross', {method: 'POST', body: 'canary', mode: 'no-cors'}).catch(() => {});
document.getElementById('f').submit();
new Worker(URL.createObjectURL(new Blob(
  ["fetch('%(home)s/w/worker', {method: 'POST', body: 'canary'}).catch(() => {})"], {type: 'text/javascript'})));
const ws = new WebSocket('%(ws)s/w/ws'); ws.onopen = () => ws.send('canary');
setTimeout(() => window.fired = true, 300);
</script>"""
KINDS = {"xhr", "keepalive", "beacon", "cross", "form", "worker", "frame", "ws", "frame-ws"}
FRAME = """<!doctype html><script>
fetch('/w/frame', {method: 'POST', body: 'canary'}).catch(() => {});
const ws = new WebSocket('%(ws)s/w/frame-ws'); ws.onopen = () => ws.send('canary');
</script>"""


def kind(path: str) -> str:
    return path.split("?")[0].removeprefix("/w/")


def canary(page, block: Block | None) -> dict:
    """Fire every kind of write at a local listener: -> {received, blocked} kinds. Block on ->
    nothing received (each blocked); off -> received, proving the canary sees a leak."""
    listener = Listener({})
    try:
        names = {"home": listener.home, "other": listener.other, "ws": listener.home.replace("http", "ws", 1)}
        listener.pages = {"/canary.html": ("text/html", CANARY % names),
                          "/frame.html": ("text/html", FRAME % (names | {"ws": listener.other.replace("http", "ws", 1)}))}
        if block:
            block.step = "canary"
        page.goto(listener.home + "/canary.html")
        page.wait_for_function("window.fired", timeout=10000)
        page.wait_for_timeout(1500)  # beacon + keepalive leave after the page's own work
        if "/canary.html" not in listener.gets:
            raise Refused("canary page never loaded")
        blocked = [kind(urlsplit(b["url"]).path) for b in (block.log if block else []) if b["after"] == "canary"]
        return {"received": sorted(kind(p) for _, p in listener.writes), "blocked": sorted(blocked)}
    finally:
        page.goto("about:blank")
        listener.close()


def canary_failed(test: dict) -> str | None:
    """Why the block can't be trusted this run, else None."""
    if test["received"] or set(test["blocked"]) != KINDS:
        return (f"canary FAILED - reached the test listener: {', '.join(test['received']) or 'none'}; "
                f"not seen blocked: {', '.join(sorted(KINDS - set(test['blocked']))) or 'none'}")
    return None


def check_page(page) -> None:
    """A service worker controlling the page can send on its own, past the page's route."""
    if page.evaluate("!!(navigator.serviceWorker && navigator.serviceWorker.controller)"):
        raise Refused(f"a service worker controls {urlsplit(page.url).hostname} - not measured (it can send past the block)")


def refused(clicks: list[str]) -> list[str]:
    return [c for c in clicks if REFUSE_CLICK.search(c)]


@contextlib.contextmanager
def throwaway(headless: bool = False):
    """A fresh Chrome on its own profile, started like the user's (fixed port, tab Chrome opened,
    no automation flag) so the page sees what it would there. Closed + profile deleted on exit."""
    from playwright.sync_api import sync_playwright

    run = RUNS / f"{datetime.now():%Y%m%d-%H%M%S}-{time.monotonic_ns() % 10**6}"
    run.mkdir(parents=True)
    port = browser.free_port()
    proc = subprocess.Popen([browser.chrome(), f"--remote-debugging-port={port}", f"--user-data-dir={run}",
                             "--no-first-run", "--no-default-browser-check", *(["--headless=new"] if headless else []),
                             "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if browser.answers(port):
                break
            time.sleep(0.5)
        else:
            raise Refused("throwaway Chrome did not start")
        target = browser.first_tab(port, "about:blank")
        with sync_playwright() as p:
            chrome = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            try:
                yield browser.opened(lambda: chrome.contexts[0].pages, target)
            finally:
                with contextlib.suppress(Exception):
                    # routes still waiting when Chrome goes print asyncio noise on exit
                    chrome.contexts[0].unroute_all(behavior="ignoreErrors")
                    chrome.new_browser_cdp_session().send("Browser.close")
    finally:
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(10)
        for _ in range(20):  # Chrome's helpers let go of the profile a moment after it exits
            shutil.rmtree(run, ignore_errors=True)
            if not run.exists():
                break
            time.sleep(0.25)
        with contextlib.suppress(OSError):
            RUNS.rmdir()


def load(page, url: str, clicks: list[str], block: Block, n: int) -> tuple[dict, list]:
    """One fresh load + the clicks -> (snapshot + page_data + unlabelled, JSON responses seen)."""
    got = []
    listen = lambda r: got.append(r) if "json" in (r.headers.get("content-type") or "") else None
    page.on("response", listen)
    try:
        block.step = f"load {n}"
        page.goto(url, wait_until="load")
        idle(page)
        check_page(page)
        for text in clicks:
            block.step = f"load {n}: click {text!r}"
            target = page.get_by_text(text, exact=True).locator("visible=true").first
            target.click(timeout=15000)
            idle(page)
            check_page(page)
        block.step = f"load {n}: read"
        snap = dom.snapshot(page) | seen_text(page)
        snap["page_data"], snap["unlabelled"] = page.evaluate(PAGE_DATA), page.evaluate(AROUND)
        snap["outline"] = page.evaluate(OUTLINE)
        return snap, [response(r) for r in got if r.request.method == "GET"]
    finally:
        page.remove_listener("response", listen)


def seen_text(page) -> dict:
    """What the page shows, beside its controls: zero boxes read can be a wall, a box drawn without
    form controls, or a click that opened nothing - only the words tell which (Paycom, 2026-10-03)."""
    try:
        return page.evaluate("""() => ({text: (document.body.innerText || '').replace(/\\s+/g, ' ').slice(0, %d),
          buttons: [...document.querySelectorAll('button, [role=button], a[href]')].filter(e => e.getClientRects().length)
            .map(e => (e.innerText || e.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 80)})""" % TEXT_KEEP)
    except Exception:  # navigating away mid-read
        return {"text": "", "buttons": []}


def idle(page) -> None:
    with contextlib.suppress(Exception):  # a page that polls never goes idle: read what's there
        page.wait_for_load_state("networkidle", timeout=IDLE_MS)


def response(r) -> dict:
    try:
        body = r.text()[:JSON_KEEP]
    except Exception:  # redirect, or body gone after navigation
        body = ""
    return {"url": r.url, "status": r.status, "bytes": int(r.headers.get("content-length") or len(body)), "first": body}


def changed(a: dict, b: dict) -> list[dict]:
    """Boxes whose id or hook differs between two loads, matched by label + kind + place among
    their like: made per load, never a hook."""
    def keyed(snap):
        seen, out = Counter(), {}
        for c in snap["controls"]:
            k = (c["label"], c["control"], c["frame"].split("?")[0])
            out[k + (seen[k],)] = c
            seen[k] += 1
        return out
    first, second = keyed(a), keyed(b)
    return [{"label": k[0], "control": k[1], "id": [first[k]["id"], second[k]["id"]], "hook": [first[k]["hook"], second[k]["hook"]]}
            for k in first if k in second and (first[k]["id"] != second[k]["id"] or first[k]["hook"] != second[k]["hook"])]


def employer(page) -> list[str]:
    meta = page.evaluate("""() => [document.title,
      (document.querySelector('meta[property="og:site_name"]') || {}).content || '']""")
    out = [s.strip() for s in meta if s and s.strip()]
    out += [m.group(1).strip() for s in out if (m := re.search(r"\bat (.+)$", s))]
    return out


def tenants(url: str, names: list[str], snap: dict) -> list[str]:
    """What names this employer: their names, the tenant part of the link, prefilled text. Parts
    every tenant shares (job-boards, greenhouse, com) left out - they'd hit every grep."""
    u = urlsplit(url)
    parts = [p for p in (u.hostname or "").split(".") if not p.isdigit()]
    path = [p for p in u.path.split("/") if p]
    # Dayforce puts the language first: /en-US/<tenant>/<board>/jobs/<id>; SmartRecruiters
    # oneclick-ui/company/<Company>/publication/<uuid>: tenant sits after its key (2026-10-03)
    keyed = [path[i + 1] for i, p in enumerate(path[:-1]) if p in ("company", "publication")]
    if path[:1] == ["oneclick-ui"]:
        parts += keyed
    else:
        parts += path[1:3] if path and re.fullmatch(r"[a-z]{2}-[A-Za-z]{2}", path[0]) else path[:1]
    # og:site_name is the platform's own name on some systems ("BambooHR", 2026-10-03): it would
    # hit every doc + code line about that system
    out = [n for n in names if n.casefold() not in GENERIC] + [p for p in parts if len(p) >= 4 and p.casefold() not in GENERIC and not re.fullmatch(r"[\d-]+|wd\d+", p)]
    out += [str(c["value"]).strip() for c in snap["controls"]
            if c["control"] in ("input", "textarea", "editable") and len(str(c["value"]).strip()) >= 4]
    return list(dict.fromkeys(out))


def record_tenants(path: Path, lines: list[str]) -> int:
    """Append lines not there yet -> how many added."""
    have = set(path.read_text(encoding="utf-8").splitlines()) if path.exists() else set()
    new = [s for s in dict.fromkeys(lines) if s and "\n" not in s and s not in have]
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.writelines(s + "\n" for s in new)
    return len(new)


def measure(url: str, clicks: list[str], headless: bool = False) -> Path:
    if bad := refused(clicks):
        sys.exit(f"refused: {', '.join(map(repr, bad))} could send or sign - the applicant's own click, never ours")
    with throwaway(headless) as page:
        block = Block()
        block.install(page)
        test = canary(page, block)
        if failed := canary_failed(test):
            sys.exit(f"{failed}. Nothing measured")
        try:
            snaps = [load(page, url, clicks, block, n) for n in (1, 2)]
        except Refused as e:
            sys.exit(f"refused: {e}")
        names = employer(page)
    snap, seen = snaps[0]
    jsons = list({r["url"]: r for r in seen + snaps[1][1]}.values())
    host = urlsplit(url).hostname or "page"
    out = OUT / f"{host}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    page_data, unlabelled, outline = snap.pop("page_data"), snap.pop("unlabelled"), snap.pop("outline")
    data = {"url": url, "clicks": clicks, "canary": test, "snapshot": snap, "changed_ids": changed(snap, snaps[1][0]),
            "json": jsons, "page_data": page_data, "unlabelled": unlabelled, "outline": outline,
            "blocked": [b for b in block.log if b["after"] != "canary"], "loads": 2}
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    added = record_tenants(OUT / "tenants.txt", tenants(url, names, snap))
    summary(data, out, added)
    return out


def summary(data: dict, out: Path, added: int) -> None:
    snap, blocked = data["snapshot"], data["blocked"]
    kinds = Counter(c["control"] for c in snap["controls"])
    print(f"canary ok: 0 of {len(KINDS)} kinds of test write got through, each blocked")
    print(f"page loads: {data['loads']} (budget: 10 per site per bead)")
    print(f"controls: {len(snap['controls'])} ({', '.join(f'{k} {n}' for k, n in kinds.most_common())}), "
          f"required {sum(c['required'] for c in snap['controls'])}")
    for what in ("captcha", "blocked_frames", "other_frames", "not_readable"):
        if snap[what]:
            print(f"{what.replace('_', ' ')}: {len(snap[what])}")
    print(f"ids changed between loads: {len(data['changed_ids'])}")
    o = data["outline"]
    print(f"outline: {', '.join(o['steps']) or 'no step count'}; {len(o['headings'])} heading(s); buttons: {', '.join(o['buttons'][:8])}")
    if o.get("links"):
        print(f"links: {', '.join(o['links'][:12])}")
    if data["page_data"]:
        print(f"page data: {', '.join(f'window.{k} {len(json.dumps(v))} B' for k, v in data['page_data'].items())}")
    if data["unlabelled"]:
        print(f"boxes with no name found: {len(data['unlabelled'])} (markup around each in 'unlabelled')")
    print(f"JSON responses: {len(data['json'])}")
    for r in sorted(data["json"], key=lambda r: -r["bytes"])[:5]:
        u = urlsplit(r["url"])
        print(f"  {r['status']} {r['bytes']:>8} B  {u.hostname}{u.path}")
    print(f"blocked: {len(blocked)} ({', '.join(f'{k} {n}' for k, n in Counter(b['method'] for b in blocked).most_common()) or 'none'})")
    print(f"written: {out}")
    print(f"tenants.txt: {added} new line(s)")
