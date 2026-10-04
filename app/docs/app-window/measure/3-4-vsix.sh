#!/bin/bash
D=$1; SP=$2; cd $D
C() { code --user-data-dir $D/data --extensions-dir $D/ext "$@"; }
t0() { python3 -c 'import time;print(time.time())'; }
dt() { python3 -c "import time;print(round(time.time()-$1,1))"; }
P="CEZ Job Finder"
meta() { python3 - "$D" <<'P'
import json,sys
for e in json.load(open(sys.argv[1]+"/data/User/profiles/cezjf/extensions.json")):
    if e["identifier"]["id"].startswith("cez-job-finder"): print(json.dumps({k:e[k] for k in ("identifier","version","relativeLocation","metadata")}, indent=1))
P
}
body() { cat ext/cez-job-finder.window-$1/extension.js | head -1; }
echo "# 3-4: local vsix into profile, VS Code $(code --version|head -1), $(date -u +%FT%TZ)"
python3 $SP/mkvsix.py a.vsix 0.0.1 content-A; python3 $SP/mkvsix.py b.vsix 0.0.1 content-B; python3 $SP/mkvsix.py c.vsix 0.0.2 content-C
echo "## install a.vsix (0.0.1, A)"; s=$(t0); C --profile "$P" --install-extension $D/a.vsix 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "exit=${PIPESTATUS[0]} secs=$(dt $s)"; meta; body 0.0.1
echo "## list profile"; C --profile "$P" --list-extensions --show-versions 2>&1
echo "## list default"; C --list-extensions 2>&1
echo "## reinstall b.vsix (same 0.0.1, content B) no --force"; C --profile "$P" --install-extension $D/b.vsix 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "exit=${PIPESTATUS[0]}"; body 0.0.1
echo "## reinstall b.vsix --force"; C --profile "$P" --install-extension $D/b.vsix --force 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "exit=${PIPESTATUS[0]}"; body 0.0.1; meta
echo "## install c.vsix (0.0.2) no --force"; C --profile "$P" --install-extension $D/c.vsix 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "exit=${PIPESTATUS[0]}"; meta; ls ext | grep cez; body 0.0.2
echo "## downgrade a.vsix (0.0.1) no --force"; C --profile "$P" --install-extension $D/a.vsix 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "exit=${PIPESTATUS[0]}"; C --profile "$P" --list-extensions --show-versions 2>&1 | grep cez
echo "## ext/extensions.json (shared) cez entries"; python3 -c "import json;print([ (e['identifier']['id'],e['version']) for e in json.load(open('ext/extensions.json'))])"
echo "## gallery lookup of the id"; C --install-extension cez-job-finder.window 2>&1 | grep -v -e DEP0169 -e trace-dep
