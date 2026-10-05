# Lever application forms - measured facts

Lever = careers site for many employers (`jobs.lever.co/<company>/<posting id>`, EU host
`jobs.eu.lever.co`; freehire links end `?utm_source=freehire.me`). Form at the same link + `/apply`.
Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer; add
yours as a new line. Measured 2026-10-03: 4 postings, 4 employers (tenants A-D), `apply-form
measure` (2 loads each, canary ok, 0 ids changed between loads) + one plain GET of each `/apply`.
Saved forms: `app/tests/fixtures/lever/tenant-<a-d>.html` (the `<form>` only, anonymised).
Filler: `app/apply/systems/lever.py`; `apply-form try` on 3 postings, 3 employers (tenants A, B, D,
2026-10-03): canary ok, 0 sent, every box `ok` except the resume (its send blocked - below) and the
consent / privacy ticks + disability signature (the applicant's own).

## Form definition

`GET https://jobs.lever.co/<co>/<id>/apply` - server-rendered HTML, public, no key, no browser
(plain GET 200, 4 of 4, 2026-10-03). Only the posting id goes out - same as opening the posting.
Lever's public postings API (`api.lever.co/v0/postings/<co>/<id>`) has no questions (description,
`categories`, `workplaceType` only - 2026-10-03), so the page is the definition.

