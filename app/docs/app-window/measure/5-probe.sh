#!/bin/bash
# one self-quitting window: open <folder> (no --profile) in the scratch VS Code w/ the probe on,
# wait for the probe JSON (it quits the window), kill the instance if it hangs.
# usage: [JOBS_VSCODE_PROBE_OPEN=..] 5-probe.sh <scratch dir> <out.json> <folder> [code args..]
D=$1; OUT=$2; F=$3; shift 3
rm -f "$OUT"
JOBS_VSCODE_PROBE="$OUT" code --user-data-dir "$D/data" --extensions-dir "$D/ext" --new-window "$F" "$@" 2>&1 | grep -v -e DEP0169 -e trace-dep
for i in $(seq 90); do [ -s "$OUT" ] && break; sleep 1; done
for i in $(seq 15); do pgrep -f "$D/data" >/dev/null || break; sleep 1; done
if pgrep -f "$D/data" >/dev/null; then echo "still running after probe - killed"; pkill -f "$D/data"; sleep 2; fi
[ -s "$OUT" ] && echo "probe written: $OUT" || echo "NO PROBE (window never activated us)"
