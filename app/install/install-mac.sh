#!/bin/bash
# Paste-line install (docs/index.html): curl -fsSL <raw url of this file> | bash
# One line for everyone: AI asked below, not on the page (JOBS_AI or an argument skips it:
# 1|claude, 2|chatgpt, 3|copilot).
# Per-user installs only => no admin prompt, no Apple developer tools.
set -euo pipefail
ZIP_URL=https://github.com/cezkid/jobs/archive/refs/heads/main.zip
DIR="${JOBS_DIR:-$HOME/jobs}"
BIN="$HOME/.local/bin"
export PATH="$BIN:$PATH"
STEP_COUNT=5
VSCODE_APP="/Applications/Visual Studio Code.app"
[ -d "$VSCODE_APP" ] || VSCODE_APP="$HOME/Applications/Visual Studio Code.app"

step() { printf '\n\033[1mStep %s of %s: %s\033[0m\n' "$1" "$STEP_COUNT" "$2"; }
fail() {
  printf '\n\033[31mInstall stopped: %s\033[0m\n' "$1"
  echo "Run the same steps again. If it fails twice, send a photo of this window to whoever shared CEZ Job Finder with you."
  exit 1
}
have() { command -v "$1" >/dev/null 2>&1; }
# 1|claude 2|chatgpt 3|copilot, any case => the word; anything else => nothing (asked again)
ai_word() {
  case "$(tr '[:upper:]' '[:lower:]' <<<"$1" | tr -d ' \r')" in
    1|claude) echo claude ;;
    2|chatgpt) echo chatgpt ;;
    3|copilot) echo copilot ;;
  esac
}
# asked first, while the user is still at the window; stdin is the piped script => ask on /dev/tty
# Copilot never guessed from extensions: its chat is built into VS Code for everyone
pick_ai() {
  local word
  word=$(ai_word "${1:-${JOBS_AI:-}}")
  if [ -z "$word" ] && [ -f "$DIR/.data/ai" ]; then word=$(ai_word "$(cat "$DIR/.data/ai")"); fi
  if [ -z "$word" ] && have code; then  # re-run to repair => keep the AI already set up, no question
    local have_ext
    # default profile + Job Finder's own (absent before its first setup: "not found", exit 1)
    have_ext=$({ code --list-extensions; code --list-extensions --profile "CEZ Job Finder"; } 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)
    if grep -qx anthropic.claude-code <<<"$have_ext"; then word=claude
    elif grep -qx openai.chatgpt <<<"$have_ext"; then word=chatgpt; fi
  fi
  if [ -n "$word" ]; then echo "$word"; return; fi
  if ! { : >/dev/tty; } 2>/dev/null; then
    printf '\n\033[31mInstall stopped: could not ask which AI you use.\033[0m\n' >&2
    echo "Open the Terminal app, paste the install line there and press Return." >&2
    return 1
  fi
  printf '\n\033[1mWhich AI do you use?\033[0m\n  1 = Claude (Pro or Max)\n  2 = ChatGPT (Plus or Pro)\n  3 = GitHub Copilot Pro ($10 a month)\n' >/dev/tty
  local answer
  while true; do
    printf 'Type 1, 2 or 3, then press Return (this accepts the terms above): ' >/dev/tty
    if ! read -r answer </dev/tty; then
      printf '\n\033[31mInstall stopped: no answer to which AI you use.\033[0m\n' >&2
      echo "Open the Terminal app, paste the install line there and press Return." >&2
      return 1
    fi
    word=$(ai_word "$answer")
    if [ -n "$word" ]; then echo "$word"; return; fi
  done
}

printf '\n\033[1mInstalling CEZ Job Finder. This takes about 5 minutes - keep this window open.\033[0m\n'
echo 'Free and open source, provided as is, with no warranty. Installing means you accept the terms: https://jobs.enrriquez.com/terms.html'
ai=$(pick_ai "${1:-}") || exit 1
# explicit per AI; copilot => none (Copilot Chat built into VS Code 1.140)
# sign_in = what to do in the window, said once the install ends (nothing here waits for a key)
case "$ai" in
  claude) ai_extension=anthropic.claude-code
    sign_in="In the chat on the right, click Sign in and use your Claude Pro or Max account." ;;
  chatgpt) ai_extension=openai.chatgpt
    sign_in="In the chat on the right, click Sign in and use your ChatGPT Plus or Pro account." ;;
  copilot) ai_extension=
    sign_in="In the chat on the right, click Sign in, then pick Claude Sonnet in the model list under the chat box. No GitHub account? Make one with your Google or Apple account." ;;
esac

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
    # VS Code is ours => launcher may quiet its app-wide settings (never a developer's own)
    mkdir -p "$DIR/.data" && : >"$DIR/.data/vscode-ours"
  fi
  mkdir -p "$BIN"
  ln -sf "$VSCODE_APP/Contents/Resources/app/bin/code" "$BIN/code"
fi
have code || fail "could not install VS Code."

step 3 "downloading CEZ Job Finder to $DIR..."
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
echo "$ai" >"$DIR/.data/ai"  # private, kept by updates; launcher + `jobs.py ai` read it

step 4 "getting CEZ Job Finder ready..."
(cd "$DIR" && uv sync --quiet) || fail "could not get CEZ Job Finder ready."

step 5 "adding the AI panel to VS Code..."
# Job Finder's own VS Code profile + AI panel, PDF viewer, typo checker, its window (plain lines);
# VS Code open => default profile. Fails => AI panel the plain way, as before the profile
if ! (cd "$DIR" && uv run app/jobs.py window-setup); then
  if [ -n "$ai_extension" ]; then
    code --install-extension "$ai_extension" --force >/dev/null 2>&1 || fail "could not add the AI panel to VS Code."
  fi
fi

bash "$DIR/app/install/make-icon-mac.sh" || true
# Desktop folder needs the Mac's OK for Terminal: "Don't Allow" => no icon, so never promise one
if [ -d "$HOME/Desktop/CEZ Job Finder.app" ]; then
  next_time='Next time, double-click "CEZ Job Finder" on your Desktop.'
else
  next_time="Your Mac didn't let the installer put an icon on your Desktop. To open CEZ Job Finder next time, paste the same line in Terminal again - your files are kept."
fi

# "Done" only once the window is on its way: closing this window earlier stopped the start
printf '\n\033[1mOpening CEZ Job Finder - keep this window open until it appears.\033[0m\n'
[ -n "${JOBS_NO_LAUNCH:-}" ] || bash "$DIR/app/install/start-mac.sh" || true
printf '\n\033[1mAll set. You can close this window.\033[0m\n'
echo "In the CEZ Job Finder window:"
echo "  1. $sign_in"
echo "  2. Fill in its first page, then click the yellow button at the bottom to put your answers in the chat."
echo "$next_time"
