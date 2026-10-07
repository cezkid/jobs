# Manatal application forms - measured facts

**Not filled yet** - no system module; `prepare` says "not supported yet". Facts for the owner's
pick of which systems get a filler (plan-k8n.23).

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
forms have them. Live try: unmeasured (no filler).

Resume: the script uploads it ONLY at Submit - presigned link
(`jobs/apply-by-career-page-resume-get-presigned-url/`), then to S3, then the answers POST
(script read; no live upload seen). Contact details + answers: at Submit.

## Closed posting

404 on the apply page (1 of 1 closed, 11 of 58 on the open list). The employer's public job list
(above) can confirm it - unmeasured per posting.

## Cost

Filler ~1 bead (JazzHR / BambooHR size): stable names, definition by plain GET, file leaves only
at Submit. Watch: full name in one box, required not in the page, the array's repeated id.
