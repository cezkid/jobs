#!/bin/bash
# p: when our extension starts + when the start page is up (plan-ejf.13.1), activationEvents as
# shipped (build a) vs + workspaceContains:app/jobs.py (build b). Scratch builds, same version,
# one scratch VS Code each ($D/a, $D/b): CEZ profile w/ Claude + yaml + pdf + the build, folder =
# Job Finder look-alike (demo Today + today.json + search settings from the checkout after
# `uv run python app/tests/demo.py` + `jobs.py today`, ai = claude, launcher's workspace settings,
# stub app/jobs.py), trust off + marker `.data/start-page` like the cold launcher, Claude's config
# in scratch. Each rep, builds in turn:
#   4-fresh        profile as just installed, never started; no search settings => START HERE
#   3-start-here   started again: START HERE tab restored
#   0-today-first  search settings + Today now exist: Today opened for the first time
#   1-today-active started again: Today restored as the active tab
#   2-today-behind after a start that left Resume details.yml on top: Today restored behind it
# Times = ms from the `code` call: extension host log's first line, our `_doActivateExtension`
# line (+ its event), probe's page shown (openStartPage resolved). Tabs read 4 s later.
# Setup runs once per scratch dir; runs append to $D/runs.jsonl; <out json> = all of them + medians.
# usage: 5-p-activation.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <checkout w/ demo> <out json> [reps=3]
D=$1; SRC=$2; OUT=$(cd "$(dirname "$3")" && pwd)/$(basename "$3"); REPS=${4:-3}
quiet() { grep -v -e DEP0169 -e trace-dep; }
vs() { local S=$1; shift; code --user-data-dir "$S/data" --extensions-dir "$S/ext" --shared-data-dir "$S/shared" "$@" 2>&1 | quiet; }

if [ ! -d "$D/b/data.fresh" ]; then
  mkdir -p "$D/fixture"
  (cd "$SRC" && uv run python - "$D" <<'P'
import json, sys, pathlib
sys.path.insert(0, "app")
import vscode_ext, workspace
d = pathlib.Path(sys.argv[1])
pkg = vscode_ext.manifest()
vscode_ext.build(d / "a", package=pkg)
more = {**pkg, "activationEvents": [*pkg["activationEvents"], "workspaceContains:app/jobs.py"]}
vscode_ext.build(d / "b", package=more)
(d / "fixture/builds.json").write_text(json.dumps({"version": pkg["version"], "a": pkg["activationEvents"], "b": more["activationEvents"]}))
for name, set_up in (("new", False), ("set-up", True)):
    workspace.write("claude", path=d / f"fixture/settings-{name}.json", set_up=set_up, look="auto")
P
  ) || exit 1
  for X in a b; do
    S="$D/$X"; F="$S/folder"
    mkdir -p "$S/data/User/globalStorage" "$S/data/User/profiles/cezjf" "$S/claude"
    python3 - "$F" "$S" <<'P'
import json, sys, pathlib
s = {"userDataProfiles": [{"location": "cezjf", "name": "CEZ Job Finder", "icon": "briefcase"}],
     "profileAssociations": {"workspaces": {pathlib.Path(sys.argv[1]).as_uri(): "cezjf"}}}
