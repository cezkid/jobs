#!/bin/bash
cd "$(dirname "$0")/../.."
# Desktop app starts with the system's bare PATH => uv and VS Code's code need adding
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
# loading splash up before update + launch (both invisible): closes once the start page shows
# (.data/window-ready as new as splash-start), on a click or after 45 s
mkdir -p .data
: > .data/splash-start
osascript -l JavaScript app/install/splash-mac.js "$PWD" >/dev/null 2>&1 &
uv run app/jobs.py update
# no window to read an error in => say it in a dialog; splash closed first (floats over the alert)
uv run app/jobs.py launch || { : > .data/window-ready; osascript -e 'display alert "CEZ Job Finder could not start" message "Run the CEZ Job Finder installer again."'; }
