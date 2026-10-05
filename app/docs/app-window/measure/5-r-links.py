#!/usr/bin/env python3
"""r: links open as a tab in a scratch Job Finder window (plan-29g.4).
Folder = copy of the program (app/, pyproject, uv.lock) + demo (`app/tests/demo.py`), ai = claude.
Local test site on 127.0.0.1 (every request logged: path, Cookie, user agent), pages titled
"JF probe <uniq> <name>" => a browser tab is told by its label (the tab API can't read URLs).
The extension's probe hold (JOBS_VSCODE_PROBE_HOLD) runs a Today click's own path + reads tabs.
  launch    cold `jobs.py launch` (launcher: trust step + --disable-workspace-trust)
    today     a Today link click (company path: http as stored; posting links are https only)
    open      `jobs.py open <url>` -> prints where + tab
    pair      two `jobs.py open` at once + one Today action w/ two links -> two tabs each
    hostile   page reaching file:// (img, fetch, iframe, location, window.open), another program
              (scheme cezprobe-r:// handled by a scratch applet that calls the site back = stand-in
              for vscode://: an escape there would land in the owner's own VS Code), popups w/o a
              click (window.open, a.click target=_blank)
    signin    page setting a 1-year cookie; then a posting-like page shown + screenshot (window only)
  closed    window quit: `jobs.open_for_user` w/ webbrowser.open stubbed
  dock      `code <folder>` alone (no trust flag, no marker; trusted by the launcher) -> cookie back?
  untrusted same after the folder's trust entry is removed -> cookie back?
usage: 5-r-links.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json> <screenshot png>
"""
import datetime
import glob
import http.server
import json
import os
import pathlib
import platform
import secrets
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import zlib

D, SRC, OUT, SHOT = (pathlib.Path(a).resolve() for a in sys.argv[1:5])
F, HOLD = D / "f", D / "hold"
UNIQ = secrets.token_hex(4)
SCHEME = "cezprobe-r"
# LaunchServices won't bind a URL scheme to an app under /tmp (kLSApplicationNotFoundErr, measured) =>
# the applet sits in the checkout's ignored .data/, ad-hoc signed; unregistered + deleted at the end
APPLET = SRC / ".data/probe-applet/cezprobe.app"
LSREGISTER = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
log, lock = [], threading.Lock()


def title(name):
    return f"JF probe {UNIQ} {name}"


