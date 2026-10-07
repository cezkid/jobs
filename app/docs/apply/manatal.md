# Manatal application forms - measured facts

Filled by `app/apply/systems/manatal.py` (plan-k8n.29): questions from the form definition (plain
HTTP), answers typed into the page in Job Finder's own Chrome, read back off the page.

Manatal = hiring system whose careers pages sit on one host for every employer:
`www.careers-page.com/<employer>/job/<hash>`, form at the same link + `/apply`. Vue 2 page
(axios, select2, flatpickr), form script `career_page/js/application-form.js` from Manatal's own
static host. Tenant named by letter, never employer.

Measured 2026-10-06 (plan-k8n.21): 3 postings, 3 employers through `apply-form measure` (2 loads
each, canary ok: 0 received, 9 blocked), + the form definition of every link on the list by plain
GET (47 forms, 27 employers; 2 s apart, 0 429). Page loads on the host: 6. Raw notes + saved
definitions: `.data/measure/manatal-rippling-2026-10-06/` (private, not shipped).

## Links

| Link | Answer (plain GET, 2026-10-06) |
|---|---|
| `/<employer>/job/<hash>/apply` | the form page (47 of 58 open links) |
| same, posting gone | 404 (11 of 58 "open" links, 1 of 1 closed) |

Apply page HTML carries `selectedJobId` (number), `clientSlug`, `isTCPPRequired`, `csrf_token`.

## Form definition

`GET https://www.careers-page.com/api/v1.0/jobs/<selectedJobId>/application-form/` - JSON list,
public, no key (47 of 47; the page itself fetches it). Each field: `id`, `label`, `is_required`,
`is_protected`, `field_type`, `response_type`, `social_media`, `horizontal_rank`, `vertical_rank`,
`client_field` (+ `_slug`, `_field_type`, `_answer_choices`, `_answer_choice_type`).

Public job list per employer: `GET /api/v1.0/c/<clientSlug>/jobs/?page_size=&page=` ->
`{count, next, previous, results: [{id, hash, position_name, ...}]}`; `id` = `selectedJobId`, so
the definition is reachable without the apply page (1 probe).

| Part | Holds (47 forms, 275 fields, 3-8 each) | Filler rule |
|---|---|---|
| standard | `full_name`* 47 (one box, not first / last), `email`* 47, `phone_number` 46 (45 required), resume (`field_type` resume) 47, all required | shared keys: full name, email, phone, resume |
| cover letter | `description` 45 - a long text box, not a file; never required | letter text pasted, or left |
| social | `social_media` 3 = LinkedIn, 14 (11 required) | linkedin |
| employer fields | `current_position` 9 (required), `expected_salary` integer 3, longtext 8, char 3, boolean 2, checkbox array 1 (Yes / No) | kinds: char -> text, longtext -> longtext, boolean -> yesno, integer -> number, array -> multichoice |
| terms | `terms_and_condition` checkbox 47 of 47 (`isTCPPRequired`) | the applicant's own consent - never ticked for them |

Yes / No questions often come as plain `char` text boxes, not booleans.

## Widgets (3 tenants, 2026-10-06)

| Box | On the page | Filler rule |
|---|---|---|
| any field | `input#field<defid>`, `name` = definition id - same both loads (0 changed ids, 3 of 3) | find by `name` = id |
| required | NOT in the page: only a `*` span in the label | required from the definition, never the page |
| boolean | one checkbox | tick = yes |
| array | checkboxes, each id the literal `<id>{index}` (template bug, same id on every box) | pick by `value`, never id |
| integer salary | `input type=number` + `select#expected_currency` + `select#expected_frequency` (Hourly ... Yearly) | number + both selects |
| page | `#app` hidden until Vue mounts | wait for it before reading |

One page, Submit button reads `Apply`. Never clicked.

## What leaves the computer, when

On load (blocked log, 6 loads): Google Analytics `g/collect` (3 POST, 1 load). No captcha frame
(0 of 3). An AWS WAF challenge appears only when the definition GET answers
`x-amzn-waf-action: challenge` (page script) - seen 0 times in 47 plain reads + 6 loads.

While filling: typing sends nothing, from the form script; a location search
(`consolidated-locations?search=`) runs only in education / experience entries - none of the 47
forms have them. Live try (below): 0 writes sent, only the 3 Google Analytics posts on load blocked.

