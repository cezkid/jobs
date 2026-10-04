#!/bin/bash
# scratch VS Code for window probes: cold CEZ profile associated w/ $D/folder (plan-ejf.1.8 #1),
# Claude + yaml + pdf + our vsix installed into it only; demo Today.md copied in.
# usage: 5-setup.sh <scratch dir from mktemp -d /tmp/jfv.XXXX> <vsix> <Today.md>
D=$1; VSIX=$2; TODAY=$3
mkdir -p "$D/data/User/globalStorage" "$D/data/User/profiles/cezjf" "$D/folder/other" "$D/elsewhere"
cp "$TODAY" "$D/folder/Today.md"; cp "$TODAY" "$D/folder/other/Today.md"; cp "$TODAY" "$D/elsewhere/Today.md"
python3 - "$D" <<'P'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
s = {"userDataProfiles": [{"location": "cezjf", "name": "CEZ Job Finder", "icon": "briefcase"}],
     "profileAssociations": {"workspaces": {(d / "folder").as_uri(): "cezjf"}}}
(d / "data/User/globalStorage/storage.json").write_text(json.dumps(s))
P
code --user-data-dir "$D/data" --extensions-dir "$D/ext" --profile "CEZ Job Finder" \
  --install-extension anthropic.claude-code --install-extension redhat.vscode-yaml \
  --install-extension tomoki1207.pdf --install-extension "$VSIX" 2>&1 | grep -v -e DEP0169 -e trace-dep
echo "## profile"; code --user-data-dir "$D/data" --extensions-dir "$D/ext" --profile "CEZ Job Finder" --list-extensions --show-versions 2>&1 | grep -v -e DEP0169 -e trace-dep
echo "## default"; code --user-data-dir "$D/data" --extensions-dir "$D/ext" --list-extensions 2>&1 | grep -v -e DEP0169 -e trace-dep; echo "(end)"
