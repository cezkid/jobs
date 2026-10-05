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
quits the window; `JOBS_VSCODE_PROBE_HOLD=<dir>` keeps it up first, serving a driver's requests (#r). VS Code 1.140.0 darwin-x64, Claude Code 2.1.288, ChatGPT 26.930.31730, 2026-10-03.
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
| m | Outline + Timeline hidden under the file list (`launch.hide_side_views`) | bundle read: no setting; `outline.removeView` / `timeline.removeView` act only while the Explorer is the shown sidebar (no-op otherwise), `toggleVisibility` flips; hidden views = profile state db key `workbench.explorer.views.state.hidden` (JSON list, `{id, isHidden}` or bare id = hidden). Scratch cold `jobs.py launch` on the demo folder, ai = claude, probe 8 s, list read after quit ([5-m-views.sh](app-window/measure/5-m-views.sh)) | Launcher writes `outline` + `timeline` hidden into the CEZ profile's db before the window, once (own row `cez-job-finder.views-hidden` => a view the user shows again stays shown). After the run VS Code re-saved its whole list: visible = `workbench.explorer.fileView` only; hidden = outline, timeline, openEditorsView (its default) ([m](app-window/probes/m-views-hidden.json)). Only tab Today.md dashboard. Profile-wide = only Job Finder's folder. |
| n | Opened w/o the Desktop icon (Dock, recent folders, File > Open) | bundle read: trusted folders = key `content.trust.model.key` (`{"uriTrustInfo": [{uri: {$mid 1, scheme, path}, trusted}]}`), storage scope -2 = app-wide shared store `~/.vscode-shared/sharedStorage/state.vscdb` (`--shared-data-dir`), falls back once to the default `User/globalStorage/state.vscdb` (key moved over on first read, listed in `__$__migratedStorageMarker`; listed => default copy ignored). Scratch cold `jobs.py launch` on the demo folder (ai = claude), then Today aged 3 h + `code <folder>` alone, 12 s settle ([5-n-trust.sh](app-window/measure/5-n-trust.sh)) | Before (launcher w/o trust step): Restricted Mode, only ours active, Claude off; ours shows the plain line ([n before](app-window/probes/n-before-untrusted.json)). After (`launch.ensure_folder_trusted`, cold start): folder trusted, Claude active, no line; key written to the default db, VS Code moved it to the shared store itself ([n after](app-window/probes/n-after-trusted.json)). Today rebuilt by ours both times (stale > 1 h). Scratch runs before this one passed no `--shared-data-dir` => read the owner's `~/.vscode-shared`; `scratch_args` carries it now. |
| o | Jobs panel above the file list (`jobs.js` model, `extension.showJobs` / `openJobs`, `launch.place_jobs_view`) | contributed view `cezJobFinder.jobs` in `views.explorer`; launcher writes it `order -1` into `workbench.explorer.views.state.hidden` once (row `cez-job-finder.jobs-view-placed`). Scratch cold `jobs.py launch` on the demo folder, ai = claude, probe 8 s, list read after quit ([5-o-jobs-view.sh](app-window/measure/5-o-jobs-view.sh)) | Order kept: after quit VS Code's list has `cezJobFinder.jobs` order -1 above `fileView`. Run 1: view registered, groups drawn, but `visible` false - bundle `showCollapsed`: an extension view contributed into the Explorer starts collapsed whatever package.json says. Fix: ours runs `cezJobFinder.jobs.focus` once per folder (workspaceState `cez-job-finder.jobs-shown`), then `focusActiveEditorGroup`. Run 2: `visible` true, groups Next up / Waiting on you / Follow up / Best to apply next, only tab Today.md dashboard, still active ([o](app-window/probes/o-jobs-view.json)). User's later collapse holds (VS Code keeps it per folder). |
| p | Start earlier: `workspaceContains:app/jobs.py` added to `activationEvents` (plan-ejf.13.1) | two scratch builds of 0.18.0 (`vscode_ext.build(out, package=...)`): a = as shipped (`onStartupFinished`, `onCustomEditor`, `onView:cezJobFinder.jobs`), b = + `workspaceContains:app/jobs.py`; one scratch VS Code each, CEZ profile w/ Claude 2.1.289 + yaml + pdf, look-alike folder (demo Today, launcher's workspace settings, marker `.data/start-page`, trust off), 5 start cases x 3 runs, builds in turn. Ours active = `_doActivateExtension cez-job-finder.window` line in `exthost.log` (+ its event), page shown = `openStartPage` resolved (probe), tabs read 4 s later ([5-p-activation.sh](app-window/measure/5-p-activation.sh)). VS Code 1.140.0 darwin-x64, 2026-10-04 | Medians, ms from the `code` call, active / page shown, a vs b ([p](app-window/probes/p-activation.json)). Today restored active: 4583 / 5060 vs 4939 / 5953. Today restored behind `Resume details.yml`: 5420 / 6204 vs 5297 / 6218. START HERE restored (no search settings): 4640 / 5771 vs 4558 / 6593. First start of a fresh profile (START HERE): 6898 / 7874 vs 6504 / 7750. Today opened the first time after setup: 4439 / 4936 vs 4531 / 5133. Extension host itself up 3.9-7.1 s after the call, run to run => read from host start: every case but the fresh profile, both builds start on `onView:cezJobFinder.jobs` (Jobs panel drawn) 0.5 s after the host (1.1 s behind the yml tab), page 1.0-2.5 s after it - b no faster, differences inside the run-to-run spread; `onCustomEditor` never came first. Fresh profile (Jobs panel still collapsed): a `onStartupFinished` 1.2-1.6 s after the host, page 2.2-2.5 s; b `workspaceContains` 0.5-0.7 s, page 1.8-2.1 s => page ~0.3 s sooner (3 runs). All 30 runs: one Today / START HERE tab, active, no duplicate. Verdict: adopt `workspaceContains:app/jobs.py` - no harm measured, gains only where the Jobs panel isn't drawn at start (first start; panel collapsed or file list hidden: same path, not measured); the wait left is VS Code reaching its extension host => the splash. |
| q | Mac loading splash live (`app/install/splash-mac.js`, plan-ejf.13.4) | scratch root (`mktemp -d /tmp/jfv.XXXX`), started like `start-mac.sh` (`.data/splash-start` written, then `osascript -l JavaScript splash-mac.js <root>`), shown on the owner's screen; script's own clock via `--log=<json>` (started = after the ObjC import, shown = after `orderFrontRegardless`, closed, why). 5 runs w/ `.data/window-ready` written 1.5 s in; one run w/ a left click posted at its middle (CGEvent); one run w/ neither. Renders: `--render=<png>` - content view drawn by `cacheDisplayInRect:toBitmapImageRep:` over the window's background colour, window never shown, no screenshot ([5-q-splash.py](app-window/measure/5-q-splash.py)). macOS 26.4.1 x86_64, 2026-10-04 | On screen (`visible` true) after the `osascript` start: median 479 ms, max 485 (469-485; 282-291 of it after the ObjC import, the rest = osascript starting) => inside the ~1 s goal, before `update` has run. Ready file written -> window closed: median 34 ms, max 93 (24-93; poll 0.1 s), all 5 closed by `ready`. Neither: closed by `cap` 44.8 s after it showed = 45.1 s after its start. Click: NOT measured - a posted click needs the Accessibility permission, not granted to the terminal (`AXIsProcessTrusted` false) => never delivered, splash stayed up; owner: pending - click it by hand. Also owner: pending (no screenshot here): spinner turning, keyboard staying w/ the app in use. Renders: `/tmp/jfv-splash-renders/splash-light.png` + `splash-dark.png` (760 x 500 px = 380 x 250 pt @2x): icon, CEZ Job Finder, spinner, Opening..., hint line, all readable in both; spinner draws dim grey in the dark render (the off-screen draw may not carry the window's dark appearance to it - look at it live). Numbers: [q](app-window/probes/q-splash.json). |
| r | Links open as a tab in a scratch window (plan-29g.4) | scratch `mktemp -d /tmp/jfv.XXXX`, folder = program copy + demo (`app/tests/demo.py`), ai = claude, extension 0.22.0 w/ probe hold (`JOBS_VSCODE_PROBE_HOLD`: driver drops requests, extension runs a Today click's own path `doAction` + reads tabs). Local test site on 127.0.0.1 logs every request (path, cookie, user agent); each page titled "JF probe <uniq> <name>" => its tab told by label. Cold `jobs.py launch` (trust step + `--disable-workspace-trust`); window quit + `jobs.open_for_user` w/ `webbrowser.open` stubbed; `code <folder>` alone (Dock); same after the folder's trust entry removed. Other-program leg: scratch applet owning `cezprobe-r://` calls the site back = stand-in for `vscode://` (an escape there lands in the owner's own VS Code); ad-hoc signed under the checkout's ignored `.data/` (LaunchServices won't bind a scheme to an app under `/tmp`: kLSApplicationNotFoundErr), control `open cezprobe-r://control` reached it ([5-r-links.py](app-window/measure/5-r-links.py)). VS Code 1.140.0 (Electron 43.7.3, Chromium 150), Claude Code 2.1.289, macOS 26.4.1 x86_64, 2026-10-04 | Today click (company link: http as stored; posting links are https only) => tab labelled w/ the page title. `jobs.py open` => "opened in the Job Finder window" (0.7 s) + tab. Two `jobs.py open` at once: both "window", 2 tabs; one Today action w/ 2 links: 2 tabs. Each tab up within 0.9 s (poll 0.5 s). Tab `type` unknown: `tab.input` undefined => the tab API tells a browser tab by its label only, never its URL. Hostile page: `file://` img + fetch of files in the folder both miss; `file://` iframe, `window.open`, navigation never ran (0 beacons), page stayed - even under `--disable-workspace-trust` (bundle: every file trusted then => Chromium's own http -> file block is what holds). `cezprobe-r://` by iframe, `window.open`, link click, navigation: 0 reached the applet (`window.open` left an empty tab labelled "scheme-open"). Popups w/o a click: `window.open` + a scripted `target=_blank` click both opened as more tabs INSIDE the window (Code user agent), 0 in the system browser => bundle: new tabs always allowed, only a separate window needs a click within 1 s. Window closed: "opened in your browser", stub got the link, 0 site requests, no request file left. Dock (launcher's trust entry): trusted, 1-year cookie from `/signin` sent back. Trust entry removed: untrusted, cookie NOT sent (ephemeral). Browser storage: `<data>/User/workspaceStorage/<id>/browserStorage`. Screenshot of a posting-like page in the tab: `.data/probe-shots/r-posting-in-window.png` (window only, ignored; owner check plan-29g.5). Claude panel's "Browser connected" = Claude in Chrome on the owner's own Chrome, not this tab (#Links inside the window, plan-29g.11). Numbers: [r](app-window/probes/r-links.json). |

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
| Job title (opens the posting) | a tab in this window: `workbench.action.browser.open` w/ the stored link as is, a plain string (http(s) only, no `reuseUrlFilter`); VS Code w/o that command (before 1.109) or the open fails => `vscode.env.openExternal` (system browser). [Links inside the window](#links-inside-the-window---what--why) | same | same | same |
| Company name | same as job title - http(s) website from the job search's company record (`app/companies.py`, cached 30 d); none on record => plain name, no link, no web search (owner 2026-10-03) | same | same | same |
| Open resume / Open folder | `vscode.open` / `revealInExplorer` - only paths under `My Jobs/`, `My Resume/`, `Guides/` that exist under the folder's real path | same | same | same |

Why a new chat for Claude, copy for ChatGPT: rows d, e (no command fills the chat shown w/o a new
one); owner 2026-10-03 picked a fresh Claude chat over copy-paste (row j).

Integrated Browser chat tools (`workbench.browser.enableChatTools`, plan-29g.1): left at VS Code's
default (on). Its own words (1.140): "chat agents can use browser tools to open and interact with
pages in the Integrated Browser". Reaches VS Code's own chat only = Copilot users (Claude +
ChatGPT windows run w/ `chat.disableAIFeatures` on). Off now would settle "fill applications
inside the window" before it's measured (plan-29g.7) + owner decides (plan-29g.8); page text stays
data either way (AGENTS.md). Revisit there.

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
- Today: job title = link to the posting, company = its website (none on record => plain name), "Open its
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
  window, not the last-used one. Links: [Links inside the window](#links-inside-the-window---what--why).
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
- Opened w/o the Desktop icon (#n): launcher puts Job Finder's folder on VS Code's trusted list at
  each cold start (this folder only, never `security.workspace.trust.enabled` off; other entries
  kept; running VS Code => next cold start) => Dock, recent folders, File > Open come up with the AI
  panel + PDF viewer. Still untrusted (VS Code never cold-started by the launcher since): ours shows
  one plain line - open it from the Desktop icon - + "Allow it here" (VS Code's own trust page).
  Today rebuilt when stale either way (#h3). Update + extension installs stay launcher-only.
- No Outline + Timeline under the file list (#m): code-editor tells, hidden once in the profile's
  state at a cold start; the file list never hidden.
- Jobs panel above the file list (#o, owner 2026-10-04): same model + actions as Today (`jobs.js`
  over `today.model`, shared `doAction`), plus Applied from `My Jobs/2 Applied`. Opened once per
  folder (VS Code starts it collapsed); redraws on `.data/today.json` + `My Jobs/**` changes.
  Squeeze on the file list: owner visual check (plan-ejf.12.6).
- Loading splash (#p, #q, owner 2026-10-04): double-click showed nothing until Today drew - update +
  launch invisible, then VS Code's empty window until its extension host is up (3.9-7.1 s, #p).
  Nothing of ours paints inside VS Code before that => small native window outside it, started by
  the start script BEFORE update: Mac `app/install/splash-mac.js` (JXA via `osascript`, no deps; on
  screen in 0.5 s, #q), Windows `splash-windows.ps1` (PowerShell 5.1 + WinForms, run from a copy in
  `.data\` so update can swap `app\`). Icon, name, "Opening...", first-start hint, spinner; brand
  paper / desk colours by `.data/look`, else the computer's mode; floats above VS Code's window, no
  Dock / taskbar entry; Mac one never takes the keyboard (Windows: owner check). Closes on the
  ready signal `.data/window-ready`
  (newer than the splash's start): extension writes it once the start page is shown (or failed) +
  at Today's first draw; launcher only where the extension won't (VS Code already running, ours not
  installed at this version, `code` failed, any exception - never a `finally`: a cold launch returns
  before the window exists); start script when launch fails. Also closes on a click or after 45 s.
  No pid file / single instance: a reused pid would hide it for good. Extension also starts on
  `workspaceContains:app/jobs.py` (#p): page ~0.3 s sooner where the Jobs panel isn't drawn at start.
- Buttons put words in the chat, never send: Copilot fills its box; Claude + ChatGPT can't be
  filled w/o a new chat (#d, #e) => copy + open + one paste line. No `vscode://` handler.

Owner checks still open (beyond the button checks above):
- Windows: folder key + profile on a real Windows install (#1w). owner: pending.
- Settings Sync skips ours on a signed-in account (#5, #8). owner: pending.
- First cold launch on the live install: profile made, AI panel + sign-in carried over, Today
  dashboard opens. owner: pending (plan-ejf.1.17).
- ChatGPT: chat on the right at first start (#e: secondary sidebar) - START HERE + What you can
  ask still say "click its icon on the left". owner: pending.
- Windows loading splash (`app/install/splash-windows.ps1`, plan-ejf.13.5): written on a Mac, never
  run - source checks only (`test_splash_windows.py`). owner: pending (plan-ejf.13.8), on a real
  Windows install, VS Code closed first:
  1. Double-click the Desktop icon: splash on screen within ~1 s, in front, centred on the screen
     the pointer is on - icon, "CEZ Job Finder", moving bar, "Opening...", the hint line. Not
     minimized w/ the console (shortcut `WindowStyle` 7), no taskbar button of its own.
  2. It closes when Today / START HERE shows - not before the VS Code window, not seconds after.
  3. Start again w/ CEZ Job Finder already open: splash closes within a second or two.
  4. Click the splash while it waits: it closes; VS Code still opens.
  5. Look: `uv run app/jobs.py look dark`, start -> dark splash; `look light` -> paper; `look auto`
     -> follows Windows' app mode (Settings > Personalization > Colors).
  6. Cap: rename `uv.exe` away (launch fails) -> splash closes at once (the bat's ready signal);
     w/ VS Code never showing a page it closes itself after 45 s.
  7. Update day (a new `app/` comes down): start still works, no "file in use" - the splash runs
     from its copy `.data\splash-windows.ps1`.
  8. Installer's own PowerShell window (`install-windows.ps1` runs the bat at its end): window
     stays, nothing printed into it by the splash, prompt usable after.
  9. Console in the taskbar: gone once the splash closes (it shares the launcher's console).
  10. Smart App Control on (PowerShell in Constrained Language Mode): WinForms may be refused =>
      no splash, nothing printed, start unchanged. Say which.
  Also note: does the splash take the keyboard from the app in use (Mac one never does)?

## Links inside the window - what + why

Owner 2026-10-04 (plan-29g): "open browser within vscode instead of another window" => job links
open as a tab in the Job Finder window. Filling an application there: measured first (plan-29g.7),
owner decides (plan-29g.8).

VS Code's Integrated Browser (1.109+): any http(s) site, sign-ins, uploads. Bundle read, VS Code
1.140, adversarial review 2026-10-04; live probe #r (plan-29g.4).
- `workbench.action.browser.open` takes a url string or `{url, openToSide, reuseUrlFilter}`. Ours
  passes the string only: w/ `reuseUrlFilter` a matching tab is re-navigated => a half-filled form
  wiped.
- `workbench.action.browser.openExternal` sends the page shown to the system browser - an item in
  the tab toolbar's overflow menu (never call it a button).
- Only localhost links route there by themselves; `vscode.env.openExternal` still goes to the system
  browser => ours calls the command.
- `workbench.browser.dataStorage` default `global` = partition `persist:vscode-browser`, shared by
  every VS Code window + profile, kept after uninstall => `workspace` (window scope, so
  `app/workspace.py` COMMON): sign-ins + cookies for this folder only. Untrusted folder forces
  ephemeral (nothing kept; #r: cookie gone once the trust entry is removed). Kept at
  `<data>/User/workspaceStorage/<workspace id>/browserStorage`. `workbench.browser.showInTitleBar:
  false`: its globe button is experiment-controlled.
- `file://` in a tab: VS Code serves files under trusted roots only (Copilot dirs, workspace folders
  when trusted) - but `--disable-workspace-trust` (launcher + `jobs.py` pass it) trusts every file.
  A web page still can't load, fetch or open one (#r): Chromium's http -> file block holds.
- Tab API: a browser tab's `input` is undefined => found by its label (page title), URL unreadable.
- Tabs sandboxed + context-isolated; links to other programs (`vscode://`) refused (permission
  `openExternal` has no category => false; #r: 0 of 4 ways reached a stand-in program). Chromium 150
  (Electron 43) vs Chrome 154; pages see `window.__vscode_helpers` + "Code/ Electron/" in the user
  agent (captcha scores may drop); a page can open more tabs in the window w/o a click (#r) - only a
  separate window needs a click within 1 s; `mailto:` does nothing.
  Navigation telemetry carries no URL.
- Google blocks Google-account sign-in in embedded browsers (since 2021) - untested here =>
  `jobs.py open --outside`.
- Claude's chat vs the window's tabs (bundle read: Claude Code extension 2.1.289 + its CLI, VS Code
  1.140; plan-29g.11). "Browser connected" over Claude's chat box = Claude in Chrome (Anthropic's
  Chrome extension) joined to that chat: it drives the user's own Google Chrome, never a tab here.
  Shows once its server is added to the chat, before Chrome answers; its x = "Disconnect browser".
  - Window tabs never reach Claude: the extension has no code for VS Code's browser (0 refs to
    `workbench.action.browser*`; tab `input` undefined anyway), its IDE tools = diagnostics only
    (+ Jupyter when connected), `@browser` lists Chrome's tabs (`tabs_context_mcp`).
  - Connects at chat start when Claude in Chrome "Enabled by default" is on
    (`claudeInChromeDefaultEnabled` in `~/.claude.json`, CLI default off; per computer user = every
    window, scratch included) + claude.ai subscription sign-in; or when the user types `@browser` /
    `/chrome`. Owner's is on => a scratch window's chat (owner's account) joins the owner's Chrome:
    probes never send a chat there.
  - Page data reaches the AI account only when Claude calls a Claude in Chrome tool (page text,
    screenshots, tab list, console): the result enters the chat. Joined at start: each tool asks
    first; after `@browser`: no asking for the rest of that chat. `@browser` itself sends the tab's
    address + title + a one-time instructions block, no page text. Workday filling (`job-apply`)
    is this route.
  - VS Code's own chat (Copilot) is the one that can read window tabs: `workbench.browser.enableChatTools`
    (default on) gives its agent `read_page`, `list_browser_pages` + page actions ("open and interact
    with pages") => page text to the GitHub account when it uses them; off => VS Code's open tool
    tells the agent it can't see the page. Privacy table names Claude in Chrome page text (plan-29g.12);
    Copilot's line waits on the chat tools pick (plan-29g.8).

How links get there:
- Today + Jobs panel (plan-29g.1): job title + company => `today.openLink` (`app/vscode/today.js`):
  http(s) only; command present => tab; missing or the open fails => system browser.
- `jobs.py open "<link>"` (plan-29g.2), how every AI shows a link: window running => one request
  `.data/open-link/<32 hex>.json` (`{url, t}`, written as `.tmp`, renamed in); extension's watcher
  claims it by rename (`.taken`) + opens a tab; jobs.py takes it back after 2 s + opens the system
  browser => whoever moves it first opens it, never twice. Requests over 10 s old deleted unseen,
  both sides. Prints "opened in the Job Finder window" / "opened in your browser" => the AI says
  where. `--outside` = system browser always. Not a file here + not http(s) => refused: a
  `vscode://` or script link from a posting's text never runs. No other local way in: VS Code's
  CLI server is remote-only, the start-page marker is read once, `vscode://` refused (+ any page
  could call it).
- Workday stays in Chrome (Claude-in-Chrome extension); other fillers keep their own Chrome profile
  (`app/apply/browser.py`).
- Privacy: sign-ins + site data stay on this computer, in this folder's browser storage (AGENTS.md
  table, `Guides/Who sees what.md`); the site itself sees the visit, as in any browser.

Owner checks still open: a posting open inside the window looks + works right (plan-29g.5;
scratch screenshot from #r: `.data/probe-shots/r-posting-in-window.png`).

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
- Opened w/o the icon: line only, no trust write (bead's first option): every Dock open would stay
  in Restricted Mode until the user clicked through VS Code's trust page - measured #n, trust write
  works on a cold start. Kept as the fallback when it hasn't run yet.
- `security.workspace.trust.enabled: false` (app-wide or in the folder's settings): trust off for
  every folder they open, not just Job Finder's; folder settings can't set it (1.140: application scope).
- Extension on the Marketplace: a public listing for a local-only helper; sync would pull it in
  everywhere. Local vsix, pinned, out of sync instead.
- Loading text inside VS Code before its extension host: every view that renders is an extension
  => nothing of ours can paint there. Splash lives outside VS Code instead.
- Notification at the double-click: fades after a few seconds, doesn't track loading.
- tkinter splash: Python's icon shows in the Dock next to ours.
- AppleScript applet progress window: frozen while the applet's `do shell script` blocks.
- Simple Browser (`simpleBrowser.show`) for job links: an iframe - sites that refuse framing (sign-in
  pages, many job sites) stay blank.
- `vscode://` handler for `jobs.py open`: any web page or posting could call it, not just the AI.
- Browser data `global` (VS Code's default): sign-ins shared w/ every VS Code window + profile, kept
  after uninstall. `workspace` instead.
- `reuseUrlFilter` on open: re-navigates a matching tab => a half-filled form wiped.
- `*` activation (start w/ every window): while the profile is pending ours lives in the default
  profile => would run in every folder they open. `workspaceContains:app/jobs.py` instead (#p).
