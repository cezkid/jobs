# Greenhouse application forms - measured facts

Greenhouse = careers site for many tech employers (`job-boards.greenhouse.io/<company>/jobs/<id>`, or
embedded on the employer's own page as `?gh_jid=<id>` - below).
`app/apply/systems/greenhouse.py` reads questions from Greenhouse's public job board, types answers
into its widgets; shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never
employer; add yours as a new line.

## Form definition

`GET https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>?questions=true`, no key (EU:
`boards-api.eu.`). Only the listing id goes out - same as opening the posting.

| Part | Holds | Filler rule |
|---|---|---|
| `questions[]` | `label`, `required`, `fields[]` (`name`, `type`, `values[]`) - contact boxes, Resume/CV, Cover Letter, employer questions (`question_<n>`) | one question per entry, first non-hidden field; Resume/CV + Cover Letter list an upload and a paste box - the upload is the question |
| `location_questions[]` | Latitude, Longitude (hidden), Location | one Location (City) question, page id `candidate-location` |
| `demographic_questions.questions[]` | employer's own optional survey: `id`, `type`, `answer_options[]` | page id = the numeric id; `free_form` options (self-describe) are a separate box, left off |
| `compliance[]` (`eeoc`) | government self-ID: Gender, Race, Veteran Status (sometimes Disability) | choice questions, never required; Hispanic/Latino shows on the page but not here - added before Race |
| not listed | Country (phone dialing code) - required on the page | added after Phone |

Types: `input_text` -> text (email/phone by name), `textarea` -> longtext, `input_file` -> file,
`multi_value_single_select` -> choice (Yes/No only -> yesno), `multi_value_multi_select` ->
multichoice, `input_hidden` skipped.

## Widgets (tenant A, 2026-10-02)

| Box | On the page | Filler rule |
|---|---|---|
| every question | input whose `id` = field name (`first_name`, `question_<n>`, `1234501`) | find by id via `[id="..."]` - ids can start with a digit, `#1234...` is not a valid selector |
| text | `input.input__single-line` | focus, wait 400 ms, `fill`, read back, once more on mismatch. Signed in to MyGreenhouse in that Chrome, first focus on First/Last Name drops the saved name in a moment later: typed at once, the two ran together ("JaneAda") |
| choice / yesno / multichoice / Country | react-select: `input[role=combobox]`, list `.select__menu [role=option]` | type, click option w/ exact text - never the first offered; nothing matches -> clear + ASK. Read back from `single-value` / `multi-value__label`. Always scope to `.select__menu`: the phone box's own hidden country list is also `[role=option]` |
| Country | options read "United States +1"; chosen it shows flag + "+1" only | match w/o the code, read back the code |
| multichoice drawn as checkboxes (some questions, 2026-10-05: one form had one of each) | `fieldset#question_<n>[]` of `input[type=checkbox][name="question_<n>[]"]`, id `question_<n>[]_<value>`, each named by its `label[for]`; the job board's list says nothing of which | checkboxes w/ that name on the page -> tick each answer by its label, untick the rest, read each back; else react-select. Counted as one question on the page |
| Location (City) | combobox `candidate-location`, places after typing (e.g. "Springfield, Illinois, United States") | type city only, pick option starting w/ the full answer |
| Resume/CV, Cover Letter | hidden `input[type=file]#resume` / `#cover_letter`; after upload `[aria-labelledby=upload-label-<id>] .file-upload__filename` shows the file name | upload first, confirm by name. Choosing it sends the file at once - see below |
| Race | shown only after Hispanic/Latino = No | not shown -> skipped |
| Education (School, Degree ...) | `school--0` ...; optional; not in the job board's list | left alone; MyGreenhouse may fill it |

`navigator.webdriver` false in Job Finder's Chrome (2026-10-02). Submit button `button[type=submit]` -
never clicked. After Submit the address ends `/confirmation`.

## What leaves the computer, when

`apply-form try`, every write blocked, 3 postings, 3 employers (tenants C-E), 2026-10-05: 2 on
`job-boards.greenhouse.io`, 1 on the employer's own page (`?gh_jid=`, embed form opened by
`recover`). Same in the Job Finder window's own tab (tenant B, `vscode-browser.md`).
Trial, off by default: `apply-form fill <job> --in-window` fills it in that tab instead of Chrome
(`vscode-browser.md` #Trial).

| When | What goes out (blocked here) |
|---|---|
| Load | analytics POST `c.spl.greenhouse.io` (3 of 3); employer page: its own analytics + cookie-consent POSTs |
| Typing, choices, ticks | nothing (0 blocked while filling, 3 of 3) |
| Resume chosen | the file: POST `multipart/form-data` to `grnhse-prod-jben-us-east-1.s3.amazonaws.com` = Greenhouse's storage, before Submit (3 of 3) |
| Cover letter chosen | same POST, same storage (2 of 2 that had the box) |
| Contact details + answers | only on Submit (never clicked - unmeasured past it) |

So the resume (and a cover letter) reaches the employer's Greenhouse as soon as it is chosen -
`FILE_ON_CHOICE`: `prepare` tells the AI to say so in the upload yes. Upload blocked, the rest of
the form still fills (3 of 3, unlike Workable) - `try` needs no `--no-upload` here; only the file
name never shows ("upload not confirmed").

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | EEOC + own demographic survey both on one form - two separate sets of voluntary questions |
| tenant C | 26 questions: work permit + sponsorship, start date, salary, own demographic survey (gender identity, orientation, transgender, disability) + EEOC; all but the resume filled with the upload blocked |
| tenant D | 12 questions, resume + cover letter boxes; both files POST to storage when chosen |
| tenant E | employer's own page (`?gh_jid=`); 30 questions; 2 "select all that apply" questions are checkboxes, not react-select (4 and 14 options) - FAILed, ticked since 2026-10-05; work history entries on the page, not in the job board's list; a required "not generated ... by AI tools" confirm - filled with a test Yes, left to the applicant since 2026-10-05 (`answers.md`) |
| tenant F | job board; 2 multi-selects on one form: the required one checkboxes, the optional one react-select - both filled (try, 2026-10-05) |

## Board that sends its job page to the employer's own site (2026-10)

`job-boards.greenhouse.io/<co>/jobs/<id>` 302s to the employer's careers page (seen: its own form, other
field names - no `#first_name`). `recover` opens `embed/job_app?for=<co>&token=<id>&b=<site>`
instead: `b=` stops the redirect, same form ids. Wait for network idle before the upload - too
early, the page shows its own "Cannot read properties of undefined (reading 'uploadFile')".

## Employer's own page w/ `?gh_jid=` (2026-10-04)

Many Greenhouse postings link to the employer's own careers page, form embedded, job id in
`gh_jid` - board name not in the link. Share of newest 50 US Greenhouse rows on freehire:

| Measured | On employer's page | On greenhouse.io |
|---|---|---|
| 2026-10-03 | 17 | 33 |
| 2026-10-04 | 10 (4 employers) | 40 |

One employer posting a batch swings it. greenhouse.io links can carry `gh_jid` too - host decides. `board_for`: `GET boards.greenhouse.io/embed/job_app?token=<id>`
(no redirect follow) -> 301 to `job-boards.greenhouse.io/embed/job_app?for=<board>&token=<id>`;
10 of 10 resolved, unknown id -> 404 -> "posting not found on Greenhouse - it may have closed".
Only the listing id goes out, to Greenhouse - same as opening the posting. Board found -> same path
as any Greenhouse link (job board read, `recover` to the embed form when its page redirects).
freehire's row also carries it (`external_id` = `<board>:<id>`), not stored - lookup works for a
pasted link too. Live gate: `test_greenhouse_employer_site_links_read`.