POSTING = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
body {{ font: 16px/1.5 -apple-system, system-ui, sans-serif; margin: 0; color: #1d2433; background: #f6f7f9 }}
header {{ background: #fff; border-bottom: 1px solid #dde1e7; padding: 18px 32px }}
header b {{ font-size: 18px }} main {{ max-width: 760px; margin: 28px auto; padding: 0 24px }}
h1 {{ font-size: 28px; margin: 0 0 4px }} .meta {{ color: #5b6475; margin-bottom: 20px }}
.card {{ background: #fff; border: 1px solid #dde1e7; border-radius: 8px; padding: 20px 24px; margin-bottom: 16px }}
.apply {{ display: inline-block; background: #2257d6; color: #fff; padding: 10px 22px; border-radius: 6px; text-decoration: none }}
</style></head><body><header><b>Example Analytics Co.</b> &nbsp; Careers</header><main>
<h1>Data Analyst</h1><div class="meta">Remote (US) &middot; Full time &middot; $78,000 - $92,000 a year</div>
<p><a class="apply" href="#apply">Apply for this job</a></p>
<div class="card"><h2>About the role</h2><p>Example Analytics Co. helps small clinics see where their week goes.
You will own the weekly reporting pack, clean up how bookings data reaches the warehouse, and answer
questions from the operations team in plain words.</p></div>
<div class="card"><h2>What you will do</h2><ul><li>Build and keep the weekly SQL reports the clinics read on Monday</li>
<li>Check bookings and billing data for gaps before it reaches a dashboard</li>
<li>Explain a trend to a clinic manager in two sentences</li></ul></div>
<div class="card"><h2>What we look for</h2><ul><li>2+ years with SQL and spreadsheets</li>
<li>A dashboard tool (Looker, Tableau or Power BI)</li><li>Clear writing</li></ul>
<p>Test page served on this computer for a Job Finder probe - not a real job.</p></div></main></body></html>"""

FILE_PAGE = """<!doctype html><title>file page</title><script>
new Image().src = "http://127.0.0.1:{port}/beacon?k=file-page-hit&via=" + encodeURIComponent(location.hash);
</script>"""

HOSTILE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head><body>
<h1>hostile test page</h1>
<img src="{file}/probe-marker.png" onload="b('file-img-hit')" onerror="b('file-img-miss')">
<iframe src="{file}/probe-file-page.html#iframe"></iframe>
<iframe src="{scheme}://scheme-iframe"></iframe>
<script>
function b(k) {{ new Image().src = "/beacon?k=" + k + "&t=" + Date.now(); }}
fetch("{file}/My%20Resume/probe-secret.txt").then((r) => r.text()).then(() => b("file-fetch-hit"), () => b("file-fetch-miss"));
const w = window.open("/popup-hit?via=open");
b(w ? "popup-open-returned" : "popup-open-null");
const a = document.createElement("a");
a.href = "/popup-hit?via=aclick"; a.target = "_blank"; document.body.appendChild(a); a.click();
window.open("{file}/probe-file-page.html#open");
window.open("{scheme}://scheme-open");
const s = document.createElement("a");
s.href = "{scheme}://scheme-aclick"; document.body.appendChild(s); s.click();
setTimeout(() => {{ location.href = "{scheme}://scheme-nav"; }}, 500);
setTimeout(() => {{ b("stayed-1"); location.href = "{file}/probe-file-page.html#nav"; }}, 1500);
setTimeout(() => b("stayed-2"), 3500);
</script></body></html>"""


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="text/html; charset=utf-8", status=200, headers=()):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(url.query))
        with lock:
            log.append({"t": round(time.time(), 3), "path": self.path, "cookie": self.headers.get("Cookie"),
                        "ua": self.headers.get("User-Agent")})
        port = self.server.server_address[1]
        if url.path.startswith("/posting/"):
            return self.send(POSTING.format(title=title(url.path.split("/")[-1])))
        if url.path == "/hostile":
            return self.send(HOSTILE.format(title=title("hostile"), file=F.as_uri(), scheme=SCHEME))
        if url.path == "/signin":
            return self.send(f"<!doctype html><title>{title('signin')}</title><p>signed in",
                             headers=[("Set-Cookie", f"jf_signin={UNIQ}; Max-Age=31536000; Path=/; SameSite=Lax")])
        if url.path == "/whoami":
            got = (self.headers.get("Cookie") or "").replace(f"jf_signin={UNIQ}", "kept")
            return self.send(f"<!doctype html><title>{title('whoami ' + (got or 'none'))}</title><p>{got or 'none'}")
        if url.path.startswith("/popup-hit"):
            return self.send(f"<!doctype html><title>{title('popup')}</title>")
        if url.path == "/beacon":
            return self.send("", "text/plain", 204)
        self.send("", "text/plain", 404)


def png():
    row = b"\x00\xff\x00\x00"
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row)) + chunk(b"IEND", b""))


def run(cmd, env=None, cwd=F, timeout=300):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=timeout)
    return {"cmd": [str(c) for c in cmd], "rc": r.returncode, "stdout": r.stdout.strip()[-600:],
            "stderr": "\n".join(l for l in r.stderr.strip().splitlines() if "DEP0169" not in l and "trace-dep" not in l)[-600:],
            "ms": round((time.time() - t) * 1000)}


def setup():
    F.mkdir(parents=True)
    subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy(SRC / name, F)
    steps = [run(["uv", "run", "python", "app/tests/demo.py"]), run(["uv", "run", "app/jobs.py", "today"])]
    (F / ".data" / "ai").write_text("claude\n")
    (F / "probe-marker.png").write_bytes(png())
    (F / "My Resume" / "probe-secret.txt").write_text("probe secret - never leaves this folder\n")
    HOLD.mkdir()
    return steps


def applet(port):
    """Scratch app owning cezprobe-r://: an escaped link calls the site back (beacon scheme-hit)."""
    script = (f'on open location u\ndo shell script "/usr/bin/curl -s -G --data-urlencode k=scheme-hit '
              f'--data-urlencode " & quoted form of ("u=" & u) & " http://127.0.0.1:{port}/beacon > /dev/null"\nend open location')
    APPLET.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(APPLET, ignore_errors=True)
    subprocess.run(["osacompile", "-o", APPLET, "-e", script], check=True)
    plist = APPLET / "Contents/Info.plist"
    subprocess.run(["plutil", "-replace", "CFBundleIdentifier", "-string", f"com.example.cezprobe.{UNIQ}", plist], check=True)
    subprocess.run(["plutil", "-insert", "CFBundleURLTypes", "-json",
                    json.dumps([{"CFBundleURLName": "cez probe", "CFBundleURLSchemes": [SCHEME]}]), plist], check=True)
    subprocess.run(["codesign", "-f", "-s", "-", APPLET], check=True, capture_output=True)
    subprocess.run([LSREGISTER, "-f", APPLET], check=True)
    # control: the OS hands this scheme to the applet, which calls back
    subprocess.run(["open", f"{SCHEME}://control"], check=False)
    return wait_for(lambda: any("scheme-hit" in e["path"] and "control" in e["path"] for e in log), 20)


def wait_for(test, secs, every=0.25):
    end = time.time() + secs
    while time.time() < end:
        got = test()
        if got:
            return got
        time.sleep(every)
    return test()


n = 0


def ask(req, secs=30):
    global n
    n += 1
    name = f"{n:03d}"
    (HOLD / f"{name}.tmp").write_text(json.dumps(req))
    os.replace(HOLD / f"{name}.tmp", HOLD / f"{name}.req")
    res = HOLD / f"{name}.res"
    if not wait_for(res.exists, secs, 0.1):
        return {"req": req, "error": "no answer"}
    time.sleep(0.05)
    return json.loads(res.read_text())


def tab_with(tabs, label):
    for g in tabs or []:
        for t in g["tabs"]:
            if t["label"] == label:
                return {"group": g["viewColumn"], **t}
    return None


def wait_tabs(*names, secs=20):
    """Polls the window's tabs until one tab per title shows; -> {name: tab or None} + ms."""
    t = time.time()
    seen = {}

    def look():
        tabs = ask({"do": "tabs"}).get("tabs")
        for name in names:
            seen[name] = tab_with(tabs, title(name))
        return all(seen.values())
    wait_for(look, secs, 0.5)
    return {"tabs": seen, "ms": round((time.time() - t) * 1000)}


def jobs_open(url, env):
    r = run(["uv", "run", "app/jobs.py", "open", url], env)
    return {k: r[k] for k in ("rc", "stdout", "stderr", "ms")}


def main_pid():
    try:
        return int((D / "data/code.lock").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


WINDOWS = """ObjC.import('CoreGraphics'); ObjC.import('Foundation');
function run(argv) {
  var all = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0, 0))), pid = Number(argv[0]);
  return JSON.stringify(all.filter(function (w) { return w.kCGWindowOwnerPID === pid && w.kCGWindowLayer === 0; })
    .map(function (w) { return { id: w.kCGWindowNumber, name: w.kCGWindowName || '', b: w.kCGWindowBounds, on: Boolean(w.kCGWindowIsOnscreen) }; }));
}"""


def screenshot():
    pid = main_pid()
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", WINDOWS, str(pid)], capture_output=True, text=True)
    try:
        wins = json.loads(r.stdout)
    except ValueError:
        return {"error": r.stderr.strip()[-300:]}
    if not wins:
        return {"error": "no window for pid %s" % pid}
    win = max(wins, key=lambda w: w["b"]["Width"] * w["b"]["Height"])
    SHOT.parent.mkdir(parents=True, exist_ok=True)
    # this window only (-l), never the whole screen (owner's)
    subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), SHOT], check=False)
    return {"path": str(SHOT), "bytes": SHOT.stat().st_size if SHOT.exists() else 0, "window": win}


def running():
    return subprocess.run(["pgrep", "-f", f"{D.name}/data"], capture_output=True).returncode == 0


def wait_quit(report):
    wait_for(report.exists, 60, 0.5)
    if wait_for(lambda: not running(), 30, 0.5) is False:
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
        time.sleep(3)
        subprocess.run(["pkill", "-9", "-f", f"{D.name}/data"])
        return {"killed": True}
    return {"killed": False}


def probe_env(name):
    return {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / f"{name}.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
            "JOBS_VSCODE_PROBE_SETTLE_MS": "3000"}


def hits(entries):
    out = {"file": [], "scheme": [], "popup": []}
    for e in entries:
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(e["path"]).query))
        k = q.get("k", "")
        if e["path"].startswith("/popup-hit"):
            out["popup"].append(e["path"])
        elif k.startswith("file-") and k.endswith("-hit"):
            out["file"].append(e["path"])
        elif k == "scheme-hit" and "control" not in q.get("u", ""):
            out["scheme"].append(q.get("u"))
    return out


