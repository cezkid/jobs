# Greenhouse application forms - measured facts

Greenhouse = careers site for many tech employers (`job-boards.greenhouse.io/<company>/jobs/<id>`, or
embedded on the employer's own page as `?gh_jid=<id>` - below).
`app/apply/systems/greenhouse.py` reads questions from Greenhouse's public job board, types answers
into its widgets; shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never
employer; add yours as a new line.

## Form definition

`GET https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>?questions=true`, no key. Only the
listing id goes out - same as opening the posting.

EU postings (`job-boards.eu.greenhouse.io`): `GET https://boards.eu.greenhouse.io/v1/boards/...`
(`JOB_BOARD`). Measured 2026-10-09:
- `boards-api.eu.greenhouse.io`, `boards-api-eu.greenhouse.io`: no DNS address - the live gate crashed
  (ConnectError) on the newest US list's first link, an EU one (4 of the newest 50 were EU).
- Greenhouse's Job Board API docs (docs.greenhouse.io/job-board.html) name only `boards-api.greenhouse.io`,
  no EU host.
- The EU job page + embed form name `"JBEN_URL":"https://boards.eu.greenhouse.io"` - the host the page
  reads its own data from; answers `x-farm-id: eu`, 200 for 4 of 4 EU jobs, 404 for a US job.
- `boards-api.greenhouse.io` also answered the 4 EU jobs (`x-farm-id: us`), same body (one listed its
  EEOC options in another order) - undocumented, so not relied on.

| Part | Holds | Filler rule |
|---|---|---|
| `questions[]` | `label`, `required`, `fields[]` (`name`, `type`, `values[]`) - contact boxes, Resume/CV, Cover Letter, employer questions (`question_<n>`) | one question per entry, first non-hidden field; Resume/CV + Cover Letter list an upload and a paste box - the upload is the question |
| `location_questions[]` | Latitude, Longitude (hidden), Location | one Location (City) question, page id `candidate-location` |
| `demographic_questions.questions[]` | employer's own optional survey: `id`, `type`, `answer_options[]` | page id = the numeric id; `free_form` options (self-describe) are a separate box, left off |
| `compliance[]` (`eeoc`) | government self-ID: Gender, Race, Veteran Status (sometimes Disability) | choice questions, never required; Hispanic/Latino shows on the page but not here - added before Race |
| not listed | Country (phone dialing code) - required on the page | added after Phone |
| `education` (top level) | `education_optional` / `education_required` / absent (no section). 48 jobs, 24 boards (2026-10-05): absent 36, required 6, optional 6 | absent -> no Education boxes |
| form page `/embed/job_app?for=<board>&token=<id>` (plain GET, 200 even where the job page redirects) | `"education_config":{school_name, degree, discipline, start_month, start_year, end_month, end_year}` each `optional` / `required` / `hidden` - 6 of 6 boards differed (one all optional; school + degree required, rest hidden; months hidden ...); `window.ENV.JBEN_URL` = the lists' host | one set of boxes per school in Resume details (`education(...)`), hidden ones left out, start dates only when required (the resume has none); unreadable -> school + degree (required as the job board says) + discipline optional |
| `<JBEN_URL>/v1/boards/<board>/education/degrees`, `/disciplines` (`?page=N`, 100 a page, `meta.total_count`) | degrees: 10 on 3 boards ("Bachelor's Degree", "Doctor of Philosophy (Ph.D.)", "Master of Business Administration (M.B.A.)", "Other" ...); disciplines 72-73 | the options of Degree / Discipline: the resume's degree as the list words it (`questions.degree_option`: BA -> Bachelor's Degree, named to the user), discipline exact or longest option it starts with, else asked |
| `/education/schools?term=` | search only, no full list: a comma in the term finds nothing ("University of California, Berkeley" -> 0, "University of California" -> "... - Berkeley"); unknown -> `[]`; "Other" is a school | typed up to the first comma, picked by its words (punctuation aside), never Other or a near name |

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
| every box, after all are filled | an owner's real run in the window (tenant G, 2026-10-05) reported every dropdown ok; the owner then said "some fields were not filled" and picked Dropdowns (which ones unknown). Never reproduced: 3 blocked runs (headless Chrome, headful Chrome unfocused, the window) + 5 more (plan-29g.24: upload succeeding, signed in to MyGreenhouse, its autofill landing mid-fill, clicking + Tab around for 30 s) - all held ([gh-dropdown-variants.json](vscode-browser/gh-dropdown-variants.json)). Page code (job board bundle, 2026-10-05): a custom question's dropdown keeps its own choice (react-select, no value passed in), so only a clear (Backspace / Delete in an empty box, the x) or a redraw of the form empties it; EEOC dropdowns show the form's saved answer. Upload success only adds the file; MyGreenhouse autofill fills names, email, phone, city, links, EEOC + its saved resume, never a custom dropdown - cause unfound | `holds`: wait 2.5 s (`form.recheck`), read each back off the page (dropdown = the choice it shows, never the filler's word); gone -> filled again once, still gone -> `FAIL answer dropped after filling - fill it by hand` |
| multichoice drawn as checkboxes (some questions, 2026-10-05: one form had one of each) | `fieldset#question_<n>[]` of `input[type=checkbox][name="question_<n>[]"]`, id `question_<n>[]_<value>`, each named by its `label[for]`; the job board's list says nothing of which | checkboxes w/ that name on the page -> tick each answer by its label, untick the rest, read each back; else react-select. Counted as one question on the page |
| Location (City) | combobox `candidate-location`, places after typing (e.g. "Springfield, Illinois, United States") | type city only, pick option starting w/ the full answer |
| Resume/CV, Cover Letter | hidden `input[type=file]#resume` / `#cover_letter`; after upload `[aria-labelledby=upload-label-<id>] .file-upload__filename` shows the file name | upload first, confirm by name. Choosing it sends the file at once - see below. Box ready only once the page's own storage-form request answers (after load): chosen before -> its own `uploadFile` error line, no name; same file again does nothing -> `put_file` waits network idle first, that line = `FAIL` (plan-29g.25, [vscode-browser.md](vscode-browser.md#upload-wait-plan-29g25)). Signed in to MyGreenhouse + a name box focused before the upload: the page puts the saved resume in, the file box is gone -> `FAIL question not on page` (measured, plan-29g.24); the fill's own order (resume first) keeps theirs |
| Race | shown only after Hispanic/Latino = No | not shown -> skipped |
| Education (School, Degree ...) | `.education--container > .education--form` per school: react-selects `school--<i>`, `degree--<i>`, `discipline--<i>`, `start-month--<i>`, `end-month--<i>`, number boxes `start-year--<i>`, `end-year--<i>`; its own `button.add-another-button` adds school i+1 (Employment has one too). School, Degree, Discipline search Greenhouse's list with each keystroke (react-select async: the last answer stays shown while the next loads) | from Resume details (plan-29g.26); school i>0: click `.education--container .add-another-button` until its boxes show; searched boxes read until the answer shows (8 s), school not on the list -> ASK, the user picks theirs (or Other); end date only as the page shows it (`hide_year` -> blank). Never counted as extra questions. MyGreenhouse may fill it |