| Part | Holds | Filler rule |
|---|---|---|
| standard boxes | `resume` (file), `name` (Full name, one box), `email`, `phone`, `location` (+ hidden `selectedLocation`), `org` (Current company), `urls[LinkedIn]` `urls[Twitter]` `urls[GitHub]` `urls[Portfolio]` `urls[Other]` | Full name + Email required 4 of 4; Phone required 3 of 4; Current location required 1 of 4; tenant D shows LinkedIn + Other only. Required = `✱` in the label / `required` attr, per tenant |
| employer questions (cards) | one `<input type=hidden name="cards[<card>][baseTemplate]" value="<JSON>">` per card (value comes before name) + its boxes `cards[<card>][field<N>]`, N = index in `fields[]` | JSON `text` (card heading), `fields[]` each `type`, `text` (the question), `required`, `options[].text`, `id`. A text box's own name is only the placeholder "Type your response" - title from JSON; a card whose JSON won't parse falls back to the label above the box |
| employer survey | `surveysResponses[<s>][baseTemplate]` (attr `data-name`, not `name`), boxes `surveysResponses[<s>][responses][field<N>]`, + `[surveyId]`, `[candidateSelectedLocation]` | same JSON shape as a card; voluntary (race, gender, veteran - tenant C), every field `required: false` |
| US EEO | `eeo[gender]` `eeo[race]` `eeo[veteran]` `eeo[disability]`; `eeo[disabilitySignature]` + `eeo[disabilitySignatureDate]` hidden until Disability status chosen | not in any JSON - read from the page; never required. Disability block 1 of 4 (tenant A) |
| consent | `consent[marketing]` checkbox (+ hidden 0), its text names the employer -> one fixed title; a card "I Accept" (multiple-select, required) | the applicant's own tick - never ours |
| hidden | `source`, `applicant-timezone` (Lever's own script fills it from the browser), `h-captcha-response` | left alone |

Card field types seen (51 fields, 4 tenants): `text` 15, `textarea` 14, `multiple-choice` 14,
`dropdown` 6, `multiple-select` 2. Shared kinds: `text` -> text, `textarea` -> longtext,
`multiple-choice` -> choice (Yes/No only -> yesno), `dropdown` -> choice (Yes/No only -> yesno),
`multiple-select` -> multichoice. `file-upload` -> file; no other card type on 21 forms (Kinds on real forms).

No "Additional information" (`comments`) box on any of the 4 (2026-10-03). Required flags in the
card JSON match the page's `required` attr (4 of 4). The read-ahead line "Lever doesn't publish
which questions are required" is about the job search's captured questions, not this page.

## Kinds on real forms (2026-10-05)

`apply-form survey` (`app/apply/survey.py`): one plain GET of `/apply` per employer, one open posting
each, 22 employers on the owner's list -> 21 read, 1 closed (404), 0 refused (paced 2 s). Counts only.
Required = card JSON `required` / page `required` or `✱`.

| Part | Type | Shared kind | Fields | Required | Employers |
|---|---|---|---|---|---|
| card | multiple-choice | choice / yesno | 43 | 42 | 12 |
| card | textarea | longtext | 41 | 34 | 14 |
| card | dropdown | choice / yesno | 37 | 36 | 8 |
| card | text | text | 22 | 18 | 10 |
| card | multiple-select | multichoice | 11 | 10 | 3 |
| card | file-upload | file (new: was text) | 1 | 0 | 1 |
| survey | multiple-choice | choice | 10 | 0 | 3 |
| survey | multiple-select | multichoice | 3 | 0 | 3 |
| EEO | select | choice | 45 | 0 | 14 |
| EEO | text (disability signature) | text, applicant's | 8 | 0 | 4 |
| EEO | radio | choice | 1 | 0 | 1 |
| standard | resume | file | 21 | 19 | 21 |
| standard | name, email | text, email | 21 each | 21 each | 21 |
| standard | phone | phone | 21 | 16 | 21 |
| standard | location | location | 21 | 9 | 21 |
| standard | org | text | 21 | 4 | 21 |
| standard | LinkedIn / Portfolio / GitHub / Twitter / Other | url | 18 / 16 / 15 / 11 / 11 | 6 / 0 / 0 / 0 / 0 | same |
| other | `urls[...]` not standard | text | 4 | 0 | 4 |
| other | `pronouns` checkboxes | multichoice | 4 | 0 | 4 |

- file-upload card ("upload a copy of your certification(s)", optional): `input[type=file]
  .application-file-input` in the card; `fill` ASKs - the user's own file, never the resume. Fixture
  `app/tests/fixtures/lever/card-file.html`. Upload behaviour unmeasured.
- Employer surveys: 3 of 21. File boxes other than the resume: 1 (the card above).
- No card type besides these six on any of the 21.

## Widgets (tenants A-D, 2026-10-03)

Plain HTML form - no framework ids; every box found by `name` (stable, same both loads).

| Box | On the page | Filler rule |
|---|---|---|
| Full name, Email, Phone, Current company, Links | `input[name=...]`, `data-qa` `name-input` / `email-input` / `phone-input` / `org-input` | find by `name` |
| Resume/CV | hidden `input[type=file]#resume-upload-input` (`data-qa=input-resume`); label states "Analyzing resume...", "Couldn't auto-read resume.", "Success!", max 100MB | upload first: choosing the file sends it to Lever's reader at once (`POST /parseResume`, 3 of 3 tries) and it fills boxes from it; wait for "Success!" / "Couldn't auto-read", type the rest after. In `try` the send is blocked -> `ASK upload not confirmed` on every tenant: the block, not the filler |
| Current location | `input#location-input.location-input` (maxlength 100), results in `.dropdown-results`, choice kept in hidden `#selected-location` | Lever's own place search: type the town, click the result that is the answer (or starts with it), read `#selected-location` back. Results came with every write blocked (3 of 3 tries) - a read; the typed town goes to Lever as you type |
| text card | `input.card-field-input[name="cards[..][fieldN]"]` | `fill`. Home address as text cards (tenant C: Address Line 1, City, State, Zip Code) -> keyed street / city / state / zip |
| textarea card | `textarea[name="cards[..][fieldN]"]` | `fill` |
| multiple-choice card | radios `name="cards[..][fieldN]"`, `value` = option text (some with a trailing space, "Other "), `ul[data-qa=multiple-choice]` | check the radio whose trimmed value is exactly the answer |
| dropdown card | native `<select>`, first option "Select..." | `select_option` by exact text |
| multiple-select card | checkboxes same `name`, `ul[data-qa=checkboxes]` | check each by exact value |
| EEO | selects (gender, veteran, disability; race as select tenant B) or radios (race tenant A, each w/ a description under it) | exact option text. Disability signature boxes labelled plain "Name" / "Date" (tenant A): titled as a signature, the applicant's own |
| Apply with LinkedIn | `script[type="IN/AwliWidget"]` row at the top, tenants A + B | left alone - it signs in to LinkedIn |

Submit: `button[data-qa=btn-submit]`, plus a hidden `#hcaptchaSubmitBtn` - hCaptcha runs at
Submit, 4 of 4. Never clicked.

## Read back

`holds` (2026-10-05, saved tenant pages A-D in headless Chrome): `form.recheck` waits 2.5 s, reads
each `ok` answer off the page, fills a dropped one once more, else FAILs it for the user. Shown value
only: text by `input_value` (phone by digits), dropdown by the option it shows, radios + checkboxes by
each option's own checked state (an extra tick = not this answer), place = `#selected-location` set
AND the box starts w/ the answer's town (typed but never picked = dropped). Box gone or unreadable =
dropped. Refill clicks only a tick that differs, so fill twice = same page (4 of 4 saved tenants).

Live (`apply-form try`, 3 postings, 3 employers not among A-D, 2026-10-05; 1 load each, canary ok,
0 writes sent; files `.data/measure/jobs.lever.co-try-20261005-151*.json`). `ok` = read back after
the 2.5 s settle (a refill, if any, not counted):

| Tenant | Boxes filled | Read back ok | Dropped (FAIL) | Kinds read back | Resume | Place |
|---|---|---|---|---|---|---|
| E | 28 | 27 | 0 | text 8 (address cards), dropdown 7, survey radios 6 + ticks 1, url 2, phone, email | ASK, block's | picked, read back |
| F | 25 | 24 | 0 | dropdown 8, multiple-select ticks 6, EEO selects 3, radios 1, textarea 1, text, phone, email | ASK, block's | picked, read back |
| G | 6 | 5 | 0 | standard boxes only (name, email, phone, company) | ASK, block's | picked, read back |

- Resume: `put_file` -> "ASK upload not confirmed on page" 3 of 3 - `POST /parseResume` blocked, so
  no "Success!" / "Couldn't auto-read" label came: the block's verdict, not the page's. Real verdict
  wording + timing still unmeasured (needs an unblocked send = a real application).
- Place: typing the town fired one `GET jobs.lever.co/searchLocations` (3 of 3, a read, came through);
  the result was clicked and `#selected-location` read back set.
- Left for the applicant (E): a required texting-consent dropdown - the applicant's own step.

## Pages

One page, 4 of 4: every box on `/apply`, no Next.

## What leaves the computer, when

On load, before anything is typed (blocked log, 2 loads x 4 tenants, 2026-10-03): hCaptcha
`checksiteconfig` (POST, ~10 per load), Cloudflare `cdn-cgi/challenge-platform/.../jsd` (POST, 1 per
load), LinkedIn `talentwidgets/apply-with-linkedin` (POST, tenants A + B). The page still renders
in full with all of them blocked.

`apply-form try`, 3 tenants (A, B, D), 2026-10-03 - blocked log while each box was filled:

| Step | Sent | When |
|---|---|---|
| Resume chosen | the file: `POST jobs.lever.co/parseResume` | at once, before Submit - Lever reads it to fill boxes (3 of 3) |
| Current location typed | the town, as a search: one `GET /searchLocations` per box (a read - came through while every write was blocked, 3 of 3 again 2026-10-05) | as typed |
| Every other box typed or ticked | nothing (no write fired, 3 of 3) | at Submit |

So the resume reaches the employer's Lever as soon as it is chosen; the rest at Submit (hCaptcha
runs there, the applicant's own step).

## Closed posting

`GET /<co>/<id>/apply` of a closed or unknown posting -> 404, page says "Sorry, we couldn't find
anything here The job posting you're looking for might have closed, or it has been removed."
(1 probe, 2026-10-03). `questions` says closed on 404; `form.CLOSED` knows the wording.

Check run over the links files (2026-10-05, `questions()` = plain GET of `/apply`, no redirects
followed, 2 s apart, 0 errors / 429):

| List | Links | Form there | May have closed (404) |
|---|---|---|---|
| open | 104 | 52 | 52 |
| closed | 9 | 6 | 3 |

- Open read as closed: 0. All 55 "may have closed" (49 + 3 of one job-board reposter on the open list,
  3 others) are 404 AND missing from the employer's own public list (`api.lever.co/v0/postings/<co>`,
  one read per employer, 2026-10-05) = taken down since the list was made. No redirect seen (0 of 113).
