#!/usr/bin/env python3
"""plan-29g.7: can an application form be filled inside the Job Finder window's own browser tab?
Measurement only - nothing here ships. Scratch VS Code 1.140 (binary started directly, never via
launch.py, never ~/.vscode/argv.json): --user-data-dir/--extensions-dir/--shared-data-dir under
$D (mktemp -d /tmp/jfv.XXXX), folder = copy of the program + demo + the window's own settings
(`workspace.write`), throwaway browser storage (dies w/ $D). Scratch extension probe-ext/ (opens
tabs, starts js-debug's "Integrated Browser: Attach", asks for its CDP proxy).

  route1   --remote-debugging-port on 127.0.0.1 (CAN'T SHIP: comparison only; refused unless
           JF_ALLOW_ROUTE1=1 - the open port hands the whole window to any program): targets listed,
           Playwright connect_over_cdp fills the local form (text, select, check, radio, upload,
           cross-site frame)
  route2   js-debug CDP proxy -> raw CDP from Python on 127.0.0.1 (the only shippable route):
           same form via Runtime.evaluate, Input.*, DOM.setFileInputFiles; frames; debugger trap;
           what the user sees (screenshots, window only); write block + canary (lab.py rules)
  gh       route 2 on ONE public Greenhouse posting: block + canary first, dummy data, never Submit
  ghfill   the trial's own filler (window.Page + form.fill_page) on every question of one posting, same
           block + canary, synthetic answers; each dropdown read back off the page now + JF_LATE s later
  ghupload when the resume box is ready (plan-29g.25): the page's own storage-form request vs load vs idle;
           a choice before it answers (held JF_HOLD s), a second choice after; the shipped put_file on a
           fresh load. Same block + canary; the dummy PDF's POST to storage answered in the tab, never sent
  score    reCAPTCHA v3 demo score: window tab (opened plain, then reloaded w/ the debugger on) vs a
           Chrome started as Job Finder's own - relative hint only, never Submit
  restricted  untrusted folder (Restricted Mode): does the attach start?
  multipage   local form only (plan-k8n.12): page 1 filled, Next, page 2 filled - (a) debug session kept
           between runs w/ no client, (c) one process attached throughout; same site / other site / in place;
           a `debugger;` line every second; the user closes the tab; window reload
  raw      route 2 on ONE public posting of any system `systems.for_url` knows (plan-nko.6 Ashby, .13 Lever):
           level-3 block (+ lab.NAMED_READS, the owner's one exception) + canary first in the same tab;
           the page's `debugger;` pauses counted (skip off once, resumed in the handler, cap 20, then
           skip on), other-site frames listed + what each is, Input.insertText into one text box + read
           back, the dummy PDF chosen + what the page then tries to send (blocked). Never Submit.
           READY read as Playwright does, tenant parts scrubbed, tenants.txt appended: rawkit.py (plan-k8n.1)
           JF_NO_FILE=1: file box found, never chosen (Workable: its upload blocked breaks the form, plan-k8n.7);
           WIDGETS: radios + lists as the page draws them, what sits on top at each list's middle - read only;
           a system with APPLY (BambooHR): that button clicked once (real click) before READY is read (plan-k8n.10)
           Oracle's email box by name (never the honeypot text box); no box in the page -> the email box in a
           same-site frame (iCIMS ?in_iframe=1) through contentDocument, focused by script + Input.insertText (plan-k8n.16)
           boxes looked up through open shadow roots too; SmartRecruiters' resume box = its FILES, the deep page text
           read after the upload (name shown, its own error words) (plan-k8n.17)

usage: measure.py <stage> <$D> <checkout> <out json> <shots dir> [posting url]
$D must hold f/ (folder copy), ext/ (probe-ext + Claude installed), hold/ - see setup in the doc.
"""
import datetime
import json
import os
import pathlib
import platform
import secrets
import socket
import subprocess
import sys
import time
import urllib.request

STAGE = sys.argv[1]
if STAGE == "route1" and os.environ.get("JF_ALLOW_ROUTE1") != "1":
    sys.exit("route1 refused: --remote-debugging-port opens the whole window (workbench, terminal, Claude's chat) "
             "to any program on this computer. Comparison only - set JF_ALLOW_ROUTE1=1 to run it anyway")
D, SRC, OUT, SHOTS = (pathlib.Path(a).resolve() for a in sys.argv[2:6])
GH_URL = sys.argv[6] if len(sys.argv) > 6 else None
F, HOLD = D / "f", D / "hold"
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(SRC / "app")]
import formsite  # noqa: E402
import rawkit  # noqa: E402
from apply.cdp import CDP  # noqa: E402

CODE = "/Applications/Visual Studio Code.app/Contents/MacOS/Code"
CLI = "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"  # the binary itself opens a window
UNIQ = secrets.token_hex(3)
TITLE = f"JF form {UNIQ}"
RESUME = D / "Test_Resume.pdf"
READS = ("GET", "HEAD", "OPTIONS")
SCRUB: list[tuple[str, str]] = []  # (tenant text, placeholder): raw adds the links' tenant parts (rawkit.scrub_pairs)
TENANTS = SRC / ".data" / "measure" / "tenants.txt"  # every measured org, for the anonymity grep (lab.py's file)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(test, secs, every=0.25):
    end = time.time() + secs
    while time.time() < end:
        got = test()
        if got:
            return got
        time.sleep(every)
    return test()


n = 0


def ask(req, secs=40):
    global n
    n += 1
    name = f"{n:03d}"
    (HOLD / f"{name}.tmp").write_text(json.dumps(req))
    os.replace(HOLD / f"{name}.tmp", HOLD / f"{name}.req")
    res = HOLD / f"{name}.res"
    if not wait_for(res.exists, secs, 0.1):
        return {"req": req, "error": "no answer"}
    return json.loads(res.read_text())


def running():
    return subprocess.run(["pgrep", "-f", f"{D.name}/data"], capture_output=True).returncode == 0


def launch(port=None, trust=True):
    for f in HOLD.iterdir():
        f.unlink()
    args = [CODE, "--user-data-dir", D / "data", "--extensions-dir", D / "ext", "--shared-data-dir", D / "shared",
            *(["--disable-workspace-trust"] if trust else []),
            *([f"--remote-debugging-port={port}"] if port else []), "--new-window", F]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ELECTRON_", "VSCODE_"))}
    env["JF_PROBE_HOLD"] = str(HOLD)
    t = time.time()
    proc = subprocess.Popen([str(a) for a in args], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    up = wait_for(lambda: (HOLD / "up.json").exists(), 90, 0.25)
    if up:  # tabs restored from the last run would match urlFilter too
        ask({"do": "command", "id": "workbench.action.closeAllEditors"})
    return proc, {"args": [str(a).replace(str(D), "$D") for a in args[1:]], "up": bool(up),
                  "upMs": round((time.time() - t) * 1000),
                  "upInfo": json.loads((HOLD / "up.json").read_text()) if up else None}


def quit_(proc):
    ask({"do": "quit"}, 20)
    try:
        proc.wait(30)
        return {"killed": False}
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
        time.sleep(3)
        subprocess.run(["pkill", "-9", "-f", f"{D.name}/data"])
        return {"killed": True}


WINDOWS = """ObjC.import('CoreGraphics'); ObjC.import('Foundation');
function run(argv) {
  var all = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0, 0))), pid = Number(argv[0]);
  return JSON.stringify(all.filter(function (w) { return w.kCGWindowOwnerPID === pid && w.kCGWindowLayer === 0; })
    .map(function (w) { return { id: w.kCGWindowNumber, name: w.kCGWindowName || '', b: w.kCGWindowBounds }; }));
}"""


def screenshot(name, proc):
    """This window only (-l <id>), never the whole screen (the owner's)."""
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", WINDOWS, str(proc.pid)], capture_output=True, text=True)
    try:
        wins = json.loads(r.stdout)
    except ValueError:
        return {"error": r.stderr.strip()[-300:]}
    if not wins:
        return {"error": f"no window for pid {proc.pid}"}
    win = max(wins, key=lambda w: w["b"]["Width"] * w["b"]["Height"])
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), path], check=False)
    return {"path": str(path), "bytes": path.stat().st_size if path.exists() else 0}


def make_resume():
    """Dummy PDF: never the user's resume."""
    body = b"%PDF-1.4\n% JF dummy resume - Test Person - not a real applicant\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    RESUME.write_bytes(body)
    return {"name": RESUME.name, "size": len(body)}


def save(result):
    if SCRUB:  # string values only, any case, longest first: a key is never cut
        result = rawkit.scrub_values(json.loads(json.dumps(result, default=str)), sorted(SCRUB, key=lambda t: -len(t[0])))
    text = json.dumps(result, indent=1, default=str)
    for a, b in ((str(D), "$D"), (str(SRC), "<checkout>"), (str(SHOTS), "<shots>")):
        text = text.replace(a, b)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + "\n")


# ---------------------------------------------------------------- route 1: debugging port
def route1(result):
    from playwright.sync_api import sync_playwright

    port = free_port()
    proc, result["launch"] = launch(port=port)
    home, other, close = formsite.serve(TITLE)
    try:
        ask({"do": "open", "url": f"{home}/form"})
        wait_for(lambda: any(t["label"] == TITLE for g in ask({"do": "tabs"}).get("tabs", []) for t in g["tabs"]), 20, 0.5)
        time.sleep(2)
        listen = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
        result["listen"] = [l.split()[8] for l in listen.splitlines()[1:]]
        targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5))
        version = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=5))
        result["version"] = {k: version.get(k) for k in ("Browser", "Protocol-Version", "User-Agent")}
        result["targets"] = [{"type": t["type"], "title": t["title"][:80], "url": t["url"][:120]} for t in targets]
        # code execution from the debugging port: the workbench page runs commands (terminal = shell)
        wb = next((t for t in targets if t["type"] == "page" and "workbench" in t["url"]), None)
        if wb:
            c = CDP("127.0.0.1", port, "/devtools/page/" + wb["id"])
            try:
                result["workbenchEval"] = c.evaluate("({hasRequire: typeof require, vscodeGlobal: typeof globalThis.vscode, "
                                                     "title: document.title})")
            except Exception as e:
                result["workbenchEval"] = {"error": str(e)}
            c.close()
        dummy = make_resume()
        fill = result["fill"] = {"resume": dummy}
        with sync_playwright() as p:
            t = time.time()
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            fill["connectMs"] = round((time.time() - t) * 1000)
            pages = [pg for ctx in browser.contexts for pg in ctx.pages]
            fill["contexts"] = len(browser.contexts)
            fill["pages"] = [pg.url[:100] for pg in pages]
            page = next((pg for pg in pages if pg.url.startswith(f"{home}/form")), None)
            if not page:
                fill["error"] = "form page not among Playwright's pages"
            else:
                steps = fill["steps"] = {}

                def step(name, fn):
                    t = time.time()
                    try:
                        fn()
                        steps[name] = {"ok": True, "ms": round((time.time() - t) * 1000)}
                    except Exception as e:
                        steps[name] = {"ok": False, "error": str(e).splitlines()[0][:300]}
                step("text", lambda: page.fill("#first_name", "Test"))
                step("email", lambda: page.fill("#email", "test.person@example.com"))
                step("textarea", lambda: page.fill("#why", "Dummy answer for a measurement."))
                step("select", lambda: page.select_option("#country", "United States"))
                step("combo", lambda: (page.click("#combo"), page.keyboard.type("Spring"),
                                       page.click("#combo-list [role=option] >> text=Springfield, Illinois, United States")))
                step("check", lambda: page.check("#agree"))
                step("radio", lambda: page.check("#auth_yes"))
                step("upload", lambda: page.set_input_files("#resume", str(RESUME)))
                frame = page.frame_locator("#other")
                step("frameText", lambda: frame.locator("#frame_name").fill("Frame Test"))
                step("frameUpload", lambda: frame.locator("#frame_resume").set_input_files(str(RESUME)))
                time.sleep(1)
                fill["state"] = page.evaluate("formState()")
                fr = next((f for f in page.frames if f.url.startswith(f"{other}/frame-form")), None)
                fill["frameState"] = fr.evaluate("frameState()") if fr else None
                fill["frames"] = [f.url[:80] for f in page.frames]
                fill["frameStateViaLocator"] = attempt(lambda: page.frame_locator("#other").locator("body").evaluate("() => frameState()"))
                fill["shot"] = screenshot("route1-local-filled", proc)
        # what else the port reaches: Claude's chat panel open, list again
        result["claudeOpen"] = ask({"do": "command", "id": "claude-vscode.sidebar.open"}).get("error") or "ok"
        time.sleep(8)
        targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5))
        result["targetsWithClaude"] = [{"type": t["type"], "title": t["title"][:80], "url": t["url"][:120]} for t in targets]
        result["shotClaude"] = screenshot("route1-claude-open", proc)
    finally:
        result["quit"] = quit_(proc)
        close()
        result["siteLog"] = formsite.log[:]


