#!/bin/bash
# l: look switch (plan-ejf.1.25). Scratch CEZ profile w/ our vsix, Job Finder folder = copy of the
# program (app/, pyproject, uv.lock) + demo Today, look auto at start; trust off like the launcher.
# Probe runs the switch's own path (`switchLook` -> `uv run app/jobs.py look WORD`) after settle,
# reads the theme before + after, w/o any window reload.
# usage: 5-l-look.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <vsix> <checkout w/ demo> <out json> <word>
D=$1; VSIX=$2; SRC=$3; OUT=$4; WORD=${5:-dark}
F="$D/folder"
mkdir -p "$D/data/User/globalStorage" "$D/data/User/profiles/cezjf" "$F/.data" "$F/My Settings"
rsync -a --exclude __pycache__ --exclude tests "$SRC/app" "$F/"; cp "$SRC/pyproject.toml" "$SRC/uv.lock" "$F/"
cp "$SRC/Today.md" "$F/"; cp "$SRC/.data/today.json" "$F/.data/"; cp "$SRC/My Settings/Search settings.yml" "$F/My Settings/"
echo claude > "$F/.data/ai"
(cd "$F" && uv run app/jobs.py look auto)   # window settings as the launcher writes them; venv made before the window
python3 - "$D" <<'P'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
s = {"userDataProfiles": [{"location": "cezjf", "name": "CEZ Job Finder", "icon": "briefcase"}],
     "profileAssociations": {"workspaces": {(d / "folder").as_uri(): "cezjf"}}}
(d / "data/User/globalStorage/storage.json").write_text(json.dumps(s))
P
code --user-data-dir "$D/data" --extensions-dir "$D/ext" --profile "CEZ Job Finder" --install-extension "$VSIX" 2>&1 | grep -v -e DEP0169 -e trace-dep
rm -f "$OUT"
JOBS_VSCODE_PROBE="$OUT" JOBS_VSCODE_PROBE_LOOK="$WORD" JOBS_VSCODE_PROBE_SETTLE_MS=4000 \
  code --user-data-dir "$D/data" --extensions-dir "$D/ext" --disable-workspace-trust --new-window "$F" 2>&1 | grep -v -e DEP0169 -e trace-dep
for i in $(seq 90); do [ -s "$OUT" ] && break; sleep 1; done
for i in $(seq 15); do pgrep -f "$D/data" >/dev/null || break; sleep 1; done
if pgrep -f "$D/data" >/dev/null; then echo "still running - killed"; pkill -f "$D/data"; sleep 2; fi
[ -s "$OUT" ] || { echo "NO PROBE"; exit 1; }
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps({"theme": r["theme"], "look": {k: r["look"][k] for k in ("word","before","after","messages","changes")}}, indent=1))' "$OUT"
