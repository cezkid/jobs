# Filling a form inside the Job Finder window - measured (plan-29g.7)

Can an application be filled in the window's own browser tab (VS Code Integrated Browser) instead
of Job Finder's own Chrome? Measurement only: nothing here ships, `app/apply/` + `app/launch.py`
untouched. Owner decides in plan-29g.8; trial bead plan-29g.9. Window + links: `app-window.md`.

Setup, 2026-10-05: scratch VS Code 1.140.0 (Electron 43.7.3, Chromium 150), Claude Code 2.1.289,
macOS 26.4.1 x86_64. Binary started directly (never `launch.py`, never `~/.vscode/argv.json`), own
`--user-data-dir` / `--extensions-dir` / `--shared-data-dir` under `$D = mktemp -d /tmp/jfv.XXXX`,
folder = program copy + demo + the window's own settings, throwaway browser storage. Dummy data
only (Test Person, `test.person@example.com`, 100-byte dummy PDF), never the user's; Submit never
clicked. Scripts: [measure.py](vscode-browser/measure.py) (stages setup, ext, route1, route2, gh,
restricted), [cdp.py](../../apply/cdp.py) (stdlib CDP client, now shipped for the trial), [formsite.py](vscode-browser/formsite.py)
(local test form, logs every request), [probe-ext/](vscode-browser/probe-ext/extension.js) (scratch
extension: opens tabs, starts the attach, asks for proxies). Screenshots (window only, ignored):
`.data/probe-shots/form/`.

Local test form (127.0.0.1): text, email, textarea, select, typed combobox w/ option list, checkbox,
radio, file, other-site frame (localhost = another site => out-of-process frame) w/ its own text +
file box, a button running `debugger;`. Page reads back every value + whether each event was real
(`isTrusted`).

## Two routes

