# Ashby application forms - measured facts

Ashby runs the careers site for many tech employers (`jobs.ashbyhq.com/<company>/<posting id>`).
`app/apply/systems/ashby.py` reads the form's questions from Ashby's public job board and types
answers into its widgets; the shared steps (`apply-form`) are in `apply-systems.md`. Each fact names the tenant it was measured
on by letter, never the employer; add yours as a new line.

## Ashby's own "Autofill from resume" (tenant A, 2026-09)

Fills contact boxes only (name, email, phone, LinkedIn). Questions the employer wrote - years of
experience, free-text answers, work permit Yes/No - are always left empty. Users read this as "the
ATS rejected my resume"; it did not. Same resume's text read cleanly in two PDF readers. Outside
autofill add-ons (Simplify, JobWizard) fill more, but hold the resume on their servers.

## Form definition

`POST https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting`, no key:
`jobPosting(organizationHostedJobsPageName, jobPostingId) { applicationForm { sections {
fieldEntries { ... on FormFieldEntry { isRequired field } } } } }`. `field` is a JSON blob:
`path`, `title`, `type`, `selectableValues`. Types seen (tenant A): String, Email, Phone, Location,
File, ValueSelect, LongText, Boolean. Voluntary disclosure (EEO) surveys are not in this list -
`fill` counts questions on the page that are not in the file and leaves them to the user.

## Widgets (tenant A)

| Type | On the page | Filler rule |
|---|---|---|
| every question | wrapper `div[data-field-path="<path>"]`, same path as the form definition | find each box by path, never by label |
| String, Email, Phone, LongText | plain input / textarea | Playwright `fill` (React takes it) |
| Location | `input[role=combobox]`; places appear as `[role=option]` after typing | type slowly, pick the option starting with the city, none -> clear + ASK (never the first option); shows as "City, State, Country" |
| Boolean | two buttons Yes / No, the chosen one `aria-pressed="true"`; hidden checkbox checked = Yes, unchecked for both No and unanswered | click the button by name unless already chosen (whether a second click clears it is unmeasured - avoided); poll `aria-pressed` up to 3s - it is set a moment after the click |
| ValueSelect | radio group, option labels = `selectableValues` | click the label with the exact text; confirm its radio is checked |
| File (`_systemfield_resume`) | `input[type=file]` in the Resume box; separate from the "Autofill from resume" uploader | upload into the Resume box only, first, so nothing re-fills over typed answers |

## Browser

Shared with every system: `apply-systems.md`, `app/apply/browser.py`.

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | banner: one application per role per 60 days - tell the user before they submit |
