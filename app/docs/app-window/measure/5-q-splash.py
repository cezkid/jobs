#!/usr/bin/env python3
"""q: Mac loading splash live (plan-ejf.13.4) - app/install/splash-mac.js on a scratch root, shown on
this screen. Started like start-mac.sh does (splash-start written, then osascript in the background).
  show   ms from the osascript start to the window ordered on screen (script's own clock, --log), 5 runs
  ready  ms from .data/window-ready written to the window closed, 5 runs (same runs, ready 1.5 s in)
  click  left click posted at the window's middle 1.5 s in (CGEvent; needs the Accessibility
         permission for the terminal - not granted => it stays up, reported as not delivered)
  cap    no ready file, no click: closes by itself (45 s)
  renders  --render=<png> in light + dark (drawn by the view, no screenshot) -> <renders dir>
usage: 5-q-splash.py <scratch root from mktemp -d /tmp/jfv.XXXX> <checkout> <out json> [renders dir=/tmp/jfv-splash-renders]
"""
import datetime
import json
import pathlib
import platform
import shutil
import statistics
import subprocess
import sys
import time

root, src, out = (pathlib.Path(a).resolve() for a in sys.argv[1:4])
renders = pathlib.Path(sys.argv[4] if len(sys.argv) > 4 else "/tmp/jfv-splash-renders")
splash = src / "app/install/splash-mac.js"
data = root / ".data"
data.mkdir(parents=True, exist_ok=True)
(root / "app/install").mkdir(parents=True, exist_ok=True)
shutil.copy(src / "app/install/icon.icns", root / "app/install")
log = data / "splash-log.json"

# click the middle of the screen under the pointer's visible area = the splash's middle; pointer put back
CLICK = """ObjC.import('Cocoa'); ObjC.import('CoreGraphics');
function run() {
  var at = $.NSEvent.mouseLocation, screens = $.NSScreen.screens, on = $.NSScreen.mainScreen;
  for (var i = 0; i < screens.count; i++) {
    var f = screens.objectAtIndex(i).frame;
    if (at.x >= f.origin.x && at.x < f.origin.x + f.size.width && at.y >= f.origin.y && at.y < f.origin.y + f.size.height) on = screens.objectAtIndex(i);
  }
  var v = on.visibleFrame, top = screens.objectAtIndex(0).frame.size.height;
  var to = { x: v.origin.x + v.size.width / 2, y: top - (v.origin.y + v.size.height / 2) }, back = { x: at.x, y: top - at.y };
  [1, 2].forEach(function (type) { $.CGEventPost(0, $.CGEventCreateMouseEvent(null, type, to, 0)); delay(0.05); });
  $.CGWarpMouseCursorPosition(back);
  return JSON.stringify({ clicked: to, trusted: Boolean($.AXIsProcessTrusted()) });
}"""


def show(act=None, wait=60):
    """One splash from start to close; act(t0) runs while it is up. -> its log + ms numbers."""
    for f in (log, data / "window-ready"):
        f.unlink(missing_ok=True)
    (data / "splash-start").write_text("")
    t0 = time.time()
    p = subprocess.Popen(["osascript", "-l", "JavaScript", str(splash), str(root), f"--log={log}"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    extra = act(t0) if act else {}
    try:
        p.wait(wait)
    except subprocess.TimeoutExpired:
        p.kill()
        return {"why": "killed - still up after %d s" % wait, **extra}
    r = json.loads(log.read_text())
    return {"why": r["why"], "onScreen": r["onScreen"], "showMs": round((r["shown"] - t0) * 1000),
            "importToShowMs": round((r["shown"] - r["started"]) * 1000), "upMs": round((r["closed"] - r["shown"]) * 1000),
            "closed": r["closed"], **extra}


def ready(t0):
    time.sleep(1.5)
    (data / "window-ready").write_text("")
    return {"readyAt": time.time()}


def click(t0):
    time.sleep(1.5)
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", CLICK], capture_output=True, text=True)
    return {"clickAt": time.time(), "clicker": json.loads(r.stdout) if r.returncode == 0 else r.stderr.strip()}


(data / "look").unlink(missing_ok=True)
runs = []
for n in range(5):
    r = show(ready)
    r["readyToClosedMs"] = round((r.pop("closed") - r.pop("readyAt")) * 1000)
    runs.append(r)
    print("ready", n + 1, r)
clicked = show(click, wait=10)
if "closed" in clicked:
    clicked["clickToClosedMs"] = round((clicked.pop("closed") - clicked.pop("clickAt")) * 1000)
print("click", clicked)
cap = show()
cap.pop("closed", None)
print("cap", cap)

renders.mkdir(parents=True, exist_ok=True)
made = {}
for look in ("light", "dark"):
    (data / "look").write_text(look + "\n")
    png = renders / f"splash-{look}.png"
    r = subprocess.run(["osascript", "-l", "JavaScript", str(splash), str(root), f"--render={png}"], capture_output=True, text=True)
    made[look] = {"png": str(png), "bytes": png.stat().st_size if png.exists() else 0, "said": r.stdout.strip() or r.stderr.strip()}
(data / "look").unlink()

med = lambda key: {"median": int(statistics.median(r[key] for r in runs)), "max": max(r[key] for r in runs), "all": [r[key] for r in runs]}
report = {"what": "q: Mac loading splash live - ms from the osascript start to on screen, from window-ready written to closed; click; cap; renders",
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "mac": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
          "showMs": med("showMs"), "importToShowMs": med("importToShowMs"), "readyToClosedMs": med("readyToClosedMs"),
          "closedBy": sorted({r["why"] for r in runs}), "click": clicked, "cap": cap, "renders": made, "runs": runs}
out.write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({k: report[k] for k in ("showMs", "importToShowMs", "readyToClosedMs", "closedBy")}))
