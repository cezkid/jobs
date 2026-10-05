# Ashby application forms - measured facts

Ashby = careers site for many tech employers (`jobs.ashbyhq.com/<company>/<posting id>`).
`app/apply/systems/ashby.py` reads questions from Ashby's public job board, types answers into
its widgets; shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never
employer; add yours as a new line.

## Ashby's own "Autofill from resume" (tenant A, 2026-09)

Fills contact boxes only (name, email, phone, LinkedIn). Employer's own questions - years of
experience, free text, work permit Yes/No - always left empty. Users read this as "the ATS
rejected my resume"; it didn't. Same resume's text read cleanly in two PDF readers. Outside
autofill add-ons (Simplify, JobWizard) fill more but hold the resume on their servers.

## Form definition

`POST https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting`, no key:
`jobPosting(organizationHostedJobsPageName, jobPostingId) { applicationForm { sections {
fieldEntries { ... on FormFieldEntry { isRequired field } } } } }`. `field` = JSON blob: `path`,
`title`, `type`, `selectableValues`. Types seen (tenant A): String, Email, Phone, Location, File,
ValueSelect, LongText, Boolean; every type on 111 forms: Kinds on real forms. Voluntary disclosure (EEO: gender, race, veteran) is
`surveyForms`, same shape - asked for in the same query (measured 2026-10, tenant A: three
ValueSelect, page labels = option labels exactly). Any other on-page question missing from the file
-> `fill` counts it, leaves it to the user.

## Kinds on real forms (2026-10-05)

`apply-form survey` (`app/apply/survey.py`): one form-definition read per employer, one open posting each,
114 employers on the owner's list -> 111 read, 3 closed (`jobPosting` null), 0 refused (paced 2 s).
Counts only. Required = `isRequired`.

| Ashby type | Shared kind | Fields | Required | Employers |
|---|---|---|---|---|
| String | text | 335 | 223 | 111 |
| ValueSelect | choice | 231 | 103 | 68 |
| Boolean | yesno | 183 | 178 | 78 |
| File | file | 129 | 105 | 110 |
| LongText | longtext | 127 | 88 | 67 |
| Email | email | 111 | 111 | 111 |
| Phone | phone | 53 | 45 | 53 |
| Location | location | 46 | 43 | 46 |
| MultiValueSelect | multichoice | 45 | 9 | 25 |
| Url | url (new: was typed as text) | 42 | 23 | 31 |
| Number | number | 12 | 10 | 11 |
| EducationHistory | text, filler ASKs (new) | 2 | 2 | 2 |
| Date | date | 2 | 2 | 2 |

- Url: link boxes (LinkedIn, GitHub, website, work samples) - keyed by title like a String; fixture
  `app/tests/fixtures/ashby/survey-kinds.json`.
- EducationHistory (`_systemfield_education_history`): one block per school - school (required),
  degree, major, start, end (optional), repeatable, min 1. Not filled: `fill` ASKs, user adds schools on
  the page. Widget unmeasured.
- Survey forms (voluntary EEO): 37 of 111.
- File boxes other than the resume: 19, on 19 employers (titles not kept; cover letter vs other unmeasured).

## Read back

A user saw Preferred First Name + a Yes/No flagged empty at Submit though both showed filled
(2026-10); not reproduced - a clean form kept all 14 answers 12 s later. `fill` now waits 2.5 s, reads
each answer back (`holds`), fills a dropped one once more, else FAILs it for the user.

## Widgets (tenant A)

| Type | On the page | Filler rule |
|---|---|---|
| every question | wrapper `div[data-field-path="<path>"]`, same path as form definition | find each box by path, never by label |
| String, Email, Phone, LongText | plain input / textarea | Playwright `fill` (React takes it) |
| Location | `input[role=combobox]`; places appear as `[role=option]` after typing | type slowly, pick option starting w/ the city, none -> clear + ASK (never first option); shows as "City, State, Country" |
| Boolean | two buttons Yes / No, chosen one `aria-pressed="true"`; hidden checkbox checked = Yes, unchecked for both No + unanswered | click button by name unless already chosen (whether a second click clears it is unmeasured - avoided); poll `aria-pressed` up to 3s - set a moment after click |
| ValueSelect | radio group, option labels = `selectableValues`; clicking the chosen label again clears it (tenant B, 2026-09-29) | click label w/ exact text unless its radio already checked; poll checked up to 3s - first fill read it unchecked right after the click (tenant B) |
| File (`_systemfield_resume`) | `input[type=file]` in Resume box; separate from "Autofill from resume" uploader | upload into Resume box only, first, so nothing re-fills over typed answers |

## Browser

Shared w/ every system: `apply-systems.md`, `app/apply/browser.py`.

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | banner: one application per role per 60 days - tell user before they submit |
