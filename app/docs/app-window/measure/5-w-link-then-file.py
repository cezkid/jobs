#!/usr/bin/env python3
"""w: a link shown with `jobs.py open`, then a file shown the same way right after (job-apply's
handover: posting, then the tailored resume) - does the link's tab survive? (owner 2026-11-05: "saw
it open but then closed")
Scratch window as #r (program copy + demo, ai = claude, probe hold reads tabs w/ isPreview).
  link        jobs.py open <page> alone -> its tab, preview or kept
  link-file   jobs.py open <page>, then at once jobs.py open <file> -> both tabs still there?
  file-link   the other order
usage: 5-w-link-then-file.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json>
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
env = {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / "w.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
       "JOBS_VSCODE_PROBE_SETTLE_MS": "3000"}
result = {"what": "w: link then file, both through jobs.py open", "uniq": UNIQ,
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}", "files": {k: str(v) for k, v in files.items()}}
show = lambda target: run(["uv", "run", "app/jobs.py", "open", str(target)], env)
try:
    result["launch"] = run(["uv", "run", "app/jobs.py", "launch"], env)
    result["up"] = layout(ask({"do": "tabs"}, 180).get("tabs"))
    steps = result["steps"] = {}
    steps["link"] = {"open": show(f"{base}/posting/alone"), "tabs": settle()}
    for kind, path in files.items():
        close_all()
        a = show(f"{base}/posting/then-{kind}")
        b = show(path)
        steps[f"link-{kind}"] = {"open": [a, b], "tabs": settle()}
        close_all()
        b = show(path)
        a = show(f"{base}/posting/after-{kind}")
        steps[f"{kind}-link"] = {"open": [b, a], "tabs": settle()}
    for k, v in steps.items():
        print(k, v)
    ask({"do": "quit"})
    time.sleep(5)
finally:
    subprocess.run(["pkill", "-f", f"{D.name}/data"])
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D") + "\n")
