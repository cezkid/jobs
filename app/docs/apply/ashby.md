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
| EducationHistory | one block per school, filled (Education History below) | 2 | 2 | 2 |
| Date | date | 2 | 2 | 2 |

- Url: link boxes (LinkedIn, GitHub, website, work samples) - keyed by title like a String; fixture
  `app/tests/fixtures/ashby/survey-kinds.json`.
- EducationHistory (`_systemfield_education_history`): one block per school - school (required),
  degree, major, start, end (optional), repeatable, min 1. Filled from Resume details since plan-nko.24:
  Education History below.
- Survey forms (voluntary EEO): 37 of 111.
- File boxes other than the resume: 19, on 19 employers (titles not kept; cover letter vs other unmeasured).

## What leaves the computer, when (2026-10-05)

`apply-form try --upload-errors` on 3 open postings, tenants C, D, E (5 loads on jobs.ashbyhq.com
incl. the closed page below; canary ok each run). Every request the page made while each box was
filled, named by its GraphQL `op` (all POST to `non-user-graphql`, all blocked - so the page never
got an answer back). Request bodies not kept: what each carries is read off its name, unmeasured.

| When | Request | C | D | E |
|---|---|---|---|---|
| page opens | `ApiJobPosting` (questions; the one named read let through) | 1 | 1 | 1 |
| file chosen, resume / cover letter / probe | `ApiCreateFileUploadHandle` - at once, before Submit | 3 | 4 | 3 |
| each box filled or clicked (text, Yes/No, choice, EEO survey too) | `ApiSetFormValue` - per box, before Submit | 15 | 31 | 20 |
| each key typed in Location | `ApiAutocompleteGeoLocation` - typed letters, as typed | - | - | 26 |
| any GET while filling | none | 0 | 0 | 0 |

- So Ashby takes answers box by box, not at Submit: privacy table (AGENTS.md + site claim rows) says so
  since plan-nko.5 - resume as soon as chosen (`FILE_ON_CHOICE`), answers as each box is filled, town
  letter by letter (`SEARCHED_AS_TYPED = ("location", "school")`, school since plan-nko.24); `prepare`
  names the upload + location + school ones.
- Location: blocked search = no places offered -> `fill` ASKs (tenant E) - never a guess.
- Files: `.data/measure/jobs.ashbyhq.com-try-20261005-14{0423,0516,0607}.json`.

## Education History (2026-10-05)

Tenants G (measure: form + after one "+ Add Education" click, 2 loads) and H (survey only); then
`apply-form try` on G (1 load, canary ok). Definition (both): `schoolName` required, `degree`, `major`,
`startDate`, `endDate` optional, `isRepeatable`, `minRepeat` 1 - read off the field itself, so `from_form`
asks each box the definition shows, required only when the entry and the box both are.

| Box | Widget | Read back | Seen |
|---|---|---|---|
| School | `input[role=combobox]` "Search schools...", right after `label[for=..-school]`; no id | its `value` (blocked search: empty) | G |
| Degree | `input#_systemfield_education_history-degree`, plain text | `value` | G |
| Field of Study | `input#..-major`, plain text | `value` | G |
| Start / End date | `div#..-startDate` / `#..-endDate`: month `<select>` (hidden "Month...", January..December, values 1-12), year `<select>` (2027 down to 1908) | chosen option's text | G |
| Still Student? | checkbox `#..-isCurrent` | - (never ticked: the resume says when they finished) | G |

- Block 0 shows on load; "+ Add Education" adds one, every block w/ the SAME ids + label-for: block i =
  the i-th match on the page (`school_box`). The click itself sent `ApiSetFormValue` (G).
- Requests (G): School typing -> `ApiSearchSchoolByCanonicalName` (Ashby's school list, the typed words,
  as typed, once more a moment later) + `ApiSetFormValue` x5; Degree, Field of Study -> `ApiSetFormValue`
  each; month / year -> none of their own (one `ApiSetFormValue` after filling). So school leaves letter by
  letter like Location: `SEARCHED_AS_TYPED`, privacy table row (AGENTS.md + site claim).
- Filler (plan-nko.24): one block per school in Resume details (`questions(url, schools)`), the page's own
  "+ Add Education" for school 2+. School picked only when the list offers its exact words, else cleared +
  ASK (search blocked in try -> ASK, as Location). Degree spelled out (`BA` -> "Bachelor of Arts") + field
  as written: free-text boxes, no list. End month + year from the graduation date as the page shows it
  (hidden year -> left blank); start dates only when required (not on a resume). Option missing -> ASK.
- Unmeasured (needs the search let through = a real application): the live school list's words (an exact
  match may be rarer than on Greenhouse), whether the box shows the pick as its value, a school not on the
  list (free text kept or not), Still Student. Fixture `app/tests/fixtures/dom/ashby-education.html`.
- Files: `.data/measure/jobs.ashbyhq.com-20261005-17{1243,1321}.json`, `-try-20261005-172210.json`.

## Upload errors (2026-10-05)