- 6 "closed" links still open per Lever: the list's closed mark is older or from elsewhere.
- File: `.data/measure/lever-closed-check-2026-10-05.json` (counts).

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | 6 cards, 17 fields (work permit + sponsorship, how-heard, legal name text, relocation dropdown + office checkboxes); full EEO incl. disability + signature; Apply with LinkedIn; Phone optional |
| tenant B | 2 cards (salary text, work permit + sponsorship dropdowns); EEO gender / race / veteran all selects, no disability; Apply with LinkedIn |
| tenant C | 2 cards, 22 fields (home address boxes, preferred name, pronouns, start date, salary, non-compete); no EEO - employer's own survey (race checkboxes, gender, veteran); Current location required |
| tenant D | 3 cards, all optional Yes/No + one textarea; required privacy "I Accept" card + marketing consent box; no EEO; Links: LinkedIn + Other only |
| tenant E | 2026-10-05: 7 cards incl. home address as text (street, city, state, province, postal code, country), work-history + family-at-employer Yes/No, salary text; employer survey (age range, race ticks, gender, LGBTQ+, pronouns, veteran, disability); required texting-consent dropdown |
| tenant F | 2026-10-05: 1 card, 17 fields - work permit + sponsorship, referral, state, degree, years; 6 multiple-select skill lists; one-sentence textarea; EEO gender / race / veteran selects |
| tenant G | 2026-10-05: no cards, no EEO - standard boxes only; Phone + Current location optional |
