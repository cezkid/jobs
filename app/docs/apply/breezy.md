# Breezy application forms - measured facts

**Not filled yet** - no system module; `prepare` says "not supported yet". Facts for the owner's
pick of which systems get a filler (plan-k8n.23).

Breezy HR = hiring system, one subdomain per employer: `<employer>.breezy.hr/p/<id>-<slug>`, form
at the same link + `/apply`. Angular 1.2 page (`javascripts/portal.js`); some employers get a
newer React build (`engineSource: allowlist`, per-company rollout). Tenant named by letter, never
employer.

Measured 2026-10-07 (plan-k8n.22): 3 postings, 3 employers through `apply-form measure` (2 loads
each, canary ok: 0 received, 9 blocked), + posting and apply page of every link on the list by
plain GET (15 links, 10 employers; 2 s apart, 0 429), + the page scripts read. Page loads on
`breezy.hr`: 6. Raw notes + saved pages: `.data/measure/breezy-teamtailor-2026-10-07/` (private,
not shipped).

## Links

| Link | Answer (plain GET, 2026-10-07) |
|---|---|
| `/p/<id>-<slug>` | posting page, Apply link (9 of 14 open links) |
| same, posting gone | **200**, not 404: page reads "Position Closed - Sorry, this position is no longer accepting candidates.", no Apply link (5 of 14 "open", 1 of 2 closed) |
| `/p/<id>-<slug>/apply` | the form page |

1 of 2 links on the closed list was still open (Apply link) - the list lags.

## Form definition

In the apply page, no separate request. Two builds:

- Angular (6 of 9): hidden `input#questions`, value = HTML-escaped JSON; `*_required` hidden
  inputs say which standard boxes are required.
- React (3 of 9): `script#portal-data` JSON. `data.position.application_form` = `{name,
  email_address, phone_number, address, salary, resume, work_history, education, summary,
  cover_letter, preferred_location, headline, profile_photo, eeoc, ccpa}`, each `required` /
  `optional` / `hidden`; `data.questions` as below. In Chrome the React-build employer measured
  (tenant A) drew the SAME Angular form - box names identical.

Questions = sections `[{_id, title, questions: [{_id, text, body, type: {id}, required, options:
[{text, actions: {add_tags}}], questionnaire_id}]}]`.

| Part | Holds (9 forms: 7 one section, 2 none; 34 questions) | Filler rule |
|---|---|---|
| kinds | text 11, dropdown 11, multiplechoice (radios) 8, checkboxes 1, paragraph 1 - all 34 required | text, select, choice, multichoice, longtext |
| other kinds (page template, 0 seen) | date, file upload, reference check (name / email / phone, professional or personal) | unmeasured |
| knockout | 9 of 34 options carry `actions.add_tags`, e.g. "auto disqualified" on a No - silent, nothing on the page says so | never shade an answer to dodge it (Hold); say it plainly |

## Widgets (3 tenants, 2026-10-07)

| Box | On the page | Filler rule |
|---|---|---|
| any box | stable names, 0 changed ids between loads (3 of 3) | find by `name` |
| labels | `h3` spans, NOT `<label>` - 14 boxes with no label on tenant A | label by `name` + the `h3` text |
| resume | `cResume`, hidden file input `#main-attachment` (page accepts `.pdf, .doc, .docx, .txt, .rtd, .pages` - `.rtd` sic) | put file first, then fill (see below) |
| name | `cName` - ONE full-name box | full name |
| email, phone | `cEmail`, `cPhoneNumber` (tenant C: country-code select + phone box) | shared keys |
| SMS consent | checkbox | the applicant's own - never ticked for them |
| address | `cAddress` `#fullAddress` = Google Places autocomplete | letters leave as typed (below) |
| salary | `salaryCurrency` select + `cSalary` text + unnamed period select (Hourly ... Yearly) | number + both selects |
| preferred location | `cLocation` select | select |
| summary, cover letter | `cSummary`, `cCoverLetter` textareas - letter is text, not a file | text pasted, or left |
| work history, education | repeaters, "Add Position" / "Add Education" buttons, month / year dates | one entry per role |
| questions | `section_<sectionid>_question_<n>`: text box / select / radios / checkboxes / textarea | by definition `_id` order |
| EEO | radios `race_ethnicity`, `gender`, `eeoc.veteran_status` - marked required in the page on 2 tenants | voluntary: the applicant's choice, never guessed |
| CCPA | `ccpaAgreement` checkbox | the applicant's consent - never ticked for them |
| `hp_7f2b` | honeypot | must stay empty |

One page on all 3 measured; the page can split into sections (application, EEO, GDPR, CCPA,
submission) with Next / Previous buttons - unmeasured live. Submit button "Submit Application"
(also "Apply Using LinkedIn", "Use My Indeed Resume"). Never clicked. Form state kept in the
browser's local storage per posting.

## What leaves the computer, when

On load (blocked log, 6 loads): Ziggeo video session POST (`embed-api.ziggeo.com`) 1 per load, 3
of 3; LogRocket session recording POST (`r.lr-ingest.com`) 1 per load on the React-build tenant
only (script config masks typed text); Google Maps script; Google Analytics.

While filling (script read, no live upload seen):

| What | Where | When |
|---|---|---|
| Resume | employer's Breezy site (`app.breezy.hr/api/portal/<company>/upload`, 50 MB cap) | as soon as it's chosen - before Submit; then Breezy reads it and refills summary + work history from it |
| Question files | employer's Breezy site | as soon as each is chosen |
| Address | Google (Places) | letter by letter as typed |
| Contact details, answers | employer's Breezy site | at Submit (+ timing / interaction signals the page adds) |

An email code may be asked at Submit (4-digit "verification code" box in the template) -
unmeasured.

## Closed posting

200 page "Position Closed", no Apply link (6 of 16 checks) - read the text, never the status.

## Cost

Filler ~1-2 beads: stable names, definition in the page, but no `<label>`s (label by `h3`),
honeypot, upload on choose + a parse that overwrites summary / work history (upload first, then
fill), Google Places address, repeaters, possible sections + email code at Submit, silent
auto-disqualify tags.