Resume: the script uploads it ONLY at Submit - presigned link
(`jobs/apply-by-career-page-resume-get-presigned-url/`), then to S3, then the answers POST
(script read; no live upload seen). Contact details + answers: at Submit.

## Closed posting

404 on the apply page (1 of 1 closed, 11 of 58 on the open list). `closed()`: 404 -> "may have
closed"; a 200 page without `selectedJobId` -> no form; other answers -> can't tell.

Closed check 2026-10-07 (`.data/measure/manatal-closed-check-2026-10-07.json`; plain GETs 2 s apart,
0 page loads): open list 58 -> 47 form, 11 read closed; closed list 1 -> 1 read closed. Each employer's
own job list (29 employers): 47 of 47 forms on it, 12 of 12 read closed off it. **Open read as
closed: 0.**

## Filler rules

| Definition | Question | On the page |
|---|---|---|
| `full_name` | text, key name (one box, never split) | `#field<id>` |
| `email`, `phone_number` | email, phone | `#field<id>` |
| `field_type` resume | file, key resume | `input[type=file]#field<id>` |
| `attachment` | file, no key (the user's own file) | ASK |
| `social_media` 3 | url, key linkedin | `#field<id>` |
| `expected_salary` / `current_salary` | number + `<id>:currency` (Manatal's own currency names, `/api/v1.0/currencies/`, read only when a pay box exists) + `<id>:frequency` (Hourly ... Yearly) | number box + `select#expected_currency` / `#expected_frequency` |
| client field `dropdown` / `multiple_select_dropdown` | choice / multichoice | native `select` (select2 on top; the script reads the native one) |
| client field `checkbox` / `multiple_choice` | multichoice / choice; Yes + No or one lone box -> yes / no | ticks by `value` |
| `gender`, notice period, years, nationalities, languages, industries | choice / multichoice, options as the page lists them | `select` |
| other: `char` / `longtext` / `integer` / `boolean` / `datetime` | text / longtext / number / yes / no (one checkbox) / date | `#field<id>` |
| `educations`, `experiences` | ASK - entries added one by one on the page (0 of 47 forms) | - |
| date | ASK - the page's calendar (flatpickr) | - |
| `terms_and_condition` | never a question - the applicant's own consent | - |

Pay box: "$85,000" typed as 85000 (the box takes digits only).

## Read back (2026-10)

What `manatal.holds` reads off the page (`form.recheck`: refilled once, still gone -> FAIL to fill by
hand) - what shows, never the answer it was given. The form script reads every value straight from
the page at Submit (`field.val()`, `:checked`), so the page's value is what's sent.

| Kind | Read back |
|---|---|
| box (contact, pay, LinkedIn, employer text) | its value; phone by digits; pay as the digits typed |
| list (currency, per, employer list) | text of the option(s) picked; "Select ..." (value "") = not held |
| tick boxes / radios | every box: ticked exactly when its `value` is an answer |
| yes box (boolean) | its tick |
| resume | the box's label (`.custom-file-label`) shows a file name, not "Choose file", no error under it, the input holds the file |
| box not on the page | not held |

Upload: nothing leaves on choosing - the script checks the file, then the label shows its name, or
`small.text-danger` in the `.custom-file` block says "This file is invalid. Supported formats include
PDF, DOC, DOCX, or RTF (max 20MB)." `put_file`: page idle (15 s cap), file chosen, label = file name
-> ok; error words -> FAIL with Manatal's words; neither in 5 s -> ASK.

## Try (2026-10-07)

`apply-form try` on 3 postings, 3 tenants (tick boxes Yes / No; pay + currency + per with LinkedIn;
three Yes / No text boxes), synthetic answers: canary ok each (0 of 9 test writes through), every
box `ok`, required 6 of 6, 5 of 5, 7 of 7; 0 writes sent (3 Google Analytics posts blocked each).
`--upload-errors` on one: a `.png` -> FAIL with the page's words above; an empty file right after ->
FAIL (the `.png`'s words still up - empty alone unmeasured); the resume after -> ok, error gone.
Page loads on the host: 4.

## Cost

Filler ~1 bead (JazzHR / BambooHR size): stable names, definition by plain GET, file leaves only
at Submit. Watch: full name in one box, required not in the page, the array's repeated id.
Took 1 bead (plan-k8n.29, 3 contexts).
