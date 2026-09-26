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
ValueSelect, LongText, Boolean. Voluntary disclosure (EEO) surveys not listed -> `fill` counts
on-page questions missing from the file, leaves them to the user.

## Widgets (tenant A)

| Type | On the page | Filler rule |
|---|---|---|
| every question | wrapper `div[data-field-path="<path>"]`, same path as form definition | find each box by path, never by label |
| String, Email, Phone, LongText | plain input / textarea | Playwright `fill` (React takes it) |
| Location | `input[role=combobox]`; places appear as `[role=option]` after typing | type slowly, pick option starting w/ the city, none -> clear + ASK (never first option); shows as "City, State, Country" |
| Boolean | two buttons Yes / No, chosen one `aria-pressed="true"`; hidden checkbox checked = Yes, unchecked for both No + unanswered | click button by name unless already chosen (whether a second click clears it is unmeasured - avoided); poll `aria-pressed` up to 3s - set a moment after click |
| ValueSelect | radio group, option labels = `selectableValues` | click label w/ exact text; confirm its radio checked |
| File (`_systemfield_resume`) | `input[type=file]` in Resume box; separate from "Autofill from resume" uploader | upload into Resume box only, first, so nothing re-fills over typed answers |

## Browser

Shared w/ every system: `apply-systems.md`, `app/apply/browser.py`.

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | banner: one application per role per 60 days - tell user before they submit |
