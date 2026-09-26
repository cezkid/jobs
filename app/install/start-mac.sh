#!/bin/bash
cd "$(dirname "$0")/../.."
# Desktop app starts with the system's bare PATH => uv and VS Code's code need adding
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
uv run app/jobs.py update
# no window to read an error in => say it in a dialog
uv run app/jobs.py launch || osascript -e 'display alert "CEZ Job Finder could not start" message "Run the CEZ Job Finder installer again."'
