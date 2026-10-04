# App window

VS Code window the Desktop icon opens (`app/launch.py`, `app/workspace.py`): look, pages, layout.
Measure in a scratch VS Code only (`JOBS_VSCODE_DIR`, [README](README.md)), never
the owner's own.

## Measured

- Look (`app/window/brand.py`, one token set): `workbench.colorCustomizations` per theme
  (`[Light Modern]`, `[Dark Modern]`) + `window.autoDetectColorScheme` => light by default, dark
  follows the computer; user's own theme elsewhere untouched. Yellow background = something a click
  does (buttons), always under ink; owner 2026-10-03: yellow words that
  don't click read as broken buttons. Selected rows, badges, text selection = quiet grey. Contrast
  >= 4.5:1 per pair, tested.
- Pages: `markdown.styles: ["app/window/pages.css"]` - relative path joined to the first workspace
  folder (1.140 bundle read). Content sits in `.markdown-body`; body carries `vscode-light` /
  `vscode-dark` / `vscode-high-contrast`. Caladea via relative `url()` from `app/resume/fonts`
  loads (preview CSP font-src = webview source); seen live, scratch window, 2026-10-03.
- Scratch dir path must stay short: VS Code's IPC socket `<data>/1.14-main.sock` over 103 chars
  => window never opens, launch still exits 0. Use `mktemp -d /tmp/jfv.XXXX`.

### Profile + local extension (phase 2 groundwork)

VS Code 1.140.0 darwin-x64, 2026-10-03, scratch `--user-data-dir` + `--extensions-dir`, CLI only,
no window, Code never running there (no `code.lock`). Raw outputs + scripts:
[app-window/measure/](app-window/measure/).

