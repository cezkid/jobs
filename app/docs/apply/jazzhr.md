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
| date (`resumator-datepicker`) | plain text box + jQuery UI datepicker | type `YYYY-MM-DD`, Escape shuts the popup, read back: typing alone keeps the value (`try`, tenant D, 2026-10-03) |
| choice / yesno | native `select`; first option = no answer: `resumator_no_selection` ("-- No answer --", employer questions) or `0` ("No answer", system fields) | select by visible option text, exact; never the no-answer option. Options are often upper case (`YES` / `NO`, tenant B) - match case-insensitively, read back |
| checkbox question | hidden `input.resumator-questionnaire-checkbox-answer` named `resumator-questionnaire[<n>]` + one `input.resumator-questionnaire-checkbox` per option, id `resumator-checkbox-<n>-<i>`, value = option text; group label = `label[for=resumator-questionnaire-q<n>]` | tick by value; on Submit JazzHR's script joins the ticked values into the hidden box (`YES-\|\|-`), so read back the ticks, not the hidden box. Yes/No as two checkboxes (tenant B, 2 questions): tick one only. A lone checkbox under a certify / authorize text = attestation: applicant's own act, never ticked |
| Resume | `#resumator-resume-value` (file) sits in a hidden wrapper until the link "Attach resume" (`#resumator-choose-upload`) is clicked; "Paste resume" (`#resumator-choose-paste`) shows the textarea instead | click "Attach resume" first (a link that only shows the box, `href="#"`) so the user sees the file chosen, then set the file on the input; confirm by the name the box holds. Choosing the file sends nothing (`try`, 4 of 4: 0 writes); the file goes with the form on Submit. No check on choosing (size, type): `submit-resume.js` read 2026-10-06 checks only at Submit; the limit is the page's own words "(limit 5MB)" (4 of 4) - see Read back |
| Address | Street box carries the label; City / State / Postal only placeholders | find by id, never by label |
| EEO | two native selects, "Decline to answer" preselected | voluntary - left as the page has it |
| Human Check | reCAPTCHA v2 checkbox (`div.g-recaptcha`, required: "Please verify." if empty); its script adds a `g-recaptcha-response` box inside the form | applicant's own step; that box is no question (`ids_on_page` leaves it out) |
| Submit | `a#resumator-submit-resume` "Submit Application" - a link, not a button | never clicked |

The page's own required check counts a select's no-answer option as answered (`$.trim(val) == ''`
on `0` / `resumator_no_selection` is false, `submit-resume.js` 2026-10-03): the filler's report
must not trust a pre-set select as answered.

## What leaves the computer, when

Measured 2026-10-03, every write blocked + logged: `apply-form measure` (load) on 4 tenants, then
`apply-form try` (load, resume chosen, every box typed / picked / ticked) on the same 4.

| Step | Writes | Tenants |
|---|---|---|
| page load | 0; 1 on tenant D (a reCAPTCHA content-security report to `csp.withgoogle.com`, nothing typed in it) | 4 |
| resume file chosen | 0 | 4 |
| typing, choices, ticks | 0 | 4 |
| Submit | form data + resume, once (native form POST to the posting link) - never clicked, unmeasured live | - |

Earliest point anything the applicant typed or chose leaves: Submit. Page also loads New Relic
and Gainsight analytics scripts: 0 writes from them while filling (4 of 4); what they send after
Submit is unmeasured.

## Read back (2026-10)

`holds(page, q)` = what the page SHOWS, read once the form had time to keep it; `form.recheck`
fills a dropped answer once more, still gone -> FAIL, the user fills it by hand. Per kind:

| Kind | Read back as | Not held when |
|---|---|---|
| text / email / date / textarea | the box's value | it differs from the answer |
| phone | the box's digits | digits differ (page formatting ignored) |
| choice / yesno (select) | the option TEXT shown, any case | the no-answer option shows (`resumator_no_selection` / `0`) - the page's own check counts it answered (Widgets) |
| checkbox question | each box's own tick, by value | any box ticked against the answer, or no boxes; never the hidden join box (filled only at Submit) |
| lone checkbox (not attestation) | ticked = yes, unticked = no | tick against the answer |
| file | the name the file box holds | no file |

Upload (`put_file`), as Greenhouse / Ashby: page idle first (15 s cap; a page that keeps polling
is read anyway), "Attach resume" clicked, file chosen, then in order: the box doesn't hold the
file name -> ASK; JazzHR's own error text by the resume box (`.resumator_label_error`,
`.dv_error` - what its script writes, at Submit only per `submit-resume.js` 2026-10-06) -> FAIL
in the page's words; file over the page's stated limit ("limit 5MB") -> FAIL with those words, the
user picks a smaller file. Server's own verdict on the file: only at Submit - unmeasured.

Covered by `app/tests/fixtures/dom/jazzhr-form.html` (tenant B form + tenant D screening selects
and start date) in real headless Chrome: text, email, phone, upper-case YES / NO select, choice
select, system select (citizenship), date, Yes/No checkbox pair, resume upload. Unmeasured - named
in JazzHR's script, seen on no tenant: felony question, country select, disability select,
two-stage form (resume first, rest on a second step; `#resumator-two-stage-resume-toggle`). No
live read-back yet (fixtures + saved `try` runs only, 2026-10-06).

## Closed posting

Measured 2026-10-06, plain GET of every link in `.data/links/jazzhr-open.txt` + `-closed.txt`
(2 s apart, 0 page loads, 0 errors, 0 429), then each employer's own job list once (13 employers):

| List | Links | Form on page | 410 gone |
|---|---|---|---|
| open | 27 | 12 | 15 |
| closed | 2 | 1 | 1 |

Taken down = 410 + the careers page + the posting's own words, no form (16 of 16): "This position
is no longer available" 15, "Hiring for this position has been put on hold at this time" 1.
Employer's own job list agrees: 0 gone postings listed, 11 of 13 live forms listed (2 live but
unlisted - the link still works). Unknown posting id: 404 + the careers page (1 tenant,
2026-10-03).

`questions` raises on 404 / 410 with the page's words ("the posting says \"This position is no
longer available\" - it may have closed"); `closed(url)` (asked by `form.closed` when no form
comes up) gives the same, "can't tell" on another status or no answer, never a guess.

Open read as closed: 0 (13 of 13 with a form read open, 1 of them on the closed list; 16 of 16
read closed are 410 with the words). Saved: `.data/measure/jazzhr-closed-check-2026-10-06.json`.
The open list lags: 15 of 27 "open" links were already taken down.

## Try (2026-10-03)

`apply-form try` on 4 postings, 4 tenants, synthetic answers: every box `ok` (A 18 of 18, B 17 of
18, C 11 of 11, D 16 of 16), canary ok, 0 writes. Left on the page, each the applicant's own: the
attestation checkbox (tenant B, "I certify / I authorize ..."), Human Check (all 4).

In the Job Finder window (2026-10-06, 2 tenants, writes blocked): fills as here, Human Check a blank space
with the block on - `vscode-browser.md` #JazzHR - route 2. Not offered there yet (plan-k8n.5).

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | salary + 6 employer questions (4 selects, 1 text, 1 textarea pronouns); EEO |
| tenant B | Address required; 7 employer questions incl. checkbox groups (attestation + 2 Yes/No as checkboxes), Yes/No selects in upper case; EEO |
| tenant C | shortest: contact + resume + salary + 1 employer question (work authorization as a textarea); no EEO |
| tenant D | Address optional; system screening fields (citizenship, 18+, start date, weekends, evenings) + 2 employer selects; no EEO |
