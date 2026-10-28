# Application systems - how Job Finder fills them, and how to add one

Each hiring system lays its form out its own way; questions are much the same (contact, resume
upload, work permit, a few employer ones). Shared logic in one place, each system's quirks in a
small plug-in.

| System | Link looks like | Route | Facts |
|---|---|---|---|
| Workday | `<co>.wd<N>.myworkdayjobs.com/[<lang>/]<site>/job/.../<title>_<req>` (also `wd<N>.myworkdaysite.com/recruiting/<co>/...`) | `apply-form`, Job Finder's own Chrome; start choice after Apply, then the user's sign-in; one step per page read off the user's tab, My Experience by `workday.js` with real clicks. Fallback: `apply` script run by the Claude Chrome extension | `workday.md` |
| Ashby | `jobs.ashbyhq.com/<co>/<id>` | `apply-form`, Job Finder's own Chrome | `ashby.md` |
| Greenhouse | `job-boards.greenhouse.io/<co>/jobs/<id>` (also `boards.`, `.eu.`, `embed/job_app?for=<co>&token=<id>`, employer's own page `?gh_jid=<id>`) | `apply-form`, Job Finder's own Chrome | `greenhouse.md` |
| Lever | `jobs.lever.co/<co>/<id>` (also `jobs.eu.`, `/apply`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions read off the public `/apply` page | `lever.md` |
| Workable | `apply.workable.com/j/<code>` (also `/<account>/j/<code>/`, `/apply/`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions from Workable's public form definition | `workable.md` |
| UKG Pro Recruiting | `recruiting<N>.ultipro.com/<tenant>/JobBoard/<board>/OpportunityDetail?opportunityId=<id>` | `apply-form`, Job Finder's own Chrome; user signs in first, questions read off the signed-in form | `ukg.md` |
| JazzHR | `<co>.applytojob.com/apply/<id>/<slug>` | `apply-form`, Job Finder's own Chrome; questions read off the posting page (plain HTTP) | `jazzhr.md` |
| BambooHR | `<co>.bamboohr.com/careers/<id>` | `apply-form`, Job Finder's own Chrome; questions from the posting's form definition (plain HTTP); the resume is sent when chosen | `bamboohr.md` |
| Paylocity | `recruiting.paylocity.com/Recruiting/Jobs/Details/<id>` (form `/Apply/<id>`) | `apply-form`, Job Finder's own Chrome; questions read from the form definition in the apply page; steps "Step 1 of N", filled on the user's tab | `paylocity.md` |
| SmartRecruiters | `jobs.smartrecruiters.com/<Company>/<postingId>-<slug>` (also the form app `oneclick-ui/company/<Company>/publication/<uuid>`) | `apply-form`, Job Finder's own Chrome; page 1 (contact + resume) filled, screening after Next on the user's tab | `smartrecruiters.md` |
| Paycom | `paycomonline.net/v4/ats/web.php/portal/<key>/jobs/<id>` (older `jobs/ViewJobDetails?job=<id>&clientkey=<key>`) | `apply-form`, Job Finder's own Chrome; start box filled; form behind it read generically after you continue - unmeasured | `paycom.md` |
| ADP Workforce Now | `workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=<uuid>&jobId=<id>` (any order, `ccId` / `lang` too) | `apply-form`, Job Finder's own Chrome; start box filled; form behind it read generically after you continue - unmeasured | `adp.md` |
| Oracle Recruiting Cloud | `<pod>.fa.<dc>.oraclecloud.com/hcmUI/CandidateExperience/<lang>/sites/<site>/job/<id>` (any host with that path) | `apply-form`, Job Finder's own Chrome; start box filled; form behind it read generically after you continue - unmeasured | `oracle.md` |
| Manatal | `www.careers-page.com/<co>/job/<hash>` (form `+ /apply`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions from the posting's form definition (plain HTTP); everything, resume too, sent at Submit | `manatal.md` |
| Breezy | `<co>.breezy.hr/p/<id>-<slug>` (form `+ /apply`) | `apply-form`, Job Finder's own Chrome; questions from the definition in the apply page (plain HTTP); resume sent on choosing it, address letters to Google as typed, the rest at Submit | `breezy.md` |
| Teamtailor | `<co>.na.teamtailor.com/jobs/<id>-<slug>` or the employer's own domain, same path (form `+ /applications/new`) | `apply-form`, Job Finder's own Chrome; questions from the form frame (plain HTTP); resume sent on choosing it, town letters to the employer's Teamtailor site as typed, the rest at Submit | `teamtailor.md` |
| iCIMS | `careers-<co>.icims.com/jobs/<id>/<slug>/job` (any `*.icims.com` host) | `apply-form`, Job Finder's own Chrome; start box filled; form behind it read generically after you continue - unmeasured | `icims.md` |
| Taleo | `<tenant>.taleo.net/careersection/<section>/jobdetail.ftl?job=<id>` or `jobapply.ftl?job=<id>`; an employer's careers-site posting whose Apply leads there (`careers_page.py`) | `apply-form`, Job Finder's own Chrome; user accepts the privacy agreement + signs in, then each step read off their tab and filled - resume attached + ticked, work history + education made to match the resume; they click Save and Continue | `taleo.md` |
| Loxo | `app.loxo.co/job/<base64 id>` (also `<firm>.app.loxo.co`; form `+ /form?source_type=app`, `?utm_source=` tail) - a recruiting firm's own site | `apply-form`, Job Finder's own Chrome; questions read off the form page (plain HTTP); resume set inside the upload box's shadow root (its hidden twin outside shows nothing); everything, resume too, sent at Submit | `loxo.md` |
| Gem | `jobs.gem.com/<board>/<id>` (id starts `am9icG9zdD`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions from the job board's own GraphQL read (plain HTTP); boxes found by their labels (no ids); everything, resume too, sent at Apply | `gem.md` |
| Zoho Recruit | `<tenant>.zohorecruit.com/jobs/Careers/<id>` (a slug + `?source=` after it too) | `apply-form`, Job Finder's own Chrome; questions from the posting's form definition (plain HTTP), form opened by the posting's own apply button; email checked as its box is left (forms with screening questions), zip / city / state / skills searched as typed, the rest - resume too - at Submit | `zoho.md` |
| Rippling | `ats.rippling.com/<employer>/jobs/<uuid>` (form `+ /apply?step=application`, `?utm_source=` tail) | `apply-form`, Job Finder's own Chrome; questions from the form definition inside the posting page (plain HTTP); boxes found by their `data-testid` (the definition's ids); resume sent on choosing it and read back into the name / email / phone / Location boxes, town letters to Google as typed, the rest at Apply | `rippling.md` |

Careers-site postings (freehire `source` radancy): the job list's link is the employer's own page;
`prepare` reads it once and goes on with the system its Apply leads to (`apply/careers_page.py`,
[taleo.md](taleo.md) #Careers-site postings) - Taleo, iCIMS and Workday seen.

Job boards' copies (freehire `source` echojobs): the board shows the employer's Apply only to its own
signed-in users, so `prepare` finds the employer's own posting on the job search - same title, same
opening text, a link a system here fills (`apply/listing_copy.py`; 96 of 180 copies found one,
2026-10-22) - and goes on with that link.

Not yet: Dayforce (form shows only after a bot check - [dayforce.md](dayforce.md)), iCIMS on an employer's own domain. Where the form's questions were read ahead
(Recruitee - [answers.md](answers.md)), `apply-form prepare` drafts from them and
`apply-form paste` writes `Application answers.md` to paste from. Otherwise `prepare` says so
plainly -> user gets tailored PDF + answers to paste.

## The pieces (`app/apply/`)

| File | Job | Changes when a system is added? |
|---|---|---|
| `questions.py` | shared question shape (`KINDS`, `KEYS`), answers from resume + setup, answers file | only if the system asks something no kind covers |
| `browser.py` | Job Finder's Chrome (own profile in `.data/`, no automation flag), reused across applications | no |
| `form.py` | the `apply-form prepare / fill` steps, report, never Submit | no |
| `careers_page.py` | an employer's careers-site posting -> the system link behind its Apply | no |
| `dom.py` | any form page read as plain HTML (frames, open shadow roots), stable hooks, generic fill | only if the page has a control it can't read |
| `lab.py` | `apply-form measure` (developers): throwaway Chrome, every write blocked, canary first | no |
| `systems/__init__.py` | picks the system from the link | one line: add to `SYSTEMS` |
| `systems/<name>.py` | read the form's questions; type an answer into its widgets | new file |

## Add a system

In order - each step's output feeds the next:

1. **Measure** - `uv run app/jobs.py apply-form measure "<link>" [--click "Apply" ...]` on a live
   posting. Writes `.data/measure/<host>-<time>.json`: every control (`dom.snapshot`), ids that
   changed between two loads (made per load - never a hook), JSON the page fetched (first 2 KB
   each: where the form definition lives), `window.<name> = {...}` globals from inline scripts
   (`page_data`: a form defined in the page itself), "Step N of M" + headings + buttons (`outline`),
   markup around boxes no reader names (`unlabelled`), every blocked write. Also: public job-board API?
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
   complete / apply / sign refused); page unchanged -> "not measurable while blocked". Kept as
   `.data/measure/<host>-try-<time>.json`: every request the page made while each box was filled
   (reads too; GraphQL `op` named), how each box shows its answer after the settle (systems w/
   `box_of(page, q)`). `--upload-errors`: a `.png` + an empty PDF in the resume box first, the
   page's new words kept - a send error then is the block's, not the page's.
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
- **No allow-lists, ever** - the named exceptions below. A page that won't render or advance
  while blocked = "not measurable while blocked", recorded as a fact. Never loosen the block to
  get further.
- **The one exception (owner OK 2026-10-05)**: Ashby's page reads its questions by POST; blocked,
  it shows "Application submission is unavailable" instead of the form (measured 2026-10-05).
  `lab.NAMED_READS` lets through only `ApiJobPosting` to `jobs.ashbyhq.com/.../non-user-graphql`:
  a query (never mutation / subscription anywhere in the text), exactly its two string variables
  (org + posting id), no other key - the same read `prepare` already sends. Anything else w/ that
  name is blocked (tests). Each one passed is listed in measure's `named_reads` + try's last line.
  Another entry = owner's OK first, never added to get a page further.
- **The second (owner OK 2026-10-26)**: Gem's job board, the same way - blocked, its posting page says
  "Job not found", then (posting read let through) draws no form. Its reads go batched (one JSON list,
  `lab.BATCHED`, at most 4) to `jobs.gem.com/api/public/graphql/batch`: `ExternalJobPosting` (board +
  posting id - the read `prepare` sends), `JobBoardTheme` (board), then `OneClickApplyEnabled`,
  `OatsTeamSettingExternalPublic`, `OatsIsJobBoardSeoStructuredDataEnabled` (board) and
  `FormAutofillData` (no variables: the applicant's saved Gem details by cookie, empty in the fresh
  profile). Each operation in a batch checked alone, same rules; one that fails blocks the whole batch.
- **Clicks**: `--click` takes exact visible text; refused if it says submit / send / save /
  finish / complete / sign. No account, password, captcha, terms / consent / SMS box, signature.
- **Synthetic only**: "Test Applicant", `test@example.com`, 555-0100, a generated test PDF.
- **Budget**: 10 page loads per employer site per bead (measure = 2 + the canary's local one);
  bot checks can flag the address the user applies from. Saved JSON once captured.
- **Anonymise**: measure appends employer names, the tenant part of the link and prefilled
  values to `.data/measure/tenants.txt`; before committing, `grep -rniwFf .data/measure/tenants.txt
  app/ AGENTS.md Guides/` prints nothing (`-w`: whole words, so a short name inside a common word -
  one inside "Kubernetes" - is no hit). Docs say "tenant A / B", fixtures `acme`.

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
| `NEXT` | CSS selector of the page's way on (Workday: its footer button). With the user's `continue_on_apply: true`, `fill` presses it when its label is Next / Continue / Save and Continue (`form.CONTINUE`) - never Submit, Review, Apply - then reads the next page (`read`) and fills on |
| `step(page)` | the page's step name: `go_on` waits for it to change (and not be blank mid-redraw) after Next |
| `page_errors(page)` | the page's own error words after Next ("The field ... is required") - stop and say them |

`fill` on a `PER_PAGE` system: required blank on this page blocks it; blank on another page is
listed, not blocking. Prints `this page: X of Y required answered` + `N question(s) on other
pages`. The user checks the page and clicks Next / Continue themselves - never us - then
`prepare` again (systems with `read`), then `fill` again. Exception, the user's own yes
(`continue_on_apply: true`, asked once by `prepare`) on a system with `NEXT`: `fill` presses it on a page
holding nothing for the user (`form.held`: no FAIL, no ASK on a required box, no blank required or
user-only question, no box missing from the file), waits for the next step, reads + drafts it, fills on;
stops on `for_the_user` questions, the page's errors, Submit, or `MAX_PAGES`. Each passed page went to
the employer - the handover names it. No "filled" flag kept: it lies after
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