def trust_entries(drop=False):
    """Folder's rows in the trusted-folder key (shared store, default store fallback); drop => removed."""
    found = {}
    for db_path in (D / "shared/sharedStorage/state.vscdb", D / "data/User/globalStorage/state.vscdb"):
        if not db_path.exists():
            continue
        db = sqlite3.connect(db_path)
        try:
            row = db.execute("SELECT value FROM ItemTable WHERE key = 'content.trust.model.key'").fetchone()
            if not row:
                continue
            model = json.loads(row[0])
            mine = [e for e in model.get("uriTrustInfo", []) if e["uri"].get("path", "").startswith(str(F))]
            found[db_path.relative_to(D).as_posix()] = mine
            if drop and mine:
                model["uriTrustInfo"] = [e for e in model["uriTrustInfo"] if e not in mine]
                db.execute("UPDATE ItemTable SET value = ? WHERE key = 'content.trust.model.key'", (json.dumps(model),))
                db.commit()
        finally:
            db.close()
    return found


def dock_run(name):
    """`code <folder>` alone, as the Dock or recent folders open it; jobs.py open /whoami."""
    for f in HOLD.iterdir():
        f.unlink()
    env = probe_env(name)
    started = run(["code", "--user-data-dir", D / "data", "--extensions-dir", D / "ext", "--shared-data-dir", D / "shared",
                   "--new-window", F], {k: v for k, v in env.items() if k != "JOBS_VSCODE_DIR"}, cwd=D)
    up = ask({"do": "tabs"}, 120)
    mark = len(log)
    opened = jobs_open(f"{base}/whoami", env)
    seen = wait_for(lambda: next((t for g in ask({"do": "tabs"}).get("tabs") or [] for t in g["tabs"]
                                  if t["label"].startswith(title("whoami"))), None), 20, 0.5)
    whoami = [e for e in log[mark:] if e["path"] == "/whoami"]
    ask({"do": "quit"})
    quit_ = wait_quit(D / f"{name}.json")
    report = json.loads((D / f"{name}.json").read_text()) if (D / f"{name}.json").exists() else None
    return {"code": {k: started[k] for k in ("rc", "ms")}, "holdUp": "error" not in up, "open": opened, "tab": seen,
            "cookieSent": [e["cookie"] for e in whoami], "cookieKept": any(f"jf_signin={UNIQ}" in (e["cookie"] or "") for e in whoami),
            "trusted": report and report.get("trusted"), "untrustedLine": report and report.get("untrustedLine"), "quit": quit_,
            "browserStorage": sorted(p.replace(str(D), "$D") for p in glob.glob(f"{D}/data/**/browserStorage", recursive=True)),
            "report": report}