# ---------------------------------------------------------------- setup (once per $D)
def run(cmd, cwd=None, timeout=600):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd or F, capture_output=True, text=True, timeout=timeout)
    return {"cmd": [str(c).replace(str(D), "$D") for c in cmd], "rc": r.returncode, "tail": (r.stdout + r.stderr).strip()[-300:]}


def vsix():
    """probe-ext/ packed by hand: a vsix is a zip w/ a manifest + content types + extension/."""
    import zipfile
    meta = json.loads((HERE / "probe-ext" / "package.json").read_text())
    ident = f'{meta["publisher"]}.{meta["name"]}'
    manifest = (f'<?xml version="1.0" encoding="utf-8"?><PackageManifest Version="2.0.0" '
                f'xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" '
                f'Id="{meta["name"]}" Version="{meta["version"]}" Publisher="{meta["publisher"]}"/><DisplayName>{meta["displayName"]}'
                f'</DisplayName><Description xml:space="preserve">{meta["description"]}</Description><Properties>'
                f'<Property Id="Microsoft.VisualStudio.Code.Engine" Value="{meta["engines"]["vscode"]}"/></Properties></Metadata>'
                f'<Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets>'
                f'<Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>'
                f'</Assets></PackageManifest>')
    types = ('<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension=".json" ContentType="application/json"/><Default Extension=".js" ContentType="application/javascript"/>'
             '<Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>')
    out = D / "form-probe.vsix"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("extension.vsixmanifest", manifest)
        z.writestr("[Content_Types].xml", types)
        for f in ("package.json", "extension.js"):
            z.write(HERE / "probe-ext" / f, f"extension/{f}")
    return out, ident


def setup(result):
    """$D/f = copy of the program + demo data (app/tests/demo.py: no real resume) + the window's own
    settings for Claude; $D/ext = probe-ext + Claude's extension (marketplace)."""
    import shutil
    F.mkdir(parents=True, exist_ok=True)
    HOLD.mkdir(exist_ok=True)
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy(SRC / name, F)
    steps = result["steps"] = [run(["uv", "run", "python", "app/tests/demo.py"])]
    (F / ".data").mkdir(exist_ok=True)
    (F / ".data" / "ai").write_text("claude\n")
    steps.append(run(["uv", "run", "python", "-c", "import sys; sys.path.insert(0, 'app'); import workspace; workspace.write('claude')"]))
    out, ident = vsix()
    base = [CLI, "--user-data-dir", D / "data", "--extensions-dir", D / "ext", "--shared-data-dir", D / "shared"]
    steps += [run([*base, "--install-extension", out]), run([*base, "--install-extension", "anthropic.claude-code"]),
              run([*base, "--list-extensions", "--show-versions"])]
    result["resume"] = make_resume()


def ext(result):
    """Re-pack + reinstall probe-ext only (after an edit)."""
    out, ident = vsix()
    base = [CLI, "--user-data-dir", D / "data", "--extensions-dir", D / "ext", "--shared-data-dir", D / "shared"]
    result["steps"] = [run([*base, "--install-extension", out, "--force"]), run([*base, "--list-extensions", "--show-versions"])]


# ---------------------------------------------------------------- route 2: js-debug's CDP proxy
from urllib.parse import urlsplit  # noqa: E402

QUIET = {"suppressDebugToolbar": True, "suppressDebugStatusbar": True, "suppressDebugView": True}


# document first, then each open shadow root in page order: SmartRecruiters' boxes live in them (plan-k8n.17);
# a box in the document itself is found as before
DEEP_Q = ("(s => { const f = r => { const hit = r.querySelector(s); if (hit) return hit;"
          " for (const e of r.querySelectorAll('*')) if (e.shadowRoot) { const h = f(e.shadowRoot); if (h) return h; }"
          " return null; }; return f(document); })")


def q(sel):
    """An element by selector (shadow roots too), or 'js:<expression>' as is."""
    return sel[3:] if sel.startswith("js:") else f"{DEEP_Q}({json.dumps(sel)})"


# a framework's own setter sees script-set values only through the prototype's setter + events
SET = """((e, v) => { const proto = e instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype
  : e instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(e, v);
  e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})); return e.value; })"""


def set_value(c, sel, v):
    return c.evaluate(f"{SET}({q(sel)}, {json.dumps(v)})")


def center(c, js_el):
    return c.evaluate(f"(() => {{ const e = {js_el}; e.scrollIntoView({{block: 'center', behavior: 'instant'}}); const r = e.getBoundingClientRect();"
                      " return [r.x + r.width / 2, r.y + r.height / 2]; })()")


def click(c, js_el, wait=True):
    """A real mouse click (isTrusted) at the element's middle, CSS px of the tab's viewport."""
    x, y = center(c, js_el)
    c.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
    c.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
    (c.send if wait else c.post)("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})


def keys(c, text):
    for ch in text:
        c.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": ch, "text": ch, "unmodifiedText": ch})
        c.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch})


def upload(c, sel, path):
    oid = c.send("Runtime.evaluate", {"expression": q(sel)})["result"]["objectId"]
    c.send("DOM.setFileInputFiles", {"files": [str(path)], "objectId": oid})


def tab_shot(c, name):
    import base64
    try:
        data = c.send("Page.captureScreenshot", {"format": "png"}, 20)["data"]
    except Exception as e:
        return {"error": str(e)[:200]}
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    path.write_bytes(base64.b64decode(data))
    return {"path": str(path), "bytes": path.stat().st_size}


def attempt(fn):
    t = time.time()
    try:
        value = fn()
        return {"ok": True, "ms": round((time.time() - t) * 1000), **({"value": value} if value is not None else {})}
    except Exception as e:
        return {"ok": False, "error": str(e).splitlines()[0][:300]}


def quietly(fn):
    try:
        return fn()
    except Exception:
        return None


def attach(url_filter, options=None, secs=40):
    """Start js-debug's "Integrated Browser: Attach" on the one tab matching url_filter, get a CDP
    proxy per new debug session -> (answer, {session: {proxy, href}}, {href: CDP})."""
    res = ask({"do": "attach", "urlFilter": url_filter, "options": options or {}, "waitMs": 10000, "settleMs": 2500}, secs)
    found, conns = {}, {}
    for sid, px in (res.get("proxies") or {}).items():
        row = found[sid] = {"proxy": px}
        if not isinstance(px, dict) or not px.get("port"):
            continue
        try:
            c = CDP(px["host"], px["port"], px["path"])
            row["href"] = c.evaluate("location.href", timeout=5)
            conns[row["href"]] = c
        except Exception as e:
            row["error"] = str(e)[:200]
    return res, found, conns


def later(found, conns, wait=4):
    """Debug sessions that started after the attach answered (a frame's own?) -> their proxies."""
    time.sleep(wait)
    rows = {}
    for s in ask({"do": "sessions"}).get("sessions", []):
        if s["id"] in found:
            continue
        px = ask({"do": "proxy", "id": s["id"]}).get("proxy")
        row = rows[s["id"]] = {"name": s["name"], "parent": s["parent"], "proxy": px}
        if isinstance(px, dict) and px.get("port"):
            try:
                x = CDP(px["host"], px["port"], px["path"])
                row["href"] = x.evaluate("location.href", timeout=5)
                conns[row["href"]] = x
            except Exception as e:
                row["error"] = str(e)[:200]
    return rows


