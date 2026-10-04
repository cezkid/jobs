#!/bin/bash
D=$1; cd $D
C() { code --user-data-dir $D/data --extensions-dir $D/ext "$@"; }
t0() { python3 -c 'import time;print(time.time())'; }
dt() { python3 -c "import time;print(round(time.time()-$1,1))"; }
echo "# 1: cold profile create = storage.json write (no prior run), VS Code $(code --version|head -1), $(date -u +%FT%TZ)"
cat data/User/globalStorage/storage.json
for x in tomoki1207.pdf redhat.vscode-yaml anthropic.claude-code; do echo "## install $x into profile (not in shared dir)"; s=$(t0); C --profile "CEZ Job Finder" --install-extension $x 2>&1; echo "exit=$? secs=$(dt $s)"; done
echo "## list profile"; C --profile "CEZ Job Finder" --list-extensions --show-versions 2>&1
echo "## list default"; C --list-extensions 2>&1; echo "(end default)"
echo "## missing profile"; C --profile "Nope" --install-extension tomoki1207.pdf 2>&1; echo "exit=$?"
echo "## install tomoki1207.pdf into DEFAULT (already in shared dir)"; s=$(t0); C --install-extension tomoki1207.pdf 2>&1; echo "exit=$? secs=$(dt $s)"
echo "## list default"; C --list-extensions 2>&1
echo "## ext dir"; ls ext
echo "## profile extensions.json"; python3 -m json.tool data/User/profiles/cezjf/extensions.json
echo "## storage.json after"; cat data/User/globalStorage/storage.json; echo
echo "## code.lock"; ls data/code.lock 2>&1
