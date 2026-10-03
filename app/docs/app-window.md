# App window

VS Code window the Desktop icon opens (`app/launch.py`, `app/workspace.py`): look, pages, layout.
Measure in a scratch VS Code only (`JOBS_VSCODE_DIR`, [README](README.md)), never
the owner's own.

## Measured

- Look (`app/window/brand.py`, one token set): `workbench.colorCustomizations` per theme
  (`[Light Modern]`, `[Dark Modern]`) + `window.autoDetectColorScheme` => light by default, dark
  follows the computer; user's own theme elsewhere untouched. Highlighter only on marks (selected
  row, badge, say chip), always under ink. Contrast >= 4.5:1 per pair, tested.
- Pages: `markdown.styles: ["app/window/pages.css"]` - relative path joined to the first workspace
  folder (1.140 bundle read). Content sits in `.markdown-body`; body carries `vscode-light` /
  `vscode-dark` / `vscode-high-contrast`. Caladea via relative `url()` from `app/resume/fonts`
  loads (preview CSP font-src = webview source); seen live, scratch window, 2026-10-03.
- Scratch dir path must stay short: VS Code's IPC socket `<data>/1.14-main.sock` over 103 chars
  => window never opens, launch still exits 0. Use `mktemp -d /tmp/jfv.XXXX`.

## Phase 1 - what + why

Still stock VS Code, on the user's own install + subscriptions; only settings + page text change.

- Brand look: `workbench.colorCustomizations` per stock theme (`app/window/brand.py`), written to
  the workspace => only this folder's window changes, their own theme elsewhere untouched.
- Pages: `app/window/pages.css` (`markdown.styles`) - Caladea, 68ch measure, list items as cards.
  Reads as one program's pages, not a code editor's Markdown preview. No remote loads.
- Today: "Open the posting" + "Open its resume" link text, never a bare 100-char URL;
  words to say as highlighter chips (code spans) - user reads + types them, nothing clicks into
  the chat. "What you can say" list at the end, same chips.
- START HERE leaves the file list once search settings exist (`files.exclude`, written at
  launch => gone from next launch, plan-ejf.1.18 for right after setup). First-run steps only.
- Documents, not code: `[yaml]` + `[markdown]` w/o line numbers, folding, guides, lightbulbs,
  minimap; terminal hidden on startup (Copilot's agent runs steps there). YAML schema underline
  + hover kept: a mistyped resume fact shows at once, not hours later at render.
- `jobs.py open`: `code <folder> <file>` like the launcher, no `-r` => opens in the Job Finder
  window, not the last-used one.
- Employer text inert (`text.inert_md`): posting, Check before sending, Application answers,
  Follow-up, Today - no links, images or HTML from the employer. A hidden image can't tell them
  when the user looked; a link can't run a VS Code command. Our own posting link line kept.
- App-wide quiet keys (release notes, experiments, telemetry, walkthroughs; Windows: compact menu
  bar) in VS Code's user settings - only on a VS Code Job Finder installed (`.data/vscode-ours`,
  installers write it only when they download VS Code), or a settings file holding only Job
  Finder's own keys (installs before the marker). A developer's own VS Code stays byte for byte.

## Rejected

- Own Electron / Tauri shell: Claude, ChatGPT + Copilot chats exist only as VS Code extensions
  on the user's subscriptions - no shell can host them.
- `--user-data-dir` instance: every extension reinstalled, GitHub sign-in lost on Mac, every
  `code` call + sign-in callback must carry the flags, Dock still says "Code".
- VS Code Agents window (1.132): its extension allowlist excludes `anthropic.claude-code` +
  `openai.chatgpt`.
- Status bar hidden: Claude's item lives there.
- `workbench.editor.showTabs: none`: Claude's + ChatGPT's editor-title buttons go w/ the tabs.
- Zen mode: hides the chat.
- Activity bar hidden: ChatGPT's icon, Claude's sessions, + the only way back to the file list
  (resume drag onto My Resume).
- Problems / decorations off: loses the YAML red underline on a mistyped resume fact.
- `vscode://anthropic.claude-code/open` from a page: opens the chat as a tab over the page.
- `vscode://` handler for Today buttons: reachable from any web page or posting, not just ours.