| # | What | Method | Result |
|---|---|---|---|
| 1 | Cold profile create + 3 installs | Fresh data dir: write `User/globalStorage/storage.json` (`userDataProfiles [{location, name, icon}]` + `profileAssociations.workspaces {"<folder uri>": "<location>"}`) + make `User/profiles/<location>/`; then `--profile "CEZ Job Finder" --install-extension` pdf, yaml, claude-code | All 3 install, exit 0. `--list-extensions --profile` = exactly those 3; default profile list empty. Files once in the shared extensions dir, profile's list in `User/profiles/<location>/extensions.json`. `storage.json` untouched by CLI. Unknown profile: `Profile 'Nope' not found.` exit 1. `location` = path relative to `User/profiles`, id = its basename (bundle). |
| 1w | Windows folder key | `URI.file()` from vscode-uri 3.2.0 (VS Code's URI class) + bundle (`E.parse(key)`, compared w/ `extUri.isEqual`) | `C:\Home\Your Name\jobs` -> `file:///c%3A/Home/Your%20Name/jobs` (drive lower-cased, `:` -> `%3A`, spaces `%20`, non-ASCII UTF-8 escaped). Key is parsed, so `file:///C:/...` matches too. owner: pending - live Windows check (no Windows here). |
| 2 | Timings | wall clock per CLI call | Profile create (file write) 0.2 s. Install not yet in shared dir: pdf 3.5 s, yaml 2.9 s, claude-code 8.9 s. Already in shared dir (2nd profile): claude-code 3.0 s, pdf 2.0 s - still a gallery query each. Already in that profile: 0.6 s, "already installed". One call w/ 4 `--install-extension` (3 gallery + vsix): 3.0 s total - batch them. |
| 3 | Local vsix metadata + auto-update | Python-built vsix (`mkvsix.py`: manifest, `[Content_Types].xml`, `extension/package.json` + `extension.js`), id `cez-job-finder.window`, installed into the profile; bundle `shouldAutoUpdateExtension` | 0.8 s. Profile list only, default untouched. Metadata `source: "vsix"`, `pinned: true`, `isApplicationScoped: false`, `isMachineScoped: false`, no uuid. Pinned => never auto-updated. Same id on the Marketplace (not today: "not found") would show a manual Update button that swaps in the Marketplace build + unpins. |
| 4 | Reinstall vsix | same id: changed content same version; `--force`; bumped version; older version | Same version, new content: replaced w/o `--force` (file content changed), exit 0. `--force`: same. 0.0.2: installs, old folder marked in `.obsolete` (VS Code deletes it later). Back to 0.0.1: refused "A newer version ... Use '--force'" - exit 0 anyway => read output or always bump version. |
| 5 | Settings Sync | bundle read (no sign-in in scratch) | Extensions sync per profile sends every installed extension, vsix too, w/ `pinned` + version; another machine then installs that id at that version from the Marketplace - "not found" today, a squatted id later. Skipped: `isMachineScoped` extensions + `settingsSync.ignoredExtensions` (scope APPLICATION => only the default profile's user settings). Profiles are their own sync resource. To set: mark ours machine-scoped (metadata) or add the id to `ignoredExtensions` - only on a VS Code Job Finder installed (`vscode-ours`). Live sync check: owner: pending (needs a signed-in account). |
| 6 | Copilot model pick | bundle read (no Copilot sign-in in scratch) | Key `chat.currentLanguageModel.<location>[.<target>]` (location e.g. panel), storage scope PROFILE, target USER; an old APPLICATION-scope value migrates once into the current profile. Lives in `User/globalStorage/state.vscdb` (default) vs `User/profiles/<location>/globalStorage/state.vscdb` => new profile starts on Auto unless copied. |
| 7 | Launcher makes it (`launch.ensure_profile`) | scratch `jobs.py launch`, cold, then again w/ that VS Code running | Cold: profile `cez-job-finder` (name `CEZ Job Finder`, icon briefcase) + folder key -> it; kept after VS Code ran + rewrote the file. `<data>/code.lock` = main pid while running => skip. Folder opened in a running VS Code before the profile => VS Code itself adds the key -> `__default__profile__`; next cold start swaps it. Extension checks read the profile's `extensions.json` once it exists (shared dir holds every profile's). |
| 8 | Migration (`launch.migrate_profile`, `keep_out_of_sync`) | scratch default `state.vscdb` seeded w/ `chat.currentLanguageModel.panel` + `sync.enable: true`, default settings `window.zoomLevel: 1`; cold `jobs.py launch`, VS Code run, then quit | Profile's `state.vscdb` holds the key; profile settings get the zoom; `.data/profile-migrated` = `model: copied` (once; `not copied` => setup skill re-says the pick-Sonnet line, Copilot). Our entry `metadata.isMachineScoped: true` kept after VS Code ran + quit; sync on => `settingsSync.ignoredExtensions` gets our id, comments kept. Sync skipping it live: owner: pending (signed-in account). |

### Window probes (local extension)

Job Finder's own extension: `app/vscode/` (plain JS, no build, no npm), packed by
`app/vscode_ext.py` into `.data/vscode/cez-job-finder.window-<version>.vsix` (installed from there,
never from `app/`). Content change => new version + `releases.txt` line (tested). Probe = same
extension w/ `JOBS_VSCODE_PROBE=<out.json>` set (cold scratch start passes env to the extension
host): after a settle delay writes tabs, theme, extensions, filtered commands, key settings, then
quits the window. VS Code 1.140.0 darwin-x64, Claude Code 2.1.288, ChatGPT 26.930.31730, 2026-10-03.
Scripts: [measure/5-*.sh](app-window/measure/); results: [probes/](app-window/probes/).

| # | What | Method | Result |
|---|---|---|---|
| a | Folder opens in its profile | cold CEZ profile + association (#1), 4 extensions installed into it only; `code <folder>` w/o `--profile` | Window in the CEZ profile: our extension present + ran ([a](app-window/probes/a-profile-restricted.json)). Fresh folder = Restricted Mode: only extensions declaring `untrustedWorkspaces` run - Claude + pdf viewer did NOT. Ours declares it (`capabilities`) => start page works before the user trusts the folder; Claude needs the trust click (or launcher's trust step). Other probes ran w/ trust off in scratch. |
| b | Extension opens Today formatted, no 6 s wait | on activation (~2 s after start): `markdown.showPreview(uri)` vs `vscode.openWith(uri, 'vscode.markdown.preview.editor')`, fresh profile + folder each | Both formatted at once, no delay. showPreview: webview tab "Preview Today.md" ([b1](app-window/probes/b1-showPreview.json)). openWith: custom tab "Today.md", input = the file ([b2](app-window/probes/b2-openWith.json)). Next start w/o the call: each comes back formatted, same kind ([b1 next](app-window/probes/b1-showPreview-next-start.json), [b2 next](app-window/probes/b2-openWith-next-start.json)). => openWith: plain title, one tab per file. `START_PAGE_DELAY_S` not needed once the extension opens it. |
| c | Claude walkthrough on first start | 4 fresh profiles, Claude installed by CLI before first start: defaults; `workbench.welcomePage.walkthroughs.openOnInstall: false`; `claudeCode.hideOnboarding: true`; `workbench.startupEditor: none`; 10 s settle | No Claude walkthrough tab in any ([c1](app-window/probes/c1-defaults.json), [c2](app-window/probes/c2-walkthroughs-off.json), [c3](app-window/probes/c3-claude-hideOnboarding.json)). Only tab = VS Code's own Welcome (`startupEditor: welcomePage` default); `none` => no tab ([c4](app-window/probes/c4-startupEditor-none.json)). A CLI install before first start opens no walkthrough, whatever these settings say. |
| d | Claude open/fill commands | command list ([c1](app-window/probes/c1-defaults.json)) + bundle read ([5-d-e-bundle-reads.txt](app-window/measure/5-d-e-bundle-reads.txt)) | Present: `claude-vscode.editor.open(sessionId?, prompt?, viewColumn?, _, fullEditor?, {programmatic})`, `sidebar.open()`, `primaryEditor.open(sessionId?, prompt?)`, `focus()` (no args; adds the active editor's selection as an @-mention), `newConversation`, `window.open`. Fill: prompt w/o sessionId => webview `fresh_with_prompt` => `createSession` = new chat replacing the one shown - breaks "never open extra chats". W/ the current sessionId already open in sidebar: "Session is already open. Your prompt was not applied" - no fill either. Session id = Claude Code session UUID; no command reads the current one. => no fill-without-new-session path in 2.1.288. |
| e | ChatGPT view + fill | `openai.chatgpt` from Marketplace into scratch profile; window probe + package.json + bundle | View "Codex" in the secondary sidebar (`codexSecondaryViewContainer`; activity bar only on VS Code w/o one). Pulls in `openai.codex-audio`. Commands ([e](app-window/probes/e-chatgpt.json)): `openSidebar`, `newChat`, `addToThread` (no args: selection), `addFileToThread(uri)`, ... - none takes text => no fill. |
| f | Copilot chat open w/ text | command list | `workbench.action.chat.open` present in 1.140 ([c1](app-window/probes/c1-defaults.json)). Fill w/ `{query, isPartialQuery: true}`: owner: pending - needs a Copilot sign-in. |
| g | Custom editor for Today.md | scratch build (+`customEditors` `filenamePattern: "Today.md"`, priority default) + provider; `vscode.open` 4 files | Takes every `Today.md` in the window: folder root, a subfolder, and one outside the folder ([g](app-window/probes/g-custom-editor.json)); `Notes.md` stays text. `customEditors` has no `when` => scope = wherever the extension is installed (the CEZ profile). Narrower = priority `option` + `workbench.editorAssociations` in the folder's settings (not measured). |
| h | Start page w/o the 6 s wait (`app/vscode/start.js`) | scratch `jobs.py launch` on the demo folder: cold (launcher writes `.data/start-page`, ONE code call); cold again (tab restored); then `code <folder>` alone w/ Today 3 h old (Dock, no marker) | Cold: only tab = Today.md formatted (custom preview editor) ~2 s after start, no text tab, marker gone ([h1](app-window/probes/h1-start-page-cold.json)). Restored: still one tab ([h2](app-window/probes/h2-start-page-restored.json)). No marker: same one tab; extension found uv, `today --refresh` rewrote Today ([h3](app-window/probes/h3-start-page-no-launcher.json)). Launcher exit 6 s incl. profile + installs. Window already open: 2nd `code <folder> <page>`, no wait (unit-tested only). |
| i | Today as a dashboard (`app/vscode/today.js`, custom editor `cezJobFinder.today`) | demo folder (`app/tests/demo.py`), scratch cold `jobs.py launch`, probe 8 s settle | Only tab = Today.md, `type: custom`, `viewType: cezJobFinder.today`, extension 0.3.0 ([i](app-window/probes/i-today-dashboard.json)). Editor priority `option` + folder association `Today.md` => only this folder's page; no extension => VS Code drops the association, page opens as the formatted Markdown (#b). Data: `.data/today.json` written beside the page by `today.py` (same model as the page; tested). |
| j | Claude button: fresh sidebar chat (`today.sayMode` "new") | demo folder (ai = claude), scratch CEZ profile w/ Claude 2.1.289 (Marketplace latest, inside the gated range), trust off, `code <folder> --profile`, 12 s settle; probe runs the button's own path (`sayWords`, `JOBS_VSCODE_PROBE_SAY`), reads tabs 4 s later | Mode `new`, status "New chat ready - press Enter"; tabs before + after the same: one group, only tab Today.md (custom dashboard), still active => no Claude editor tab ([j](app-window/probes/j-claude-new-chat.json)). Bundle: `honor-preferred-location` + preferredLocation sidebar + no panel for the session => `target: sidebar` => `activateInSidebar(undefined, words)` => webview `fresh_with_prompt` (#d). Not sent: no transcript w/ the words under the folder's `~/.claude/projects/` key besides the probing session's own. Words visible in the sidebar box: owner: pending (scratch Claude not signed in; webview not readable from a probe). |
| k | Claude ready before the first click (`start.warmUpPlan`, `extension.warmUp`) | scratch CEZ profile w/ Claude 2.1.289 + 0.5.0, demo Today, ai = claude, trust off, Claude config in scratch (`CLAUDE_CONFIG_DIR`, not signed in); each run cold w/ window state cleared; warm = off / activate / view (`claude-vscode.sidebar.open` + `focusActiveEditorGroup`); button's own path 3 s after Today shows; Claude's log read after ([5-k-warm.sh](app-window/measure/5-k-warm.sh)) | Claude active 5.2-7.5 s after launch in every run, warm-up or not (`onStartupFinished`, before ours) => activate alone gains nothing. Its chat view loads only when shown: w/o view warm-up 0.8 s after the press; press -> new chat launched 1.0-1.5 s (first start of a profile 12 s). View warm-up: view loaded 7.2-8.6 s after launch, before any press; press -> chat 0.007-0.16 s (first start 0.16 s). Command itself resolves in <40 ms either way => feedback can't wait on it alone. Sidebar shown or hidden at start: same. Every run: one tab, Today.md active, no Claude tab ([k](app-window/probes/k-claude-warm-up.json)). Shipped: view warm-up for Claude; ChatGPT activate only (view not measured); Copilot nothing. Button: busy label "Starting Claude…" at once, "the first time takes a few seconds" line past 400 ms (node-tested). |
| l | Look switch (`.data/look`, `jobs.py look`, Today's Match my computer · Light · Dark) | scratch CEZ profile w/ 0.9.0, folder = program copy + demo Today, look auto, computer in dark mode; probe runs the switch's own path (`switchLook` -> `uv run app/jobs.py look WORD`) 4 s after start ([5-l-look.sh](app-window/measure/5-l-look.sh)) | dark: `workbench.colorTheme` Dark Modern, autoDetect off, page told 0.49 s after the click ([l](app-window/probes/l-look-switch.json)). light: theme kind dark -> light 0.73 s after the click, Light Modern, same window, no reload ([l light](app-window/probes/l-look-switch-light.json)). Settings file rewritten => VS Code applies it live. High contrast left to the computer. |

### Today dashboard - what a click does

Buttons live inside the window only: no `vscode://` link handler (any web page or posting could
call one). Webview sends a button index, never words, links or paths; words come from
`.data/today.json`, each matched against `app/vscode/say.json` (shared w/ `today.py`, tested) or
the button is dropped. CSP `default-src 'none'`, nonce'd style + script, no remote loads. Yellow
only on buttons (owner rule).

| Button | Copilot | Claude | ChatGPT | AI unknown / not set |
|---|---|---|---|---|
| Say words ("Make my resume", "Help me apply", ...) | `workbench.action.chat.open {query, isPartialQuery: true}`: words in the chat box, not sent | new chat in the sidebar, words typed in, not sent: `claude-vscode.editor.open(undefined, words, undefined, undefined, false, {programmatic: "honor-preferred-location"})`; chat shown before moves to Claude's session history; title "Opens a new chat with these words typed in - press Enter to start", then "New chat ready - press Enter" on the page + status bar (owner 2026-10-03, measured: [j](app-window/probes/j-claude-new-chat.json)). Pressed: button reads "Starting Claude…" (others "Opening the chat…"), greyed until done; still waiting after 400 ms => "Starting Claude - the first time takes a few seconds"; chat view opened at window start so it rarely shows (k). Only Claude 2.1.288 up to 2.2 w/ `claudeCode.preferredLocation: sidebar`; else copy words + `claude-vscode.sidebar.open` + line "Copied - click the chat box, paste (Cmd+V, or Ctrl+V off Mac), press Enter."; button reads "Copy: <words>" | copy + `chatgpt.openSidebar` + same line | copy + same line |
| I sent it / I heard back / It's closed | no chat: `jobs.py status set N applied\|heard_back\|closed` run by the extension (user's click = their own record), folder moves; line "Job N marked as sent." + Undo for 10 s => `status undo N --from STATE` (takes back only that state, log row dropped, folder back); fail => plain line + the chat words (owner 2026-10-04) | same | same | same |
| Job title (opens the posting) | `vscode.env.openExternal` - https only, the stored link as is | same | same | same |
| Company name | `vscode.env.openExternal` - http(s) website from the job search's company record (`app/companies.py`, cached 30 d), else `https://duckduckgo.com/?q=<name>` (owner 2026-10-03) | same | same | same |
| Open resume / Open folder | `vscode.open` / `revealInExplorer` - only paths under `My Jobs/`, `My Resume/`, `Guides/` that exist under the folder's real path | same | same | same |

Why a new chat for Claude, copy for ChatGPT: rows d, e (no command fills the chat shown w/o a new
one); owner 2026-10-03 picked a fresh Claude chat over copy-paste (row j).

Owner checks by hand (scratch has no sign-ins):
- Copilot: click "Make my resume" => words sit in the chat box, nothing sent. owner: pending.
- Claude / ChatGPT: click => chat opens, the copied line shows, paste works, nothing sent; no new
  chat in the history list. owner: pending.
- "Never sent" by transcript count (no new file under `~/.claude/projects/<key>`,
  `~/.codex/sessions`, `workspaceStorage/*/chatSessions` after a click): owner: pending - needs a
  signed-in scratch.
- Look: tiles, cards in columns beside the chat, light + dark theme. owner: pending (preview).

## Phase 1 - what + why

Still stock VS Code, on the user's own install + subscriptions; only settings + page text change.

- Brand look: `workbench.colorCustomizations` per stock theme (`app/window/brand.py`), written to
  the workspace => only this folder's window changes, their own theme elsewhere untouched.
- Pages: `app/window/pages.css` (`markdown.styles`) - Caladea, 68ch measure, list items as cards.
  Reads as one program's pages, not a code editor's Markdown preview. No remote loads.
- Today: job title = link to the posting, company = its website (else a web search), "Open its
  resume" link text, never a bare 100-char URL; separate "Open the posting" dropped 2026-10-04
  (the title does it, less clutter); words to say as plain bold
  quoted words (code spans) - user reads + types them; real buttons + a dashboard Today = phase 2
  (owner 2026-10-03). "What you can say" list at the end, same words.
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

## Phase 2 - what + why

Owner pick 2026-10-03 (plan-ejf.1.10): own profile + local extension. Still stock VS Code on
the user's own install + subscriptions.

- Own profile "CEZ Job Finder" (`launch.ensure_profile`, #7): made on a cold start, folder tied
  to it => extensions installed there only (AI panel, pdf, yaml, ours), user's own VS Code
  elsewhere unchanged. Every `code` call carries `--profile`; what's missing goes in ONE batched
  install (#2: 3 s vs ~15 s one by one).
- Moving in (`launch.migrate_profile`, #8): Copilot model pick, zoom, text size copied once from
  the default profile; pick not found => `.data/profile-migrated` `model: not copied` =>
  `job-setup` re-says the pick-Sonnet line once (Copilot).
- Out of Settings Sync (#5): ours marked machine-scoped + id in `settingsSync.ignoredExtensions`
  when sync is on - another computer would fetch "cez-job-finder.window" from the Marketplace
  (not there; could be squatted).
- Local extension `app/vscode/` (plain JS, no npm), vsix built by `app/vscode_ext.py` into
  `.data/vscode/`, pinned (never auto-updated), new version per content change. Runs before the
  folder is trusted (`untrustedWorkspaces`, #a).
- Start page (`start.js`, #h): launcher writes `.data/start-page`, extension opens that page as
  the window starts and deletes the marker - no 6 s wait, one `code` call. Opened from the Dock
  (no marker): extension runs `today --refresh` itself, same as the launcher.
- Today = dashboard (`today.js`, #i): paper look like the install site (heading + rule, jobs split
  by rules, Next up alone framed), tiles, real buttons. Caladea shipped in the vsix
  (`app/vscode/media/fonts`, OFL.txt w/ it): `localResourceRoots` = that folder, CSP `font-src` =
  `cspSource` only, `@font-face` via `asWebviewUri` - w/o it the page fell back to Georgia. Data =
  `.data/today.json`, same model as `Today.md`; words from `say.json`, shared w/ the page. W/o
  the extension the folder's association drops => formatted `Today.md`, words to type.
- Buttons put words in the chat, never send: Copilot fills its box; Claude + ChatGPT can't be
  filled w/o a new chat (#d, #e) => copy + open + one paste line. No `vscode://` handler.

Owner checks still open (beyond the button checks above):
- Windows: folder key + profile on a real Windows install (#1w). owner: pending.
- Settings Sync skips ours on a signed-in account (#5, #8). owner: pending.
- First cold launch on the live install: profile made, AI panel + sign-in carried over, Today
  dashboard opens. owner: pending (plan-ejf.1.17).
- ChatGPT: chat on the right at first start (#e: secondary sidebar) - START HERE + What you can
  ask still say "click its icon on the left". owner: pending.

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
- Filling Claude's / ChatGPT's chat from a button: only via a new chat (#d, #e) - breaks one chat.
- Extension on the Marketplace: a public listing for a local-only helper; sync would pull it in
  everywhere. Local vsix, pinned, out of sync instead.