`navigator.webdriver` false in Job Finder's Chrome (2026-10-02). Submit button `button[type=submit]` -
never clicked. After Submit the address ends `/confirmation`.

## Email security code after Submit

Greenhouse's help page [Invisible reCAPTCHA](https://support.greenhouse.io/hc/en-us/articles/115005448066)
(updated 2026-03-02; vendor doc): every job board runs invisible reCAPTCHA, scoring "mouse movements
and typing patterns" on the posting; "depending on your spam sensitivity setting and the user's score,
a user may be asked to verify their email before submitting their application". The employer picks
that setting per job board - stricter needs a higher score. So any Greenhouse application, Chrome or
window, may end in a code emailed to the applicant, pasted on the page before it goes through.

Seen: owner's application filled in the window (tenant G, 2026-10-05) asked for a code; their
Chrome-filled one the day before (another employer) didn't - one each, two employers, so the
employer's setting alone can explain it. Window vs Chrome on Google's v3 demo: 0.9 every sample
both ways (`vscode-browser.md` #Email code after Submit). `job-apply` step 5 tells the user before
Submit.

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
| School, Degree, Discipline typed (Education) | each keystroke: GET `boards.greenhouse.io/v1/boards/<board>/education/<schools\|degrees\|disciplines>?term=<typed>` - the words typed, before Submit (page code, 2026-10-05); prepare says so (`SEARCHED_AS_TYPED`) |
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
| tenant G | job board; phone country, 2 lists, state, Yes/No, own demographic survey (3 tag lists, 2 Yes/No) + EEOC: owner's run in the window: dropdowns reported ok, owner said some were not filled (plan-29g.20); blocked re-runs all held ([gh-fill-tenant-g.json](vscode-browser/gh-fill-tenant-g.json), [gh-dropdown-variants.json](vscode-browser/gh-dropdown-variants.json)). Page has MyGreenhouse quick apply + autofill on: first focus on a name/email/phone/city box asks my.greenhouse.io for the signed-in profile (signed out: 401, nothing) |
| tenant F | job board; 2 multi-selects on one form: the required one checkboxes, the optional one react-select - both filled (try, 2026-10-05) |

## Board that sends its job page to the employer's own site (2026-10)

`job-boards.greenhouse.io/<co>/jobs/<id>` 302s to the employer's careers page (seen: its own form, other
field names - no `#first_name`). `recover` opens `embed/job_app?for=<co>&token=<id>&b=<site>`
instead: `b=` stops the redirect, same form ids. Upload too early -> the page's own "Cannot read
properties of undefined (reading 'uploadFile')": `put_file` waits for network idle on every link, not
only here (plan-29g.25).

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
