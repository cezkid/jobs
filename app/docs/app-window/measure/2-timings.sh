#!/bin/bash
D=$1; cd $D
C() { code --user-data-dir $D/data --extensions-dir $D/ext "$@" 2>&1 | grep -v -e DEP0169 -e trace-dep; }
t0() { python3 -c 'import time;print(time.time())'; }
dt() { python3 -c "import time;print(round(time.time()-$1,1))"; }
echo "# 2: timings, VS Code $(code --version|head -1), $(date -u +%FT%TZ)"
s=$(t0); python3 - $D <<'P'
import json,os,sys
p=sys.argv[1]+"/data/User/globalStorage/storage.json"; s=json.load(open(p))
s["userDataProfiles"].append({"location":"second","name":"Second"}); os.makedirs(sys.argv[1]+"/data/User/profiles/second",exist_ok=True)
json.dump(s,open(p,"w"))
P
echo "## cold profile create (storage.json write + folder) secs=$(dt $s)"
for x in anthropic.claude-code tomoki1207.pdf; do echo "## install $x into Second (already in shared dir)"; s=$(t0); C --profile Second --install-extension $x; echo "secs=$(dt $s)"; done
echo "## same again (already in this profile)"; s=$(t0); C --profile Second --install-extension anthropic.claude-code; echo "secs=$(dt $s)"
ls ext
