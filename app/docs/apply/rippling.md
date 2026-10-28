# Rippling application forms - measured facts

Filler: `app/apply/systems/rippling.py` (2026-10-28). Tests: `app/tests/test_apply_rippling.py`.

Rippling Recruiting = hiring system on one host for every employer:
`ats.rippling.com/<employer>/jobs/<id>`, form at the same link + `/apply` (`?step=application`).
Next.js page, assets from `ats.us1.rippling.com`. Tenant named by letter, never employer.

Measured 2026-10-06 (plan-k8n.21): 3 postings, 3 employers through `apply-form measure` (2 loads
each, canary ok: 0 received, 9 blocked), + the posting page of every link on the list by plain
GET (13 read; 2 s apart, 0 429). 2026-10-27: 24 more posting pages by plain GET (2 s apart), 1
`measure` + 3 page probes (throwaway Chrome, block + canary, nothing typed), 3 `apply-form try`
(tenants B, C twice, D), and one real application filled by hand through the Chrome extension
(tenant A). Raw notes + saved pages: `.data/measure/` (private, not shipped).

## Links

| Link | Answer (plain GET) |
|---|---|
| `/<employer>/jobs/<id>` | posting page, form definition inside (13 of 15 open links 2026-10-06; 21 of 24 2026-10-27) |
| same, posting gone | 308 -> `/<employer>/jobs?rr_message=job_not_found` (2 of 15 "open", 1 of 1 closed; 3 of 24) |

## Form definition

In the posting page's `__NEXT_DATA__`: `props.pageProps.apiData.jobPost.activeJobApplication`
(also `/_next/data/<build>/en-US/<employer>/jobs/<id>/apply.json`). No separate request.

- `basicQuestions: [{oid, fieldType, title, required}]`
- `additionalQuestions: [{name, id, form: {questions, sections, skipLogic}}]` (null on 13 of 24), each
  question `{uniqueKey, title, dataType, questionType, isRequired, strChoices, intChoices,
  isMultiSelectEnabled, isOtherEnabled, allowComments, maxChars?}`
- one `uniqueKey` can sit in two groups (tenant B, 2026-10-27): question id = `customQuestions.<group id>.<uniqueKey>`,
  the page's own `data-testid` for that question
- `jobPost.eeocQuestionnaireEnabledForJobPost` true on 12 of 13 (2026-10-06): the EEO block is drawn

Public job list per employer: `GET api.rippling.com/platform/api/ats/v1/board/<employer>/jobs` ->
`[{uuid, name, department, url, workLocation}]` (1 probe).

| Part | Holds | Filler rule |
|---|---|---|
| basic, required on all | `first_name`, `last_name`, `email`, `phone_number` (PHONE_NUMBER), `location` ("Location (city only)"), `resume` FILE | shared keys; Location = key `city` (home_address) |
| basic, sometimes | `pronouns` (PRONOUN), `current_company`, `linkedin_link` (required on some), `website_link`, `cover_letter` FILE (required on 1 of 24) | pronouns from saved self-identification only |
| additional | 18 groups / 45 questions (2026-10-06); 0 sections, 0 skip logic | `title` = question, `isRequired`, `maxChars` -> max_chars |

Question types: KNOCKOUT, SINGLE_SELECT_RADIO, SHORT_ANSWER, YES_NO_SCALE_4 (Strong No ... Strong
Yes), LONG_ANSWER, DATE, SINGLE_SELECT_DROPDOWN, MULTI_SELECT_CHECKBOX. A KNOCKOUT is not always Yes /
No: tenant C's offered 4 worded answers (2026-10-27), so it is a `choice`, `yesno` only when its
options are exactly Yes / No. MULTI_SELECT_CHECKBOX -> multichoice, DATE -> date, LONG_ANSWER ->
longtext. "How did you hear" on tenant A: a MULTI_SELECT_CHECKBOX listing "Company Careers Page"
(`questions.own_site`). Some allow a comment ("Add comment" button) - left.

## Widgets

Every block carries a stable `data-testid` (4 tenants, 2026-10-27); `id` (`field-N`) and `name`
(random per load) never used.

