#!/bin/bash
# m: Outline + Timeline hidden under the file list (plan-ejf.12.1). Scratch cold `jobs.py launch`
# on the demo folder (this checkout after `uv run python app/tests/demo.py`, .data/ai = claude):
# launcher makes the CEZ profile + writes the hidden views, window runs w/ the probe, quits. VS Code
# re-saves the Explorer's whole view list on quit => the list read after is its own model, not ours.
# usage: 5-m-views.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json>
D=$1; SRC=$2; OUT=$(cd "$(dirname "$3")" && pwd)/$(basename "$3")
rm -f "$OUT"
(cd "$SRC" && JOBS_VSCODE_DIR="$D" JOBS_VSCODE_PROBE="$OUT" JOBS_VSCODE_PROBE_SETTLE_MS=8000 uv run app/jobs.py launch)
for i in $(seq 120); do [ -s "$OUT" ] && break; sleep 1; done
for i in $(seq 15); do pgrep -f "$D/data" >/dev/null || break; sleep 1; done
if pgrep -f "$D/data" >/dev/null; then echo "still running - killed"; pkill -f "$D/data"; sleep 3; pkill -9 -f "$D/data"; fi
[ -s "$OUT" ] || { echo "NO PROBE"; exit 1; }
python3 - "$D" "$OUT" <<'Q'
import json, sqlite3, sys, pathlib
d, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
storage = json.loads((d / "data/User/globalStorage/storage.json").read_text())
loc = next(p["location"] for p in storage["userDataProfiles"] if p["name"] == "CEZ Job Finder")
db = sqlite3.connect(d / "data/User/profiles" / loc / "globalStorage/state.vscdb")
rows = dict(db.execute("SELECT key, value FROM ItemTable WHERE key IN (?, ?)",
                       ("workbench.explorer.views.state.hidden", "cez-job-finder.views-hidden")).fetchall())
views = json.loads(rows["workbench.explorer.views.state.hidden"])
r = json.loads(out.read_text())
r["explorerViews"] = {"profile": loc, "doneKey": rows.get("cez-job-finder.views-hidden"),
                      "afterQuit": views,
                      "visible": sorted(v["id"] for v in views if isinstance(v, dict) and not v["isHidden"]),
                      "hidden": sorted(v["id"] if isinstance(v, dict) else v for v in views if not isinstance(v, dict) or v["isHidden"])}
out.write_text(json.dumps(r, indent=1) + "\n")
print(json.dumps({"tabs": r["tabs"], "extensions": r["extensions"], "explorerViews": {k: r["explorerViews"][k] for k in ("profile", "visible", "hidden")}}, indent=1))
Q
