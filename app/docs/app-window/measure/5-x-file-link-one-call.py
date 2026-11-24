#!/usr/bin/env python3
"""x: job-apply's handover as it runs it - ONE call, `jobs.py open <resume pdf> <posting link>` - as the
window's first PDF since it started (viewer not yet running). #w measured file-then-link as two
calls with the viewer already warm: page in front. Owner 2026-11-23: "browser windows don't open
anymore" - the posting's tab was there, behind the resume.
Scratch window as #w.
  cold   first PDF of the window: jobs.py open <pdf> <page> -> which tab is in front?
  warm   all closed, the same call again
  yml    all closed, a plain text file + page
usage: 5-x-file-link-one-call.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json>
"""
import datetime
import http.server
import json
import os
import pathlib
import platform
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

D, SRC, OUT = (pathlib.Path(a).resolve() for a in sys.argv[1:4])
F, HOLD = D / "f", D / "hold"
UNIQ = secrets.token_hex(4)


def title(name):
    return f"JF probe {UNIQ} {name}"


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        name = urllib.parse.urlsplit(self.path).path.strip("/").split("/")[-1]
        body = f"<!doctype html><title>{title(name)}</title><h1>{name}</h1>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(cmd, env=None):
    t = time.time()
    r = subprocess.run(cmd, cwd=F, env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=300)
    return {"rc": r.returncode, "stdout": r.stdout.strip()[-400:], "s": round(time.time() - t, 1)}


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
    short = lambda label: label.replace(title(""), "")
    return [{"group": g["viewColumn"], "tabs": [short(t["label"]) + (" (preview)" if t.get("isPreview") else "") + ("*" if t["isActive"] else "")
                                                for t in g["tabs"]]} for g in tabs or []]


def settle(secs=3.0):
    time.sleep(secs)
    return layout(ask({"do": "tabs"}).get("tabs"))


def close_all():
    ask({"do": "command", "id": "workbench.action.closeAllEditors"})
    time.sleep(1)


F.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
for name in ("pyproject.toml", "uv.lock"):
    shutil.copy(SRC / name, F)
run(["uv", "run", "python", "app/tests/demo.py"])
run(["uv", "run", "app/jobs.py", "today"])
(F / ".data" / "ai").write_text("claude\n")
HOLD.mkdir()
files = {"yml": F / "My Settings" / "probe-w.yml"}
files["yml"].parent.mkdir(parents=True, exist_ok=True)
files["yml"].write_text("probe: w\n")
# a resume-like PDF where job-apply's handover finds one (job folder); the pdf viewer = launch's own
job = F / "My Jobs" / "1 To apply" / "1 - Probe - Engineer"
job.mkdir(parents=True, exist_ok=True)
files["pdf"] = job / "First_Last_Resume.pdf"
shutil.copy(SRC / "app/web/research/resume-parser-test-2026-10/pdf/one-column.pdf", files["pdf"])
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
env = {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / "x.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
       "JOBS_VSCODE_PROBE_SETTLE_MS": "3000"}
result = {"what": "x: file + link in one jobs.py open call, first PDF of the window", "uniq": UNIQ,
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}", "files": {k: str(v) for k, v in files.items()}}
show = lambda *targets: run(["uv", "run", "app/jobs.py", "open", *map(str, targets)], env)
try:
    result["launch"] = run(["uv", "run", "app/jobs.py", "launch"], env)
    result["up"] = layout(ask({"do": "tabs"}, 180).get("tabs"))
    steps = result["steps"] = {}
    steps["cold"] = {"open": show(files["pdf"], f"{base}/posting/cold"), "tabs": settle(6), "later": settle(10)}
    close_all()
    steps["warm"] = {"open": show(files["pdf"], f"{base}/posting/warm"), "tabs": settle()}
    close_all()
    steps["yml"] = {"open": show(files["yml"], f"{base}/posting/yml"), "tabs": settle()}
    for k, v in steps.items():
        print(k, v)
    ask({"do": "quit"})
    time.sleep(5)
finally:
    subprocess.run(["pkill", "-f", f"{D.name}/data"])
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D") + "\n")