class Flat:
    """CDP to an out-of-process frame through its page's proxy: Target.attachToTarget flatten true,
    then messages carrying its sessionId on the same socket (non-flat is refused, measured)."""

    def __init__(self, c, target_id):
        self.c = c
        self.sid = c.send("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]

    def send(self, method, params=None, timeout=15):
        return self.c.send(method, params, timeout, session=self.sid)

    evaluate = CDP.evaluate

    def close(self):
        pass


def tab_into_frame(c, before_sel, text):
    """No session in the frame: focus the box before it, Tab into the frame, type (real key events)."""
    c.evaluate(f"{q(before_sel)}.focus()")
    c.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
    c.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
    time.sleep(0.2)
    c.send("Input.insertText", {"text": text})
    return c.evaluate("document.activeElement && document.activeElement.id")


def pick(conns, start):
    return next((c for href, c in conns.items() if href and href.startswith(start)), None)


def site(url):
    host = urlsplit(url).hostname or ""
    return host if host.replace(".", "").isdigit() else ".".join(host.split(".")[-2:])


# an inert WebSocket: the page's script carries on (a throwing stub stopped the canary, measured),
# nothing connects. In-page only - a page script could reach a pristine one; the network layer can't
# be asked through this proxy (setBlockedURLs let ws through, measured)
WS_STUB = """(() => { class WebSocket extends EventTarget {
  constructor(url) { super(); this.url = String(url); this.readyState = 0; this.bufferedAmount = 0; this.protocol = '';
    this.extensions = ''; this.binaryType = 'blob'; (window.__jfWs = window.__jfWs || []).push(this.url); }
  send() {} close() { this.readyState = 3; } }
  Object.assign(WebSocket, {CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3}); window.WebSocket = WebSocket; })();"""


class Block:
    """lab.py's rule on route 2, one CDP connection = one target: every non-read request failed
    before it leaves (Fetch, request stage; a dedicated worker's too), WebSockets refused
    (Network.setBlockedURLs, new urlPatterns form first), service workers bypassed. level 2 also
    fails another site's frame before it loads (it would be its own target, out of this Fetch's
    reach); level 3 also swaps in an inert WebSocket before the page's scripts run."""

    def __init__(self, c, level, named=False):
        self.c, self.level, self.log, self.seen, self.step, self.reads = c, level, [], [], "start", 0
        self.main, self.named, self.passed = None, named, []

    def install(self):
        c = self.c
        c.send("JsDebug.subscribe", {"events": ["Fetch.requestPaused", "Network.requestWillBeSent", "Network.webSocketCreated"]})
        c.on("Fetch.requestPaused", self.paused)
        c.on("Network.requestWillBeSent", self.sent)
        c.on("Network.webSocketCreated", lambda p, m: self.seen.append({"ws": p.get("url", "")[:200], "after": self.step}))
        c.send("Network.enable")
        c.send("Network.setBypassServiceWorker", {"bypass": True})
        try:
            c.send("Network.setBlockedURLs", {"urlPatterns": [{"urlPattern": "ws://*", "block": True},
                                                               {"urlPattern": "wss://*", "block": True}]})
            how = "urlPatterns"
        except RuntimeError:
            c.send("Network.setBlockedURLs", {"urls": ["ws://*", "wss://*"]})
            how = "urls"
        top = c.send("Page.getFrameTree")["frameTree"]["frame"]
        self.main, self.top = top["id"], top["url"]
        if self.level >= 3:
            c.send("Page.addScriptToEvaluateOnNewDocument", {"source": WS_STUB, "runImmediately": True})
        c.send("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
        return {"level": self.level, "blockedUrls": how}

    def paused(self, p, msg):
        r = p["request"]
        frame_doc = p.get("resourceType") == "Document" and p.get("frameId") != self.main
        if self.level >= 2 and frame_doc and self.top and site(r["url"]) != site(self.top):
            self.log.append({"method": r["method"], "url": r["url"][:300], "type": "other-site frame", "after": self.step})
            return self.c.post("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"})
        if p.get("resourceType") == "Document" and p.get("frameId") == self.main:
            self.top = r["url"]
        if r["method"] in READS:
            self.reads += 1
            return self.c.post("Fetch.continueRequest", {"requestId": p["requestId"]})
        op = self.named and named_read(r)
        if op:  # lab.NAMED_READS, exactly as lab.Block lets it through (owner OK 2026-10-05)
            self.passed.append({"method": r["method"], "url": r["url"][:300], "op": op, "after": self.step})
            return self.c.post("Fetch.continueRequest", {"requestId": p["requestId"]})
        self.log.append({"method": r["method"], "url": r["url"][:300], "type": p.get("resourceType"), "after": self.step,
                         "contentType": next((v for k, v in r.get("headers", {}).items() if k.lower() == "content-type"), "")[:60],
                         "body": r.get("hasPostData", False)})
        self.c.post("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"})

    top = None

    def sent(self, p, msg):
        r = p["request"]
        if r["method"] not in READS:
            self.seen.append({"method": r["method"], "url": r["url"][:200], "type": p.get("type"), "after": self.step})


def named_read(r):
    """lab.named_read on a Fetch.requestPaused request: the body from postData, else its entries."""
    import base64
    from apply import lab
    body = r.get("postData")
    if body is None and r.get("postDataEntries"):
        try:
            body = b"".join(base64.b64decode(e.get("bytes", "")) for e in r["postDataEntries"]).decode()
        except (ValueError, UnicodeDecodeError):
            return None
    return lab.named_read(r["method"], r["url"], body)


def canary(c, block, label):
    """lab.py's canary (every way a page sends w/o the user) at a local listener -> what arrived."""
    from apply import lab
    listener = lab.Listener({})
    try:
        names = {"home": listener.home, "other": listener.other, "ws": listener.home.replace("http", "ws", 1)}
        listener.pages = {"/canary.html": ("text/html", lab.CANARY % names),
                          "/frame.html": ("text/html", lab.FRAME % (names | {"ws": listener.other.replace("http", "ws", 1)}))}
        if block:
            block.step = label
        c.send("Page.navigate", {"url": listener.home + "/canary.html"})
        fired = wait_for(lambda: quietly(lambda: c.evaluate("window.fired === true", timeout=3)), 10)
        time.sleep(2.5)  # beacon + keepalive leave after the page's own work
        received = sorted(lab.kind(p) for _, p in listener.writes)
        blocked = sorted({lab.kind(urlsplit(b["url"]).path) for b in (block.log if block else []) if b["after"] == label})
        stubbed = quietly(lambda: c.evaluate("window.__jfWs || []", timeout=3))
        return {"loaded": "/canary.html" in listener.gets, "fired": bool(fired), "received": received, "blocked": blocked,
                "wsStubbed": stubbed,
                "neither": sorted(lab.KINDS - set(received) - set(blocked)),
                "seen": [s for s in (block.seen if block else []) if s["after"] == label]}
    finally:
        listener.close()


def trap(c, label):
    """A page's `debugger;` (anti-bot scripts use them) while js-debug is attached: paused?
    Needs JsDebug.subscribe Debugger.paused on c first."""
    t0, e0 = len(formsite.log), len(c.events)
    click(c, q("#trapbtn"), wait=False)
    passed = wait_for(lambda: any("trap-passed" in e["path"] for e in formsite.log[t0:]), 4)
    return {"passed": bool(passed), "pausedEvent": any(e.get("method") == "Debugger.paused" for e in c.events[e0:])}


def resume(c):
    """Debugger.resume through the proxy; js-debug's own Continue command when that fails."""
    r = attempt(lambda: c.send("Debugger.resume", {}, 5))
    return r if r["ok"] else {"cdp": r, "command": ask({"do": "command", "id": "workbench.action.debug.continue"}).get("error") or "ok"}


