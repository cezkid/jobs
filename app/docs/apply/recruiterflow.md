# Recruiterflow application forms - measured facts

Filler: `app/apply/systems/recruiterflow.py` (2026-10-30). Tests: `app/tests/test_apply_recruiterflow.py`.

Recruiterflow = recruiting firms' own applicant system, one host for every firm:
`recruiterflow.com/<firm>/jobs/<id>`, form on the posting page itself (one page, no Next). The site
shows the recruiting firm; the posting may describe the hiring company without naming it (tenant A:
"an early-stage, Series A fintech company"). React page, form script
`/static/application-form/js/application-form-src-bundle.js`. Tenant named by letter, never firm.

Measured 2026-10-30: 3 postings, 3 firms (tenants A, B, C), each posting page by one plain GET;
`apply-form measure` on tenant A (2 loads, canary ok, 9 of 9 blocked); `apply-form try` on all 3
(tenant A three times while fixing the filler); the form script read (plain GET); one real application
filled by hand through the Chrome extension (tenant A), which is why this filler exists. Saved
definitions: `app/tests/fixtures/recruiterflow/tenant-<a-c>.json` (firm -> Acme, a file link in a list
-> example.com); a stand-in page with the measured markup: `form.html`.

## Links

freehire `source` recruiterflow: 8 of 8 links on a user's list `https://recruiterflow.com/<firm>/jobs/<id>?utm_source=freehire.me`,
3 firms (2026-10-30). Id = digits. `application_url` = the posting without the tail.

A closed posting: unmeasured (none found). The definition carries `job_visibility_id` and
`ACTIVE_JOB_VISIBILITY` `[1, 2, 3, 4]` / `JOB_VISIBILITY_CLOSED` `6`: a visibility outside the active
list reads as closed; 404 / 410 or a page with no definition as "may have closed".

## Form definition

In the posting page: `<script>var convertedToJSON = {...}; window.applyJobData = convertedToJSON;</script>`.
Plain GET, no browser - only the posting link goes out, as when opening it. `application_form`:

| Part | Holds | Filler rule |
|---|---|---|
| `personal_info: [{key, display_name, requirement_type}]` | `name`, `email`, `phone`, `address` (Location), `linkedin_profile` | `requirement_type` `mandatory` / `optional` / `off` (off = not drawn). Name = First + Last boxes; Location = city, state, zip (home_address) + a Country list |
| `candidate_profile` | `resume`, `cover_letter` (files), `summary` (text area), `experience`, `education` (rows) | resume mandatory on 3 of 3; cover letter off on A + C, optional on B; experience mandatory on C |
| `questions: [{question_id, question_text, custom_field_view_field_id, requirement_type, choices, is_knockout, rank}]` | the firm's own questions, by `rank` | id `q<question_id>`; label on the page = `question_text` |

Question types (`custom_field_view_field_id`, the bundle's own `APPLICATION_FORM_VIEW_FIELD` table):
1 short text, 2 long text, 3 rich text, 4 number, 5 money, 6 date, 9 yes / no, 10 single select, 11
multi select, 12 money range, 13 number range, 14 file, 19 parent-child. Seen on tenant A (11
questions; B + C have none): 12, 10, 9, 11, 2. A range is two boxes, Min + Max: two `number`
questions `q<id>.min` / `.max` - pay on tenant A, so the user's own answer (`questions` "the pay you
expect"). `is_knockout` false on all 11.

`choices` hold blanks and, on tenant A, another applicant's file link among an office-setting list's
options (the page draws it as an option): blanks and links are never offered as answers. Tenant A's
"What's most important" list repeats some options in quotes - kept, the page offers them.

## Widgets (tenant A, 2026-10-30; same markup on B + C)

| Box | On the page | Filler rule |
|---|---|---|
| firm's own boxes | `input[name=personal_info.first_name / last_name / email / phone / linkedin_profile]`, `personal_info.location.city / state / postal_code` | one fill + change, read back (phone by digits, without US +1: the country picker beside it says +1) |
| question block | `div` > `p.form-label` (question text, `span.required` "*" when required) > `div.common-input-wrapper` > the box | found by the label's whole words; ids are per type (`rf-application-form-12` on every money range), never used |
| text / long text / number | `input` / `textarea` in the block | as above; number by digits |
| money range | `input[placeholder=Min]`, `input[placeholder=Max]` | digits typed, the page shows `180,000` - read back by digits |
| yes / no | `button.yes-input`, `button.no-input`; the picked one gets class `selected`; "Clear" appears | click, read the class back |
| single / multi select, Country | react-select: `input[role=combobox]` (`react-select-<n>-input`); menu drawn on `<body>`, options `react-select-<n>-option-<i>` (role=option); a multi list stays open while picking; "Clear" / "Clear All" after a pick | click the box (Country: type its name), click the answer's option, Escape; read back = the value container's words (the input's grandparent), placeholder ("Click to view options", "Country") dropped. Options by this list's own id: the phone box's hidden country list is role=option too (a filler waiting on role alone never saw a menu - try, 2026-10-30) |
| Experience / Education | rows by "+Add Experience" / "+Add Education": company, title, date pickers, "I am currently working in this role" | not filled: the user's on the page |
| date, rich text, parent-child | unmeasured (none seen) | date: the user picks it in the calendar |
| Submit | button "Submit Application" | never clicked |

Cookie notice: "Got it!" only - no decline offered (tenant A).

## Resume

`#fileInput` (hidden `input[type=file]`) in a drop area at the top. Choosing a file sends it at once:
POST `/api/file/generate-file-id`, then the file in 2 MB chunks to `/api/file/upload` (bundle; try's
blocked log shows the first, 3 of 3 tenants). On success the page toasts "File uploaded successfully",
draws the name in `.file-list-item` (cut at 35 letters + "...") and fills boxes from the server's
`parsed_data`: first + last name, email, phone, LinkedIn (tenant A, real application). Its name read can
be wrong - tenant A got First "Wcag", Last "2.2" from a skills line. So the resume goes first (as on
every form), `fill` waits up to 15 s for the name box to change, and the name answers are typed after.
Under try's block the upload never shows ("upload not confirmed" - not measurable while blocked).

## What leaves when

- resume: the firm's Recruiterflow site, the moment it is chosen (above) - `FILE_ON_CHOICE`
- everything else: at Submit (unmeasured: Submit never clicked; the bundle builds one form of every
  answer then). Typing sent nothing in 3 of 3 tries: every request, reads too, came while the resume
  was being chosen (its upload, a spinner icon, the trackers below) - none while a box was typed.
- every page posts errors to Sentry on load (3 of 3). The firm's own tracking code: tenant B Google
  Analytics (two collects as the resume was chosen); tenant C Google Ads, LinkedIn, Intercom, factors.ai and
  cr-relay (one batch as the resume was chosen). What those held: unmeasured.
