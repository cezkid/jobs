#!/usr/bin/env python3
"""t: `jobs.py clear-signins` empties the window's sign-ins (plan-29g.14).
Folder = copy of the program + demo (as s). Local site on 127.0.0.1: /signin sets a 1-year cookie,
/whoami shows whether it came back (server log keeps the Cookie header).
  launch    cold `jobs.py launch`, `jobs.py open /signin` -> /whoami: kept; close every tab; quit
  cold      `jobs.py launch` again, no tab restored or opened (server log: no page loaded) -> cookie
            row on disk -> `jobs.py clear-signins`
            (screenshot, window only: any dialog?) -> /whoami: gone? cookie rows left?
  tabs      /signin again -> /whoami kept -> `jobs.py clear-signins` w/ both tabs open -> /whoami
  closed    quit -> `jobs.py clear-signins` w/ the window closed: says so, exit 1
  relaunch  `jobs.py launch` -> /whoami: still gone?
usage: 5-t-clear-cmd.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json> <screenshot png>
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
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

D, SRC, OUT, SHOT = (pathlib.Path(a).resolve() for a in sys.argv[1:5])
F, HOLD = D / "f", D / "hold"
UNIQ = secrets.token_hex(4)
log, lock = [], threading.Lock()


def title(name):
    return f"JF probe {UNIQ} {name}"


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, headers=()):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        with lock:
            log.append({"t": round(time.time(), 3), "path": self.path, "cookie": self.headers.get("Cookie")})
        if url.path == "/signin":
            return self.send(f"<!doctype html><title>{title('signin')}</title><p>signed in",
                             [("Set-Cookie", f"jf_signin={UNIQ}; Max-Age=31536000; Path=/; SameSite=Lax")])
        if url.path == "/whoami":
            got = (self.headers.get("Cookie") or "").replace(f"jf_signin={UNIQ}", "kept")
            return self.send(f"<!doctype html><title>{title('whoami ' + (got or 'none'))}</title><p>{got or 'none'}")
        self.send("")


def run(cmd, env=None, cwd=F, timeout=300):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=timeout)
    return {"cmd": [str(c) for c in cmd], "rc": r.returncode, "stdout": r.stdout.strip()[-600:],
            "stderr": r.stderr.strip()[-600:], "ms": round((time.time() - t) * 1000)}


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


def tab_label(prefix):
    for g in ask({"do": "tabs"}).get("tabs") or []:
        for t in g["tabs"]:
            if t["label"].startswith(prefix):
                return t["label"]
    return None


def whoami(env, step):
    """jobs.py open /whoami?n=<step> -> cookie the site got + the tab's label."""
    path = f"/whoami?n={step}"
    for _ in range(3):  # a busy window can miss one; a miss falls back to the BROWSER stub
        said = run(["uv", "run", "app/jobs.py", "open", base + path], env)["stdout"]
        if said == "opened in the Job Finder window":
            break
        time.sleep(2)
    got = wait_for(lambda: [e for e in log if e["path"] == path], 20, 0.25)
    label = wait_for(lambda: tab_label(title("whoami")), 10, 0.5)
    cookie = got[0]["cookie"] if got else None
    return {"said": said, "cookieSent": cookie, "kept": f"jf_signin={UNIQ}" in (cookie or ""), "tab": label}


def storage():
    """Every browserStorage dir under the scratch data: its folder's workspace.json, files, bytes, cookie rows."""
    out = []
    for p in sorted(glob.glob(f"{D}/data/**/browserStorage", recursive=True)):
        p = pathlib.Path(p)
        files = [f for f in p.rglob("*") if f.is_file()]
        ws = p.parent / "workspace.json"
        rows = None
        cookies = p / "Cookies"
        if cookies.exists():
            with tempfile.TemporaryDirectory() as tmp:  # live db: read a copy
                shutil.copy(cookies, tmp)
                for side in ("Cookies-wal", "Cookies-journal"):
                    if (p / side).exists():
                        shutil.copy(p / side, tmp)
                try:
                    db = sqlite3.connect(pathlib.Path(tmp) / "Cookies")
                    rows = [r[0] for r in db.execute("SELECT name FROM cookies WHERE host_key LIKE '%127.0.0.1%'")]
                    db.close()
                except sqlite3.Error as err:
                    rows = f"unreadable: {err}"
        out.append({"path": str(p), "workspaceJson": json.loads(ws.read_text()) if ws.exists() else None,
                    "files": len(files), "bytes": sum(f.stat().st_size for f in files), "cookieRows": rows})
    return out


WINDOWS = """ObjC.import('CoreGraphics'); ObjC.import('Foundation');
function run(argv) {
  var all = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0, 0))), pid = Number(argv[0]);
  return JSON.stringify(all.filter(function (w) { return w.kCGWindowOwnerPID === pid && w.kCGWindowLayer === 0; })
    .map(function (w) { return { id: w.kCGWindowNumber, b: w.kCGWindowBounds }; }));
}"""


