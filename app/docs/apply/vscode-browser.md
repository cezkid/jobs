# Filling a form inside the Job Finder window - measured (plan-29g.7)

Can an application be filled in the window's own browser tab (VS Code Integrated Browser) instead
of Job Finder's own Chrome? Measurement only: nothing here ships, `app/apply/` + `app/launch.py`
untouched. Owner decides in plan-29g.8; trial bead plan-29g.9. Window + links: `app-window.md`.

Setup, 2026-10-05: scratch VS Code 1.140.0 (Electron 43.7.3, Chromium 150), Claude Code 2.1.289,
macOS 26.4.1 x86_64. Binary started directly (never `launch.py`, never `~/.vscode/argv.json`), own
`--user-data-dir` / `--extensions-dir` / `--shared-data-dir` under `$D = mktemp -d /tmp/jfv.XXXX`,
folder = program copy + demo + the window's own settings, throwaway browser storage. Dummy data
only (Test Person, `test.person@example.com`, 100-byte dummy PDF), never the user's; Submit never
clicked. Scripts: [measure.py](vscode-browser/measure.py) (stages setup, ext, route1 - refused unless
`JF_ALLOW_ROUTE1=1`, route2, gh, ghfill, ghupload, score, restricted, raw, multipage), [cdp.py](../../apply/cdp.py) (stdlib CDP client, now shipped for the trial), [formsite.py](vscode-browser/formsite.py)
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

## Ashby - route 2 (plan-nko.6)