| | Route 1 - debugging port | Route 2 - js-debug CDP proxy |
|---|---|---|
| How | VS Code started w/ `--remote-debugging-port=<p>` -> Playwright `connect_over_cdp` | extension starts `{type: "pwa-editor-browser", request: "attach", urlFilter}` (js-debug's attach to a browser tab), then `extension.js-debug.requestCDPProxy` per debug session -> raw CDP over WebSocket on 127.0.0.1 from Python |
| Ship? | **No** - comparison only (security row) | the only shippable one |
| Numbers | [route1-local.json](vscode-browser/route1-local.json) | [route2-local.json](vscode-browser/route2-local.json) |

## Local form

| | Route 1 | Route 2 |
|---|---|---|
| Start | port listens on 127.0.0.1 only; connect 174-291 ms, 1 context | attach 8.2-8.5 s: parent session + 1 page session; page proxy answers, parent's never (timed out at 5 s). `urlFilter` must match exactly ONE tab - else js-debug shows "Select a browser tab to debug" and the attach waits on it |
| Text, email, textarea | `fill` ok, read back right, input + key events real | click + `Input.insertText` ok; key events (`Input.dispatchKeyEvent`) ok; value set by script ok but its events not real |
| Select | `select_option` ok (change event not real) | set by script ok (events not real) |
| Typed list (combobox) | click, type, click option ok, all real | same, all real |
| Checkbox, radio | ok, real clicks | mouse click (real) ok; radio by script `click()` ok |
| Upload | `set_input_files` ok, page read file back (name, size, first bytes); change event not real | `DOM.setFileInputFiles` ok, file read back, change event real |
| Other-site frame | own target on the port; `frame_locator` text + upload ok, read back ok (`page.frames` lists it w/ url "") | **no session for it**: js-debug makes none, `Target.attachToTarget` flatten false refused ("only supports flatten=true"), flatten true => the proxy drops `sessionId` (answers come from the top page). Typing works by focusing the box before it + Tab + `Input.insertText`; script + **upload there: impossible** |
| Page `debugger;` (anti-bot scripts use it) | not tried (no debugger attached: nothing to pause it) | **pauses the page** (default + quiet options): a source tab `form:25:9` opens over the form, debug toolbar, status bar in debug color. `Debugger.resume` through the proxy ok; `Debugger.setSkipAllPauses` true => passes |
| What the user sees | nothing | floating debug toolbar over the editor tabs, Debug Console panel opens (on Greenhouse: full of red source-map errors), Run view badge 1. Quiet options (`suppressDebugToolbar` / `Statusbar` / `View` on `startDebugging`) do not hide the toolbar (Greenhouse run, focused window). Shots: `route2-local-before.png`, `route2-local-attached.png`, `route2-local-filled.png`, `gh-route2-attached-quiet.png` |
| Ending | quit | `vscode.debug.stopDebugging()` (all, or the parent) **closes the browser tab** - filled form lost (2 of 2, `route2-local-stopped.png`: only the paused source tab left). Stopping only the page session, or `workbench.action.debug.disconnect`, keeps it |
| Untrusted folder (Restricted Mode) | not tried | attach stops at VS Code's "Do you trust the authors of the files in this folder? Debugging executes build tasks and program code from your workspace" - no session until answered; Claude's panel is empty there too ([restricted.json](vscode-browser/restricted.json), `route2-restricted.png`). The launcher's window is trusted (`app-window.md` #r) |
| Security | port has no password: **any program on this computer** reaches every target - the browser tab, its frames, the **workbench itself** (`Runtime.evaluate` there runs, `globalThis.vscode` present = every command + the terminal = runs code), and once the Claude panel is open its webview + service worker (`route1-claude-open.png`). Needs a launch flag. Can't ship | proxy on 127.0.0.1, random 40-hex path handed only to the extension that asked; reaches the one tab, not the workbench. Any extension in the window can ask for one |

## Writes blocked + canary (route 2)

`app/apply/lab.py` rule: the canary page sends one write each way a page can w/o the user (xhr,
fetch keepalive, beacon, cross-site fetch, form post, worker, WebSocket, other-site frame + its
WebSocket) to a local listener; "received" = what arrived. Same tab, through the proxy.

| Level | Added | Received |
|---|---|---|
| off | - | all 9 |
| 1 | `Fetch` fails every non-read request before it leaves (a worker's POST is caught too), `Network.setBlockedURLs` ws/wss (new + old form both tried), service workers bypassed | frame, frame-ws, ws - **WebSockets not blocked** by `setBlockedURLs` through this proxy |
| 2 | + another site's frame document failed before it loads (it would be its own target, out of this `Fetch`'s reach) | ws |
| 3 | + inert `WebSocket` swapped in before the page's scripts (`Page.addScriptToEvaluateOnNewDocument`) | **none** (0 writes; stub saw the ws url). In-page only: a page script could reach a pristine one |

Form site itself got 0 writes in the local runs.

## Greenhouse - route 2, one public posting

`job-boards.greenhouse.io/<board>/jobs/<id>`, tenant B, open (job board answered 200), 2026-10-05,
level 3. Numbers: [gh-tenant-b.json](vscode-browser/gh-tenant-b.json) (board, id + employer name
scrubbed).

| Step | Result |
|---|---|
| Canary in the same tab first | received none - posting opened only then (the stage refuses otherwise) |
| Load | 0.8-0.9 s, `#first_name` present; 23 boxes listed (contact, phone country list, resume + cover letter files, 2 text + 4 Yes/No questions, 3 voluntary demographic lists, reCAPTCHA textarea) |
| First name | click + `Input.insertText` ok, focus confirmed, read back "Test" |
| Last name, email | set by script ok, read back right |
| Phone | key events ok, read back "5555550100" |
| Yes / No question (react-select) | click, type "No", click option w/ that text => shows "No" (`gh-route2-filled-tab.png`) |
| Resume | `DOM.setFileInputFiles` ok - and the page **at once POSTs the file** (`multipart/form-data`) to `grnhse-prod-jben-us-east-1.s3.amazonaws.com` = Greenhouse's storage, before Submit. Blocked here, so no file name shown. Same in Job Finder's own Chrome (3 of 3 employers): privacy rows split, `greenhouse.md` #What leaves the computer |
| Blocked on load | analytics POST (`c.spl.greenhouse.io`), reCAPTCHA Enterprise frame (`recaptcha.net`, other site, level 2). Form filled anyway; whether Submit passes the captcha w/ the frame blocked - unmeasured (never Submit) |
| Gotcha | page has `scroll-behavior: smooth`: coordinates read right after `scrollIntoView` miss the box (first run: first name, phone, Yes/No all empty). `behavior: 'instant'` fixes it |
| What the user sees | `gh-route2-filled.png`: form in the tab, debug toolbar on top, Debug Console below; Claude panel's "Browser connected" is Claude in Chrome, not this tab (`app-window.md`) |

## Recommendation

Route 1: never - one open port hands the whole window (commands, terminal, Claude's chat) to any
program on the computer.

Route 2 fills Greenhouse's own boxes + upload in the tab. Costs, all measured:
- user sees debug chrome (toolbar, Debug Console, Run badge); options don't hide it
- a page's `debugger;` freezes the form unless every attach sets `Debugger.setSkipAllPauses`
- the wrong stop closes the tab + loses the form; stop only the page session
- needs a trusted folder, else VS Code's trust dialog
- another site's frame: type by Tab only, no upload => an employer page embedding Greenhouse needs
  the embed form opened top-level (`recover` in `greenhouse.md` already does)
- WebSocket block is in-page only; a measure run must stay at level 3
- urlFilter must match one tab; two matching tabs => a picker

Job Finder's own Chrome has none of these. Keep filling there; if the owner wants it in the
window, Greenhouse only, off by default (plan-29g.9).

## Owner decision (plan-29g.8)

2026-10-05: build the Greenhouse trial, off by default; verify live on one real application before
anyone else gets it. Greenhouse = largest system on the owner's list (537 of 1,589 open rows;
Ashby 178, Lever 98, Workday 94). Built on the route-2 costs above: skip pauses on every attach,
scroll `instant`, stop only the page session (never stop all - closes the tab), urlFilter matching
exactly one tab, trusted folder required, embed forms opened top-level. Default Chrome path unchanged.

## Trial (plan-29g.9)

`uv run app/jobs.py apply-form fill <job> --in-window` - Greenhouse only (other systems refused in
one line), off by default; w/o the flag `fill` opens Chrome exactly as before. `job-apply` hard
limits unchanged: never Submit, a file only after the user's yes (`form.fill` decides, not the window).

- Tab = a holding page only this run knows: Python serves `http://127.0.0.1:<port>/jf-<32 hex>`,
  the window opens it (plain open request), then `attach-form` w/ that link as urlFilter. Never the
  posting's link: a Greenhouse posting is its own form page, often already open from Today => two
  matches => js-debug's picker. js-debug's filter drops scheme, trailing slash + `#hash`, keeps the
  query (bundle read, VS Code 1.140) - a fragment can't make a tab unique.
- `extension.js`: `attach-form` taken only for that loopback shape (`start.js` `ATTACH_REQUEST`);
  Restricted Mode => "untrusted"; picker shown anyway => closed after 15 s, "picker"; waits for the
  page session, asks `requestCDPProxy` for it, answers {session, proxy}.
- Python drives the tab over raw CDP ([cdp.py](../../apply/cdp.py), moved from the measure
  scripts): Playwright can't use the proxy (one page, no browser). `apply/window.py` `Page` +
  `Locator` cover only what `greenhouse.py` + `form.fill` call: click = instant scroll to the box's
  middle + real mouse events, typing = `Input.insertText`, file = `DOM.setFileInputFiles`.
  `Debugger.setSkipAllPauses` on attach + after each navigation.
- Done: `detach-form` => `disconnect {terminateDebuggee: false}` on the page session, then its
  parent - never stop all (closes the tab).
- Any failure: one plain line ending "run fill without --in-window to fill it in Chrome".

Tests (`uv run pytest -k in_window`): the adapter fills `app/tests/fixtures/dom/greenhouse-form.html`
(smooth scrolling, a `debugger;` line on input, react-select dropdown, checkbox list, file box) in
real headless Chrome over CDP, every answer read back off the page; w/o pause skipping the same
test hangs (checked). Two of its dropdowns empty themselves 800 ms after a pick (once / always): refilled + held, and
`FAIL ... fill it by hand` - w/o `greenhouse.holds` the second reads ok while the page shows it empty. Window side = fake extension: holding page, attach, detach, each refusal.

Owner's real run (plan-29g.18, tenant G): every dropdown reported ok, all empty on the page. Not
reproduced (plan-29g.20): `measure.py ghfill` = the shipped filler in a scratch window, writes
blocked, canary 0 - all 14 dropdowns ok, shown + still shown 8 s later ([gh-fill-tenant-g.json](vscode-browser/gh-fill-tenant-g.json));
same in headless + unfocused headful Chrome. Guard since: each answer read back off the page
2.5 s after filling (`form.recheck` + `greenhouse.holds`, Chrome path too), refilled once, else FAIL.

Unmeasured live, left to plan-29g.18 (one real application in the window): detach keeps the tab +
leaves no session; whether `internalConsoleOptions: "neverOpen"` + the suppress options now hide the
Debug Console + toolbar (above: options didn't); reCAPTCHA w/ the window's frame at Submit.
