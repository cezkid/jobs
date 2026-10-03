# Application systems - how Job Finder fills them, and how to add one

Each hiring system lays its form out its own way; questions are much the same (contact, resume
upload, work permit, a few employer ones). Shared logic in one place, each system's quirks in a
small plug-in.

| System | Link looks like | Route | Facts |
|---|---|---|---|
| Workday | `<co>.wd<N>.myworkdayjobs.com` | `apply` script, run by the Claude Chrome extension (sign-in wall, multi-page) | `workday.md` |
| Ashby | `jobs.ashbyhq.com/<co>/<id>` | `apply-form`, Job Finder's own Chrome | `ashby.md` |
| Greenhouse | `job-boards.greenhouse.io/<co>/jobs/<id>` (also `boards.`, `.eu.`, `embed/job_app?for=<co>&token=<id>`) | `apply-form`, Job Finder's own Chrome | `greenhouse.md` |
| Lever | `jobs.lever.co/<co>/<id>` (also `jobs.eu.`, `/apply`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions read off the public `/apply` page | `lever.md` |
| UKG Pro Recruiting | `recruiting<N>.ultipro.com/<tenant>/JobBoard/<board>/OpportunityDetail?opportunityId=<id>` | `apply-form`, Job Finder's own Chrome; user signs in first, questions read off the signed-in form | `ukg.md` |

Not yet: SmartRecruiters, iCIMS, Workable; Greenhouse embedded on an
employer's own page (`?gh_jid=` - board name unknown). Where the form's questions were read ahead
(Workable, Recruitee - [answers.md](answers.md)), `apply-form prepare` drafts from them and
`apply-form paste` writes `Application answers.md` to paste from. Otherwise `prepare` says so
plainly -> user gets tailored PDF + answers to paste.

## The pieces (`app/apply/`)

| File | Job | Changes when a system is added? |
|---|---|---|
| `questions.py` | shared question shape (`KINDS`, `KEYS`), answers from resume + setup, answers file | only if the system asks something no kind covers |
| `browser.py` | Job Finder's Chrome (own profile in `.data/`, no automation flag), reused across applications | no |
| `form.py` | the `apply-form prepare / fill` steps, report, never Submit | no |
| `dom.py` | any form page read as plain HTML (frames, open shadow roots), stable hooks, generic fill | only if the page has a control it can't read |
| `lab.py` | `apply-form measure` (developers): throwaway Chrome, every write blocked, canary first | no |
| `systems/__init__.py` | picks the system from the link | one line: add to `SYSTEMS` |
| `systems/<name>.py` | read the form's questions; type an answer into its widgets | new file |

## Add a system

In order - each step's output feeds the next:

1. **Measure** - `uv run app/jobs.py apply-form measure "<link>" [--click "Apply" ...]` on a live
   posting. Writes `.data/measure/<host>-<time>.json`: every control (`dom.snapshot`), ids that
   changed between two loads (made per load - never a hook), JSON the page fetched (first 2 KB
   each: where the form definition lives), every blocked write. Also: public job-board API?
   (Ashby, Greenhouse, Lever have one.) Never generated class names like `_active_1svni_57`.
2. **Facts doc** `docs/<name>.md`: widgets table + tenant notes, measured + dated, how many
   postings / tenants, like `ashby.md`. Unmeasured = say so.
3. **Module** `systems/<name>.py` per contract in `systems/__init__.py`: `NAME`, `READY`,
   `matches`, `application_url`, `questions`, `fill`, `ids_on_page`. Plain HTML form ->
   `dom.questions` + `dom.fill`, no copy. Native types -> `questions.KINDS`, native system
   fields -> `questions.KEYS`. Unknown types -> `text`, native name kept in `native`.
   Employer's own boxes: `key_from_title` (links, names). Names: box labelled legal /
   background check -> `contact.legal_*`; preferred -> page name; other / maiden ->
   `other_names`; plain Name / First / Last -> NEEDED when page name != legal name until
   `contact.form_name` says which. First/last never split from a 3+ word name or initial.
   Work history: jobs from `questions.form_roles` (tailored page's jobs vs all,
   `contact.form_jobs`; form asking complete history -> all; `asks_complete_history` reads the
   form text), never `master["roles"]`. Form over several pages: the optional members below
   (`PER_PAGE`, `LATER`, `page`, `read`, `on_tab`). `fill` checks what took: read value /
   selected state back; `ok`, `ASK <why>` or `FAIL <why>`. Never click Submit, Next or Save.
   Found automatically - a new file is a new system; the contract test fails until every member
   is there, and each `EXAMPLES` link must match this system only.
4. **Test file** `app/tests/test_apply_<name>.py`: saved (anonymised) form definition ->
   questions; link matching. `test_systems_live.py` checks `SOURCES` against freehire's newest
   US postings by itself.
5. **Try** on 3 live postings - `uv run app/jobs.py apply-form try "<link>" [--next]`: same
   throwaway Chrome, block + canary as measure; synthetic answers by kind through the system's
   own `fill`; consent / terms / SMS / signature, password + captcha left as the applicant's own
   step. Prints the per-question report, `this page: X of Y`, LATER count, every blocked request
   w/ the question being filled when it fired. `--next` presses the one Next / Continue / Next
   Step button (never "Save and Continue"; anything saying submit / send / save / finish /
   complete / apply / sign refused); page unchanged -> "not measurable while blocked".
6. **Shared rows**: a row in the table above, and the `AGENTS.md` privacy row for the system,
   from try's blocked log (what leaves the computer, when).

### Measuring safely

A live form must never get an applicant record, anything typed, or the user's window:

- **Throwaway profile**: fresh Chrome per run in `.data/measure-browser/<run>`, deleted after;
  never `.data/apply-browser`. Started like the user's (fixed port, no automation flag).
  Never reads `My Resume/` or `My Settings/`.
- **Block**: at browser-context level, before the page loads - every request not GET / HEAD /
  OPTIONS aborted + logged w/ the step that set it off; every WebSocket stubbed, never
  connected; service workers bypassed, and a page one controls is refused (it can send past the
  block). GETs pass: a link can still carry text (measured 2026-10-03: image pixel w/ typed text
  went through) - safe only because measure types nothing and try types only synthetic values.
- **Canary first, every run**: local listener on two hosts; a page fires XHR POST, keepalive
  fetch, sendBeacon, native form POST, worker fetch, cross-site frame POST, WebSocket send (main
  page + frame). Any reaching the listener, or any not seen blocked -> run stops, nothing measured.
  Measured 2026-10-03, Chrome attached over its debugging port + headless: all 9 blocked.
- **No allow-lists, ever.** A page that won't render or advance while blocked = "not
  measurable while blocked", recorded as a fact. Never loosen the block to get further.
- **Clicks**: `--click` takes exact visible text; refused if it says submit / send / save /
  finish / complete / sign. No account, password, captcha, terms / consent / SMS box, signature.
- **Synthetic only**: "Test Applicant", `test@example.com`, 555-0100, a generated test PDF.
- **Budget**: 10 page loads per employer site per bead (measure = 2 + the canary's local one);
  bot checks can flag the address the user applies from. Saved JSON once captured.
- **Anonymise**: measure appends employer names, the tenant part of the link and prefilled
  values to `.data/measure/tenants.txt`; before committing, `grep -rniFf .data/measure/tenants.txt
  app/ AGENTS.md Guides/` prints nothing. Docs say "tenant A / B", fixtures `acme`.

## Browser (every system)

Chrome starts as a normal window on Job Finder's profile (`.data/apply-browser`), fixed debugging
port Job Finder picks + records (`job-finder-port` in the profile). Filler attaches, fills,
disconnects; window stays open. Measured 2026-09, Chrome 154, reading `navigator.webdriver` (what
an employer's spam check sees at Submit):

| Launch | webdriver |
|---|---|
| `--remote-debugging-port=<fixed>`, tab opened by Chrome (command line or `/json/new`) | `false` - used |
| `--remote-debugging-port=0` | `true` on every page, before any attach |
| tab opened by Playwright (`new_page`) | `true` |
| Playwright `launch()` (adds `--enable-automation`) | `true` + banner |

Second application reuses the open window: new tab via `/json/new`, picked by the target id it
returns - never "newest tab" (after a redirect that was any tab, possibly another employer's form).
Chrome just started -> its only tab; restored tabs beside it -> a new tab of our own.
`page_at(url, match=...)`: a tab matching (the system's `on_tab`, default same host + posting id
from `parse_url`, last part) -> attach to it (the one in front, else newest), no new tab. Another Chrome on the same
profile would just hand the link to the first, no port to attach to.

No Chrome on Windows -> Edge (ships w/ Windows 10/11), same flags + profile. Measured 2026-09-28,
Edge via `page_at`: `webdriver` `false`; window outlives command (PowerShell + Bash tool both).

## Forms over several pages

Start box then form (email or name first), "Step 1 of 5", profile then screening after Next.
Optional members (`systems/__init__.py`):

| Member | Does |
|---|---|
| `PER_PAGE = True` | `fill` attaches to the user's own tab - a fresh tab is page 1 again, their place lost |
| `fill` -> `LATER ...` (`questions.LATER`) | box on another page: not a failure, not printed; single-page systems keep `FAIL question not on page` |
| `page=` on `question()` | section / step the box is on: from the form definition, or what identifies the page read (its heading) |
| `read(page)` | questions off the page the user is on; `prepare` attaches to their tab + merges (`questions.merge`): other pages kept as they are, this page's replaced, a new page appended. No `page` on what's read (UKG, one page) -> whole list replaced |
| `on_tab(url, tab_url)` | this application's tab, when the default (host + posting id) doesn't fit |

`fill` on a `PER_PAGE` system: required blank on this page blocks it; blank on another page is
listed, not blocking. Prints `this page: X of Y required answered` + `N question(s) on other
pages`. The user checks the page and clicks Next / Continue themselves - never us - then
`prepare` again (systems with `read`), then `fill` again. No "filled" flag kept: it lies after
Back or a re-render, so each run fills what the page shows. `recheck` reads back only boxes
that were `ok` in this run.

## Shared rules (every system)

- Resume answers only what it states outright: name, email, phone, links. Location asked.
- Work-permit yes/no from setup, only for the same US question, named to the user.
- Everything else asked, clickable choices where the form gives options.
- Upload resume only after user said yes to that named file. Upload first -> no re-parse
  overwrites typed answers.
- Questions on page but not in answers file (voluntary disclosures): counted, left for user.

## Declined

Seen in other application tools, not done here:

- **Submitting for the user, or Save on their behalf.** Never - they click it (job-apply hard
  limits). A duplicate or wrong application costs their credibility with that employer.
- **AI-written answers sent without the user seeing each.** Every free-text answer is theirs to
  read before Submit; facts only from the resume.
- **Reading their mailbox** to track replies, **a third-party browser service**, **masking the
  browser as human**. Nothing leaves the computer that the privacy table doesn't name; the user's
  own Chrome, seen.