| Box | On the page | Filler rule |
|---|---|---|
| basic text | `[data-testid=<oid>]` holding `input[data-testid=input-<oid>]` | one fill (insert, not keys) |
| employer question | `[data-testid=customQuestions.<group>.<key>]` | by its id |
| EEO | `[data-testid=eeoc.gender]`, `eeoc.race`, `eeoc.hispanicOrLatino`, `eeoc.veteranStatus` | saved self-identification only, after their yes |
| pronouns | `[data-testid=pronouns_strategy]`, a search combobox | list: She/her/hers, He/him/his, They/them/theirs, She/her/hers, they/them/theirs, He/him/his, they/them/theirs, Just use my name, Enter my pronouns |
| KNOCKOUT / dropdown / EEO | `div[role=combobox]` showing `Select`; race = an input combobox | click, then the `[role=option]` that is the answer - never the first |
| radios / ticks / scale | blocks `[role=radio]` / `[role=checkbox]` with `aria-checked`, words in a `<p>` (scale: `aria-label`) | click the visible block - a click on the hidden `input` did nothing (by hand, tenant A) |
| phone | country = search combobox showing `+1 US` (default), then `input-phone_number` | digits, a US number's leading 1 dropped; 10 digits show as 201-555-0100 |
| Location | `[data-testid=location]`, a place search (hidden `externalPlaceId` behind it) | town typed key by key, the one US place of that name clicked; two -> ASK |
| date | `input-month` / `input-day` / `input-year` (MM / DD / YYYY) | split the date |
| long answer | `textarea` (`maxlength` = `maxChars`, "0/100" counter) | one fill: 689 characters typed key by key stalled the page (CDP key event timed out at 30 s, all text in; by hand, tenant A) |
| resume / cover letter | `input[data-testid=input-resume]` / `input-cover_letter` in `label[data-testid=resume]` | upload first, wait for the read (below) |
| SMS opt-in | `[data-testid=sms_opt_in]` radiogroup, on every form opened (not in the definition) | the applicant's own consent - never filled; `ids_on_page` names it |

EEO options (3 tenants, 2026-10-27): Gender Male / Female / Non-binary / Choose not to disclose;
race American Indian or Alaskan Native / Asian / Black or African American / Middle Eastern or North
African / White / Native Hawaiian or other Pacific Islander / Two or more races / Choose not to
disclose; Hispanic Yes / No / Choose not to disclose; Veteran "I am not a protected veteran" / "I
identify as one or more of the classifications of a protected veteran" / "Choose not to disclose".
No disability question seen.

Closed shadow root = Turnstile container (not readable, every load). One page, Submit button reads
`Apply`; enabled once the required boxes were filled (tenant A, by hand). Never clicked.

## The resume read

Choosing the resume (tenant A, by hand, 2026-10-27): the page read it and filled first name, last
name, email, phone and Location some seconds later - Location got the resume's "NYC". So `fill`
puts the resume in first (`form.fill_page` does files first), waits until the first-name box fills
(at most 12 s), then types the rest and puts the town they live in over Location. With the upload
blocked (try) the box says "<file> upload failed" and nothing is read: `fill` reports FAIL then.

## Location

Typing a town (tenant A, by hand) listed "<town>, <ST>, USA", two UK towns of that name and a
"<town> Township" in another state; clicking one set it. Try: Google Maps' script loads
while the town is typed (`maps.googleapis.com/maps/api/mapsjs/gen_204`, 3 of 3 tries) -
the suggestions are Google's (`SEARCHED_WITH`). "New York" picked "New York, NY, USA" (3 of 3 tries).

## What leaves the computer, when

On load (blocked log, 6 loads + 3 tries): Cloudflare `cdn-cgi/challenge-platform/h/g/precursor` POST
1-2 per load; Datadog `browser-intake .../api/v2/rum` 4-7 per load.

While filling (3 tries, every write blocked): the resume and cover letter - `GET
api/v1/utility/file_upload_url` then `POST prod-rippling-us1-ats.s3.amazonaws.com` as each file is
chosen (3 of 3), plus a Sentry error report (`ingest.sentry.io`, the blocked upload); Datadog `rum`
and session replay (`/api/v2/replay`, 1 of 4 tries, while the resume, Location and race were filled) -
what replay carries (typed text?) is unmeasured: blocked every time.

Turnstile token taken at `Apply` (`getAndResetTurnstile`, an interactive check if it fails) -
script read. Contact details + answers: at Apply (never clicked - unmeasured past it).

## Try results (2026-10-27, synthetic answers, every write blocked)

| Tenant | Questions | Filled ok | Not ok |
|---|---|---|---|
| B | 19 (scale, ticks, knockout, EEO) | 19 | - |
| C | 19 (date, worded knockout, certify box) | 17 | resume (upload blocked); certify box left (the applicant's). First try: the worded knockout ASKed (read as Yes / No) - fixed, ok on the second |
| D | 19 (radios, long answer w/ maxChars) | 17 | resume + cover letter (upload blocked) |

## Closed posting

308 to the employer's job list with `rr_message=job_not_found` (6 of 6 gone links). Plain GET,
no page load. Open read as closed: 0 of 34.
