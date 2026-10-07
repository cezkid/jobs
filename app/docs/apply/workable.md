# Workable application forms - measured facts

Workable = careers site for many employers (`apply.workable.com/<account>/j/<SHORTCODE>/`;
freehire serves the short `apply.workable.com/j/<SHORTCODE>?utm_source=freehire.me`). Form at the
same link + `/apply/`. Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter,
never employer; add yours as a new line. Measured 2026-10-03: 4 postings, 4 employers (tenants
A-D) through `apply-form measure` (2 loads each, canary ok), + the form definition of 17 postings,
17 employers (tenants A-F among them) by plain GET. Saved definitions:
`app/tests/fixtures/workable/tenant-<a-f>.json` (anonymised: employer -> Acme, prefilled address ->
"Example City").

## Links

| Link | Answer (plain GET, 2026-10-03) |
|---|---|
| `/j/<SHORTCODE>` | 301 -> `/<account>/j/<SHORTCODE>` (1 of 1) |
| `/j/<SHORTCODE>/apply` | 301 -> `/<account>/j/<SHORTCODE>/apply` (5 of 5) - the form link works from the short link, no account needed |
| `/<account>/j/<SHORTCODE>/` | posting page only: 0 form boxes (1 measure); the form is on `/apply/` |
| `/j/<unknown>/apply` | 302 -> `/oops` (1 probe) |

## Form definition

`GET https://apply.workable.com/api/v1/jobs/<SHORTCODE>/form` - JSON, public, no key, no account
in the path (17 of 17, 2026-10-03; the page itself fetches it). Unknown shortcode -> 404 body
`Not Found` (1 probe). Only the shortcode goes out - same as opening the posting.
Job JSON (title, location, `workplace`, description) at `GET /api/v2/accounts/<account>/jobs/<SHORTCODE>`
- needs the account.

Shape: list of sections, same 3 names on 17 of 17: `Personal information`, `Profile`, `Details`.
Each `{name, fields: [{id, required, label, type, ...}]}`; extra keys per type: `maxLength`,
`helper`, `value` + `prefilledByLocation`, `options: [{name, value}]` + `singleOption`, `max`
(number), `supportedFileTypes` / `supportedMimeTypes` / `maxFileSize` (file), `fields` (group).