Resume box, before the real file: a `.png` (box `accept` = pdf, doc, docx ...; a picked file skips it)
and an empty PDF.

- No check before sending: both fire `ApiCreateFileUploadHandle` at once (C, D, E).
- Then "ERROR" + "<file> failed to upload" (C, D; E's words not caught - 10-line diff filled by
  text the page drew late). With the send blocked these are the block's errors, not a verdict on the
  file: Ashby's own type / empty-file wording unmeasured (needs an unblocked send = a real application).
- Failed upload still shows the file name + "Replace" in the box (C, D, E): the name is no verdict.
  `put_file` (plan-nko.5): page idle first (as Greenhouse), then "<file> failed to upload" anywhere on
  the page -> FAIL w/ the page's words; ok = name shown + no error for 3 s after it. Success wording +
  how long a real upload takes: unmeasured (needs an unblocked send).

## Read back (2026-10)

A user saw Preferred First Name + a Yes/No flagged empty at Submit though both showed filled
(2026-10); not reproduced - a clean form kept all 14 answers 12 s later. `fill` now waits 2.5 s, reads
each answer back (`holds`), fills a dropped one once more, else FAILs it for the user.

How each widget shows its answer, read after `fill` + the 2.5 s settle (`try` readout, 2026-10-05):

| Type | Shows the answer as | Seen |
|---|---|---|
| String, Url, Email, Phone, LongText | box `value` | C, D, E |
| Date | plain text input, `value` "11/04/2026" (typed as given, month first) | C |
| Number | `input[type=number]`, `value` | E |
| Boolean | chosen button `aria-pressed="true"`, other "false"; 1 hidden checkbox | C, D |
| ValueSelect, short (3-8 options) | radios, chosen one `checked` | D, E |
| ValueSelect, long (15 options) | one `input[role=combobox]`, pick = its `value`; no radios | D |
| MultiValueSelect (9, 18 options) | checkboxes, each pick `checked` - 18 still checkboxes, not a search box | D, E |
| Location | `input[role=combobox]`; empty here (search blocked, nothing picked) | E |
| File | box text "<file name> Replace or drag and drop here"; `input[type=file]` value = fake path | C, D, E |

- `holds()` reads each kind as above (plan-nko.5): ticks by their own `checked` (an answer w/ no such
  option = not held), long ValueSelect by the search box `value`, Location by the answer's town inside
  the box `value`, Yes / No by `aria-pressed`; box or widget missing = not held. `put_choice` on a long
  list: skipped when the box already shows the pick, waits up to 8 s for the option, then the pick shown.
- Phone (C): an SMS-updates Yes / No consent sits inside the Phone wrapper (2 radios) - not a question
  in the form definition.
- Consent w/ empty title (D): a MultiValueSelect "I agree" (survey form, path `_systemfield_data_consent_ack`),
  title ""; its words ("I consent to my data being retained beyond one year ...") are the form entry's
  `descriptionHtml` - not on the field (keys read 2026-10-05: no description there). `try` ticked it.
  Now (plan-nko.26): the question read asks for each entry's `descriptionHtml`; an empty title takes its
  text, so the consent words name the box -> left for the applicant by `try`, `prepare` and `fill`.
  A box still w/o words = the applicant's own step on every system (`questions.signs`): what it agrees
  to is unknown.

## Closed posting (2026-10-05)

- Question read (`ApiJobPosting`, plain HTTP): 3 closed links on the list -> HTTP 200, `jobPosting: null`,
  no errors. Null = closed or never existed; can't tell which.
- Page (tenant F, measure, 2 loads): lands on `jobs.ashbyhq.com/<org>/`, heading "Page not found",
  "The page you requested was not found"; `window.__appData.posting` + `.organization` null (an open
  posting's page: both objects). No "closed" wording - `form.CLOSED` misses it.
- File: `.data/measure/jobs.ashbyhq.com-20261005-140653.json`.
- Check (plan-nko.5, `ashby.closed`, asked by `form.closed` when no form shows): question read; null ->
  the employer's public list `api.ashbyhq.com/posting-api/job-board/<org>` once: 404 (unknown org) =
  "can't tell (board moved?)"; list w/o the posting = "may have closed"; posting listed = "can't tell".
  `questions()` raises the same words. Ashby errors / 429 = "can't tell".

Check run over the links files (2026-10-05, plain HTTP, 1.5 s apart; first run at 0.3 s got 429 from
the question read after ~150 calls):

| List | Links | Form there | May have closed | Can't tell |
|---|---|---|---|---|
| open | 177 | 154 | 22 | 1 |
| closed | 31 | 18 | 13 | 0 |

- Open read as closed: 0. All 35 "may have closed": page's own `__appData.posting` + `.organization`
  null too = taken down since the list was made.
- The 1 "can't tell": question read null (no errors, minimal query + slug case too), yet on the board
  (listed) and its page carries the posting. Cause unknown; `prepare` can't read its questions
  (follow-up filed). Null alone is never "closed".
- 18 "closed" links still open per Ashby: the list's closed mark is older or from elsewhere.

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
