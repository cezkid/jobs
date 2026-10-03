# Lever application forms - measured facts

Lever = careers site for many employers (`jobs.lever.co/<company>/<posting id>`, EU host
`jobs.eu.lever.co`; freehire links end `?utm_source=freehire.me`). Form at the same link + `/apply`.
Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer; add
yours as a new line. Measured 2026-10-03: 4 postings, 4 employers (tenants A-D), `apply-form
measure` (2 loads each, canary ok, 0 ids changed between loads) + one plain GET of each `/apply`.
Saved forms: `app/tests/fixtures/lever/tenant-<a-d>.html` (the `<form>` only, anonymised).

## Form definition

`GET https://jobs.lever.co/<co>/<id>/apply` - server-rendered HTML, public, no key, no browser
(plain GET 200, 4 of 4, 2026-10-03). Only the posting id goes out - same as opening the posting.
Lever's public postings API (`api.lever.co/v0/postings/<co>/<id>`) has no questions (description,
`categories`, `workplaceType` only - 2026-10-03), so the page is the definition.

| Part | Holds | Filler rule |
|---|---|---|
| standard boxes | `resume` (file), `name` (Full name, one box), `email`, `phone`, `location` (+ hidden `selectedLocation`), `org` (Current company), `urls[LinkedIn]` `urls[Twitter]` `urls[GitHub]` `urls[Portfolio]` `urls[Other]` | Full name + Email required 4 of 4; Phone required 3 of 4; Current location required 1 of 4; tenant D shows LinkedIn + Other only. Required = `✱` in the label / `required` attr, per tenant |
| employer questions (cards) | one `<input type=hidden name="cards[<card>][baseTemplate]" value="<JSON>">` per card (value comes before name) + its boxes `cards[<card>][field<N>]`, N = index in `fields[]` | JSON `text` (card heading), `fields[]` each `type`, `text` (the question), `required`, `options[].text`, `id`. Page label of a text box is only the placeholder "Type your response" - title from JSON, never the page |
| employer survey | `surveysResponses[<s>][baseTemplate]` (attr `data-name`, not `name`), boxes `surveysResponses[<s>][responses][field<N>]`, + `[surveyId]`, `[candidateSelectedLocation]` | same JSON shape as a card; voluntary (race, gender, veteran - tenant C), every field `required: false` |
| US EEO | `eeo[gender]` `eeo[race]` `eeo[veteran]` `eeo[disability]`; `eeo[disabilitySignature]` + `eeo[disabilitySignatureDate]` hidden until Disability status chosen | not in any JSON - read from the page; never required. Disability block 1 of 4 (tenant A) |
| consent | `consent[marketing]` checkbox (+ hidden 0); a card "I Accept" (multiple-select, required) | the applicant's own tick - never ours |
| hidden | `source`, `applicant-timezone` (Lever's own script fills it from the browser), `h-captcha-response` | left alone |

Card field types seen (51 fields, 4 tenants): `text` 15, `textarea` 14, `multiple-choice` 14,
`dropdown` 6, `multiple-select` 2. Shared kinds: `text` -> text, `textarea` -> longtext,
`multiple-choice` -> choice (Yes/No only -> yesno), `dropdown` -> choice (Yes/No only -> yesno),
`multiple-select` -> multichoice. Other card types (file, date ...): unmeasured.

No "Additional information" (`comments`) box on any of the 4 (2026-10-03). Required flags in the
card JSON match the page's `required` attr (4 of 4). The read-ahead line "Lever doesn't publish
which questions are required" is about the job search's captured questions, not this page.

## Widgets (tenants A-D, 2026-10-03)

Plain HTML form - no framework ids; every box found by `name` (stable, same both loads).

| Box | On the page | Filler rule |
|---|---|---|
| Full name, Email, Phone, Current company, Links | `input[name=...]`, `data-qa` `name-input` / `email-input` / `phone-input` / `org-input` | find by `name` |
| Resume/CV | hidden `input[type=file]#resume-upload-input` (`data-qa=input-resume`); label states "Analyzing resume...", "Couldn't auto-read resume.", "Success!", max 100MB | upload first: Lever reads the resume and fills boxes from it (what is sent + when: unmeasured until `try`); type the rest after |
| Current location | `input#location-input.location-input` (maxlength 100), results in `.dropdown-results`, choice kept in hidden `#selected-location` | Lever's own place search; whether results come while every write is blocked: unmeasured |
| text card | `input.card-field-input[name="cards[..][fieldN]"]` | `fill` |
| textarea card | `textarea[name="cards[..][fieldN]"]` | `fill` |
| multiple-choice card | radios `name="cards[..][fieldN]"`, `value` = option text, `ul[data-qa=multiple-choice]` | check the radio whose value is exactly the answer |
| dropdown card | native `<select>`, first option "Select..." | `select_option` by exact text |
| multiple-select card | checkboxes same `name`, `ul[data-qa=checkboxes]` | check each by exact value |
| EEO | selects (gender, veteran, disability; race as select tenant B) or radios (race tenant A, each w/ a description under it) | exact option text |
| Apply with LinkedIn | `script[type="IN/AwliWidget"]` row at the top, tenants A + B | left alone - it signs in to LinkedIn |

Submit: `button[data-qa=btn-submit]`, plus a hidden `#hcaptchaSubmitBtn` - hCaptcha runs at
Submit, 4 of 4. Never clicked.

## Pages

One page, 4 of 4: every box on `/apply`, no Next.

## What leaves the computer, when

On load, before anything is typed (blocked log, 2 loads x 4 tenants, 2026-10-03): hCaptcha
`checksiteconfig` (POST, ~10 per load), Cloudflare `cdn-cgi/challenge-platform/.../jsd` (POST, 1 per
load), LinkedIn `talentwidgets/apply-with-linkedin` (POST, tenants A + B). The page still renders
in full with all of them blocked. Typing, resume upload, location search: unmeasured (build bead,
`apply-form try`).

## Closed posting

Unmeasured.

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | 6 cards, 17 fields (work permit + sponsorship, how-heard, legal name text, relocation dropdown + office checkboxes); full EEO incl. disability + signature; Apply with LinkedIn; Phone optional |
| tenant B | 2 cards (salary text, work permit + sponsorship dropdowns); EEO gender / race / veteran all selects, no disability; Apply with LinkedIn |
| tenant C | 2 cards, 22 fields (home address boxes, preferred name, pronouns, start date, salary, non-compete); no EEO - employer's own survey (race checkboxes, gender, veteran); Current location required |
| tenant D | 3 cards, all optional Yes/No + one textarea; required privacy "I Accept" card + marketing consent box; no EEO; Links: LinkedIn + Other only |
