#!/bin/bash
# k: Claude warm-up (plan-ejf.1.21). Scratch CEZ profile w/ Claude + our vsix, Job Finder folder
# (demo Today + today.json + search settings, ai = claude, workspace settings), trust off like the
# launcher, Claude's own config in scratch (CLAUDE_CONFIG_DIR: not signed in, owner's untouched).
# Each run cold + fresh window state (workspaceStorage cleared => first-window defaults apply):
# window start -> Claude active -> Today button's own path, per warm mode; Claude's log read after.
# usage: 5-k-warm.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <vsix> <checkout w/ demo> <out dir> <visible|hidden>
D=$1; VSIX=$2; SRC=$3; OUT=$4; SIDEBAR=$5
F="$D/folder"
mkdir -p "$D/data/User/globalStorage" "$D/data/User/profiles/cezjf" "$F/.data" "$F/My Resume" "$F/My Settings" "$F/.vscode" "$D/claude" "$OUT"
cp "$SRC/Today.md" "$F/"; cp "$SRC/.data/today.json" "$F/.data/"; cp "$SRC/My Settings/Search settings.yml" "$F/My Settings/"
sed "s/\"workbench.secondarySideBar.defaultVisibility\": \"visible\"/\"workbench.secondarySideBar.defaultVisibility\": \"$SIDEBAR\"/" \
  "$SRC/.vscode/settings.json" > "$F/.vscode/settings.json"
echo claude > "$F/.data/ai"
python3 - "$D" <<'P'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
s = {"userDataProfiles": [{"location": "cezjf", "name": "CEZ Job Finder", "icon": "briefcase"}],
     "profileAssociations": {"workspaces": {(d / "folder").as_uri(): "cezjf"}}}
(d / "data/User/globalStorage/storage.json").write_text(json.dumps(s))
P
code --user-data-dir "$D/data" --extensions-dir "$D/ext" --profile "CEZ Job Finder" \
  --install-extension anthropic.claude-code --install-extension "$VSIX" 2>&1 | grep -v -e DEP0169 -e trace-dep
run() {  # <name> <warm: off|activate|view|plan> <settle ms>
  local out="$OUT/$1.json" i; rm -f "$out"
  rm -rf "$D/data/User/workspaceStorage" "$D/data/User/profiles/cezjf/workspaceStorage"
  CLAUDE_CONFIG_DIR="$D/claude" JOBS_VSCODE_PROBE="$out" JOBS_VSCODE_PROBE_WARM="$2" JOBS_VSCODE_PROBE_SETTLE_MS="$3" \
  JOBS_VSCODE_PROBE_SAY="apply to job 1" JOBS_VSCODE_PROBE_T0="$(python3 -c 'import time;print(int(time.time()*1000))')" \
    code --user-data-dir "$D/data" --extensions-dir "$D/ext" --disable-workspace-trust --new-window "$F" 2>&1 | grep -v -e DEP0169 -e trace-dep
  for i in $(seq 90); do [ -s "$out" ] && break; sleep 1; done
  for i in $(seq 15); do pgrep -f "$D/data" >/dev/null || break; sleep 1; done
  if pgrep -f "$D/data" >/dev/null; then echo "$1: still running - killed"; pkill -f "$D/data"; sleep 2; fi
  [ -s "$out" ] || { echo "$1: NO PROBE"; return; }
  # Claude's own log of this run: activation event + when its chat view loaded + each chat launched
  python3 - "$out" "$(ls -d "$D"/data/logs/* | tail -1)" <<'P'
import json, sys, pathlib, re, datetime
out, logs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
r = json.loads(out.read_text()); t0 = r.get("t0")
ms = lambda line: int(datetime.datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S.%f").timestamp() * 1000)
ext = (logs / "window1/exthost/exthost.log").read_text()
m = re.search(r"^(.{23}) .*_doActivateExtension Anthropic\.claude-code, startup: \w+, activationEvent: '([^']+)'", ext, re.M)
log = logs / "window1/exthost/Anthropic.claude-code/Claude VSCode.log"
lines = log.read_text().splitlines() if log.exists() else []
seen = {"activationEvent": m.group(2) if m else None, "launchToActiveMs": ms(m.group(1)) - t0 if m else None,
        "launchToViewInitMs": [ms(l) - t0 for l in lines if '"type":"init"' in l],
        "launchToChatLaunchMs": [ms(l) - t0 for l in lines if "Launching Claude on channel" in l]}
press = r.get("say", {}).get("pressedLaunchMs")
after = [x for x in seen["launchToChatLaunchMs"] if press is not None and x >= press]
seen["pressToNewChatLaunchMs"] = after[0] - press if after else None
r["claudeLog"] = seen
out.write_text(json.dumps(r, indent=1) + "\n")
print(out.stem, json.dumps({"active": seen["launchToActiveMs"], "event": seen["activationEvent"], "view": seen["launchToViewInitMs"],
      "page": r["claudeActive"].get("launchToPageMs"), "press": press, "toChat": seen["pressToNewChatLaunchMs"],
      "tabs": [t["label"] + ("*" if t["isActive"] else "") for g in r["say"]["tabsAfter"] for t in g["tabs"]]}))
P
}
run "k-$SIDEBAR-0-first-${FIRST:-off}" "${FIRST:-off}" 6000   # first start of a fresh profile: own row
for n in 1 2; do
  run "k-$SIDEBAR-$n-off" off 3000
  run "k-$SIDEBAR-$n-activate" activate 3000
  run "k-$SIDEBAR-$n-view" view 3000
done