(pathlib.Path(sys.argv[2]) / "data/User/globalStorage/storage.json").write_text(json.dumps(s))
P
    vs "$S" --profile "CEZ Job Finder" --install-extension anthropic.claude-code --install-extension redhat.vscode-yaml \
      --install-extension tomoki1207.pdf --install-extension "$S"/*.vsix
    rm -rf "$S/data/logs"
    cp -R "$S/data" "$S/data.fresh"
  done
fi

folder() {  # <build> <new|set-up>: the Job Finder folder before / after setup
  local F="$D/$1/folder"
  mkdir -p "$F/.data" "$F/My Resume" "$F/My Settings" "$F/My Jobs" "$F/.vscode" "$F/app"
  echo "# scratch stub" > "$F/app/jobs.py"; echo claude > "$F/.data/ai"
  cp "$SRC/START HERE.md" "$F/"; cp "$SRC/My Resume/Resume details.yml" "$F/My Resume/"
  cp "$D/fixture/settings-$2.json" "$F/.vscode/settings.json"
  if [ "$2" = set-up ]; then
    cp "$SRC/Today.md" "$F/"; cp "$SRC/.data/today.json" "$F/.data/"; cp "$SRC/My Settings/Search settings.yml" "$F/My Settings/"
  else
    rm -f "$F/Today.md" "$F/.data/today.json" "$F/My Settings/Search settings.yml"
  fi
}

run() {  # <build> <case> <rep> <marker page | ""> [file opened on top instead of the start page => not recorded]
  local S="$D/$1" F="$D/$1/folder" out="$D/$1/probe.json" i t0
  rm -f "$out"
  [ -n "$4" ] && printf '%s\n' "$4" > "$F/.data/start-page"
  t0=$(python3 -c 'import time;print(int(time.time()*1000))')
  CLAUDE_CONFIG_DIR="$S/claude" JOBS_VSCODE_PROBE="$out" JOBS_VSCODE_PROBE_SETTLE_MS="${5:+1500}" JOBS_VSCODE_PROBE_T0="$t0" \
  JOBS_VSCODE_PROBE_OPEN="$5" JOBS_VSCODE_PROBE_OPEN_HOW=open \
    vs "$S" --disable-workspace-trust --new-window "$F"
  for i in $(seq 450); do [ -s "$out" ] && break; sleep 0.2; done
  for i in $(seq 100); do pgrep -f "$S/data" >/dev/null || break; sleep 0.2; done
  if pgrep -f "$S/data" >/dev/null; then echo "$1 $2: still running - killed"; pkill -f "$S/data"; sleep 3; pkill -9 -f "$S/data"; fi
  [ -s "$out" ] || { echo "$1 $2: NO PROBE"; return; }
  [ -n "$5" ] && return
  python3 - "$S" "$out" "$1" "$2" "$3" "$D/runs.jsonl" <<'P'
import json, sys, pathlib, re, datetime
s, out, build, case, rep, runs = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), *sys.argv[3:6], pathlib.Path(sys.argv[6])
r = json.loads(out.read_text()); t0 = r["t0"]
log = sorted(s.glob("data/logs/*/window1/exthost/exthost.log"))[-1].read_text()
ms = lambda stamp: int(datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S.%f").timestamp() * 1000) - t0
m = re.search(r"^(.{23}) .*_doActivateExtension cez-job-finder\.window, startup: (\w+), activationEvent: '([^']+)'", log, re.M)
tabs = [t for g in r["tabs"] for t in g["tabs"]]
count = lambda name: sum(1 for t in tabs if t.get("uri", "").endswith("/" + name))
page = "START%20HERE.md" if case in ("4-fresh", "3-start-here") else "Today.md"
row = {"build": build, "case": case, "rep": int(rep), "event": m.group(3) if m else None, "startup": m.group(2) if m else None,
       "hostMs": ms(log[:23]), "activeMs": ms(m.group(1)) if m else None, "pageMs": r["claudeActive"]["launchToPageMs"],
       "tabs": [t["label"] + ("*" if t["isActive"] else "") for t in tabs],
       "pageTabs": {"Today.md": count("Today.md"), "START HERE.md": count("START%20HERE.md")},
       "onePageTab": count(page) == 1 and any(t["isActive"] and t.get("uri", "").endswith("/" + page) for t in tabs),
       "vscode": r["vscode"], "extensions": r["extensions"]}
with runs.open("a") as f: f.write(json.dumps(row) + "\n")
print(json.dumps({k: row[k] for k in ("build", "case", "rep", "event", "hostMs", "activeMs", "pageMs", "tabs", "onePageTab")}))
P
}

N0=$(grep -c '"case": "4-fresh"' "$D/runs.jsonl" 2>/dev/null); N0=$(( ${N0:-0} / 2 ))
for n in $(seq $((N0 + 1)) $((N0 + REPS))); do
  for X in a b; do
    S="$D/$X"
    rm -rf "$S/data" "$S/shared" "$S/folder"; cp -R "$S/data.fresh" "$S/data"
    folder "$X" new
    run "$X" 4-fresh "$n" "START HERE.md"
    run "$X" 3-start-here "$n" "START HERE.md"
    folder "$X" set-up
    run "$X" 0-today-first "$n" "Today.md"
    run "$X" 1-today-active "$n" "Today.md"
    run "$X" prime "$n" "" "$S/folder/My Resume/Resume details.yml"
    run "$X" 2-today-behind "$n" "Today.md"
  done
done

python3 - "$D" "$OUT" <<'P'
import json, sys, pathlib, statistics, datetime
d, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rows = [json.loads(l) for l in (d / "runs.jsonl").read_text().splitlines()]
builds = json.loads((d / "fixture/builds.json").read_text())
med = lambda xs: int(statistics.median(xs)) if xs else None
summary = []
for case in sorted({r["case"] for r in rows}):
    for b in "ab":
        mine = [r for r in rows if r["case"] == case and r["build"] == b]
        summary.append({"case": case, "build": b, "runs": len(mine), "events": sorted({str(r["event"]) for r in mine}),
                        "hostMs": med([r["hostMs"] for r in mine]), "activeMs": med([r["activeMs"] for r in mine if r["activeMs"] is not None]),
                        "pageMs": med([r["pageMs"] for r in mine if r["pageMs"] is not None]),
                        "pageMsAll": [r["pageMs"] for r in mine], "onePageTab": all(r["onePageTab"] for r in mine)})
report = {"what": "p: our extension's activation + start page shown, ms from the code call (medians); build a = activationEvents as shipped, b = + workspaceContains:app/jobs.py",
          "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "vscode": rows[0]["vscode"],
          "extensions": rows[0]["extensions"], "builds": builds, "summary": summary,
          "runs": [{k: v for k, v in r.items() if k not in ("vscode", "extensions")} for r in rows]}
out.write_text(json.dumps(report, indent=1) + "\n")
for s in summary: print(s["case"], s["build"], s["runs"], s["events"], "host", s["hostMs"], "active", s["activeMs"], "page", s["pageMs"], s["pageMsAll"], "one tab" if s["onePageTab"] else "TAB PROBLEM")
P