def route2(result):
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    dummy = make_resume()
    try:
        ask({"do": "open", "url": f"{home}/form"})
        wait_for(lambda: any(t["label"] == TITLE for g in ask({"do": "tabs"}).get("tabs", []) for t in g["tabs"]), 20, 0.5)
        time.sleep(2)
        result["shotBefore"] = screenshot("route2-local-before", proc)
        res, found, conns = attach(f"{home}/form*")
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions", "events", "tabs")} | {"found": found}
        time.sleep(1.5)
        result["shotAttached"] = screenshot("route2-local-attached", proc)
        c, fc = pick(conns, f"{home}/form"), pick(conns, f"{other}/frame-form")
        if not c:
            result["error"] = "no CDP proxy reached the form's tab"
            return
        result["later"] = later(found, conns)  # a session for the other site's frame after the settle?
        fc = fc or pick(conns, f"{other}/frame-form")
        result["frameVia"] = "own debug session" if fc else None
        if not fc:
            frame_id = quietly(lambda: next(t["targetId"] for t in c.send("Target.getTargets")["targetInfos"]
                                           if t["type"] == "iframe" and t["url"].startswith(f"{other}/frame-form")))
            got = attempt(lambda: Flat(c, frame_id))
            result["frameAttach"] = {k: v for k, v in got.items() if k != "value"} | {"targetFound": bool(frame_id)}
            if got["ok"]:
                fc = got["value"]
                href = result["frameHref"] = attempt(lambda: fc.evaluate("location.href", timeout=5))
                if href.get("value", "").startswith(f"{other}/"):
                    result["frameVia"] = "page's proxy: Target.attachToTarget flatten true + sessionId"
                else:
                    fc = None
        result["subscribe"] = attempt(lambda: c.send("JsDebug.subscribe", {"events": ["Debugger.paused", "Debugger.resumed"]}))
        result["frameTree"] = attempt(lambda: [f["frame"]["url"][:80] for f in c.send("Page.getFrameTree")["frameTree"].get("childFrames", [])])
        result["targets"] = attempt(lambda: [(t["type"], t["url"][:80]) for t in c.send("Target.getTargets")["targetInfos"]])
        fill = result["fill"] = {"resume": dummy}
        fill["text: click + Input.insertText"] = attempt(lambda: (click(c, q("#first_name")), c.send("Input.insertText", {"text": "Test"}))[1])
        fill["email: script sets value"] = attempt(lambda: set_value(c, "#email", "test.person@example.com"))
        fill["textarea: click + key events"] = attempt(lambda: (click(c, q("#why")), keys(c, "Dummy answer for a measurement."))[1])
        fill["select: script sets value"] = attempt(lambda: set_value(c, "#country", "United States"))

        def combo():
            click(c, q("#combo"))
            c.send("Input.insertText", {"text": "Spring"})
            time.sleep(0.4)
            click(c, "[...document.querySelectorAll('#combo-list [role=option]')]"
                     ".find((o) => o.textContent === 'Springfield, Illinois, United States')")
        fill["combo: click, type, click option"] = attempt(combo)
        fill["check: mouse click"] = attempt(lambda: click(c, q("#agree")))
        fill["radio: script click()"] = attempt(lambda: c.evaluate(f"{q('#auth_yes')}.click()"))
        fill["upload: DOM.setFileInputFiles"] = attempt(lambda: upload(c, "#resume", RESUME))
        if not fc:
            fill["frame text: Tab into it + type"] = attempt(lambda: tab_into_frame(c, "#resume", "Frame Typed"))
        if fc:
            fill["frame text: script sets value"] = attempt(lambda: set_value(fc, "#frame_name", "Frame Test"))
            fill["frame upload: DOM.setFileInputFiles"] = attempt(lambda: upload(fc, "#frame_resume", RESUME))
        time.sleep(1)
        fill["state"] = attempt(lambda: c.evaluate("formState()"))
        fill["frameState"] = attempt(lambda: fc.evaluate("frameState()")) if fc else {"ok": False, "error": "no frame session"}
        fill["tabShot"] = tab_shot(c, "route2-local-tab")
        result["shotFilled"] = screenshot("route2-local-filled", proc)

        tr = result["trap"] = {"default": trap(c, "default")}
        if not tr["default"]["passed"]:
            time.sleep(1)
            tr["shotPaused"] = screenshot("route2-trap-paused", proc)
            tr["resume"] = resume(c)
            tr["afterResume"] = bool(wait_for(lambda: any("trap-passed" in e["path"] for e in formsite.log), 4))
            tr["skipAllPauses"] = attempt(lambda: c.send("Debugger.setSkipAllPauses", {"skip": True}, 5))
            tr["skipped"] = trap(c, "skip")
            if not tr["skipped"]["passed"]:
                tr["resume2"] = resume(c)

        for x in conns.values():
            x.close()
        stop = ask({"do": "stop"})
        time.sleep(2)
        result["stop"] = {"tabs": [t["label"] for g in stop.get("tabs") or [] for t in g["tabs"]], "events": stop.get("events")}
        result["shotStopped"] = screenshot("route2-local-stopped", proc)

        # a fresh tab (the stop above closed the form's), quiet options: what the user sees; trap again
        ask({"do": "open", "url": f"{home}/form?again"})
        time.sleep(2.5)
        res, found, conns = attach(f"{home}/form*", QUIET)
        result["attachQuiet"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions")} | {"found": found}
        time.sleep(1.5)
        result["shotQuiet"] = screenshot("route2-local-attached-quiet", proc)
        c = pick(conns, f"{home}/form")
        if c:
            quietly(lambda: c.send("JsDebug.subscribe", {"events": ["Debugger.paused", "Debugger.resumed"]}))
            result["trapQuiet"] = trap(c, "quiet")
            if not result["trapQuiet"]["passed"]:
                time.sleep(1)
                result["shotQuietPaused"] = screenshot("route2-trap-paused-quiet", proc)
                result["trapQuiet"]["resume"] = resume(c)
            result["canary"] = {"off": canary(c, None, "off")}
        else:
            result["error"] = "quiet attach: no CDP proxy reached the form's tab"

        # write block per level, each on its own fresh tab + session (Fetch + init scripts stay on a
        # session once set); each ends a different way, no pause: does the tab survive the end?
        ends = {1: "stopDebugging(page session)", 2: "stopDebugging() all", 3: "command workbench.action.debug.disconnect"}
        for level in (1, 2, 3):
            for x in conns.values():
                x.close()
            if level == 1:  # the quiet session above: end all of it first (its tab closes, measured above)
                ask({"do": "stop"})
                time.sleep(1.5)
            ask({"do": "open", "url": f"{home}/blank{level}"})
            time.sleep(2)
            res, found, conns = attach(f"{home}/blank{level}*", QUIET)
            c = pick(conns, f"{home}/blank{level}")
            row = result.setdefault("canary", {}).setdefault(f"level{level}", {})
            if not c:
                row |= {"error": "no CDP proxy", "found": found}
                continue
            block = Block(c, level)
            row["install"] = attempt(block.install)
            row |= canary(c, block, f"level{level}")
            # the end: does the tab survive?
            for x in conns.values():
                x.close()
            page_sid = next((sid for sid, f in found.items() if (f.get("href") or "").startswith(f"{home}/")), None)
            if level == 1:
                end_res = ask({"do": "stop", "id": page_sid})
            elif level == 2:
                end_res = ask({"do": "stop"})
            else:
                end_res = ask({"do": "command", "id": "workbench.action.debug.disconnect"})
            time.sleep(2.5)
            after = ask({"do": "sessions"})
            row["end"] = {"how": ends[level], "error": end_res.get("error"), "sessionsLeft": len(after.get("sessions", [])),
                          "tabsAfter": [t["label"] for g in after.get("tabs") or [] for t in g["tabs"]]}
            if after.get("sessions"):
                ask({"do": "stop"})
                time.sleep(1.5)
        result["siteWrites"] = [e for e in formsite.log if e["write"]]
    finally:
        result["quit"] = quit_(proc)
        close()
        result["siteLog"] = formsite.log[:]


# ---------------------------------------------------------------- one public Greenhouse posting, route 2
GH_FILL = [("first_name", "click", "Test"), ("last_name", "script", "Person"),
           ("email", "script", "test.person@example.com"), ("phone", "keys", "5555550100")]
GH_FIELDS = """[...document.querySelectorAll('input:not([type=hidden]), select, textarea')].map((e) => ({id: e.id,
  type: e.type, role: e.getAttribute('role') || '', label: ((e.labels && e.labels[0] && e.labels[0].innerText) || e.getAttribute('aria-label') || '').slice(0, 60)}))"""


def gh(result):
    """Block + canary first on a local page in the same tab, then the posting: dummy data, never Submit."""
    if not GH_URL or "greenhouse.io/" not in GH_URL:
        sys.exit("gh needs a job-boards.greenhouse.io posting link")
    level = int(os.environ.get("JF_BLOCK_LEVEL", "3"))
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    dummy = make_resume()
    try:
        ask({"do": "open", "url": f"{home}/blank"})
        time.sleep(2)
        res, found, conns = attach(f"{home}/blank*", QUIET)
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions")} | {"found": found}
        time.sleep(1.5)
        result["shotAttached"] = screenshot("gh-route2-attached-quiet", proc)  # quiet options: toolbar shown?
        c = pick(conns, f"{home}/blank")
        if not c:
            result["error"] = "no CDP proxy reached the tab"
            return
        block = Block(c, level)
        result["install"] = attempt(block.install)
        result["canary"] = canary(c, block, "canary")
        if result["canary"]["received"] or not result["canary"]["loaded"]:
            result["refused"] = "canary received writes (or never loaded): posting not opened"
            return
        block.step = "load"
        t = time.time()
        c.send("Page.navigate", {"url": GH_URL})
        result["loaded"] = bool(wait_for(lambda: quietly(lambda: c.evaluate("document.readyState === 'complete' && !!document.querySelector('#first_name')", timeout=3)), 40, 0.5))
        result["loadMs"] = round((time.time() - t) * 1000)
        time.sleep(4)  # its own scripts settle (greenhouse.md: upload too early fails)
        result["url"] = quietly(lambda: c.evaluate("location.host + location.pathname"))
        result["fields"] = quietly(lambda: c.evaluate(GH_FIELDS))
        result["scrollBehavior"] = quietly(lambda: c.evaluate("getComputedStyle(document.documentElement).scrollBehavior"))
        fill = result["fill"] = {"resume": dummy}

        def typed(sel, value, how):
            click(c, q(sel))
            time.sleep(0.4)  # greenhouse.md: focus, wait 400 ms
            focused = c.evaluate("document.activeElement && document.activeElement.id")
            c.send("Input.insertText", {"text": value}) if how == "click" else keys(c, value)
            return {"focused": focused}

        for box, how, value in GH_FILL:
            sel = f'[id="{box}"]'
            block.step = f"fill {box}"
            if how in ("click", "keys"):
                fill[box] = attempt(lambda: typed(sel, value, how))
            else:
                fill[box] = attempt(lambda: set_value(c, sel, value))
            fill[box]["readBack"] = quietly(lambda: c.evaluate(f"{q(sel)}.value"))
        block.step = "fill resume"
        fill["resume upload"] = attempt(lambda: upload(c, '[id="resume"]', RESUME))
        time.sleep(3)
        fill["resume shown"] = quietly(lambda: c.evaluate(f"document.body.innerText.includes({json.dumps(RESUME.name)})"))
        fill["resume box"] = quietly(lambda: c.evaluate("(() => { let e = document.querySelector('#resume');"
                                                         " for (let i = 0; i < 6 && e; i++) { e = e.parentElement;"
                                                         " if (e && /Resume/i.test(e.innerText)) return e.innerText.slice(0, 200); } return null; })()"))
        # one react-select choice: the first Yes/No question on the form, answer "No"
        block.step = "fill choice"
        choice = quietly(lambda: c.evaluate("""(() => { for (const e of document.querySelectorAll('input[role=combobox][id^=question_]')) {
          const lab = (e.labels && e.labels[0] && e.labels[0].innerText) || ''; if (/previously worked|ever worked|worked at/i.test(lab)) return e.id; }
          const e = document.querySelector('input[role=combobox][id^=question_]'); return e && e.id; })()"""))
        fill["choice id"] = choice
        if choice:
            sel = f'[id="{choice}"]'

            def pick_no():
                click(c, q(sel))
                c.send("Input.insertText", {"text": "No"})
                time.sleep(0.6)
                click(c, "[...document.querySelectorAll('.select__menu [role=option]')].find((o) => o.innerText.trim() === 'No')")
                time.sleep(0.4)
                return c.evaluate(f"(() => {{ const e = {q(sel)}; const root = e.closest('.select__container, .select-shell')"
                                  " || e.parentElement.parentElement.parentElement.parentElement;"
                                  " const v = root.querySelector('[class*=single-value]'); return v && v.innerText; })()")
            fill["choice: click, type, click option"] = attempt(pick_no)
        time.sleep(1)
        fill["tabShot"] = tab_shot(c, "gh-route2-filled-tab")
        result["shotFilled"] = screenshot("gh-route2-filled", proc)
        result["submitClicked"] = False
        result["block"] = {"reads": block.reads, "failed": block.log, "seenWrites": block.seen}
    finally:
        result["quit"] = quit_(proc)
        close()


# ---------------------------------------------------------------- the shipped filler, every question (plan-29g.20)
# each dropdown's shown choice (react-select single-value / multi-value tags), straight off the page
SHOWN = """Object.fromEntries([...document.querySelectorAll('input[role=combobox]')].map((e) => {
  const box = e.closest('.select__container') || e.closest('.select-shell') || e.parentElement;
  return [e.id, [...box.querySelectorAll('[class*=single-value], [class*=multi-value__label]')].map((v) => v.innerText.trim())]; }))"""


def ghfill(result):
    """The trial's own filler (window.Page + form.fill_page, as `fill --in-window`) on every question of one
    posting, synthetic answers (trial.synthetic): block + canary first, never Submit. Each dropdown read
    back off the page at once and again after LATE s - what the filler said vs what the page shows."""
    from apply import form, trial, window
    from apply.systems import greenhouse
    if not GH_URL or "greenhouse.io/" not in GH_URL:
        sys.exit("ghfill needs a job-boards.greenhouse.io posting link")
    late = int(os.environ.get("JF_LATE", "8"))
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    try:
        ask({"do": "open", "url": f"{home}/blank"})
        time.sleep(2)
        res, found, conns = attach(f"{home}/blank*", QUIET)
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions")}
        c = pick(conns, f"{home}/blank")
        if not c:
            result["error"] = "no CDP proxy reached the tab"
            return
        block = Block(c, 3)
        result["install"] = attempt(block.install)
        result["canary"] = canary(c, block, "canary")
        if result["canary"]["received"] or not result["canary"]["loaded"]:
            result["refused"] = "canary received writes (or never loaded): posting not opened"
            return
        page = window.Page(c)
        page.quiet()
        block.step = "load"
        page.goto(GH_URL)
        form.open_form(page, greenhouse, GH_URL)
        page.wait_for_load_state("networkidle")
        result["focus"] = quietly(lambda: c.evaluate("[document.hasFocus(), document.visibilityState, devicePixelRatio, innerWidth]"))
        qs = greenhouse.questions(GH_URL)
        for q in qs:
            q["answer"], why = trial.synthetic(q)
        asked = [q for q in qs if q["answer"] is not None]
        resume, letter = trial.files(D)

        def before(q):
            block.step = f"fill {q['id']}" if q else "done"
        report, extra = form.fill_page(page, greenhouse, asked, resume, letter, before)
        now_, then = c.evaluate(SHOWN), (time.sleep(late), c.evaluate(SHOWN))[1]
        kinds = {q["id"]: q["kind"] for q in asked}
        result["fill"] = [{"id": id, "kind": kinds[id], "answer": next(q["answer"] for q in asked if q["id"] == id),
                           "said": said, "shown": now_.get(id), f"shownAfter{late}s": then.get(id)}
                          for id, said in report if id in now_]
        result["other"] = [(id, said) for id, said in report if id not in now_]
        result["tabShot"] = tab_shot(c, "gh-fill-tab")
        result["shot"] = screenshot("gh-fill", proc)
        result["submitClicked"] = False
        result["block"] = {"reads": block.reads, "failed": [(b["method"], b["url"][:80], b["after"]) for b in block.log]}
    finally:
        result["quit"] = quit_(proc)
        close()


# ---------------------------------------------------------------- resume box ready? (plan-29g.25)
class Stub(Block):
    """Block (level 3) + both ends of Greenhouse's upload kept in this tab: its own request for the storage
    form (presigned_fields, a read) held `hold` s - a choice made before it answers = the owner's case; the
    file's POST to storage (and its CORS preflight) answered here - nothing leaves, the page sees a 2xx."""

    def __init__(self, c, hold=0):
        super().__init__(c, 3)
        self.hold, self.held, self.stored = hold, [], []

    def paused(self, p, msg):
        import threading
        r = p["request"]
        if "/uncacheable_attributes/presigned_fields" in r["url"] and self.hold:
            self.held.append({"after": self.step, "s": self.hold})
            self.reads += 1
            go = lambda: quietly(lambda: self.c.post("Fetch.continueRequest", {"requestId": p["requestId"]}))
            return threading.Timer(self.hold, go).start()
        if (urlsplit(r["url"]).hostname or "").endswith(".amazonaws.com") and r["method"] in ("POST", "OPTIONS"):
            origin = next((v for k, v in r.get("headers", {}).items() if k.lower() == "origin"), "*")
            self.stored.append({"method": r["method"], "after": self.step, "body": r.get("hasPostData", False)})
            cors = [{"name": "Access-Control-Allow-Origin", "value": origin}, {"name": "Access-Control-Allow-Methods", "value": "POST"},
                    {"name": "Access-Control-Allow-Headers", "value": "*"}]
            return self.c.post("Fetch.fulfillRequest", {"requestId": p["requestId"], "responseCode": 204 if r["method"] == "POST" else 200,
                                                        "responseHeaders": cors})
        return super().paused(p, msg)


# a real upload reports progress as it goes; one answered at request stage never does, so the page's own
# "progress at 100 -> show the name" never runs: report it once the stubbed POST loads, as a real one would
XHR_PROGRESS = """(() => { const send = XMLHttpRequest.prototype.send, open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { this.__jfUrl = String(u); return open.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    if (/amazonaws[.]com/.test(this.__jfUrl || '')) this.addEventListener('load', () => {
      (window.__jfXhr = window.__jfXhr || []).push(this.status);
      this.upload.onprogress && this.upload.onprogress({loaded: 1, total: 1, lengthComputable: true}); });
    return send.apply(this, arguments); }; })()"""

RESUME_BOX = """(() => ({name: (document.querySelector('[aria-labelledby="upload-label-resume"] .file-upload__filename') || {}).innerText || '',
  error: (document.getElementById('resume-error') || {}).innerText || '',
  progress: !!document.querySelector('[aria-labelledby="upload-label-resume"] [role=progressbar]')}))()"""


def ghupload(result):
    """Two loads of one posting in the window tab, block + canary first, dummy PDF, never Submit:
    1 storage-form request held JF_HOLD s, file chosen once it is out (the page hydrated, its box not ready),
    then again after idle (as a person attaching by hand): the same file, then a copy under another name;
    2 plain load: when it goes out + ends vs load vs
    idle, what is still out at load, then the shipped greenhouse.put_file."""
    import threading
    from apply import form, window
    from apply.systems import greenhouse
    if not GH_URL or "greenhouse.io/" not in GH_URL:
        sys.exit("ghupload needs a job-boards.greenhouse.io posting link")
    eu, board, job = greenhouse.parse_url(GH_URL)
    anon = lambda u: u.replace(board, "<board>").replace(job, "<id>")
    hold = float(os.environ.get("JF_HOLD", "5"))
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    make_resume()
    second = D / "Test_Resume_2.pdf"
    second.write_bytes(RESUME.read_bytes())
    try:
        ask({"do": "open", "url": f"{home}/blank"})
        time.sleep(2)
        res, found, conns = attach(f"{home}/blank*", QUIET)
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions")}
        c = pick(conns, f"{home}/blank")
        if not c:
            result["error"] = "no CDP proxy reached the tab"
            return
        block = Stub(c, hold)
        result["install"] = attempt(block.install)
        result["canary"] = canary(c, block, "canary")
        if result["canary"]["received"] or not result["canary"]["loaded"]:
            result["refused"] = "canary received writes (or never loaded): posting not opened"
            return
        result["xhrProgress"] = attempt(lambda: c.send("Page.addScriptToEvaluateOnNewDocument", {"source": XHR_PROGRESS})["identifier"])
        page = window.Page(c)
        page.quiet()
        lock, urls, marks = threading.Lock(), {}, []
        t0 = [time.monotonic()]

        def mark(what, **extra):
            marks.append({"ms": round((time.monotonic() - t0[0]) * 1000), "what": what, **extra})

        def watch(p, msg):
            with lock:
                if msg["method"] == "Network.requestWillBeSent":
                    urls[p["requestId"]] = p["request"]["url"]
                url = urls.get(p.get("requestId"), "")
            if "presigned_fields" in url:
                mark(msg["method"].split(".")[1] + " presigned")
        for name in window.NETWORK:
            c.on(name, watch)

        def out_now():
            with page.lock, lock:
                return sorted(anon(urls.get(i, "?"))[:120] for i in page.inflight)

        def load(step):
            block.step, t0[0] = step, time.monotonic()
            marks.clear()
            page.goto(GH_URL)
            mark("readyState complete", inflight=out_now())
            form.open_form(page, greenhouse, GH_URL)
            mark("READY #first_name")

        # 1 the owner's case: box shown, page hydrated, its storage form not back yet
        load("held")
        seen = wait_for(lambda: block.held or any(m["what"] == "requestWillBeSent presigned" for m in marks), 20, 0.05)
        early = result["early"] = {"presignedOut": bool(seen)}
        block.step = "early choice"
        early["choose"] = attempt(lambda: page.locator("#resume").set_input_files(str(RESUME)))
        mark("chosen early")
        time.sleep(2)
        early["box"] = quietly(lambda: c.evaluate(RESUME_BOX))
        early["tabShot"] = tab_shot(c, "gh-upload-early")
        early["idle"] = attempt(lambda: page.wait_for_load_state("networkidle", timeout=30000))
        mark("idle")
        block.step = "same file again"
        early["same"] = attempt(lambda: page.locator("#resume").set_input_files(str(RESUME)))
        mark("same file chosen again")
        time.sleep(3)
        early["boxSame"] = quietly(lambda: c.evaluate(RESUME_BOX))
        block.step = "second choice"
        early["again"] = attempt(lambda: page.locator("#resume").set_input_files(str(second)))
        mark("other name chosen")
        early["shownAgain"] = bool(wait_for(lambda: (quietly(lambda: c.evaluate(RESUME_BOX)) or {}).get("name"), 15, 0.25))
        mark("name shown" if early["shownAgain"] else "no name after 15 s")
        early["boxAgain"] = quietly(lambda: c.evaluate(RESUME_BOX))
        early["tabShotAgain"] = tab_shot(c, "gh-upload-again")
        early["marks"] = marks[:]
        # 2 a plain load, the shipped path
        block.hold = 0
        load("plain")
        block.step = "put_file"
        t = time.monotonic()
        plain = result["plain"] = {"putFile": attempt(lambda: greenhouse.put_file(page, {"id": "resume"}, str(RESUME)))}
        plain["putFileMs"] = round((time.monotonic() - t) * 1000)
        mark("put_file returned")
        plain["box"] = quietly(lambda: c.evaluate(RESUME_BOX))
        plain["marks"] = marks[:]
        plain["tabShot"] = tab_shot(c, "gh-upload-plain")
        result["xhr"] = quietly(lambda: c.evaluate("window.__jfXhr || []"))
        result["stored"] = block.stored
        result["held"] = block.held
        result["submitClicked"] = False
        result["block"] = {"reads": block.reads, "failed": [(b["method"], anon(b["url"])[:80], b["after"]) for b in block.log]}
    finally:
        result["quit"] = quit_(proc)
        close()


# ---------------------------------------------------------------- reCAPTCHA score signal (plan-29g.21)
# Google's public v3 demo: scores the page on load, shows its own backend's verdict. Another site key than
# Greenhouse's Enterprise one, a demo that says its score means nothing - a relative hint only, no Submit.
SCORE_URL = "https://recaptcha-demo.appspot.com/recaptcha-v3-request-scores.php"
SCORE = """(() => { try { const d = JSON.parse(document.querySelector('.response').innerText);
  return 'success' in d ? d : null; } catch (e) { return null; } })()"""
SIGNALS = """({ua: navigator.userAgent, webdriver: navigator.webdriver, helpers: typeof window.__vscode_helpers,
  brands: navigator.userAgentData && navigator.userAgentData.brands.map((b) => b.brand + ' ' + b.version),
  plugins: navigator.plugins.length, languages: navigator.languages, focus: document.hasFocus()})"""
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def read_score(c, secs=30):
    got = wait_for(lambda: quietly(lambda: c.evaluate(SCORE, timeout=3)), secs, 0.5)
    return got if isinstance(got, dict) else None


def score(result):
    """Window tab, two ways per sample: opened plain (no debugger; its verdict read off a window-only
    screenshot) and opened w/ the debugger on the way `fill --in-window` does it (loopback holding page,
    attach, skip pauses, navigate). Chrome: as Job Finder's own (fixed port, fresh throwaway profile
    under $D, tab opened by Chrome itself). Same page, same samples, no input either side."""
    samples = int(os.environ.get("JF_SAMPLES", "3"))
    rows = result["window"] = []
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    try:
        for i in range(samples):
            row = {}
            ask({"do": "open", "url": f"{SCORE_URL}?jf={UNIQ}{i}"})
            ask({"do": "command", "id": "workbench.action.closePanel"})  # last attach's Debug Console hides the verdict
            time.sleep(12)
            row["plainShot"] = screenshot(f"score-window-plain-{i}", proc)
            # the demo tab itself gave js-debug no page session (3 of 3, exact link + glob): the trial's way instead
            ask({"do": "command", "id": "workbench.action.closeAllEditors"})
            ask({"do": "open", "url": f"{home}/blank?s={i}"})
            time.sleep(2)
            res, found, conns = attach(f"{home}/blank?s={i}", QUIET)
            c = pick(conns, f"{home}/blank")
            if not c:
                row["later"] = later(found, conns)
                c = pick(conns, f"{home}/blank")
            row["attach"] = {k: res.get(k) for k in ("ok", "error")} | {"reached": bool(c)}
            if c:
                quietly(lambda: c.send("Debugger.setSkipAllPauses", {"skip": True}, 5))
                c.send("Page.navigate", {"url": f"{SCORE_URL}?jf={UNIQ}a{i}"})
                time.sleep(2)
                quietly(lambda: c.send("Debugger.setSkipAllPauses", {"skip": True}, 5))  # other site, other process
                row["attached"] = read_score(c)
                row["signals"] = quietly(lambda: c.evaluate(SIGNALS))
                row["attachedShot"] = screenshot(f"score-window-attached-{i}", proc)
            rows.append(row)
            ask({"do": "stop"})  # stop all: closes the tab - wanted here, next sample opens its own
            ask({"do": "command", "id": "workbench.action.closeAllEditors"})
            time.sleep(2)
    finally:
        result["quit"] = quit_(proc)
        close()
    rows = result["chrome"] = []
    prof, port = D / "chrome-score", free_port()
    p = subprocess.Popen([CHROME, f"--remote-debugging-port={port}", f"--user-data-dir={prof}", "--no-first-run",
                          "--no-default-browser-check", f"{SCORE_URL}?jf={UNIQ}c0"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for i in range(samples):
            url = f"{SCORE_URL}?jf={UNIQ}c{i}"
            if i:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{url}", method="PUT")
                urllib.request.urlopen(req, timeout=10).read()
            time.sleep(12)
            tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=10).read())
            tab = next((t for t in tabs if t.get("type") == "page" and t.get("url") == url), None)
            if not tab:
                rows.append({"error": "tab not found", "urls": [t.get("url") for t in tabs]})
                continue
            c = CDP("127.0.0.1", port, urlsplit(tab["webSocketDebuggerUrl"]).path)
            rows.append({"opened": read_score(c), "signals": quietly(lambda: c.evaluate(SIGNALS))})
            c.close()
    finally:
        p.terminate()
        time.sleep(2)
        subprocess.run(["pkill", "-f", str(prof)])


# ---------------------------------------------------------------- one public posting, any system, route 2 (plan-nko.6)
# another site's frame -> what it is, by its host
FRAME_KIND = (("recaptcha", r"recaptcha\.net|google\.com/recaptcha|gstatic\.com/recaptcha"), ("hcaptcha", r"hcaptcha\.com"),
              ("turnstile", r"challenges\.cloudflare\.com"), ("linkedin", r"linkedin\.com"), ("google sign-in", r"accounts\.google\.com"))
# what the page carries before Submit: captcha + Cloudflare scripts, Lever's Apply with LinkedIn widget
MARKS = """(() => ({hcaptchaApi: typeof window.hcaptcha, grecaptchaApi: typeof window.grecaptcha, turnstileApi: typeof window.turnstile,
  hiddenCaptchaButton: !!document.querySelector('#hcaptchaSubmitBtn, .h-captcha, [data-hcaptcha-widget-id]'),
  linkedinWidget: !!document.querySelector('script[type="IN/AwliWidget"]'),
  scripts: [...new Set([...document.scripts].map((s) => s.src).filter((u) => /hcaptcha|recaptcha|challenge-platform|turnstile|linkedin|licdn/.test(u))
    .map((u) => { try { const x = new URL(u); return x.host + x.pathname.replace(/[0-9a-f]{16,}/gi, '<h>').slice(0, 80) } catch (e) { return '?' } }))]}))()"""
# the upload's own words: Ashby's toast, Lever's label states (lever.md)
VERDICT = """(() => { const m = document.body.innerText.match(/failed to upload|couldn.t auto-read resume\\.?|analyzing resume\\.*|success!/i);
  return m ? m[0] : null })()"""
FRAMES = """(() => [...document.querySelectorAll('iframe')].map((f) => ({src: (f.src || '').slice(0, 300),
  title: (f.title || '').slice(0, 60), shown: !!f.getClientRects().length, w: f.offsetWidth, h: f.offsetHeight})))()"""


# reCAPTCHA v2 checkbox (JazzHR's "Human Check", plan-k8n.4): scrolled to, then is its frame there + on top at the box's middle
CAPTCHA_BOX = """(() => { const b = document.querySelector('.g-recaptcha'); if (!b) return null;
  b.scrollIntoView({block: 'center', behavior: 'instant'}); const r = b.getBoundingClientRect(), f = b.querySelector('iframe');
  const hit = document.elementFromPoint(r.x + Math.min(r.width, 300) / 2, r.y + Math.min(r.height, 74) / 2);
  return {shown: !!b.getClientRects().length, w: Math.round(r.width), h: Math.round(r.height), frame: !!f,
    frameShown: f ? !!f.getClientRects().length : false, frameW: f ? f.offsetWidth : 0, frameH: f ? f.offsetHeight : 0,
    onTopAtMiddle: hit ? (hit === f ? 'its frame' : hit.nodeName.toLowerCase() + (hit.className ? '.' + String(hit.className).split(' ')[0] : '')) : null,
    responseBox: !!document.querySelector('[name="g-recaptcha-response"]'), text: b.innerText.slice(0, 80)}; })()"""

# Workable's widgets (plan-k8n.7): the [role=radio] beside each radio input, the [role=combobox] in each
# list's wrapper, and what takes a click at a list's middle (Chrome: plain clicks timed out, workable.md)
WIDGETS = """(() => { const boxes = [...document.querySelectorAll('[role=combobox]')];
  const top = (e) => { e.scrollIntoView({block: 'center', behavior: 'instant'}); const r = e.getBoundingClientRect();
    const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return hit === e ? 'itself' : !hit ? null : e.contains(hit) ? 'inside it' : hit.contains(e) ? 'its ancestor ' + hit.nodeName.toLowerCase()
      : hit.nodeName.toLowerCase() + (hit.getAttribute('data-ui') ? '[data-ui]' : '') + (hit.getAttribute('role') ? '[role=' + hit.getAttribute('role') + ']' : ''); };
  window.scrollTo(0, 0);
  return {roleRadio: document.querySelectorAll('[role=radio]').length, radioInputs: document.querySelectorAll('input[type=radio]').length,
    radioGroups: document.querySelectorAll('fieldset[role=radiogroup], [role=radiogroup]').length,
    checkboxes: document.querySelectorAll('input[type=checkbox]').length, combobox: boxes.length,
    comboboxInDataUi: boxes.filter((b) => b.closest('[data-ui]')).length, options: document.querySelectorAll('[role=option]').length,
    fileInputs: document.querySelectorAll('input[type=file]').length, resumeWrapper: !!document.querySelector('[data-ui="resume"]'),
    onTopAtListMiddle: boxes.slice(0, 8).map(top),
    dialogs: [...document.querySelectorAll('[role=dialog]')].filter((d) => d.getClientRects().length).map((d) => ({ui: d.getAttribute('data-ui'),
      modal: d.getAttribute('aria-modal'), text: (d.innerText || '').replace(/\\s+/g, ' ').slice(0, 60)}))}; })()"""

FRAME_BOX = ("[...document.querySelectorAll('iframe')].map((f) => { try { return f.contentDocument && "
             "f.contentDocument.querySelector('input[name=css_loginName], input[type=email]') } catch (e) { return null } }).find(Boolean)")
NAMES = """[document.title, (document.querySelector('meta[property="og:site_name"]') || {}).content || ''].map((s) => s.trim()).filter(Boolean)"""


def frame_kind(url):
    import re
    return next((k for k, rx in FRAME_KIND if re.search(rx, url)), "other")


def short(url):
    """scheme + host + path: a query can carry the tenant; a GraphQL op name (?op=) is kept."""
    from urllib.parse import parse_qs
    u = urlsplit(url)
    op = parse_qs(u.query).get("op")
    return f"{u.scheme}://{u.hostname or ''}{u.path}"[:160] + (f"?op={op[0][:60]}" if op else "")


def raw(result):
    """Canary first in the same tab, then the posting's form: pauses, frames, one typed box, the dummy PDF."""
    import re
    from apply import lab, systems
    system = systems.for_url(GH_URL or "")
    if not system:
        sys.exit("raw needs a posting link systems.for_url knows")
    tag = system.NAME.lower()
    app_url = system.application_url(GH_URL)
    SCRUB.extend(rawkit.scrub_pairs(system, GH_URL, app_url))  # host tenant parts, path org + ids, query values
    result["tenantsAdded"] = lab.record_tenants(TENANTS, rawkit.tenant_lines(system, [GH_URL, app_url]))
    cap, level = int(os.environ.get("JF_PAUSE_CAP", "20")), int(os.environ.get("JF_BLOCK_LEVEL", "3"))
    result |= {"system": system.NAME, "ready": system.READY, "url": app_url, "level": level, "pauseCap": cap}
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    dummy = make_resume()
    pauses = result["pauses"] = []
    try:
        ask({"do": "open", "url": f"{home}/blank"})
        time.sleep(2)
        res, found, conns = attach(f"{home}/blank*", QUIET)
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions")} | {"found": found}
        c = pick(conns, f"{home}/blank")
        if not c:
            result["error"] = "no CDP proxy reached the tab"
            return
        block = Block(c, level, named=True)
        result["install"] = attempt(block.install)

        def paused(p, msg):
            top = (p.get("callFrames") or [{}])[0]
            loc = top.get("location", {})
            pauses.append({"n": len(pauses) + 1, "reason": p.get("reason"), "after": block.step,
                           "script": short(top.get("url") or ""), "fn": (top.get("functionName") or "")[:40],
                           "line": loc.get("lineNumber"), "col": loc.get("columnNumber")})
            if len(pauses) >= cap:  # enough counted: let the page run
                c.post("Debugger.setSkipAllPauses", {"skip": True})
            c.post("Debugger.resume", {})
        c.on("Debugger.paused", paused)
        result["subscribe"] = attempt(lambda: c.send("JsDebug.subscribe", {"events": ["Debugger.paused", "Debugger.resumed"]}))
        result["skipOff"] = attempt(lambda: c.send("Debugger.setSkipAllPauses", {"skip": False}, 5))
        result["canary"] = canary(c, block, "canary")
        if result["canary"]["received"] or not result["canary"]["loaded"]:
            result["refused"] = "canary received writes (or never loaded): posting not opened"
            return
        block.step = "load"
        t = time.time()
        c.send("Page.navigate", {"url": app_url})
        ready = rawkit.ready_js(system.READY)  # ':visible' + open shadow roots, as Playwright reads READY
        if apply := getattr(system, "APPLY", None):  # the form opens only after this button (BambooHR, plan-k8n.10)
            button = (f"[...document.querySelectorAll('button, a')].find(e => e.innerText.trim() === {json.dumps(apply)})")
            result["applyButton"] = {"found": bool(wait_for(lambda: quietly(lambda: c.evaluate(f"!!{button}", timeout=3)), 40, 0.5)),
                                     "ms": round((time.time() - t) * 1000)}
            if result["applyButton"]["found"]:
                block.step = "apply click"
                time.sleep(2)  # its own scripts settle, as a person reads the posting first
                result["applyButton"]["click"] = attempt(lambda: click(c, button))
                block.step = "load"
        result["loaded"] = bool(wait_for(lambda: quietly(lambda: c.evaluate(ready, timeout=3)), 40, 0.5))
        result["readyMs"] = round((time.time() - t) * 1000)
        time.sleep(4)  # its own scripts settle
        result["pausesOnLoad"] = len(pauses)
        # where the page landed: a short link can move to the employer's own path (Workable /j/ -> /<account>/j/, plan-k8n.7)
        landed = quietly(lambda: c.evaluate("location.href")) or ""
        SCRUB.extend(rawkit.scrub_pairs(system, landed))
        result["tenantsAdded"] += lab.record_tenants(TENANTS, rawkit.tenant_lines(system, [landed]))
        result["at"] = quietly(lambda: c.evaluate("location.host + location.pathname"))
        result["fields"] = quietly(lambda: c.evaluate(rawkit.count_js(system.READY)))
        names = quietly(lambda: c.evaluate(NAMES)) or []  # the employer's own names: tenants.txt + scrubbed
        names += [m.group(1).strip() for s in names if (m := re.search(r"\bat (.+)$", s))]
        lines = rawkit.tenant_lines(system, [], names)
        result["tenantsAdded"] += lab.record_tenants(TENANTS, lines)
        SCRUB.extend((s, "<org>") for s in lines if len(s) >= 4)
        result["boxes"] = quietly(lambda: c.evaluate(GH_FIELDS.replace("label: ", "_: ").replace("type: e.type,", "type: e.type, name: e.name,")))
        if isinstance(result["boxes"], list):  # labels are the employer's words: kinds only
            import re  # question ids are the employer's: "<field>"
            uuid = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
            result["boxes"] = [{k: uuid.sub("<field>", v) if isinstance(v, str) else v for k, v in b.items() if k != "_"}
                               for b in result["boxes"]]
        frames = result["frames"] = {}
        frames["iframes"] = [f | {"kind": frame_kind(f["src"]), "src": short(f["src"])} for f in quietly(lambda: c.evaluate(FRAMES)) or []]
        frames["blockedOtherSite"] = [{"url": short(b["url"]), "kind": frame_kind(b["url"]), "after": b["after"]}
                                     for b in block.log if b["type"] == "other-site frame"]
        frames["targets"] = attempt(lambda: [{"type": t["type"], "url": short(t["url"]), "kind": frame_kind(t["url"])}
                                             for t in c.send("Target.getTargets")["targetInfos"] if t["type"] == "iframe"])
        result["marks"] = quietly(lambda: c.evaluate(MARKS))
        fill = result["fill"] = {"resume": dummy}
        box = next((s for s in ('[id="_systemfield_name"]', '#application-form input[name=name]', 'input[name=firstname]', '#firstName',
                                'input[name^="primary-email"]', '#first-name-input', 'input[type=text]') if quietly(lambda: c.evaluate(f"!!{q(s)}"))), None)
        fill["box"] = box
        if box:
            block.step = "type"

            def typed():
                click(c, q(box))
                time.sleep(0.4)
                focused = c.evaluate(f"document.activeElement === {q(box)}")
                c.send("Input.insertText", {"text": "Test Applicant"})
                time.sleep(0.5)
                return {"focused": focused}
            fill["type: click + Input.insertText"] = attempt(typed)
            fill["readBack"] = quietly(lambda: c.evaluate(f"{q(box)}.value"))
            if not fill["readBack"]:  # the click landed on something over the box: focused by script, as Locator.fill does

                def focused_typed():
                    c.evaluate(f"{q(box)}.focus()")
                    c.send("Input.insertText", {"text": "Test Applicant"})
                    time.sleep(0.5)
                    return {"focused": c.evaluate(f"document.activeElement === {q(box)}")}
                fill["type: focused by script + Input.insertText"] = attempt(focused_typed)
                fill["readBackAfterFocus"] = quietly(lambda: c.evaluate(f"{q(box)}.value"))
        if not box:  # the start box in the page's own same-site frame (iCIMS ?in_iframe=1, plan-k8n.16): reached through
            # contentDocument from the top page's session, focused by script + Input.insertText (no click: frame offset)
            fill["frameBox"] = quietly(lambda: c.evaluate(f"!!{FRAME_BOX}"))
            if fill["frameBox"]:
                block.step = "type"

                def frame_typed():
                    c.evaluate(f"{FRAME_BOX}.focus()")
                    c.send("Input.insertText", {"text": "test@example.com"})
                    time.sleep(0.5)
                    return {"focused": c.evaluate(f"{FRAME_BOX}.ownerDocument.activeElement === {FRAME_BOX}")}
                fill["frame: focused by script + Input.insertText"] = attempt(frame_typed)
                fill["frameReadBack"] = quietly(lambda: c.evaluate(f"{FRAME_BOX}.value"))
                fill["frameMarks"] = quietly(lambda: c.evaluate(f"(() => {{ const d = {FRAME_BOX}.ownerDocument; return {{"
                                                                f"hcaptcha: !!d.querySelector('.h-captcha, [data-hcaptcha-widget-id]'), "
                                                                f"tick: !!d.querySelector('#accept_gdpr'), "
                                                                f"boxes: d.querySelectorAll('input:not([type=hidden]), select, textarea').length}} }})()"))
        # SmartRecruiters: its resume field = the file box after the name (FILES), never the parsing box above it
        files = (f"js:({system.FILES})()",) if hasattr(system, "FILES") else ()
        fbox = next((s for s in (*files, '[id="_systemfield_resume"]', '#resume-upload-input', 'input[type=file]')
                     if quietly(lambda: c.evaluate(f"!!{q(s)}"))), None)
        fill["fileBox"] = fbox
        result["widgets"] = quietly(lambda: c.evaluate(WIDGETS))
        fill["fileChosen"] = bool(fbox) and os.environ.get("JF_NO_FILE") != "1"
        if fill["fileChosen"]:
            block.step = "upload"
            fill["upload: DOM.setFileInputFiles"] = attempt(lambda: upload(c, fbox, RESUME))
            time.sleep(6)
            fill["nameShown"] = quietly(lambda: c.evaluate(f"document.body.innerText.includes({json.dumps(RESUME.name)})"))
            fill["failedLine"] = quietly(lambda: c.evaluate("/failed to upload/i.test(document.body.innerText)"))
            fill["verdict"] = quietly(lambda: c.evaluate(VERDICT))
            if deep := getattr(system, "DEEP", None):  # names + errors drawn in shadow roots (SmartRecruiters)
                text = quietly(lambda: c.evaluate(f"({deep})(document.body)")) or ""
                fill["nameShownDeep"] = RESUME.name in text
                fill["pageErrors"] = system.UPLOAD_ERRORS.findall(text) if hasattr(system, "UPLOAD_ERRORS") else None
            fill["fileHeld"] = quietly(lambda: c.evaluate(f"({q(fbox)}.files[0] || {{}}).name || ''") == RESUME.name)
            fill["sentOnChoice"] = [{"method": b["method"], "url": short(b["url"]), "type": b["type"],
                                     "contentType": b.get("contentType"), "body": b.get("body")}
                                    for b in block.log if b["after"] == "upload"]
        block.step = "end"
        fill["tabShot"] = tab_shot(c, f"{tag}-route2-tab")
        result["captchaBox"] = quietly(lambda: c.evaluate(CAPTCHA_BOX))
        if result["captchaBox"]:
            time.sleep(1)
            result["captchaShot"] = tab_shot(c, f"{tag}-route2-captcha")
        result["shot"] = screenshot(f"{tag}-route2-window", proc)
        result["pausesTotal"] = len(pauses)
        result["skipOnAfterCap"] = len(pauses) >= cap
        result["submitClicked"] = False
        result["block"] = {"reads": block.reads, "namedReads": [{"op": b["op"], "url": short(b["url"]), "after": b["after"]} for b in block.passed],
                           "failed": [{"method": b["method"], "url": short(b["url"]), "type": b["type"], "after": b["after"]} for b in block.log],
                           "seenWrites": [s | ({"url": short(s["url"])} if "url" in s else {}) for s in block.seen]}
        result["pageLoads"] = 1
        result["handlerErrors"] = [e for e in c.events if "handlerError" in e][:5]
    finally:
        result["quit"] = quit_(proc)
        close()


# ---------------------------------------------------------------- Restricted Mode (untrusted folder)
def restricted(result):
    """User setting startupPrompt never -> the folder opens untrusted w/o a dialog: does the attach start?"""
    user = D / "data" / "User" / "settings.json"
    before = user.read_text() if user.exists() else None
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text(json.dumps({"security.workspace.trust.startupPrompt": "never"}))
    proc, result["launch"] = launch(trust=False)
    home, other, close = formsite.serve(TITLE)
    try:
        ask({"do": "open", "url": f"{home}/form"})
        time.sleep(3)
        result["trust"] = ask({"do": "trust"}).get("trusted")
        res = ask({"do": "attach", "urlFilter": f"{home}/form*", "waitMs": 6000, "settleMs": 500}, 25)
        result["attach"] = {k: res.get(k) for k in ("ok", "error", "ms", "sessions", "proxies")}
        time.sleep(1)
        result["shot"] = screenshot("route2-restricted", proc)
    finally:
        result["quit"] = quit_(proc)
        close()
        if before is None:
            user.unlink()
        else:
            user.write_text(before)


# ---------------------------------------------------------------- multi-page: keep the user's place (plan-k8n.12)
MP_EVENTS = ["Debugger.paused", "Debugger.resumed", "Page.frameNavigated", "Page.navigatedWithinDocument",
             "Page.loadEventFired", "Runtime.executionContextsCleared", "Inspector.detached", "Target.detachedFromTarget"]
NEXT_MS = 4000  # page 1's own timer clicks Next (the user's click: no client of ours sends it)


def ticks(since, page=None):
    """The page's `debugger;` line, once a second: [(t, page, ms held)] logged after `since`."""
    out = []
    for e in formsite.log:
        if e["t"] >= since and e["path"].startswith("/beacon?k=tick"):
            qs = dict(x.split("=", 1) for x in e["path"].split("?", 1)[1].split("&"))
            if page is None or qs["p"] == str(page):
                out.append((e["t"], int(qs["p"]), int(qs["ms"])))
    return out


def tick_summary(since, until=None):
    rows = [t for t in ticks(since) if until is None or t[0] <= until]
    by = {}
    for p in (1, 2):
        mine = [t for t in rows if t[1] == p]
        gaps = [round(b[0] - a[0], 1) for a, b in zip(mine, mine[1:])]
        by[f"page{p}"] = {"n": len(mine), "maxHeldMs": max((t[2] for t in mine), default=None),
                          "maxGapS": max(gaps, default=None)}
    return by


def mp_open(home, name, to, client_events=True):
    """As window.page_at: a holding page, attach to it alone, skip pauses, then the form -> (child id, CDP, row)."""
    hold = f"{home}/blank-{name}"
    ask({"do": "open", "url": hold})
    wait_for(lambda: any(e["path"] == f"/blank-{name}" for e in formsite.log), 20, 0.2)
    res = ask({"do": "attach", "urlFilter": hold, "options": QUIET, "extra": {"internalConsoleOptions": "neverOpen"},
               "waitMs": 10000, "settleMs": 1500}, 45)
    row = {"attachMs": res.get("ms"), "sessions": res.get("sessions"), "error": res.get("error")}
    child = next((s["id"] for s in res.get("sessions") or [] if s.get("parent")), None)
    px = (res.get("proxies") or {}).get(child) or {}
    row["proxyPath"] = px.get("path")
    c = CDP(px["host"], px["port"], px["path"])
    c.send("JsDebug.subscribe", {"events": MP_EVENTS})
    c.send("Page.enable")
    c.send("Page.navigate", {"url": f"{home}/mp/1?to={to}&tick=1"})
    wait_for(lambda: quietly(lambda: c.evaluate("document.readyState === 'complete' && !!window.mpState", timeout=3)), 15)
    c.send("Debugger.setSkipAllPauses", {"skip": True}, 5)  # after the load, as window.Page.goto: a navigation resets it (run 1)
    click(c, q("#mp_first"))
    c.send("Input.insertText", {"text": "Test"})
    row["page1"] = quietly(lambda: c.evaluate("mpState()", timeout=3))
    return child, c, row


def on_page2(to, since):
    """Page 2 showed: its request (new page) or its first tick (drawn in place)."""
    if to == "spa":
        return bool(ticks(since, 2))
    return any(e["t"] >= since and e["path"].startswith("/mp/2") for e in formsite.log)


def reconnect(child):
    """(a): the same debug session's proxy asked for again -> (CDP or None, row)."""
    px = ask({"do": "proxy", "id": child}).get("proxy") or {}
    row = {"proxyPath": px.get("path"), "error": px.get("error")}
    if not px.get("port"):
        return None, row
    try:
        c = CDP(px["host"], px["port"], px["path"])
        c.send("JsDebug.subscribe", {"events": MP_EVENTS})
        return c, row
    except Exception as e:
        row["error"] = str(e)[:200]
        return None, row


def fill_page2(c, row):
    row["href"] = attempt(lambda: c.evaluate("location.href", timeout=5))
    row["resume"] = attempt(lambda: c.send("Debugger.resume", {}, 5))
    row["skip"] = attempt(lambda: c.send("Debugger.setSkipAllPauses", {"skip": True}, 5))
    t = time.time()
    row["fill"] = attempt(lambda: (click(c, q("#mp_email")), c.send("Input.insertText", {"text": "test.person@example.com"}))[1])
    row["state"] = attempt(lambda: c.evaluate("mpState()", timeout=5))
    time.sleep(3)
    time.sleep(3)
    row["ticksAfter"] = tick_summary(t)
    row["pausedNow"] = attempt(lambda: c.evaluate("1", timeout=3))


def end_all():
    ask({"do": "stop"})
    time.sleep(1.5)
    ask({"do": "command", "id": "workbench.action.closeAllEditors"})
    time.sleep(1)


def reload_window(proc):
    (HOLD / "up.json").unlink(missing_ok=True)
    ask({"do": "command", "id": "workbench.action.reloadWindow"}, 5)
    t = time.time()
    up = wait_for(lambda: (HOLD / "up.json").exists(), 60, 0.25)
    time.sleep(3)
    after = ask({"do": "sessions"})
    return {"upAgain": bool(up), "upMs": round((time.time() - t) * 1000), "sessions": after.get("sessions"),
            "tabs": [t["label"] for g in after.get("tabs") or [] for t in g["tabs"]],
            "shot": screenshot(f"mp-reloaded-{UNIQ}", proc)}


def keep_quiet(c):
    """(c): what a fill staying attached does - skip pauses again on each new page, resume any pause -> its log."""
    fixes = []

    def requiet(p, m):
        if m["method"] == "Debugger.paused":
            fixes.append(("resume", p.get("reason")))
            c.post("Debugger.setSkipAllPauses", {"skip": True})
            c.post("Debugger.resume")
        elif not (p.get("frame") or {}).get("parentId"):
            fixes.append(("skip", m["method"]))
            c.post("Debugger.setSkipAllPauses", {"skip": True})
    for ev in ("Debugger.paused", "Page.frameNavigated", "Page.navigatedWithinDocument"):
        c.on(ev, requiet)
    return fixes


def multipage(result):
    """Local form only: page 1 filled, Next clicked by the page itself, page 2 filled - (a) the debug
    session kept between runs (no client of ours while the user works), (c) one fill process attached
    throughout. Same site, other site, drawn in place; a `debugger;` line every second on both pages."""
    proc, result["launch"] = launch()
    home, other, close = formsite.serve(TITLE)
    try:
        # control: no debugger at all - the page's ticks reach the log
        ask({"do": "open", "url": f"{home}/mp/1?to=same&tick=1&plain"})
        t = time.time()
        time.sleep(4)
        result["control"] = tick_summary(t)
        ask({"do": "command", "id": "workbench.action.closeAllEditors"})
        time.sleep(1)
        # today's shipped end, for the baseline: fill, detach - what's left
        child, c, row = mp_open(home, "base", "same")
        c.close()
        row["detach"] = {k: ask({"do": "detach", "id": child}).get(k) for k in ("sessions", "error")}
        time.sleep(1)
        row["shot"] = screenshot("mp-base-detached", proc)
        t = time.time()
        time.sleep(4)
        row["ticksAfterDetach"] = tick_summary(t)
        result["baseline"] = row
        end_all()

        # bpoff: VS Code's own "Deactivate breakpoints" on while the session is kept (js-debug -> setBreakpointsActive
        # false, which V8 applies to `debugger;` lines too) - does it hold where the skip doesn't?
        for to, off in (("same", False), ("other", False), ("spa", False), ("other", True), ("same", True)):
            name = f"{to}-bpoff" if off else to
            # (a) session kept, no client while the user works
            child, c, row = mp_open(home, f"a-{name}", to)
            if off:
                row["bpoff"] = ask({"do": "command", "id": "workbench.debug.viewlet.action.toggleBreakpointsActivatedAction"}).get("error") or "ok"
            c.evaluate(f"autoNext({NEXT_MS})")
            c.close()
            gone = time.time()
            time.sleep(2)
            row["shotIdlePage1"] = screenshot(f"mp-a-{name}-idle-page1", proc)
            row["onPage2"] = bool(wait_for(lambda: on_page2(to, gone), 15, 0.2))
            time.sleep(6)
            row["shotIdlePage2"] = screenshot(f"mp-a-{name}-idle-page2", proc)
            row["ticksIdle"] = tick_summary(gone)
            s = ask({"do": "sessions"})
            row["sessionsIdle"] = s.get("sessions")
            row["tabsIdle"] = [t["label"] for g in s.get("tabs") or [] for t in g["tabs"]]
            c2, row["reconnect"] = reconnect(child)
            if c2:
                fill_page2(c2, row["reconnect"])
                c2.close()
                # the user closes the tab while the session is kept
                t = time.time()
                ask({"do": "command", "id": "workbench.action.closeAllEditors"})
                time.sleep(3)
                s = ask({"do": "sessions"})
                row["userClosesTab"] = {"sessions": s.get("sessions"), "tabs": [t["label"] for g in s.get("tabs") or [] for t in g["tabs"]]}
                c3, row["userClosesTab"]["reconnect"] = reconnect(child)
                if c3:
                    row["userClosesTab"]["href"] = attempt(lambda: c3.evaluate("location.href", timeout=5))
                    c3.close()
            if off:
                ask({"do": "command", "id": "workbench.debug.viewlet.action.toggleBreakpointsActivatedAction"})
            result[f"a-{name}"] = row
            end_all()
            if off:
                continue

            # (c) one process attached across pages
            child, c, row = mp_open(home, f"c-{to}", to)
            e0 = len(c.events)
            row["fixes"] = keep_quiet(c)
            c.evaluate(f"autoNext({NEXT_MS})")
            t = time.time()
            row["onPage2"] = bool(wait_for(lambda: on_page2(to, t), 15, 0.2))
            nav = next((e for e in c.events[e0:] if e.get("method") in ("Page.frameNavigated", "Page.navigatedWithinDocument")
                        and not (e.get("params", {}).get("frame") or {}).get("parentId")), None)
            row["navEvent"] = nav and {"method": nav["method"], "afterMs": round((nav["t"] - t) * 1000)}
            time.sleep(4)
            row["shotPage2"] = screenshot(f"mp-c-{to}-page2", proc)
            row["ticksBeforeQuiet"] = tick_summary(t)
            row["events"] = [{"method": e.get("method"), "dt": round(e["t"] - t, 2)} for e in c.events[e0:] if e.get("method")][:40]
            row["page2"] = {}
            fill_page2(c, row["page2"])
            if to == "same":  # the user closes the tab while attached
                ask({"do": "command", "id": "workbench.action.closeAllEditors"})
                time.sleep(3)
                s = ask({"do": "sessions"})
                row["userClosesTab"] = {"cdpClosed": c.closed, "evaluate": attempt(lambda: c.evaluate("1", timeout=3)),
                                        "sessions": s.get("sessions")}
            c.close()
            result[f"c-{to}"] = row
            end_all()

        # window reload on page 2: (a) session kept, (c) attached
        for how in ("a", "c"):
            child, c, row = mp_open(home, f"r-{how}", "same")
            if how == "c":
                row["fixes"] = keep_quiet(c)
            c.evaluate(f"autoNext({NEXT_MS})")
            t = time.time()
            if how == "a":
                c.close()
            wait_for(lambda: on_page2("same", t), 15, 0.2)
            time.sleep(2)
            if how == "c":
                row["fill2"] = attempt(lambda: (click(c, q("#mp_email")), c.send("Input.insertText", {"text": "test.person@example.com"}))[1])
            row["reload"] = reload_window(proc)
            if how == "c":
                row["reload"]["cdpClosed"] = c.closed
                row["reload"]["evaluate"] = attempt(lambda: c.evaluate("1", timeout=3))
            c2, row["reload"]["reconnect"] = reconnect(child)
            if c2:
                row["reload"]["reconnect"]["href"] = attempt(lambda: c2.evaluate("location.href", timeout=5))
                c2.close()
            # fresh attach on the tab's own link (here a local http one: a real https form made no page session, 3 of 3)
            page2 = next((t for t in row["reload"]["tabs"] if t.endswith(" mp")), None)
            if page2:
                res = ask({"do": "attach", "urlFilter": f"{home}/mp/2*", "options": QUIET,
                           "extra": {"internalConsoleOptions": "neverOpen"}, "waitMs": 10000, "settleMs": 1500}, 45)
                kid = next((s["id"] for s in res.get("sessions") or [] if s.get("parent")), None)
                px = (res.get("proxies") or {}).get(kid) or {}
                row["reload"]["freshAttach"] = {"error": res.get("error"), "sessions": len(res.get("sessions") or [])}
                if px.get("port"):
                    c3 = CDP(px["host"], px["port"], px["path"])
                    row["reload"]["freshAttach"]["state"] = attempt(lambda: c3.evaluate("mpState()", timeout=5))
                    c3.close()
            result[f"reload-{how}"] = row
            end_all()
    finally:
        result["quit"] = quit_(proc)
        close()
        result["siteWrites"] = [e for e in formsite.log if e["write"]]
        result["siteLog"] = [{k: e[k] for k in ("t", "host", "path")} for e in formsite.log]


if __name__ == "__main__":
    if running():
        sys.exit("a scratch VS Code on this dir is already running")
    out = {"stage": STAGE, "at": now(), "uniq": UNIQ, "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
           "scratch": "$D = mktemp -d /tmp/jfv.XXXX"}
    try:
        {"setup": setup, "ext": ext, "route1": route1, "route2": route2, "gh": gh, "ghfill": ghfill, "ghupload": ghupload, "score": score, "restricted": restricted, "raw": raw, "multipage": multipage}[STAGE](out)
    finally:
        if running():
            subprocess.run(["pkill", "-f", f"{D.name}/data"])
        save(out)
