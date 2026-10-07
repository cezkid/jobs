# Teamtailor application forms - measured facts

**Not filled yet** - no system module; `prepare` says "not supported yet". Facts for the owner's
pick of which systems get a filler (plan-k8n.23).

Teamtailor = hiring system, one site per employer: `<employer>.na.teamtailor.com/jobs/<id>-<slug>`
or the employer's own domain (same path). Form at the same link + `/applications/new`. Rails page
(Stimulus + Turbo). Tenant named by letter, never employer.

Measured 2026-10-07 (plan-k8n.22): 3 postings, 3 employers through `apply-form measure` (2 loads
each, canary ok: 0 received, 9 blocked), + posting and form of every link on the list by plain GET
(10 links, 6 employers; 2 s apart, 0 429), + the form script read. Page loads: 2 per site, 6 in
all (each employer its own host). Raw notes + saved pages:
`.data/measure/breezy-teamtailor-2026-10-07/` (private, not shipped).

## Links

| Link | Answer (plain GET, 2026-10-07) |
|---|---|
| `/jobs/<id>-<slug>` | posting page; form in a lazy frame (9 of 10 open links); 1 of 10 301 to a new slug, same host |
| same, posting gone | posting page, no form frame, "no longer" text (1 of 10 "open") |
| `/jobs/<id>-<slug>/applications/new` | the whole form page, Submit button included |

Measuring the posting page draws no form (tenant A): the frame loads only when scrolled into
view or Apply is clicked. Measure `/applications/new`.

## Form definition

No JSON definition - the form HTML is the definition. Plain GET of `/applications/new` with
header `Turbo-Frame: application_form` returns the whole form (9 of 9). Questions:
`div.question` with `data-question-mandatory`, `data-question-multiple-choice`; answers
`candidate[answers_attributes][N][question_id | boolean | text | number | choice | range]`.

| Part | Holds (9 forms) | Filler rule |
|---|---|---|
| standard | `candidate[first_name]`, `[last_name]`, `[email]` required 9 of 9; `[phone]` 9 (optional on 2 measured); resume required 9 of 9 | shared keys |
| cover letter | `[job_applications_attributes][0][cover_letter]` textarea 5 of 9 | text pasted, or left |
| LinkedIn | `linkedin_url` 9 (+ "Apply with LinkedIn" button) | linkedin |
| location | combobox 2 of 9 (`candidate[location][query]` + hidden address / city / state / zip / country / lat / long / place id); `location_ids` 1 | city search (below) |
| questions | 28 (0-10 per form), 26 mandatory: yes/no 11, text 11 (+1 long), number 2, choice 2, range 1 | yesno, text, longtext, number, choice; range unmeasured |
| knockout | "qualifying" yes/no on 1 employer (2 forms): form greyed until answered; wrong answer -> "You have to meet these requirements to be able to apply" | never shade an answer to pass it (Hold); say it plainly |
| consent | `consent_given` 9 of 9 required; future jobs 3; SMS 1 | the applicant's own - never ticked for them |

## Widgets (3 tenants, 2026-10-07)

| Box | On the page | Filler rule |
|---|---|---|
| any box | stable Rails names + real `<label for=>`; unlabelled only the range number box + Submit | find by `name` |
| yes/no | radios `value` true / false; id `boolean-<n>-true`, `n` differs per load (tenant B 7 of 7, C 2 of 2) | pick by `name` + `value`, never id |
| choice | radios `value` 1..n | pick by label text |
| range | hidden `input type=range` + visible number box `range-custom_number` | unmeasured |
| phone | intl-tel-input, country search box, default United States (+1) | country first, then number |
| resume, other files | hidden file inputs (Dropzone, no `name`), `#candidate_resume_remote_url`, `#candidate_file_remote_url` (max 3) | put file by id |
| email | typo hint shown in the page (nothing sent) | - |
| cookie banner | Accept all / Decline non-necessary / preferences | the user's choice - never ours |

One page, button "Submit application". Never clicked. Bot check: Teamtailor's own proof-of-work
solved in the page on load - no captcha frame, no user step (0 of 3 showed one).

## What leaves the computer, when

On load (blocked log, 6 loads): `POST /pageview` to the employer's Teamtailor site, 1 per load -
the only write seen. Script read: chat window after 5 s, a live presence channel on the form.

While filling (script read, no live upload seen):

| What | Where | When |
|---|---|---|
| Resume, other files | employer's Teamtailor site (`/uploads/presigned_data` with the file name), then its S3 storage | as soon as each is chosen - before Submit |
| Town or city typed | employer's Teamtailor site (`/location_suggestions/autocomplete`) | after 3 letters + 0.5 s pause, as typed; the pick -> `place_details` |
| Contact details, answers | employer's Teamtailor site | at Submit |

## Closed posting

Posting page without the form frame + "no longer" text (1 of 10). Status unmeasured on a 404 -
none seen.

## Cost

Filler ~1 bead (BambooHR / Workable size): stable names + real labels, form by plain GET,
proof-of-work runs itself, upload on choose. Watch: yes/no ids change per load, knockout greys
the form, location box on 2 of 9.
