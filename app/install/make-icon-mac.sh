#!/bin/bash
# Desktop icon = small app, not a .command => no Terminal window left open once VS Code is up
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
app="$HOME/Desktop/CEZ Job Finder.app"
rm -rf "${app:?}"
osacompile -o "$app" -e "set d to \"$DIR\"" \
  -e 'do shell script "bash " & quoted form of (d & "/app/install/start-mac.sh") & " >/dev/null 2>&1 &"'
rm -f "$HOME/Desktop/CEZ Job Finder.command"  # icon from installs before the app
