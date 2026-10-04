#!/bin/bash
# n: opened w/o the Desktop icon (plan-ejf.12.2). Scratch cold `jobs.py launch` on the demo folder
# (this checkout after `uv run python app/tests/demo.py`, .data/ai = claude), window self-quits; then
# Today aged 3 h + the folder opened alone (`code <folder>`: no trust flag, no marker, like the Dock).
# BEFORE=1: launcher w/o its trust step (= code before the fix). Every code call carries
# --shared-data-dir: VS Code 1.140 keeps trusted folders in ~/.vscode-shared otherwise.
# usage: [BEFORE=1] 5-n-trust.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout> <out json>
D=$1; SRC=$2; OUT=$(cd "$(dirname "$3")" && pwd)/$(basename "$3"); L=$D/launch.json
rm -f "$OUT" "$L"
wait_quit() {
  for i in $(seq 120); do [ -s "$1" ] && break; sleep 1; done
  for i in $(seq 20); do pgrep -f "$D/data" >/dev/null || break; sleep 1; done
  if pgrep -f "$D/data" >/dev/null; then echo "still running - killed"; pkill -f "$D/data"; sleep 3; pkill -9 -f "$D/data"; fi
  [ -s "$1" ] || { echo "NO PROBE $1"; exit 1; }
}
LAUNCH='import sys; sys.argv=["jobs.py","launch"]; sys.path.insert(0,"app"); import launch, jobs
if __import__("os").environ.get("BEFORE"): launch.ensure_folder_trusted = lambda *a, **k: None
jobs.main()'
(cd "$SRC" && JOBS_VSCODE_DIR="$D" JOBS_VSCODE_PROBE="$L" JOBS_VSCODE_PROBE_SETTLE_MS=8000 uv run python -c "$LAUNCH")
wait_quit "$L"
touch -t "$(date -v-3H +%Y%m%d%H%M)" "$SRC/Today.md"; rm -f "$SRC/.data/start-page"
BEFORE_MTIME=$(stat -f %m "$SRC/Today.md")
JOBS_VSCODE_PROBE="$OUT" JOBS_VSCODE_PROBE_SETTLE_MS=12000 code --user-data-dir "$D/data" --extensions-dir "$D/ext" \
  --shared-data-dir "$D/shared" --new-window "$SRC" 2>&1 | grep -v -e DEP0169 -e trace-dep
wait_quit "$OUT"
python3 - "$D" "$OUT" "$L" "$BEFORE_MTIME" "$(stat -f %m "$SRC/Today.md")" "${BEFORE:+before}" <<'Q'
import json, sqlite3, sys, pathlib
d, out, first = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), json.loads(pathlib.Path(sys.argv[3]).read_text())
def rows(p):
    if not p.exists(): return None
    db = sqlite3.connect(p)
    try: return dict(db.execute("SELECT key, value FROM ItemTable WHERE key IN ('content.trust.model.key', '__$__migratedStorageMarker')").fetchall())
    finally: db.close()
r = json.loads(out.read_text())
r["run"] = sys.argv[6] or "after"
r["launcherWindow"] = {k: first.get(k) for k in ("trusted", "untrustedLine", "active")}
r["trustStore"] = {"shared": rows(d / "shared/sharedStorage/state.vscdb"), "default": rows(d / "data/User/globalStorage/state.vscdb")}
r["todayRefreshed"] = int(sys.argv[5]) > int(sys.argv[4])
out.write_text(json.dumps(r, indent=1) + "\n")
print(json.dumps({k: r.get(k) for k in ("run", "launcherWindow", "trusted", "untrustedLine", "active", "claudeActive", "todayRefreshed", "trustStore")}, indent=1))
Q
