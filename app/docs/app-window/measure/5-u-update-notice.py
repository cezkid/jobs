#!/usr/bin/env python3
"""u: an update ships window extension N+1 while the window runs N (plan-29g.19).
Folder = copy of the program + demo (as t), ai = copilot (no chat extension to fetch).
  cold      `jobs.py launch` on N -> window-running.json = N, Today: no restart line
  update    copy's app/vscode/package.json -> N+1, `jobs.py window-update` while it runs -> what it
            said, window-installed = N+1, Today redrawn w/ the restart line (how long), version N still
  closed    close the window only (VS Code left running) -> `jobs.py window-update` again: says nothing?
  warm      `jobs.py launch` on the running VS Code -> which version the new window records
  relaunch  quit fully, cold `jobs.py launch` -> N+1, Today: no restart line
usage: 5-u-update-notice.py <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json>
"""
import datetime
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

D, SRC, OUT = (pathlib.Path(a).resolve() for a in sys.argv[1:4])
F, HOLD = D / "f", D / "hold"
RUNNING, INSTALLED = F / ".data" / "window-running.json", F / ".data" / "window-installed"


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


def records():
    def read(p):
        try:
            return p.read_text().strip()
        except OSError:
            return None
    running = read(RUNNING)
    return {"running": json.loads(running) if running else None, "installed": read(INSTALLED)}


def today():
    """Last Today drawn: its restart line + the window's own version (extension.js holdFor)."""
    r = ask({"do": "today"})
    return {"own": r.get("own"), "restart": (r.get("today") or {}).get("restart"), "error": r.get("error")}


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


def clear_hold():
    for f in HOLD.iterdir():
        f.unlink()


def launch(name, wait=600):
    clear_hold()
    env = {"JOBS_VSCODE_DIR": str(D), "JOBS_VSCODE_PROBE": str(D / f"{name}.json"), "JOBS_VSCODE_PROBE_HOLD": str(HOLD),
           "JOBS_VSCODE_PROBE_SETTLE_MS": "3000", "BROWSER": "/usr/bin/true"}
    started = run(["uv", "run", "app/jobs.py", "launch"], env)
    up = ask({"do": "tabs"}, wait)  # loaded Mac: a cold window once took ~9 min
    return env, {"rc": started["rc"], "ms": started["ms"], "holdUp": "error" not in up}


if running():
    sys.exit("a scratch VS Code on this dir is already running")
result = {"what": "u: update ships window extension N+1 while the window runs N", "scratch": "$D = mktemp -d /tmp/jfv.XXXX",
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}"}
F.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude", "__pycache__", f"{SRC}/app", f"{F}/"], check=True)
for name in ("pyproject.toml", "uv.lock"):
    shutil.copy(SRC / name, F)
result["setup"] = [{k: s[k] for k in ("cmd", "rc", "ms")} for s in
                   (run(["uv", "run", "python", "app/tests/demo.py"]), run(["uv", "run", "app/jobs.py", "today"]))]
(F / ".data" / "ai").write_text("copilot\n")
HOLD.mkdir()
pkg_file = F / "app" / "vscode" / "package.json"
pkg = json.loads(pkg_file.read_text())
n_version = pkg["version"]
parts = n_version.split(".")
n1_version = ".".join([*parts[:-1], str(int(parts[-1]) + 1)])
result["versions"] = {"N": n_version, "N+1": n1_version}
steps = result["steps"] = {}
try:
    env, result["cold"] = launch("cold")
    steps["cold"] = {**records(), "today": wait_for(lambda: (t := today())["own"] and t, 30, 1)}
    print("cold", steps["cold"])

    pkg_file.write_text(json.dumps({**pkg, "version": n1_version}, indent=2) + "\n")
    t0 = time.time()
    said = run(["uv", "run", "app/jobs.py", "window-update"], env)
    shown = wait_for(lambda: (t := today())["restart"] and t, 30, 0.5)
    steps["update"] = {"said": {k: said[k] for k in ("rc", "stdout", "stderr", "ms")}, **records(),
                       "today": shown or today(), "noticeMs": round((time.time() - t0) * 1000) - said["ms"]}
    print("update", steps["update"])

    # the window only: on a Mac VS Code keeps running w/o a window (the owner's case)
    ask({"do": "command", "id": "workbench.action.closeWindow"}, 10)
    time.sleep(5)
    steps["closed"] = {"vscodeStillRunning": running(), **records(),
                       "said": {k: v for k, v in run(["uv", "run", "app/jobs.py", "window-update"], env).items()
                                if k in ("rc", "stdout", "stderr")}}
    print("closed", steps["closed"])

    before = (records()["running"] or {}).get("pid")
    env, result["warm"] = launch("warm", 60)  # new window may not get the probe's env
    steps["warm"] = {**records(), "newRecord": wait_for(lambda: (records()["running"] or {}).get("pid") != before, 60, 1),
                     "today": today() if result["warm"]["holdUp"] else None}
    print("warm", steps["warm"])
    result["warmQuit"] = quit_window(D / "warm.json") if result["warm"]["holdUp"] else None
    if running():
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
        wait_for(lambda: not running(), 30, 0.5)

    env, result["relaunch"] = launch("relaunch")
    steps["relaunch"] = {**records(), "today": wait_for(lambda: (t := today())["own"] and t, 30, 1)}
    print("relaunch", steps["relaunch"])
    result["relaunchQuit"] = quit_window(D / "relaunch.json")
finally:
    if running():
        subprocess.run(["pkill", "-f", f"{D.name}/data"])
    OUT.write_text(json.dumps(result, indent=1).replace(str(D), "$D").replace(str(SRC), "<checkout>") + "\n")