`measure.py raw <link>`: any system `systems.for_url` knows; READY from it (Ashby `[data-field-path]`). Level 3 +
`lab.NAMED_READS` (`ApiJobPosting` query only, the owner's one exception - else no form, plan-nko.2). Canary in
the same tab first, then the application page. `debugger;` pauses: skip off once, each resumed in the handler,
cap 20, then skip on. One text box: click + `Input.insertText`. Dummy PDF by `DOM.setFileInputFiles`. Never Submit.
2 employers (tenants A + B), 2026-10-05, 3 page loads on `jobs.ashbyhq.com`. Numbers:
[ashby-tenant-a.json](vscode-browser/ashby-tenant-a.json), [ashby-tenant-b.json](vscode-browser/ashby-tenant-b.json)
(org, posting + question ids scrubbed).

Every system since 2026-10-06 (plan-k8n.1, `rawkit.py`, tested on local pages + every EXAMPLES link, no live
page): READY read as Playwright reads it - `:visible` (Oracle, iCIMS, ADP) = non-empty box + not
`visibility:hidden`, open shadow roots walked (SmartRecruiters `#first-name-input`; closed ones can't be).
Scrub per link: parse_url parts (any count - Paylocity 1), tenant host + its labels (Oracle pod, iCIMS
`careers-<tenant>`), path parts, query values; string values only, any case. Shared hosts
(`apply.workable.com` ...) kept. Org / tenant host / page title + `og:site_name` appended to
`.data/measure/tenants.txt`, as `apply-form measure` does. Text box + file box still found by
`document.querySelector`: inside a shadow root unmeasured.

| Step | A | B |
|---|---|---|
| Canary first | received none | received none |
| `READY` from navigate | 1.4-1.5 s (2 runs) | 1.6 s |
| Form | 9 fields (`[data-field-path]`) | 11 (incl. Education History, phone, consent radios) |
| Question read | `ApiJobPosting` passed (named read) | same |
| Blocked on load | `ApiOrganizationFromHostedJobsPageName` x2 | same + `ApiSetFormValue` x1 |
| `debugger;` pauses | 0 | 0 |
| Other-site frames | none (no iframe, no frame target, none blocked) - no captcha on the form before Submit | none |
| Name: click + `Input.insertText` | focused, read back "Test Applicant" | same |
| Sent on typing | `ApiSetFormValue` (blocked) - answers leave box by box, as in Chrome (`ashby.md`) | same |
| Dummy PDF chosen | `ApiCreateFileUploadHandle` POST at once (blocked); page shows the name + its own "failed to upload" toast | same |
| What the user sees | debug toolbar, Debug Console (red source-map line from Ashby's CDN), Run badge 1 - as Greenhouse | - |

Reading: Ashby has none of Greenhouse's frame or pause costs - no other-site frame to Tab into, no
`debugger;`, no captcha frame before Submit (2 of 2; captcha at Submit unmeasured). Same route-2 costs
otherwise (debug chrome, stop only the page session, trusted folder, one-tab urlFilter). Answers + file
leave before Submit, window or Chrome alike - privacy rows already say so. Owner decides (plan-nko.7).

## Lever - route 2 (plan-nko.13)

Same `measure.py raw` as Ashby, level 3, no named read (Lever's form is in the page). Box = `input[name=name]`,
file = hidden `#resume-upload-input`. 3 employers (tenants A-C; C picked for its Apply with LinkedIn row - plain
GET of 2 apply pages, 1 had it), 2026-10-05; page loads on `jobs.lever.co`: 3 navigations + 2 plain GETs = 5.
Numbers: [lever-tenant-a.json](vscode-browser/lever-tenant-a.json), [lever-tenant-b.json](vscode-browser/lever-tenant-b.json),
[lever-tenant-c.json](vscode-browser/lever-tenant-c.json) (org, posting + card ids scrubbed).

| Step | A | B | C |
|---|---|---|---|
| Canary first | received none | none | none |
| `READY` from navigate | 2.0 s | 0.8 s | 1.4 s |
| Boxes listed | 6 (standard boxes only) | 56 | 30 |
| `debugger;` pauses | 0 | 0 | 0 |
| hCaptcha on load | `js.hcaptcha.com/1/secure-api.js` + 2 enclave frames (`newassets.hcaptcha.com`, other site) - failed by the block before they loaded; 0 `checksiteconfig` (runs inside the frame; Chrome lab: ~10 POSTs/load, `lever.md`) | same | same |
| Cloudflare challenge | `cdn-cgi/challenge-platform/.../jsd` POST, 1 (blocked) + an empty 1x1 frame | none | none |
| Apply with LinkedIn | - | - | `platform.linkedin.com/in.js` + widget script load (reads); its frame = POST `linkedin.com/talentwidgets/apply-with-linkedin` (other site, failed). Row stays "Loading..." (`lever-route2-tab.png`) |
| Frame targets | none | none | none - every other-site frame failed before it became one |
| Name: click + `Input.insertText` | focused, read back "Test Applicant" | same | same |
| Dummy PDF chosen | `POST jobs.lever.co/parseResume` (multipart) at once (blocked); label "Couldn't auto-read resume." | same | same |
| Other writes | none while typing | none | none |

Readings:
- No `debugger;`, no frame needed to fill: every box + the file box is in the page.
- hCaptcha's frames load on the form, not only at Submit. Blocked here (level 3), the form still fills; the
  hidden `#hcaptchaSubmitBtn` is there 3 of 3. Whether hCaptcha passes at Submit in the window tab
  (frame unblocked, debugger attached) - unmeasured: never Submit. Greenhouse's reCAPTCHA frame same open question.
- "Couldn't auto-read resume." here = the block's doing (send failed), not Lever's verdict - as in Chrome
  (`lever.md` #Read back). File name shows in the file button (upper-case by CSS: `innerText` reads it upper).
- Resume leaves on choosing, window or Chrome alike; privacy row already says so.
- LinkedIn row: left alone either way (it signs in to LinkedIn); in the window it is one more other-site frame.

Route-2 costs otherwise as Greenhouse (debug chrome, stop only the page session, trusted folder, one-tab
urlFilter). Owner decides (plan-nko.14).

## JazzHR - route 2 (plan-k8n.4)

Same `measure.py raw`, level 3, no named read (JazzHR's form is one server-rendered page). Box =
`input[type=text]`, file = `input[type=file]`. 2 employers (tenants A, B; B picked for its Apply with LinkedIn
widget), 2026-10-06; page loads: 1 per host (each tenant its own host) = 2. Numbers:
[jazzhr-tenant-a.json](vscode-browser/jazzhr-tenant-a.json), [jazzhr-tenant-b.json](vscode-browser/jazzhr-tenant-b.json)
(host, ids + org scrubbed).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| `READY` from navigate | 0.8 s | 0.9 s |
| Boxes listed | 28 | 24 |
| `debugger;` pauses | 0 | 0 |
| reCAPTCHA v2 "Human Check" | `google.com/recaptcha/api.js` + `gstatic` script (reads), `grecaptcha` object; its anchor frame (other site) failed by the block | same |
| Human Check box (`.g-recaptcha`, scrolled to) | 440x78, its 304x78 frame shown + on top at the box's middle, frame document blocked => blank space, nothing to click (`jazzhr-route2-captcha.png`) | same |
| Apply with LinkedIn | - | `platform.linkedin.com` + `awliWidget` scripts (reads); its frame = POST `linkedin.com/talentwidgets/apply-with-linkedin` (other site, failed) |
| Cookie banner | "This website uses cookies..." (Allow / Reject all) over the page bottom | none |
| Frame targets | none | none - every other-site frame failed before it became one |
| Name: click + `Input.insertText` | focused, read back "Test Applicant" | same |
| Dummy PDF chosen | held in the box (`files[0]` = it), 0 writes | same |
| Other writes | none while typing | none |

Readings:
- No `debugger;`, no frame needed to fill: every box + the file box is in the page.
- Choosing the file sends nothing, window as Chrome (`jazzhr.md`); answers + file leave at Submit only.
- Human Check = the applicant's own click, never ours. With the block on (level 3) it is a blank space; whether it
  renders + takes the click in the window tab unblocked (debugger attached) - unmeasured: never measured w/o
  the block, never Submit. Greenhouse + Lever captchas same open question.
- LinkedIn row: left alone either way (it signs in to LinkedIn), as Lever C.
- Cookie banner: the employer's own, over the page bottom; name + file still filled + read back. User answers it.

Route-2 costs otherwise as Greenhouse (debug chrome, stop only the page session, trusted folder, one-tab
urlFilter). In `window.SYSTEMS` since the owner's yes 2026-10-06 (plan-k8n.5).

## Workable - route 2 (plan-k8n.7)

Same `measure.py raw`, level 3, no named read. Box = `input[name=firstname]`, file box = `input[type=file]` found,
never chosen (`JF_NO_FILE=1`: the upload goes to Workable's storage at once and, blocked, breaks the form -
`workable.md`). 2 employers (tenants A, B; A for its 3 dropdowns, B for its 16 radio questions - picked by 12
plain reads of form definitions, not page loads), 2026-10-06; page loads apply.workable.com: 4 (A x3: one rerun
after the landed link leaked the employer into `at` - scrubbed since, one w/ the widget probe; B x1). Numbers:
[workable-tenant-a.json](vscode-browser/workable-tenant-a.json), [workable-tenant-b.json](vscode-browser/workable-tenant-b.json)
(host path, ids + org scrubbed).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| `READY` from navigate | 2.3 s (earlier loads 2.8, 2.1 s) | 2.3 s |
| Boxes listed | 24 | 74 |
| `debugger;` pauses | 0 | 0 |
| Frames | none (1st load of 3: one 1x1 empty frame) | none |
| Cloudflare `jsd/oneshot` POST on load | blocked on the 1st load of 3, none on the last 2 | none |
| Captcha | Turnstile script (`challenges.cloudflare.com/turnstile/v0/api.js`, `turnstile` object), no Turnstile frame on load; no reCAPTCHA / hCaptcha | same |
| Widgets | 2 radio groups (4 `[role=radio]`), 3 `[role=combobox]` lists, each in its `[data-ui]` wrapper | 16 radio groups (53 `[role=radio]`), no lists |
| Cookie dialog | `[data-ui=cookie-consent]` `role=dialog` `aria-modal=true`, "This website uses cookies..." (Accept all / Decline all / Cookies settings), grey overlay over the whole form on load; on top at each list's middle: the dialog, 3 of 3 | same dialog |
| Name: click + `Input.insertText` | not focused (the click met the dialog), read back "" | same |
| Name: focused by script + `Input.insertText` | focused, read back "Test Applicant" | same |
| Other writes | none while typing | none |

Readings:
- The cookie dialog covers the form: a person's click lands on it. Likely the "something sits over the box" that
  made Chrome's plain clicks time out (`workable.md`, 8 of 8, 2026-10-03) - likely: not measured in Chrome.
- The filler still fills under it, window as Chrome: typing = focus by script + `Input.insertText` (as
  `Locator.fill`), lists opened by Down on the focused box, radios by Space on the focused `[role=radio]`, an
  option's click dispatched on it - the paths `workable.py` already takes when a click times out.
- File: never chosen here. Its upload in the tab - unmeasured; checked on the owner's real application (plan-k8n.9).
- Turnstile script loads but shows nothing on load; at Submit - unmeasured (never Submit).
- Cookie dialog = the employer's own; the user answers it.

Route-2 costs otherwise as Greenhouse (debug chrome, stop only the page session, trusted folder, one-tab
urlFilter). In `window.SYSTEMS` since the owner's yes 2026-10-06 (plan-k8n.8).

## BambooHR - route 2 (plan-k8n.10)

Same `measure.py raw`, level 3, no named read. The form opens only after "Apply for This Job": `raw` now clicks a
system's `APPLY` button once (real click) before reading `READY`. Box = `#firstName`, file = `input[type=file]`
(resume), dummy PDF chosen. 2 employers (tenants A, B; each its own host; B = another open posting of the employer
on line 2 of the links, picked by 3 plain reads - its job list + 2 form definitions), 2026-10-06; page loads: 1
per host = 2. Numbers: [bamboohr-tenant-a.json](vscode-browser/bamboohr-tenant-a.json),
[bamboohr-tenant-b.json](vscode-browser/bamboohr-tenant-b.json) (host, ids + org scrubbed).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| Apply button found, from navigate | 7.4 s, real click ok | 4.3 s, ok |
| `READY` from navigate (incl. the 2 s before the click) | 10.2 s | 7.4 s |
| Boxes listed | 26 (honeypot `nickname_hpcsaf` incl.) | 18 |
| Widgets | 3 radio groups (7 native radios), Fabric lists as native `select` + toggle button, no `[role=combobox]` | no radios |
| `debugger;` pauses | 0 | 0 |
| reCAPTCHA | `google.com/recaptcha/api.js` + `gstatic` script (reads), `grecaptcha` object, `g-recaptcha-response` box; anchor frame 304x78 (v2 tick-box size) shown, its document failed by the block (other site) | same |
| Frame targets | none | none |
| Page load write | `POST api.rollbar.com/api/1/item/` (BambooHR's error report, as in Chrome) - failed | same |
| Name: click + `Input.insertText` | focused, read back "Test Applicant" | same |
| Dummy PDF chosen | sent at once: `POST <host>/ajax/files/attachTemporary.php` (multipart) - failed; page: banner "Whoops, something on our side prevented your file from uploading. Please give it another try." + "Please try uploading again" in the resume block, "No file selected" (`bamboohr-route2-tab.png`) | same request, file not held |
| Other writes | none while typing | none |

Readings:
- Every box + the file box is in the page; no `debugger;`, no frame needed to fill.
- File leaves on choice, window as Chrome (`bamboohr.md`). Blocked here, so the page showed its own failure words -
  the `unknown_error` banner `put_file` reads (FAIL with the page's words); an unblocked upload in the tab -
  unmeasured (the owner's real application).
- reCAPTCHA frame is tick-box sized but blank under the block; Chrome tries saw nothing to tick (`bamboohr.md`).
  Whether it shows + takes a click unblocked, and what it checks at Submit - unmeasured (never Submit), same open
  question as JazzHR, Greenhouse, Lever.
- Adapter gaps: none. The parity test (`test_in_window_fills_bamboohr_as_playwright_does`, saved form fixture,
  Playwright vs `window.Page` in one headless Chrome) passes: same report, same read-back, a second fill changes
  nothing - every call `bamboohr.fill` + `holds` + `form.fill_page` make already exists in `window.py`
  (`check(force=)`, xpath, `get_by_role`, `evaluate_all`).

Route-2 costs otherwise as Greenhouse (debug chrome, stop only the page session, trusted folder, one-tab
urlFilter). `window.SYSTEMS` unchanged; owner decides (plan-k8n.11).

## Oracle - route 2 (plan-k8n.16)

Same `measure.py raw`, level 3, no named read. Box = the start box's email box (`input[name^=primary-email]`, never
the honeypot text box); no file box on the start box. 2 employers (tenants A, B; own hosts, posted records on the
open list, none page-loaded earlier in the bead), 2026-10-06; page loads: 1 per host = 2. Numbers:
[oracle-tenant-a.json](vscode-browser/oracle-tenant-a.json), [oracle-tenant-b.json](vscode-browser/oracle-tenant-b.json)
(host, site, ids scrubbed).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| `READY` from navigate | 3.8 s | 3.8 s |
| Boxes in the page / shown (`READY`) | 4 (assistant box, email, honeypot, terms tick; email id number swaps with the trap's, as in Chrome) / 2 | 4 / 2 |
| `debugger;` pauses | 0 | 0 |
| Frames / frame targets | none / none | none / none |
| Captcha | none on load (no hCaptcha / reCAPTCHA / Turnstile script or object) | none |
| Cookie banner | "This website collects cookies ..." (no `aria-modal`) | "Cookie Policy ... ACCEPT" |
| Email: click + `Input.insertText` | not focused, read back "" - what took the click: unmeasured (banner likely) | focused, read back ok |
| Email: focused by script + `Input.insertText` | focused, read back ok | - |
| Page writes | none failed after load (visit tracking seen on tenant B in Chrome, 2026-10-03: not here) | none |

Readings:
- Start box fills in the tab: typing = focus by script + `Input.insertText` (as `Locator.fill`), whatever sits over the
  box. No frame, no pause, no captcha on these 2 (Chrome saw an invisible hCaptcha on 2 of 7, `oracle.md`).
- Cookie banner = the employer's own; the user answers it.
- Pages after Next: unmeasured (never Next) - the owner's real application (plan-6oq.6.6, .6.8). Oracle's flow is
  multi-page, so whether it fills in the window waits on the multi-page decision (plan-k8n.20).

## iCIMS - route 2 (plan-k8n.16)

Same `measure.py raw`, level 3. The start box sits in the page's own same-site frame (`?in_iframe=1`): `raw` now
reaches its email box through the top page's `contentDocument`, focused by script + `Input.insertText`. 2 employers
(tenants A, B; `careers-<co>` hosts on the open list, none page-loaded earlier in the bead), 2026-10-06; page loads:
3 (A x2: a shell slip loaded A's link again - rerun kept out of the numbers; B x1). Numbers: [icims-tenant-a.json](vscode-browser/icims-tenant-a.json),
[icims-tenant-b.json](vscode-browser/icims-tenant-b.json) (host, slug, ids scrubbed).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| `READY` from navigate (the frame) | 2.7 s | 0.9 s |
| Same-site frame | 1, "iCIMS Content iFrame" 720x586, shown | 1, same title, 980x989, shown |
| **Its own frame target?** | **no** - `Target.getTargets` lists no iframe; js-debug made no session for it | **no** |
| Email box in the frame | found through `contentDocument` | found; frame holds 5 boxes, the privacy tick, an `h-captcha` mark |
| Email: focused by script + `Input.insertText` | focused, read back ok | same |
| `debugger;` pauses | 0 | 0 |
| hCaptcha | 2 `newassets.hcaptcha.com/.../hcaptcha.html` frames (other site) - failed before load by the block | same |
| Page writes on load (failed) | Google Analytics `g/collect` x2 + DoubleClick ping, Snowplow (`c.talentplatform.us`) | GA x2, Snowplow |

Readings:
- Frame target answered: the same-site `?in_iframe=1` frame runs in the page's own process, no target of its own, so
  the page's proxy reaches it (unlike another site's frame, where fill + upload are impossible - Local form). The
  start box fills in the tab. Privacy tick on B (A's frame marks unread: a script slip, fixed before B's run).
- hCaptcha frames are another site's: blank under the block; unblocked, whether its check shows and what it asks at
  Next - unmeasured (never Next), same open question as Oracle and BambooHR's reCAPTCHA.
- Upload in the frame (`DOM.setFileInputFiles` on a frame element from the top session): unmeasured - no file box
  on the start box; pages after Next unmeasured (the owner's real application, plan-6oq.6.6, .6.8).
- `window.SYSTEMS` unchanged: iCIMS is multi-page (start box -> Next -> account), so it waits on plan-k8n.20.

Route-2 costs otherwise as Greenhouse (debug chrome, stop only the page session, trusted folder, one-tab urlFilter).

## SmartRecruiters - route 2 (plan-k8n.17)

Same `measure.py raw`, level 3, no named read. Boxes now looked up through open shadow roots (name box
`#first-name-input`; resume = the file box after it, `smartrecruiters.FILES`, never the parsing box above).
Link = posting + `?oga=true` (302 to the form app, as the filler opens it). 2 employers (tenants A, B; record
active + on the company's own list), 2026-10-06; page loads: 2 (one host for every employer; bead total 6 of 10).
Numbers: [smartrecruiters-tenant-a.json](vscode-browser/smartrecruiters-tenant-a.json),
[smartrecruiters-tenant-b.json](vscode-browser/smartrecruiters-tenant-b.json) (host, company, ids scrubbed - the
shared host reads `jobs.<org>`: an earlier run recorded it as a tenant line, kept).

| Step | A | B |
|---|---|---|
| Canary first | received none | none |
| 302 to the form app | yes | yes |
| `READY` (`#first-name-input`) | **never** (40 s cap) | **never** |
| What the tab got instead | **DataDome Device Check**: one other-site frame `geo.captcha-delivery.com/interstitial/` 828x465 in place of the form app - its document failed before load by the block => blank tab (`smartrecruiters-route2-tab.png`) | same |
| Boxes / file boxes | 0 / 0 (nothing typed, no file chosen) | 0 / 0 |
| Page writes (failed) | Cloudflare challenge `POST /cdn-cgi/challenge-platform/.../jsd/oneshot/...` | none past the frame |
| `debugger;` pauses | 0 | 0 |
| Frame targets | none | none |

Same posting kind in Job Finder's own Chrome (apply-form measure, same block): headed - the form app drew
(DataDome's `api-js.datadome.co/js/` POST failed, no device check); headless - the same device check
(2026-10-06, `smartrecruiters.md`). So the window tab reads to DataDome as headless Chrome does: flagged on the
first load, before any box exists.

Readings:
- Under the block the form never renders in the tab (2 of 2): nothing to fill, nothing to read back. Every
  page-1 kind (`holds`, `put_file`, City, phone country) stays measured in Chrome + fixtures only.
- Unblocked, the user would get DataDome's device check first - whether it passes by itself, asks for a slider
  puzzle, or blocks the tab: unmeasured (its frame is another site's: the block fails it, and Claude couldn't
  reach into it anyway - Local form, other-site frame). Why the tab is flagged (Electron build, debugger
  attached, fresh storage): unmeasured.
- Screening after Next = the user's own tab (`smartrecruiters.md` Pages) -> in the window it needs the
  multi-page decision (F4, plan-k8n.20).
- `window.SYSTEMS` unchanged: SmartRecruiters stays in Job Finder's own Chrome.

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
window, Greenhouse, Ashby, Lever, JazzHR + Workable only, off by default (plan-29g.9, Ashby plan-nko.8, Lever
plan-nko.15, JazzHR plan-k8n.5, Workable plan-k8n.8).

## Owner decision (plan-29g.8)

2026-10-05: build the Greenhouse trial, off by default; verify live on one real application before
anyone else gets it. Greenhouse = largest system on the owner's list (537 of 1,589 open rows;
Ashby 178, Lever 98, Workday 94). Built on the route-2 costs above: skip pauses on every attach,
scroll `instant`, stop only the page session (never stop all - closes the tab), urlFilter matching
exactly one tab, trusted folder required, embed forms opened top-level. Default Chrome path unchanged.

2026-10-06 (plan-k8n.5): JazzHR added - one page, no frames, no `debugger;` pauses, choosing the file sends
nothing, adapter parity passes (plan-k8n.4). Gap: Human Check at Submit unmeasured unblocked, as Lever's
hCaptcha => `AT_SUBMIT` note + Chrome fallback. JazzHR = 27 open jobs / 13 employers on the owner's list.

2026-10-06 (plan-k8n.8): Workable added - one page, no frames, no `debugger;` pauses, adapter parity passes
(plan-k8n.7); the employer's cookie dialog covers the form, filler fills under it as in Chrome. Gaps: Turnstile at
Submit + the resume upload in the tab unmeasured (upload goes to Workable's storage at once; checked on the owner's
real application, plan-k8n.9) => `AT_SUBMIT` note + Chrome fallback. Workable = 46 open jobs / 28 employers on the
owner's list.

## Trial (plan-29g.9)

`uv run app/jobs.py apply-form fill <job> --in-window` - Greenhouse, Ashby, Lever, JazzHR + Workable only (owner's yes
for Ashby 2026-10-05, plan-nko.7, Lever plan-nko.14, JazzHR 2026-10-06 plan-k8n.5, Workable 2026-10-06 plan-k8n.8; other systems refused in one line), off by default; w/o the flag `fill` opens Chrome exactly as before. `job-apply` hard
limits unchanged: never Submit, a file only after the user's yes (`form.fill` decides, not the window).
Multi-page form (`PER_PAGE`, `form.fill` passes `match`) refused by `window.page_at` before any tab opens, one line
ending in the Chrome way: a fresh tab is page 1 again, the user's place lost (plan-k8n.2, 2026-10-06; keep-place measured: "Multi-page (keep the user's place)" below, plan-k8n.12).

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
  `Locator` cover only what `greenhouse.py`, `ashby.py`, `lever.py`, `jazzhr.py`, `workable.py` + `form.fill` call: click = instant scroll to the box's
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
Ashby (plan-nko.8, 2026-10-05): `ashby.fill` + `holds` + `form.fill_page` on `fixtures/dom/ashby-form.html`
through Playwright AND `window.Page` (same headless Chrome build): same report, same read-back (Yes / No
pressed late, radios ticked late, second click clears, lists, place box, file name), a second fill
changes nothing; the dropping list = `FAIL ... fill it by hand` in both. Added to the adapter:
`get_by_role` (button / option + `[role=X]`, accessible name = aria-labelledby, aria-label, value,
text; a file box is a button, as Playwright), `locator(sel, has_text=)` (pattern = Python's source
+ i/s/m as a JS RegExp, tested on the element's whole text), `is_checked`; each lookup's count +
texts checked against Playwright's on that page. Unmeasured: Ashby filled live in the window tab.
Lever (plan-nko.15, 2026-10-05): `lever.fill` + `holds` + `form.fill_page` on `fixtures/lever/tenant-a.html`
(saved live form) + a stand-in for Lever's own scripts (place search answers 300 ms after typing, pick =
town in the box + `#selected-location`; resume verdict 500 ms after choosing) through Playwright AND
`window.Page`: same report, same read-back (radios, ticks, lists, text, place + Lever's record, file + verdict),
a second fill changes nothing, signature left to the applicant in both. Before: `ids_on_page` passes a 3rd
arg => TypeError at the end of every fill. Added: `eval_on_selector_all(sel, fn, arg)`, `Locator.all()`,
`filter(visible=)`, `select_option(label=)` (by `option.label`, input + change, as Playwright); shown =
Playwright's rule (style visible + a box with width and height; was any rect, 0x0 counted), each checked
against Playwright's on that page. The fill says hCaptcha at Submit is untested in the window (`AT_SUBMIT`).
Unmeasured: Lever filled live in the window tab; hCaptcha at Submit there.
JazzHR (plan-k8n.4, 2026-10-06; in `--in-window` since the owner's yes, plan-k8n.5): `jazzhr.fill` + `holds` +
`form.fill_page` on `fixtures/jazzhr/tenant-b.html` (saved live form: checkbox groups, upper-case YES / NO
lists) + a stand-in for "Attach resume" (swaps paste / attach for the file box) through Playwright AND
`window.Page`: same report, same read-back (boxes, lists as the page writes them, ticks, file, file box shown),
a second fill changes nothing, attestation tick left to the applicant in both. Added: `Locator.is_visible()`
(no wait, nothing there = False, Playwright's shown rule), `select_option(value=)` (Playwright's signature:
value or `label=`), each checked against Playwright's on that page. The fill says the Human Check at Submit is
untested in the window (`AT_SUBMIT`). Unmeasured: JazzHR filled live in the window tab; Human Check unblocked there.
Workable (plan-k8n.7, 2026-10-06; in `--in-window` since the owner's yes, plan-k8n.8): `workable.fill` + `holds` +
`form.fill_page` on `fixtures/dom/workable-form.html` (hand-built from measured widgets: radios, ticks, lists, the
resume box + a storage stand-in) + the cookie dialog as measured over the whole form, through Playwright AND
`window.Page`: same report, same read-back (boxes, `[role=radio]` picks, ticks, list picks, stored file's name), a
second fill changes nothing. Not a saved live page: Workable draws its form by script, a saved copy has no
behaviour. Under the dialog a plain click times out in both, and the filler falls to keyboard / dispatched paths.
Added: `click(force=)` + Playwright's hit check (waits until nothing else sits on the box's middle, else
TimeoutError; force clicks whatever is on top - before, a covered click landed on the overlay silently),
`dispatch_event` (MouseEvent etc., bubbles + cancelable + composed, as Playwright), `page.keyboard.press`,
ArrowDown + Space by name, `page.evaluate` (a function called w/ its arg, else evaluated), `:visible` closing a
selector part; each checked against Playwright's on that page. The fill says Turnstile at Submit + the resume upload
are untested in the window (`AT_SUBMIT`). Unmeasured: Workable filled live in the window tab; its upload + Turnstile there.
Generic reader + the rest of the fillers' calls (plan-k8n.14, 2026-10-06; `window.SYSTEMS` unchanged):
`fixtures/dom/frames-shadow.html` (same-site frame w/ a list, another site's frame, open + closed shadow roots,
`.form-group`, xpath shapes) through Playwright AND `window.Page` - `dom.snapshot` equal, `dom.fill` same reports +
read-back (a list clicked inside the frame, a resume chosen in a shadow root), tests `test_in_window_parity_*`.
Added: selectors ported from Playwright's injected script - CSS, text, role + label look inside open shadow
roots (combinators, comma lists in page order, `:scope`, `:visible` anywhere in a part), `xpath=` / `//`,
`get_by_text(exact=)`, `get_by_label`, `.last` / `nth(-1)`, `filter(has=, has_text=)`; `page.frames` +
`main_frame` + `frame.evaluate` / `locator` (a frame inside = Chrome's isolated world: its page, never its
scripts' globals; clicks offset by the frame's box); `evaluate_handle` + `JSHandle` / `ElementHandle`
(handles let go after each fill); `page.context.new_cdp_session` (`dom.closed_shadow`); `goto(wait_until=)`;
`press("ControlOrMeta+a")` (held Control / Alt / Meta types nothing, as Playwright; macOS editing commands:
Meta+A only - Playwright maps ~100, e.g. Control+B = move back); `check` / `uncheck(force=)`; `type(delay=)`.
Measured (headless Chrome 154): Chrome's frame tree leaves out another site's frame (own process) -
`Target.getTargets` names it (url + parent), listed after its parent's other frames; its page request starts
in the tab + ends unreported there, so networkidle drops requests of frames gone from the tree. Gaps:
another site's frame can't be read (dom never reads it); unmeasured whether js-debug's proxy passes
`Page.getFrameTree`, `Page.createIsolatedWorld`, `DOM.getFrameOwner`, `Target.getTargets` (frames then = the
main frame only).

Owner's real run (plan-29g.18, tenant G): every dropdown reported ok; owner: "some fields were not filled", picked Dropdowns. Not
reproduced (plan-29g.20; plan-29g.24 adds upload success, MyGreenhouse sign-in + clicking around, `greenhouse.md` #Widgets): `measure.py ghfill` = the shipped filler in a scratch window, writes
blocked, canary 0 - all 14 dropdowns ok, shown + still shown 8 s later ([gh-fill-tenant-g.json](vscode-browser/gh-fill-tenant-g.json));
same in headless + unfocused headful Chrome. Guard since: each answer read back off the page
2.5 s after filling (`form.recheck` + `greenhouse.holds`, Chrome path too), refilled once, else FAIL.

Unmeasured live, left to plan-29g.18 (one real application in the window): detach keeps the tab +
leaves no session; whether `internalConsoleOptions: "neverOpen"` + the suppress options now hide the
Debug Console + toolbar (above: options didn't). reCAPTCHA at Submit: passed, after an email code (below).

## Email code after Submit (plan-29g.21)

Owner's run (plan-29g.18, job 72, tenant G): after Submit, Greenhouse emailed a security code; the
application went through once it was pasted. Owner's Chrome-filled Greenhouse application the day
before (job 1069, another employer): no code. One sample each way, two employers - hint only.

When Greenhouse asks - its help page [Invisible reCAPTCHA](https://support.greenhouse.io/hc/en-us/articles/115005448066)
(updated 2026-03-02; vendor doc): invisible reCAPTCHA on every job board (careers page options 1-4)
scores "activity on a job post, like mouse movements and typing patterns"; "depending on your spam
sensitivity setting and the user's score, a user may be asked to verify their email before submitting
their application". Setting = per job board, picked by the employer; stricter = higher score needed.
=> same person, same browser: code at one employer, none at another. Not published: levels, cutoffs,
what else feeds the score.

Score signal w/o Submit (`measure.py score`, [recaptcha-score.json](vscode-browser/recaptcha-score.json),
2026-10-05): Google's public v3 demo page (`recaptcha-demo.appspot.com`), no input, 3 samples each.

| Where | Score |
|---|---|
| Window tab opened plain (no debugger) | 0.9, 0.9, 0.9 (read off window-only screenshots) |
| Window tab w/ debugger on, as `fill --in-window` (holding page, attach, skip pauses, navigate) | 0.9, 0.9, 0.9 |
| Chrome started as Job Finder's own (fixed port, fresh profile) | 0.9, 0.9, 0.9 |

Window page sees: user agent `Code/1.140.0 Chrome/150.0.7871.250 Electron/43.7.3`, brands
`Chromium 150` only (no "Google Chrome"), `navigator.languages` 35 entries (Chrome: 2),
`window.__vscode_helpers`, webdriver false. None lowered the demo score. Limits: demo key, not
Greenhouse's Enterprise key (per-site model); the demo says its score reflects nothing; no filling
scored - the real form also scores the fill's own input (window: `Input.insertText`, no key events,
clicks jump to the box; Chrome path's Playwright `fill` sends no key events either); fresh profiles,
no Google sign-in. Gotcha: attached to the demo's https tab directly, js-debug made no page session
(3 of 3, exact link + glob) - the trial attaches to its loopback holding page, unaffected.

Reading: the window's browser is not shown to lower the score; the employer's own setting alone
explains a code at one employer. Roll-out cost: any Greenhouse application may ask for a code,
window or Chrome - one paste from their email, not a failure. `job-apply` step 5 says so before
Submit. plan-29g.23 records whether the next window application asks again.

## Upload wait (plan-29g.25)

Owner's application (plan-29g.23, `fill --in-window`, job board link): resume `ASK upload not
confirmed on page`, the page's own red line "Cannot read properties of undefined (reading 'uploadFile')"
under Resume. Their own attach after it: name shown, red line stayed.

Cause (Greenhouse's public job-board script, read 2026-10-05): the file box uploads through
`uploaders[<box>]`, filled only when the page's own request for the storage form answers (`GET
boards.greenhouse.io/uncacheable_attributes/presigned_fields`, sent after the page hydrates). File
chosen before that = that error, choice cleared. Name shown only after the POST to storage returns 2xx
=> name = file stored. A later upload never clears the error line.

Old wait: `networkidle` counted the page's list of finished requests (misses one still out, stops at
250) + ran only on a redirected board (`recover`); a plain job-board link chose the file right at `READY`.

Fix: `window.Page` tracks requests in flight off the tab's own Network events (js-debug passes them on
once `JsDebug.subscribe` asks; adds to what the block asked for); idle = loaded + none out + 500 ms quiet.
`greenhouse.put_file` (both paths; Chrome = Playwright's own networkidle) waits for it (15 s cap - a page
that keeps polling goes on, the read-back decides), chooses, reads back: name -> `ok`; the page's
`uploadFile` line -> `FAIL ... fill again (it reloads the page), or reload it and attach the file by hand`;
neither in 20 s -> `ASK`.

Measured: `measure.py ghupload`, one public posting (tenant H), level-3 block + canary (0 received),
dummy PDF, storage POST + its preflight answered inside the tab - nothing left the computer, never Submit.
2 runs, 2026-10-05, macOS 26.4.1; run 2 = [gh-upload-tenant-h.json](vscode-browser/gh-upload-tenant-h.json).
ms from navigate:

| Plain load | Run 1 | Run 2 |
|---|---|---|
| page loaded (`readyState` complete; 1 locale file still out) | 749 | 374 |
| `READY` (`#first_name`) | 826 | 406 |
| storage-form request out / answered | 990 / 1051 | 487 / 647 |
| shipped `put_file` | chose after it answered, no error; stub answered POST, no name (below) | `ok` in 988 ms, name, no error |

Storage-form request held 5 s (the owner's case made certain):

| Step | Result |
|---|---|
| chosen 0.1-0.3 s after the request went out | page's own `uploadFile` line, no name (2 of 2) |
| idle wait | returned 0.5 s after the request answered (2 of 2) |
| same file chosen again (as a person re-picking it) | nothing: no request, no progress, line stays (2 of 2) - Chrome fires no change for an identical choice |
| copy under another name chosen | stored, name in 263 ms, red line stays (run 2) |

Gotcha: a POST answered by `Fetch.fulfillRequest` at request stage sends no upload progress; the page
shows the name only at progress 100 -> run 1 stuck on its progress bar (`ASK`). Run 2 reports progress
once the answered POST loads, as a real upload does (`XHR_PROGRESS`).

Reading: the request goes out 0.1-0.2 s after `READY` -> files first at `READY` (the fill's order)
raced it; the wait costs ~1 s. After the error, re-picking the same PDF does nothing and the red line
stays for the tab -> reload is the clean way; a fresh fill reloads the page and now waits.
Owner's Submit check (blank Last Name on a live posting): not run - the loop's permission check refused
clicking Submit on a live employer page; owner decides (plan-29g.25.1).

## Multi-page (keep the user's place) (plan-k8n.12)

Problem: `window.page_at` opens a fresh holding-page tab + loads page 1 every run => after the user
clicks Next, a second fill starts over. Measured 2026-10-06, local form only (`formsite.py` `/mp/1`:
Next -> page 2 on the same site, on another site = another process, or drawn in place by pushState),
0 employer page loads. Page 1 + 2 run a `debugger;` line every second and report how long it held
(stand-in for a site's own debugger). Next clicked by the page's own timer = the user's click; no
client of ours sends it. Setup: scratch VS Code 1.140.0, Claude Code 2.1.292, macOS 26.4.1 x86_64.
Stage `multipage` in [measure.py](vscode-browser/measure.py); numbers:
[multipage-local.json](vscode-browser/multipage-local.json); shots `.data/probe-shots/form/mp-*.png`.

Options: (a) the extension keeps the page's debug session after a fill run, no client attached while
the user works, the next run asks its proxy again (`debugSessions` + `requestCDPProxy` already in
`app/vscode/extension.js`); (b) attach by the tab's own https link - dead (`start.js` takes only the
loopback holding page; a direct https attach made no page session 3 of 3); (c) one fill process stays
attached across pages: sees the navigation, skips pauses again, fills the new page.

Base fact: `Debugger.setSkipAllPauses` does NOT survive a new page (same site too, run 1) - set again
after each load. A page drawn in place keeps it.

| | (a) session kept, no client | (c) one process attached |
|---|---|---|
| place kept - same site | session + proxy survive (same proxy, same 2 sessions); page 2 filled after resume | yes, page 2 filled, read back |
| place kept - other site | same as same site | yes; `Page.frameNavigated` still arrives |
| place kept - in place | yes, page 2 filled | yes (`Page.navigatedWithinDocument`) |
| pauses while idle | new page: FROZEN on its `debugger;` (0 ticks in 8 s, same + other site); VS Code opens a JS source tab over the form at the paused line (`mp-a-same-idle-page2.png`); `Runtime.evaluate` hangs until `Debugger.resume`. In place: none (7 ticks, 0 ms held) | none: every tick on page 2 held 0 ms (all 3 ways); the handler re-skips on each main-frame navigation + resumes any pause (0 needed) |
| VS Code "Deactivate breakpoints" on while kept | no help: page 2 froze the same (same + other site) | - |
| debug toolbar between pages | shown (floating over the tab bar, Pause button, Run and Debug badge 1) | shown, same (`mp-c-same-page2.png`); today's detach removes it (`mp-base-detached.png`) |
| user closes the tab | both sessions end; proxy request -> nothing | socket closes ("Connection is closed"), sessions end |
| window reload | sessions gone, tab kept (same label), proxy -> nothing | same; socket closed |
| fresh attach after reload (local http link) | 2 sessions, page paused at once (evaluate hung 5 s); run 1: 0 sessions. Real https link: no page session 3 of 3 (above) | same |

Also seen: (a) after resume + skip, 0 ticks for 6 s while the source tab covered the form - likely
the hidden tab's timers held; unmeasured.

Recommendation: (c). It is the only way that kept the place on a new page without freezing it;
(a) works only for forms drawn in place and freezes any new page that runs `debugger;` (anti-bot scripts use it; 0
on the systems measured above so far) - the user would face a stopped form + a code tab. Costs of (c), all unmeasured live:
the fill process must stay alive while the user reads + clicks Next (end on tab closed, window
reload, Submit page, or a time limit); the debug toolbar stays visible the whole time (VS Code's
`debug.toolBarLocation: hidden` may hide it - untested); a page whose script runs `debugger;` before
the navigation event lands pauses until the handler resumes it (0 of 3 here). Reload or closed tab
= place lost in both: say so plainly, Chrome way as today. Owner decides: plan-k8n.13.