if running():
    sys.exit("a scratch VS Code on this dir is already running")
result = {"what": "r: links open as a tab in a scratch Job Finder window - Today click, jobs.py open, pairs, hostile page, "
          "window closed, Dock-style + untrusted cookie", "uniq": UNIQ,
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}", "scratch": "$D = mktemp -d /tmp/jfv.XXXX"}
result["setup"] = [{k: s[k] for k in ("cmd", "rc", "ms")} for s in setup()]
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
(F / "probe-file-page.html").write_text(FILE_PAGE.format(port=server.server_address[1]))
try:
    result["schemeControl"] = bool(applet(server.server_address[1]))
    print("scheme control", result["schemeControl"])

    # --- launch: cold, as the Desktop icon does
    env = probe_env("launch")
    result["launch"] = {k: v for k, v in run(["uv", "run", "app/jobs.py", "launch"], env).items() if k != "cmd"}
    up = ask({"do": "tabs"}, 180)
    result["holdUp"] = {"ok": "error" not in up, "tabs": up.get("tabs")}
    print("hold up", result["holdUp"]["ok"])
    steps = result["steps"] = {}

    res = ask({"do": "today-link", "urls": [f"{base}/posting/today"]})
    steps["today"] = {"action": {k: res.get(k) for k in ("ms", "error")}, **wait_tabs("today")}
    print("today", steps["today"]["tabs"])

    steps["open"] = {"jobsPy": jobs_open(f"{base}/posting/open", env), **wait_tabs("open")}
    print("open", steps["open"]["jobsPy"]["stdout"], steps["open"]["tabs"])

    t = time.time()
    pair = [subprocess.Popen(["uv", "run", "app/jobs.py", "open", f"{base}/posting/pair-{i}"], cwd=F, env={**os.environ, **env},
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True) for i in (1, 2)]
    said = [p.communicate(timeout=60)[0].strip() for p in pair]
    steps["pairJobsPy"] = {"said": said, "ms": round((time.time() - t) * 1000), **wait_tabs("pair-1", "pair-2")}
    res = ask({"do": "today-link", "urls": [f"{base}/posting/click-1", f"{base}/posting/click-2"]})
    steps["pairToday"] = {"action": {k: res.get(k) for k in ("ms", "error")}, **wait_tabs("click-1", "click-2")}
    print("pairs", steps["pairJobsPy"]["said"], steps["pairJobsPy"]["tabs"], steps["pairToday"]["tabs"])

    mark = len(log)
    steps["hostile"] = {"jobsPy": jobs_open(f"{base}/hostile", env), **wait_tabs("hostile")}
    time.sleep(6)
    steps["hostile"]["requests"] = [e["path"] for e in log[mark:]]
    steps["hostile"]["tabsAfter"] = ask({"do": "tabs"}).get("tabs")
    print("hostile", steps["hostile"]["requests"])

    steps["signin"] = {"jobsPy": jobs_open(f"{base}/signin", env), **wait_tabs("signin")}
    steps["shot"] = {"jobsPy": jobs_open(f"{base}/posting/shot", env), **wait_tabs("shot")}
    time.sleep(3)
    steps["shot"]["screenshot"] = screenshot()
    print("shot", steps["shot"]["screenshot"])
    result["browserStorage"] = sorted(p.replace(str(D), "$D") for p in glob.glob(f"{D}/data/**/browserStorage", recursive=True))
    result["trustAfterLaunch"] = trust_entries()
    ask({"do": "quit"})
    result["launchQuit"] = wait_quit(D / "launch.json")
    result["launchReport"] = json.loads((D / "launch.json").read_text()) if (D / "launch.json").exists() else None

    # --- window closed: system browser path, webbrowser.open stubbed
    stub = ("import sys, webbrowser; sys.path.insert(0, 'app'); import jobs\n"
            "got = []; webbrowser.open = lambda u, *a, **k: got.append(u) or True\n"
            "jobs.open_for_user(sys.argv[1]); print('stub got', got)")
    mark = len(log)
    r = run(["uv", "run", "python", "-c", stub, f"{base}/posting/closed"], {"JOBS_VSCODE_DIR": str(D)})
    result["closed"] = {"running": running(), "stdout": r["stdout"], "rc": r["rc"], "ms": r["ms"],
                        "siteRequests": [e["path"] for e in log[mark:]], "leftRequests": os.listdir(F / ".data/open-link")}
    print("closed", result["closed"])

    result["dock"] = dock_run("dock")
    print("dock", {k: result["dock"][k] for k in ("holdUp", "open", "cookieKept", "trusted")})
    result["untrustedDropped"] = trust_entries(drop=True)
    result["untrusted"] = dock_run("untrusted")
    print("untrusted", {k: result["untrusted"][k] for k in ("holdUp", "open", "cookieKept", "trusted")})
finally:
    if running():
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
    if APPLET.exists():
        subprocess.run([LSREGISTER, "-u", APPLET], check=False)
        shutil.rmtree(APPLET, ignore_errors=True)
    server.shutdown()
    result["serverLog"] = log
    result["hits"] = hits(log)
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D").replace(str(SRC), "<checkout>") + "\n")
    print("hits", json.dumps(result["hits"]))
