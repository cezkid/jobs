#!/usr/bin/env python3
"""v: job pages from Today open in one pane beside it, mail-reader style (owner 2026-10-13).
Scratch window as #r (program copy + demo, ai = claude, probe hold runs a Today click's own path).
Local site pages titled "JF probe <uniq> <name>" => tabs told by label.
  one       click job-1 -> Today in group 1, job-1 in group 2, focus back on Today
  replace   click job-2, then job-2b -> each closes the one before, still 2 groups, focus on Today
  touched   focus moved into job-2b (as a click on its page does), back to Today, click job-3 ->
            job-2b kept, job-3 beside it
  closed    pane's tabs closed -> one group, Today full width; again: job-4 opens a fresh pane
usage: 5-v-pane.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json> <screenshot png>
"""
import datetime
import http.server
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import pathlib

D, SRC, OUT, SHOT = (pathlib.Path(a).resolve() for a in sys.argv[1:5])
F, HOLD = D / "f", D / "hold"
UNIQ = secrets.token_hex(4)


def title(name):
    return f"JF probe {UNIQ} {name}"


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{t}</title><style>
body {{ font: 16px/1.5 -apple-system, system-ui, sans-serif; margin: 0; color: #1d2433; background: #f6f7f9 }}
main {{ max-width: 760px; margin: 28px auto; padding: 0 24px }} h1 {{ font-size: 26px }}
</style></head><body><main><h1>{name}</h1><p>Posting text for {name}. Apply below.</p><form><input placeholder="Name"></form></main></body></html>"""


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        name = urllib.parse.urlsplit(self.path).path.strip("/").split("/")[-1]
        body = PAGE.format(t=title(name), name=name).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(cmd, env=None):
    r = subprocess.run(cmd, cwd=F, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=300)
    return {"rc": r.returncode, "stdout": r.stdout.strip()[-400:]}


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


def layout(tabs):
    """[[group, active?, [labels]]] w/ probe titles shortened to their name."""
    short = lambda label: label.replace(title(""), "")
    return [{"group": g["viewColumn"], "active": g["isActive"], "tabs": [short(t["label"]) + ("*" if t["isActive"] else "") for t in g["tabs"]]}
            for g in tabs or []]


def settle(secs=2.5):
    time.sleep(secs)
    return layout(ask({"do": "tabs"}).get("tabs"))


def screenshot():
    pid = int((D / "data/code.lock").read_text().split()[0])
    js = """ObjC.import('CoreGraphics'); function run(a) { var all = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0, 0)));
      return JSON.stringify(all.filter(function (w) { return w.kCGWindowOwnerPID === Number(a[0]) && w.kCGWindowLayer === 0; })
      .map(function (w) { return { id: w.kCGWindowNumber, b: w.kCGWindowBounds }; })); }"""
    wins = json.loads(subprocess.run(["osascript", "-l", "JavaScript", "-e", js, str(pid)], capture_output=True, text=True).stdout or "[]")
    if not wins:
        return None
    win = max(wins, key=lambda w: w["b"]["Width"] * w["b"]["Height"])
    subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), SHOT], check=False)  # this window only
    return str(SHOT)


F.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
for name in ("pyproject.toml", "uv.lock"):
    shutil.copy(SRC / name, F)
run(["uv", "run", "python", "app/tests/demo.py"])
run(["uv", "run", "app/jobs.py", "today"])
(F / ".data" / "ai").write_text("claude\n")
HOLD.mkdir()
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
env = {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / "v.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
       "JOBS_VSCODE_PROBE_SETTLE_MS": "3000"}
result = {"what": "v: job pages from Today in one side pane", "uniq": UNIQ,
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}"}
click = lambda name: ask({"do": "today-link", "urls": [f"{base}/posting/{name}"]})
try:
    result["launch"] = run(["uv", "run", "app/jobs.py", "launch"], env)
    result["up"] = layout(ask({"do": "tabs"}, 180).get("tabs"))
    steps = result["steps"] = {}
    steps["one"] = {"ms": click("job-1").get("ms"), "tabs": settle()}
    steps["replace"] = {"ms": click("job-2").get("ms"), "tabs": settle()}
    steps["replace2"] = {"ms": click("job-2b").get("ms"), "tabs": settle()}
    result["screenshot"] = screenshot()
    ask({"do": "command", "id": "workbench.action.focusSecondEditorGroup"})
    time.sleep(0.5)
    ask({"do": "command", "id": "workbench.action.focusFirstEditorGroup"})
    steps["touched"] = {"ms": click("job-3").get("ms"), "tabs": settle()}
    ask({"do": "command", "id": "workbench.action.focusSecondEditorGroup"})
    ask({"do": "command", "id": "workbench.action.closeEditorsInGroup"})
    steps["closed"] = {"tabs": settle()}
    steps["again"] = {"ms": click("job-4").get("ms"), "tabs": settle()}
    for k, v in steps.items():
        print(k, v)
    ask({"do": "quit"})
    time.sleep(5)
finally:
    subprocess.run(["pkill", "-f", f"{D.name}/data"])
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D") + "\n")
