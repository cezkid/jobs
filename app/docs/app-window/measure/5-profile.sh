#!/bin/bash
# one more cold profile in the scratch VS Code, associated w/ <folder>, its settings.json = <json>,
# same 4 extensions; VS Code must not be running there (storage.json written by hand).
# usage: 5-profile.sh <scratch dir> <location> <folder> '<settings json>' <vsix>
D=$1; LOC=$2; F=$3; SET=$4; VSIX=$5
mkdir -p "$D/data/User/profiles/$LOC" "$F"; cp "$D/folder/Today.md" "$F/"
echo "$SET" > "$D/data/User/profiles/$LOC/settings.json"
python3 - "$D" "$LOC" "$F" <<'P'
import json, sys, pathlib
d, loc, f = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
p = d / "data/User/globalStorage/storage.json"; s = json.loads(p.read_text())
s["userDataProfiles"].append({"location": loc, "name": loc})
s["profileAssociations"]["workspaces"][f.as_uri()] = loc
p.write_text(json.dumps(s))
P
code --user-data-dir "$D/data" --extensions-dir "$D/ext" --profile "$LOC" \
  --install-extension anthropic.claude-code --install-extension redhat.vscode-yaml \
  --install-extension tomoki1207.pdf --install-extension "$VSIX" 2>&1 | grep -c "successfully installed"
