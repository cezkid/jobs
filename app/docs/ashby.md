# Ashby application forms - measured facts

Ashby runs the careers site for many tech employers (`jobs.ashbyhq.com/<company>/<posting id>`).
`app/apply/ashby.py` reads the form's questions from Ashby's public job board, then fills them in
a real Chrome window and lets go before **Submit**. Each fact names the tenant it was measured
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
| Location | `input[role=combobox]`; places appear as `[role=option]` after typing | type slowly, pick the option starting with the city; shows as "City, State, Country" |
| Boolean | two buttons Yes / No + hidden checkbox (checked = Yes, unchecked for both No and unanswered) | click the button by name; check the box only for Yes |
| ValueSelect | radio group, option labels = `selectableValues` | click the label with the exact text |
| File (`_systemfield_resume`) | `input[type=file]` in the Resume box; separate from the "Autofill from resume" uploader | upload into the Resume box only, first, so nothing re-fills over typed answers |

## Browser

Chrome is started as a normal window with its own profile (`.data/apply-browser`) and a debugging
port; the filler attaches, fills, and disconnects. No `--enable-automation`: `navigator.webdriver`
reads `false`, so the employer's spam check sees an ordinary browser when the user clicks Submit.

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | banner: one application per role per 60 days - tell the user before they submit |