| Part | Holds (17 forms) | Filler rule |
|---|---|---|
| standard ids | `firstname`* `lastname`* `email`* 17; `phone` 16 (14 required); `address` 16 (13 required); `headline` 8; `resume` 17 (16 required); `avatar` (Photo, jpg/gif/png) 6, never required; `summary` 11; `cover_letter` 14, never required | fixed ids -> shared keys: first_name, last_name, email, phone, location, resume, cover_letter. `avatar` = a photo - never filled (AGENTS.md: no photo). `headline` / `summary` = resume headline / summary |
| address | `address` text, `value` = a town from the requester's internet address, `prefilledByLocation: true` - 16 of 16, before anything is typed | never the user's answer: prepare drafts nothing for it from the prefill and says "the page filled this itself from your internet address - check it" |
| groups | `education` 13 (school*, field_of_study, degree, start_date, end_date), `experience` 14 (title*, company, industry, summary, start_date, end_date, current) - the group itself never required (17 of 17) | entries, one per school / job; inner `*` only once an entry is added |
| employer questions | ids `QA_<n>` (83) and `CA_<n>` (40, the account's reusable questions) - same shape, both in `Details` | `label` = question, `required` per field |

Employer question types (123 fields, 17 forms): `boolean` 53, `paragraph` 27, `text` 17,
`dropdown` 10 (all `singleOption: true`), `multiple` 10 (6 `singleOption: true`, 4 false),
`number` 5, `date` 1. Shared kinds: `boolean` -> yesno, `paragraph` -> longtext, `text` -> text,
`number` -> number, `date` -> date, `dropdown` -> choice (Yes/No only -> yesno), `multiple` +
`singleOption` -> choice, `multiple` without -> multichoice, `file` -> file. Others: unmeasured.

No EEO block in any definition (0 of 17). Tenants ask gender / veteran as their own required
`multiple` questions (tenant A) or optional `CA_` ones; one (tenant C) says "EEO forms listed on
the following page" - a page after Submit: unmeasured. Consent / attestation lines come as plain
`boolean` (tenants A, C) or `multiple` (privacy notice "I have read", 1 tenant) or a `date`
("enter today's date to verify your acknowledgment", tenant F) - the applicant's own.

## Widgets (tenants A-D, 2026-10-03)

| Box | On the page | Filler rule |
|---|---|---|
| standard text boxes | `input#<id>` w/ `name` = the definition id (`firstname`, `lastname`, `email`, `headline`, `address`); phone `input#input_phone[name=phone]` type tel; `textarea#summary`, `textarea#cover_letter` | find by `name` = id (stable both loads, 4 of 4) |
| address helpers | `input#city`, `#postcode`, `#country`, no label, never required, empty on load (4 of 4) | left alone - what fills them (Address's place search?): unmeasured |
| Resume | `input[type=file]` id `input_files_input_<random>` - changes every load (4 of 4), no `name`; wrapper `[data-ui="resume"]` (form script, 2026-10-06) | the file input whose nearest words say resume / CV (not photo), never by id. Choosing it uploads at once - see below; read back off the wrapper's words (Read back) |
| boolean | radio pair labelled YES / NO, `name` = `QA_<n>`, id random per load, inside a `fieldset` (radiogroup); each option a `[role=radio]` w/ `aria-checked` | the input only mirrors the pick: ticked by script it doesn't stay, its label isn't clickable (try, 2026-10-03). Pick the `[role=radio]` by its text, case-insensitive; a plain click times out (covered), so a click where it sits, then Space on it focused - ticked = `aria-checked` true (try: 3 of 3 postings, 11 radio questions) |
| `multiple` single | same radios; the `[role=radio]` holds no text - the option's words sit beside it, after an icon whose fallback text "SVGs not supported by this browser." is read in (headless) | option text = the widest box around it holding no other option, fallback text stripped (1 tenant) |
| `multiple` multi | checkboxes, `name` = the option's `name` from the definition (e.g. `5249623`), no id | tick each by the option `name` the definition gives for the answer |
| `text` / `paragraph` | `input[name=QA_<n>]` / `textarea[name=QA_<n>]`, id = name | `fill` |
| `number` | `input type=text name=QA_<n>`, no id; label read with a leading `*` (tenant D) | `fill` digits; strip `*` from the read label |
| `dropdown` | `div[data-ui=<id>][data-input-type=select]` wrapping `input#input_<id>_input` role=combobox, `aria-haspopup=listbox`; a box named `<id>` beside it takes no typed value (try, tenant E, 8 of 8) | open the combobox: a click times out (covered), Down on it focused opens it; click the `[role=option]` whose text is the answer; read back off the wrapper (8 of 8 ok) |
| `date` | one tenant (F): the EEO acknowledgment - left to the applicant (signing) | never filled |
| education / experience entries, `avatar` | groups need an "add" click, not done; photo never | unmeasured |

No captcha frame at load (0 of 4). Submit button: unmeasured (controls only). Never clicked.

Cookie dialog (window, 2 tenants, 2026-10-06): `[data-ui=cookie-consent]` `role=dialog` `aria-modal` covers the
whole form on load - a click at a list's middle meets it (3 of 3). Likely what "a plain click times out (covered)"
above is; Chrome unmeasured. Typing focused by script still fills. `vscode-browser.md` "Workable - route 2".
Offered there from the owner's yes 2026-10-06 (plan-k8n.8) to 2026-10-07: `fill --in-window`, off by default.
Pulled 2026-10-07 (owner, plan-k8n.34): Submit failed 2 of 2 in the window, 2026-10-07 - owner's real application
(1 job), filled 7/8 + read back, resume uploaded (file name shown) though the filler said ASK; Submit -> "Something
went wrong" twice (2nd after Workable's own resume autofill), no confirmation email. Same job in Job Finder's Chrome:
Submit went through after a "verify you are human" check (1 of 1). Points at the window, not the form or answers.
`fill --in-window` now refused in one line (`window.REFUSED`); Chrome only. Likely why: the window's debugger
stayed on the form - a session for each cross-site frame (Turnstile) under the tab's was never let go (measured on
the local form 3 of 3, fixed in window extension 0.26.0: 0 left, 3 of 3); `vscode-browser.md` "Workable Submit in
the window". Back in the window only after a real Submit there passes.

## Pages

One page, 7 of 7 (4 measured + 3 tried): every box on `/apply/`, no Next. Tenant C's "following page" for EEO: unmeasured.

## What leaves the computer, when

On load, before anything is typed (blocked log, 2 loads x 4 tenants, 2026-10-03): Cloudflare
`cdn-cgi/challenge-platform/.../jsd/oneshot` (POST, 1 per load). Nothing else blocked; the page
renders in full with it blocked. The address prefill is the server's own guess from the request
(in the GET answer of `/form`), nothing typed.

While filling (`apply-form try`, 3 postings, 3 employers, 2026-10-03): typing, radios, ticks and
dropdowns send nothing (0 blocked while filling, every box). Choosing the resume file sends it at
once: POST to `workable-application-form.s3.us-east-1.amazonaws.com/` (2 per choose) + an error
report to `api.rollbar.com` once blocked - the resume reaches Workable's storage before Submit.
With that upload blocked the form breaks (every later box "not on page", 1 posting), so try runs
`--no-upload` here and the resume box is left: on the user's own run it goes out on their yes.
Contact details + answers: only on Submit (never clicked - unmeasured past it).

## Try (`apply-form try --no-upload`, 2026-10-03)

| Posting | Boxes | Result |
|---|---|---|
| tenant F | 17: text, phone, address, paragraphs, 4 boolean radios, 1 set of 3 ticks | all ok; resume left (upload), EEO date left (acknowledgment = signing) |
| tenant E | 25: 8 dropdowns (2 lists, 6 Yes / No), boolean, paragraphs, text | all ok; resume left; authorization line left (signing) |
| tenant G | 21: headline, numbers as text, 5 boolean, single `multiple`, checkbox `multiple` | all ok; resume left; "Do you certify ..." left (signing) |

## Read back (2026-10)

`holds(page, q)` = what the page SHOWS, read once the form had time to keep it; `form.recheck`
fills a dropped answer once more, still gone -> FAIL, the user fills it by hand. Per kind:

| Kind | Read back as | Not held when |
|---|---|---|
| text / number / paragraph / email / address | the box's value | it differs from the answer |
| phone | the box's digits, ending in the answer's | other digits (a dialling code the box puts in front is the page's) |
| boolean, single `multiple` (radios) | the option text of the one `[role=radio]` with `aria-checked` true, any case | none ticked, or another option ticked |
| checkbox `multiple` | each box's own tick, by the option `name` the definition gives | any box ticked against the answer, or a box missing |
| dropdown | the text shown in its `div[data-ui=<id>]` wrapper, outside the list | nothing or another option shows |
| resume | a file name in the `[data-ui="resume"]` box, no error words | no name, or Workable's error words show |

Upload (`put_file`), as Greenhouse / Ashby: page idle first (15 s cap; a page that keeps polling
is read anyway), file chosen - it goes to Workable's storage at once (What leaves). Then the
resume box's words, every 250 ms up to 20 s: Workable's own error words -> FAIL in those words;
the file's name shows and no error for 2 s -> ok; neither -> ASK. What the box shows, from
Workable's form script (plain download, 2026-10-06; no live upload seen): wrapper `data-ui` = the
field id (`resume`, as each dropdown's); the name shows only once storage answered (name + stored
link set together); errors "File is too big" (the page's own size check, before anything goes;
limit = the definition's `maxFileSize`: 12000000 on tenant A, script default 5242880), "Something
went wrong. We are working on this, please try again later." (upload failed), "Please use a
different file." (type it doesn't take).

Covered by `app/tests/fixtures/dom/workable-form.html` in real headless Chrome (measured widget
shapes + the script's resume box; upload to a stand-in endpoint on the fixture's own host):
text, email, phone, prefilled address, paragraph, number as text, YES / NO radios, single
`multiple` radios w/ icon text, checkbox `multiple`, 2 dropdowns (list + Yes / No), resume ok /
too big / upload failed. Live: 3 saved `try --no-upload` runs (2026-10-03, below) - every kind
above but the resume; no new try (no kind unseen). Live upload + its read-back: unmeasured - the
upload sends the file to Workable before Submit, and blocked it breaks the form (owner decides
whether a measuring tab may answer it: plan-k8n.9).

## Closed posting

Measured 2026-10-06, plain GET (0 page loads, 2 s apart, 0 errors, 0 429) of each link's form
definition in `.data/links/workable-open.txt` + `-closed.txt`, then its short link (redirect not
followed), then each employer's own public job list `GET /api/v1/widget/accounts/<account>` once
(26 employers):

| List | Links | Form (200) | 404, short link names the employer | 404, short link -> `/oops` |
|---|---|---|---|---|
| open | 46 | 38 | 4 | 4 |
| closed | 2 | 0 | 1 | 1 |

Employer's own list agrees: 38 of 38 forms listed, 5 of 5 404s w/ an employer not listed. 404
body = `Not Found` either way (10 of 10) - no words of its own; `/oops` = Workable no longer knows
the shortcode. A closed posting's page wording: unmeasured (no page load spent - the definition +
the list decide).

`questions` raises on 404 with the reason (`board_says`): not on the employer's list -> "the
posting is no longer on the employer's Workable job list - it may have closed"; short link to
`/oops` -> "Workable no longer knows this posting - it may have closed"; still listed -> "can't
tell". `closed(url)` (asked by `form.closed` when no form comes up) gives the same; another
status or no answer -> "can't tell", never a guess.

Open read as closed: 0 (38 of 38 with a form read open, all on their employer's list).
Saved: `.data/measure/workable-closed-check-2026-10-06.json`. The open list lags: 8 of 46
"open" links already gone.

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | page + definition: headline, summary, education + experience; 16 questions - 10 boolean (work permit, background check, 3 attestations), gender + veteran as required single choice, languages + phone-screen times as checkboxes, 2 text |
| tenant B | page + definition: no education / experience / cover letter; 4 required paragraphs (salary, start date, travel) |
| tenant C | page + definition: education + experience + summary; 17 questions - 6 boolean (clearance, on-site, degree, EEO + investigation attestations), 10 paragraph, 1 text; says an EEO page follows |
| tenant D | page + definition: no education / experience; 2 boolean (sponsorship, on-site), salary `number`, referrer text |
| tenant E | definition only: 17 `CA_` questions - 8 dropdowns (how heard, degree, 18+, work permit, sponsorship, relatives, past employer, non-compete), 5 paragraphs (follow-ups after "If yes", reason for leaving), 3 text, 1 boolean (attestation) |
| tenant F | definition only: 9 questions (8 `CA_`); photo box; `multiple` checkboxes (weekends / evenings / holiday); criminal-history boolean + its explanation; EEO acknowledgment as a `date` |
| tenant G | try only: salary + notice as text, second citizenship, gender as checkboxes, adjustments as single `multiple` ("Yes - please add details below" / No), 5 boolean |