def screenshot():
    try:
        pid = int((D / "data/code.lock").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return {"error": "no code.lock"}
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", WINDOWS, str(pid)], capture_output=True, text=True)
    wins = json.loads(r.stdout or "[]")
    if not wins:
        return {"error": f"no window for pid {pid}"}
    win = max(wins, key=lambda w: w["b"]["Width"] * w["b"]["Height"])
    SHOT.parent.mkdir(parents=True, exist_ok=True)
    # this window only (-l), never the whole screen (owner's)
    subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), SHOT], check=False)
    return {"path": str(SHOT), "bytes": SHOT.stat().st_size if SHOT.exists() else 0}


def running():
    return subprocess.run(["pgrep", "-f", f"{D.name}/data"], capture_output=True).returncode == 0


def quit_window(report):
    ask({"do": "quit"})
    wait_for(report.exists, 60, 0.5)
    if wait_for(lambda: not running(), 30, 0.5) is False:
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
        time.sleep(3)
        return {"killed": True}
    return {"killed": False}


def launch(name):
    for f in HOLD.iterdir():
        f.unlink()
    # BROWSER: a link the window doesn't take falls back to webbrowser.open => never the owner's
    # real browser (first run: a cold window missed /signin and it opened there)
    env = {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / f"{name}.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
           "JOBS_VSCODE_PROBE_SETTLE_MS": "3000", "BROWSER": "/usr/bin/true"}
    started = run(["uv", "run", "app/jobs.py", "launch"], env)
    up = ask({"do": "tabs"}, 600)  # loaded Mac: a cold window once took ~9 min
    return env, {"rc": started["rc"], "ms": started["ms"], "holdUp": "error" not in up}


def clear(env):
    """`jobs.py clear-signins` as the AI runs it: what it said, exit code, time."""
    r = run(["uv", "run", "app/jobs.py", "clear-signins"], env)
    return {k: r[k] for k in ("rc", "stdout", "stderr", "ms")}


def signin(env, step):
    """`jobs.py open /signin` until the window takes it (a cold window can miss the first); tries kept."""
    tries = []
    for _ in range(6):
        said = run(["uv", "run", "app/jobs.py", "open", f"{base}/signin?n={step}"], env)["stdout"]
        tries.append(said)
        if said == "opened in the Job Finder window":
            break
        time.sleep(2)
    got = wait_for(lambda: [e for e in log if e["path"] == f"/signin?n={step}"], 20, 0.25)
    return {"tries": tries, "served": bool(got), "tab": wait_for(lambda: tab_label(title("signin")), 20, 0.5)}


def browser_tabs():
    return [t["label"] for g in ask({"do": "tabs"}).get("tabs") or [] for t in g["tabs"] if t["label"].startswith("JF probe")]


if running():
    sys.exit("a scratch VS Code on this dir is already running")
result = {"what": "t: jobs.py clear-signins empties the window's sign-ins (with and without a tab open)", "uniq": UNIQ,
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}", "scratch": "$D = mktemp -d /tmp/jfv.XXXX"}
F.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
for name in ("pyproject.toml", "uv.lock"):
    shutil.copy(SRC / name, F)
result["setup"] = [{k: s[k] for k in ("cmd", "rc", "ms")} for s in
                   (run(["uv", "run", "python", "app/tests/demo.py"]), run(["uv", "run", "app/jobs.py", "today"]))]
(F / ".data" / "ai").write_text("claude\n")
HOLD.mkdir()
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
steps = result["steps"] = {}
try:
    env, result["launch"] = launch("launch")
    print("launch", result["launch"])
    steps["signin"] = signin(env, 1)
    steps["before"] = whoami(env, 1)
    print("before", steps["before"])
    # every tab shut => none restored next start: the clear runs before any page has loaded
    steps["closeAll"] = ask({"do": "command", "id": "workbench.action.closeAllEditors"}).get("error")
    result["launchQuit"] = quit_window(D / "launch.json")
    steps["whereQuit"] = storage()
    print("whereQuit", steps["whereQuit"])

    env, result["cold"] = launch("cold")
    steps["coldTabs"] = browser_tabs()
    steps["coldLoadsBefore"] = len(log)
    steps["coldBefore"] = storage()
    steps["coldClear"] = clear(env)
    steps["coldLoadsAtClear"] = len(log)
    time.sleep(1)
    steps["coldShot"] = screenshot()
    steps["coldWhere"] = storage()
    steps["coldAfter"] = whoami(env, 2)
    print("cold", steps["coldTabs"], steps["coldClear"], steps["coldAfter"], steps["coldWhere"])

    steps["signinAgain"] = signin(env, 2)
    steps["tabsBefore"] = whoami(env, 3)
    steps["tabsOpen"] = browser_tabs()
    steps["tabsClear"] = clear(env)
    time.sleep(1)
    steps["tabsAfter"] = whoami(env, 4)
    print("tabs", steps["tabsBefore"], steps["tabsOpen"], steps["tabsClear"], steps["tabsAfter"])
    result["coldQuit"] = quit_window(D / "cold.json")

    steps["closedClear"] = clear(env)
    print("closed", steps["closedClear"])

    env, result["relaunch"] = launch("relaunch")
    steps["relaunched"] = whoami(env, 5)
    print("relaunched", steps["relaunched"])
    result["relaunchQuit"] = quit_window(D / "relaunch.json")
    steps["whereEnd"] = storage()
finally:
    if running():
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
    server.shutdown()
    result["serverLog"] = log
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D").replace(str(SRC), "<checkout>") + "\n")
