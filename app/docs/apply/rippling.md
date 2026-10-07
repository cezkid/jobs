# Rippling application forms - measured facts

**Not filled yet** - no system module; `prepare` says "not supported yet". Facts for the owner's
pick of which systems get a filler (plan-k8n.23).

Rippling Recruiting = hiring system on one host for every employer:
`ats.rippling.com/<employer>/jobs/<id>`, form at the same link + `/apply` (`?step=application`).
Next.js page, assets from `ats.us1.rippling.com`. Tenant named by letter, never employer.

Measured 2026-10-06 (plan-k8n.21): 3 postings, 3 employers through `apply-form measure` (2 loads
each, canary ok: 0 received, 9 blocked), + the posting page of every link on the list by plain
GET (13 read; 2 s apart, 0 429). Page loads on the host: 6. Raw notes + saved pages:
`.data/measure/manatal-rippling-2026-10-06/` (private, not shipped).

## Links

| Link | Answer (plain GET, 2026-10-06) |
|---|---|
| `/<employer>/jobs/<id>` | posting page, form definition inside (13 of 15 open links) |
| same, posting gone | 308 -> `/<employer>/jobs?rr_message=job_not_found` (2 of 15 "open", 1 of 1 closed) |

## Form definition

In the posting page's `__NEXT_DATA__`: `props.pageProps.apiData.jobPost.activeJobApplication`
(also `/_next/data/<build>/en-US/<employer>/jobs/<id>/apply.json`). No separate request.

- `basicQuestions: [{oid, fieldType, title, required}]`
- `additionalQuestions: [{name, id, form: {questions, sections, skipLogic}}]`, each question
  `{uniqueKey, title, dataType, questionType, isRequired, strChoices, intChoices,
  isMultiSelectEnabled, isOtherEnabled, allowComments}`
- `eeocQuestionnaireEnabledForJobPost` true on 12 of 13

Public job list per employer: `GET api.rippling.com/platform/api/ats/v1/board/<employer>/jobs` ->
`[{uuid, name, department, url, workLocation}]` (1 probe).

| Part | Holds (13 forms) | Filler rule |
|---|---|---|
| basic, required 13 of 13 | `first_name`, `last_name`, `email`, `phone_number` (PHONE_NUMBER), `location` ("Location (city only)"), `resume` FILE | shared keys |
| basic, never required | `pronouns` 12, `current_company` 12, `linkedin` 12 (5 required), `cover_letter` FILE 11, `website` 6 | pronouns = the user's call, left unless on file |
| additional | 18 groups, 45 questions; 0 sections, 0 skip logic; 3 postings none | `title` = question, `isRequired` |

Question types (45): KNOCKOUT 15 (Yes / No select, `isMultiSelectEnabled` true), SINGLE_SELECT_RADIO
12, SHORT_ANSWER 7, YES_NO_SCALE_4 3 (Strong No ... Strong Yes), LONG_ANSWER 2, DATE 2,
SINGLE_SELECT_DROPDOWN 2, MULTI_SELECT_CHECKBOX 2. Kinds: KNOCKOUT -> yesno, SHORT_ANSWER ->
text, LONG_ANSWER -> longtext, radio / dropdown / scale -> choice, checkbox -> multichoice,
DATE -> date. Some allow a comment ("Add comment" button) - left.

## Widgets (3 tenants, 2026-10-06)

| Box | On the page | Filler rule |
|---|---|---|
| text boxes | ids `field-N` (React), `name` random per load (changed both loads, 3 of 3); question labels not tied to the box (label `''`) | find by the words beside the box, matched to the definition's `title` - never id or name |
| KNOCKOUT / dropdown | div combobox showing `Select` | open, click the option by text |
| phone | country = combobox labelled `Search` (required) | pick country, then digits |
| pronouns | combobox | left unless on file |
| date | 3 boxes month / day / year | split the date |
| scale | radiogroup | pick by text |
| radios / checkboxes | `name` = `customQuestions.<groupid>.<uniqueKey>` | stable: definition ids |
| resume / cover letter | `input[data-testid=input-resume]` / `input-cover_letter`, "Drop or select (.doc/.docx/.pdf)", max 10 MB (script) | choose first: the page reads the resume and fills boxes from it (below) |
| EEO | same page: gender, race (combobox input), Hispanic, veteran - voluntary | the user's call, never answered for them |
| SMS opt-in | radiogroup | the applicant's own consent - left |

Closed shadow root = Turnstile container (not readable, 3 of 3). One page, Submit button reads
`Apply`. Never clicked.

## What leaves the computer, when

On load (blocked log, 6 loads): Cloudflare `cdn-cgi/challenge-platform/h/g/precursor` POST 1 per
load; Datadog `browser-intake .../api/v2/rum` 4-7 per load; Datadog `/api/v2/replay` (session
replay) on 2 of 6 loads - what replay carries (typed text?): unmeasured.

Turnstile token taken at `Apply` (`getAndResetTurnstile`, an interactive check if it fails) -
script read.

Resume: uploaded as soon as chosen (script: `GET v1/utility/file_upload_url` signed link, upload
with progress), then its stored link is sent to be read and fill boxes - before Apply. No live
upload seen. Location: a hidden `externalPlaceId` behind a place search; per-letter lookups
unmeasured. Contact details + answers: at Apply (never clicked - unmeasured past it).

## Closed posting

308 to the employer's job list with `rr_message=job_not_found` (3 of 3 gone links). Plain GET,
no page load. Open read as closed: 0 of 13.

## Cost

Filler ~2-3 beads (Lever / Ashby size): random names -> match by label to the definition,
comboboxes, 3-box date, resume read may overwrite filled boxes (upload first, then fill),
Turnstile at Apply, Datadog session replay on the page.
