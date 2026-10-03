# JazzHR application forms - measured facts

JazzHR = careers site for many small + mid employers (`<co>.applytojob.com/apply/<id>/<slug>`; 2.0%
of freehire's US postings, 2026-10-03). Measured 2026-10-03: 4 postings, 4 tenants (A-D), each
`apply-form measure` (2 loads, canary ok, 9 of 9 blocked) + one plain GET of the posting page.
Tenant named by letter, never employer; add yours as a new line. Saved forms:
`app/tests/fixtures/jazzhr/tenant-<a-d>.html` (the `<form>` only, employer -> Acme).

## Form definition

No JSON anywhere (measure: 0 JSON responses on all 4). The form is server-rendered in the posting
page itself: `GET <posting link>` -> 200, `<form id="form_submit_new_resume" method="POST"
enctype="multipart/form-data">`, action = the posting link. Plain HTTP GET, no browser - only the
listing id goes out, same as opening the posting. One page, no Apply click, no Next (4 of 4).

Each question = one `div.form-group`: `label.control-label` (text; `<i class="asterisk">` =
required) + its control. JazzHR's own submit script decides required the same way (asterisk in the
label, `/js/apply/submit-resume.js`, 2026-10-03).

| Field (name) | Seen | Shared kind / key |
|---|---|---|
| `resumator-firstname-value`, `-lastname-`, `-email-` (type email), `-phone-` (type tel) | 4 of 4, always required | text `first_name` / `last_name`, email, phone |
| `resumator-address-value` + `-city-`, `-state-`, `-postal-` | 4 of 4; one label "Address" over all four boxes, asterisk on 3 of 4; City / State / Postal have no label, only a placeholder | text `street`, `city`, `state`, `zip` |
| `resumator-resume-value` (file) / `resumator-resumetext-value` (textarea) | 4 of 4, required: either one | file `resume` |
| `resumator-salary-value` (text, "Desired salary") | 2 of 4, required both | text, asked |
| `resumator-citizen-value` (select: US citizen / non-citizen for any employer / for current employer / seeking authorization, Canada, Other; `optgroup` per country) | 1 of 4 | choice, asked (work permit) |
| `resumator-over18-value`, `-weekends-`, `-evenings-` (select Yes / No) | 1 of 4 | yesno |
| `resumator-start-value` (text, class `resumator-datepicker`, format `yy-mm-dd` -> 2026-10-03) | 1 of 4 | date |
| `resumator-questionnaire[<n>]` - employer's own questions | 4 of 4, 1-7 per form | select -> choice (Yes/No only -> yesno), text -> text, textarea -> longtext, checkboxes -> multichoice |
| `resumator-eeo_gender-value`, `resumator-eeo_race-value` (select, "Decline to answer" preselected) | 2 of 4, after "The following questions are entirely optional." | choice, voluntary - left for the user |
| hidden: `resumator-subdomain-value` (tenant), `-job-value` (posting id), `-sfdc-id`, `-application-id`, `-source-value`, `uploaded-file`, `linkedin-profile`, `resumator-xml-value` (textarea, class `none`) | 4 of 4 | skipped |

Named in JazzHR's submit script, not on any of the 4 forms (unmeasured): `resumator-felony-value` +
`resumator-felonyexplain-value`, `resumator-country-value`, `resumator-eeoc_disability` (+ `_date`,
`_signature`), `resumator-wmyu` and a two-stage form (`form#stage_one_application`, posts to
`/apply/job/<id>/stage-one`).

Employer questions seen (4 tenants): work authorization (as a textarea in tenant C - yes/no asked
in a free-text box), sponsorship, prior employment with the employer, non-compete, background
check, export-control access, how did you hear (choice), referrer name, desired salary as a range,
pronouns (textarea), years of experience (choice `0-1 ... 10+`), lives near the job, and one
attestation (tenant B: a single `YES` checkbox under a long "I certify / I authorize the company to
investigate references" text, required).

## Widgets (4 tenants, 2026-10-03)

| Box | On the page | Filler rule |
|---|---|---|
| every question | stable ids: `resumator-<field>-value`, employer ones `resumator-questionnaire-q<n>` (name `resumator-questionnaire[<n>]`) | find by id via `[id="..."]`; ids never changed between two loads (0 of 4) |
| text / email / tel / date | plain `input.form-control` | `fill`, read back |
| date (`resumator-datepicker`) | plain text box + jQuery UI datepicker | type `YYYY-MM-DD`, read back; no popup click needed (unmeasured: whether typing alone keeps the value) |
| choice / yesno | native `select`; first option = no answer: `resumator_no_selection` ("-- No answer --", employer questions) or `0` ("No answer", system fields) | select by visible option text, exact; never the no-answer option. Options are often upper case (`YES` / `NO`, tenant B) - match case-insensitively, read back |
| checkbox question | hidden `input.resumator-questionnaire-checkbox-answer` named `resumator-questionnaire[<n>]` + one `input.resumator-questionnaire-checkbox` per option, id `resumator-checkbox-<n>-<i>`, value = option text; group label = `label[for=resumator-questionnaire-q<n>]` | tick by value; on Submit JazzHR's script joins the ticked values into the hidden box (`YES-\|\|-`), so read back the ticks, not the hidden box. Yes/No as two checkboxes (tenant B, 2 questions): tick one only. A lone checkbox under a certify / authorize text = attestation: applicant's own act, never ticked |
| Resume | `#resumator-resume-value` (file) sits in a hidden wrapper until the link "Attach resume" (`#resumator-choose-upload`) is clicked; "Paste resume" (`#resumator-choose-paste`) shows the textarea instead | set the file on the hidden input directly (no click needed for a file chooser); confirm by its value. Upload sends nothing until Submit (the page script has no upload request; real file sent with the form, max 5 MB per the page text) - measured by reading the script, unmeasured live |
| Address | Street box carries the label; City / State / Postal only placeholders | find by id, never by label |
| EEO | two native selects, "Decline to answer" preselected | voluntary - left as the page has it |
| Human Check | reCAPTCHA v2 checkbox (`div.g-recaptcha`, required: "Please verify." if empty) | applicant's own step |
| Submit | `a#resumator-submit-resume` "Submit Application" - a link, not a button | never clicked |

The page's own required check counts a select's no-answer option as answered (`$.trim(val) == ''`
on `0` / `resumator_no_selection` is false, `submit-resume.js` 2026-10-03): the filler's report
must not trust a pre-set select as answered.

## What leaves the computer, when

Measured on load only, every write blocked (2026-10-03): 0 writes on 3 tenants, 1 on tenant D (a
reCAPTCHA content-security report to `csp.withgoogle.com`). Page also loads New Relic and Gainsight
analytics scripts - their later sends unmeasured. Typing, upload and choices: unmeasured (filled by
the build bead from `apply-form try`). Form data leaves once, on Submit (native form POST to the
posting link).

## Closed posting

Unmeasured (all 4 open; JSON-LD `validThrough` about 3 months after `datePosted`, 4 of 4).

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | salary + 6 employer questions (4 selects, 1 text, 1 textarea pronouns); EEO |
| tenant B | Address required; 7 employer questions incl. checkbox groups (attestation + 2 Yes/No as checkboxes), Yes/No selects in upper case; EEO |
| tenant C | shortest: contact + resume + salary + 1 employer question (work authorization as a textarea); no EEO |
| tenant D | Address optional; system screening fields (citizenship, 18+, start date, weekends, evenings) + 2 employer selects; no EEO |
