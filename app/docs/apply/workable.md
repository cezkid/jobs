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
| Resume | `input[type=file]` id `input_files_input_<random>` - changes every load (4 of 4), no `name` | the file input whose nearest words say resume / CV (not photo), never by id. Choosing it uploads at once - see below |
| boolean | radio pair labelled YES / NO, `name` = `QA_<n>`, id random per load, inside a `fieldset` (radiogroup); each option a `[role=radio]` w/ `aria-checked` | the input only mirrors the pick: ticked by script it doesn't stay, its label isn't clickable (try, 2026-10-03). Pick the `[role=radio]` by its text, case-insensitive; a plain click times out (covered), so a click where it sits, then Space on it focused - ticked = `aria-checked` true (try: 3 of 3 postings, 11 radio questions) |
| `multiple` single | same radios; the `[role=radio]` holds no text - the option's words sit beside it, after an icon whose fallback text "SVGs not supported by this browser." is read in (headless) | option text = the widest box around it holding no other option, fallback text stripped (1 tenant) |
| `multiple` multi | checkboxes, `name` = the option's `name` from the definition (e.g. `5249623`), no id | tick each by the option `name` the definition gives for the answer |
| `text` / `paragraph` | `input[name=QA_<n>]` / `textarea[name=QA_<n>]`, id = name | `fill` |
| `number` | `input type=text name=QA_<n>`, no id; label read with a leading `*` (tenant D) | `fill` digits; strip `*` from the read label |
| `dropdown` | `div[data-ui=<id>][data-input-type=select]` wrapping `input#input_<id>_input` role=combobox, `aria-haspopup=listbox`; a box named `<id>` beside it takes no typed value (try, tenant E, 8 of 8) | open the combobox: a click times out (covered), Down on it focused opens it; click the `[role=option]` whose text is the answer; read back off the wrapper (8 of 8 ok) |
| `date` | one tenant (F): the EEO acknowledgment - left to the applicant (signing) | never filled |
| education / experience entries, `avatar` | groups need an "add" click, not done; photo never | unmeasured |

No captcha frame at load (0 of 4). Submit button: unmeasured (controls only). Never clicked.

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

## Closed posting

`/j/<unknown>/apply` -> 302 to `/oops`; `/api/v1/jobs/<unknown>/form` -> 404 `Not Found` (1 probe
each, unknown shortcode, 2026-10-03). A posting closed by its employer: unmeasured.

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
