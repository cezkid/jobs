#!/bin/bash
# Paste-line install (docs/index.html): curl -fsSL <raw url of this file> | bash
# One line for everyone: AI asked below, not on the page (JOBS_AI 1 Claude / 2 ChatGPT skips it).
# Per-user installs only => no admin prompt, no Apple developer tools.
set -euo pipefail
ZIP_URL=https://github.com/cezkid/jobs/archive/refs/heads/main.zip
DIR="${JOBS_DIR:-$HOME/jobs}"
BIN="$HOME/.local/bin"
export PATH="$BIN:$PATH"
STEP_COUNT=5
VSCODE_APP="/Applications/Visual Studio Code.app"
[ -d "$VSCODE_APP" ] || VSCODE_APP="$HOME/Applications/Visual Studio Code.app"

step() { printf '\n\033[36mStep %s of %s: %s\033[0m\n' "$1" "$STEP_COUNT" "$2"; }
fail() {
  printf '\n\033[31mInstall stopped: %s\033[0m\n' "$1"
  echo "Run the same steps again. If it fails twice, send a photo of this window to whoever shared CEZ Job Finder with you."
  exit 1
}
have() { command -v "$1" >/dev/null 2>&1; }
# asked first, while the user is still at the window; stdin is the piped script => ask on /dev/tty
pick_ai() {
  if [ -n "${JOBS_AI:-}" ]; then echo "$JOBS_AI"; return; fi
  if have code; then  # re-run to repair => keep the AI already set up, no question
    local have_ext
    have_ext=$(code --list-extensions 2>/dev/null || true)
    if grep -qx anthropic.claude-code <<<"$have_ext"; then echo 1; return; fi
    if grep -qx openai.chatgpt <<<"$have_ext"; then echo 2; return; fi
  fi
  printf '\n\033[36mWhich AI do you pay for?\033[0m\n  1 = Claude\n  2 = ChatGPT\n' >/dev/tty
  local answer
  while true; do
    printf 'Type 1 or 2, then press Enter: ' >/dev/tty
    read -r answer </dev/tty || { echo 1; return; }
    case "$(tr '[:upper:]' '[:lower:]' <<<"$answer" | tr -d ' ')" in
      1|claude) echo 1; return ;;
      2|chatgpt) echo 2; return ;;
    esac
  done
}

printf '\n\033[36mInstalling CEZ Job Finder. This takes about 5 minutes - keep this window open.\033[0m\n'
if [ "$(pick_ai)" = 2 ]; then ai_extension=openai.chatgpt; else ai_extension=anthropic.claude-code; fi

step 1 "installing uv (runs CEZ Job Finder)..."
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

step 4 "downloading CEZ Job Finder to $DIR..."
# My folders + .data never in zip => replacing every top-level entry keeps them
staging="$DIR/.data/install"
rm -rf "$staging"
mkdir -p "$staging"
curl -fsSL -o "$staging/jobs.zip" "$ZIP_URL" || fail "could not download CEZ Job Finder."
unzip -q "$staging/jobs.zip" -d "$staging"
for entry in "$staging"/jobs-main/* "$staging"/jobs-main/.[!.]*; do
  [ -e "$entry" ] || continue
  rm -rf "$DIR/$(basename "$entry")"
  mv "$entry" "$DIR/"
done
rm -rf "$staging"

step 5 "getting CEZ Job Finder ready..."
(cd "$DIR" && uv sync --quiet) || fail "could not get CEZ Job Finder ready."

launcher="$HOME/Desktop/CEZ Job Finder.command"
printf '#!/bin/bash\nexec bash "%s/app/install/start-mac.sh"\n' "$DIR" > "$launcher"
chmod +x "$launcher"

printf '\n\033[32mDone. Next time, double-click "CEZ Job Finder" on your Desktop.\033[0m\n'
printf '\033[32mVS Code opens now. Click Sign in on the right-hand panel, then press Enter.\033[0m\n'
[ -n "${JOBS_NO_LAUNCH:-}" ] || exec bash "$DIR/app/install/start-mac.sh"
