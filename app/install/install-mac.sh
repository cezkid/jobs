#!/bin/bash
# Paste-line install (docs/index.html): curl -fsSL <raw url of this file> | JOBS_AI=1 bash
# Per-user installs only => no admin prompt, no Apple developer tools. JOBS_AI 2 = ChatGPT, else Claude.
set -euo pipefail
ZIP_URL=https://github.com/cezkid/jobs/archive/refs/heads/main.zip
DIR="${JOBS_DIR:-$HOME/jobs}"
BIN="$HOME/.local/bin"
export PATH="$BIN:$PATH"
STEP_COUNT=5
if [ "${JOBS_AI:-}" = 2 ]; then ai_extension=openai.chatgpt; else ai_extension=anthropic.claude-code; fi
VSCODE_APP="/Applications/Visual Studio Code.app"
[ -d "$VSCODE_APP" ] || VSCODE_APP="$HOME/Applications/Visual Studio Code.app"

step() { printf '\n\033[36mStep %s of %s: %s\033[0m\n' "$1" "$STEP_COUNT" "$2"; }
fail() {
  printf '\n\033[31mInstall stopped: %s\033[0m\n' "$1"
  echo "Run the same steps again. If it fails twice, send a photo of this window to whoever shared Job Finder with you."
  exit 1
}
have() { command -v "$1" >/dev/null 2>&1; }

printf '\n\033[36mInstalling Job Finder. This takes about 5 minutes - keep this window open.\033[0m\n'

step 1 "installing uv (runs Job Finder)..."
have uv || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null || fail "could not install uv."
have uv || fail "could not install uv."

step 2 "installing VS Code..."
if ! have code; then
  if [ ! -d "$VSCODE_APP" ]; then
    tmp=$(mktemp -d)
    curl -fsSL -o "$tmp/vscode.zip" https://update.code.visualstudio.com/latest/darwin-universal/stable || fail "could not download VS Code."
    mkdir -p "$HOME/Applications"
    unzip -q "$tmp/vscode.zip" -d "$HOME/Applications"
    VSCODE_APP="$HOME/Applications/Visual Studio Code.app"
  fi
  mkdir -p "$BIN"
  ln -sf "$VSCODE_APP/Contents/Resources/app/bin/code" "$BIN/code"
fi
have code || fail "could not install VS Code."

step 3 "adding the AI panel to VS Code..."
code --install-extension "$ai_extension" --force >/dev/null 2>&1 || fail "could not add the AI panel to VS Code."

step 4 "downloading Job Finder to $DIR..."
# My folders + .data never in zip => replacing every top-level entry keeps them
staging="$DIR/.data/install"
rm -rf "$staging"
mkdir -p "$staging"
curl -fsSL -o "$staging/jobs.zip" "$ZIP_URL" || fail "could not download Job Finder."
unzip -q "$staging/jobs.zip" -d "$staging"
for entry in "$staging"/jobs-main/* "$staging"/jobs-main/.[!.]*; do
  [ -e "$entry" ] || continue
  rm -rf "$DIR/$(basename "$entry")"
  mv "$entry" "$DIR/"
done
rm -rf "$staging"

step 5 "getting Job Finder ready..."
(cd "$DIR" && uv sync --quiet) || fail "could not get Job Finder ready."

launcher="$HOME/Desktop/Job Finder.command"
printf '#!/bin/bash\nexec bash "%s/app/install/start-mac.sh"\n' "$DIR" > "$launcher"
chmod +x "$launcher"

printf '\n\033[32mDone. Next time, double-click "Job Finder" on your Desktop.\033[0m\n'
printf '\033[32mVS Code opens now. Click Sign in on the right-hand panel, then press Enter.\033[0m\n'
[ -n "${JOBS_NO_LAUNCH:-}" ] || exec bash "$DIR/app/install/start-mac.sh"
