# Teamtailor application forms - measured facts

Filled by `app/apply/systems/teamtailor.py` (plan-k8n.31) - `apply-form`, Job Finder's own Chrome.

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
| questions | 28 (0-10 per form), 26 mandatory: yes/no 11, text 11 (+1 long), number 2, choice 2, range 1 | yesno, text, longtext, number, choice; range as a number |
| knockout | "qualifying" yes/no on 1 employer (2 forms): form greyed until answered; wrong answer -> "You have to meet these requirements to be able to apply" | never shade an answer to pass it (Hold); say it plainly |
| consent | `consent_given` 9 of 9 required; future jobs 3; SMS 1 | the applicant's own - never ticked for them |

## Widgets (3 tenants, 2026-10-07)

| Box | On the page | Filler rule |
|---|---|---|
| any box | stable Rails names + real `<label for=>`; unlabelled only the range number box + Submit | find by `name` |
| yes/no | radios `value` true / false; id `boolean-<n>-true`, `n` differs per load (tenant B 7 of 7, C 2 of 2) | pick by `name` + `value`, never id |
| choice | radios `value` 1..n | pick by label text |
| range | `input type=range` (min / max / step / unit) + its own number box `range-custom_number`, hidden until "Edit number" | value set in the number box + its input event; slider read back |
| phone | intl-tel-input, country search box, default United States (+1); box keeps `+<country><number>` | number typed as `+...`; 10 digits = +1; else ASK for the country code |
| resume, other files | hidden file inputs (Dropzone, no `name`), `#candidate_resume_remote_url`, `#candidate_file_remote_url` (max 3) | put file by id |
| email | typo hint shown in the page (nothing sent) | - |
| cookie banner | Accept all / Decline non-necessary / preferences; on 2 of 10 postings a takeover box (`takeover-modal-value="true"`) that holds the keyboard (focus trap): typing lands nowhere (live, 2026-10-07) | the user's choice - never clicked; boxes it holds get the value set with their own events (`write`), places picked by their own click |

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

Posting page without the form frame + "no longer" text (1 of 10). `closed()` = plain GET of the
form frame: 404 / 410 -> "posting not found on Teamtailor"; no form + "no longer ..." -> those
words; no Teamtailor scripts (`teamtailor-cdn.com`) -> "not a Teamtailor form".

Closed check 2026-10-07 over `.data/links/teamtailor-open.txt` (10 links, plain GET 2 s apart, 0
page loads): 9 forms, 1 read closed (404 - the "no longer" posting of 2026-10-06, since removed);
open read as closed 0. Record: `.data/measure/teamtailor-closed-check-2026-10-07.json`.

## Filler rules

- Links: any host whose path is `/jobs/<5-8 digits>-<slug>` (+ `/applications/new`) - 6 of 10 owner
  links sit on the employer's own domain (`jobs.<x>.com`, `people.<x>.com`). The page's Teamtailor
  scripts confirm it; a matched page without them -> "not a Teamtailor form". `on_tab`: same host +
  id (the slug may change, 301).
- Questions by plain GET of the form frame (`QUESTIONS_OVER_HTTP`, header
  `Turbo-Frame: application_form`); `<template>` contents skipped (the upload preview's link boxes).
  Ids = box names. Title = label (or legend) + the description line under it.
- Standard boxes -> shared keys; address combobox -> `location`; cover letter -> longtext; the
  form's own office ticks (`location_ids`) -> multichoice.
- Yes/no radios by `name` + `value` (ids change per load); choices by their words.
- Qualifying yes/no: an answer the form refuses shows "You have to meet these requirements to be
  able to apply" -> ASK naming it; the answer stays the user's (Hold), never changed to pass.
- Address: typed (3 letters + 0.5 s), the place naming every part of the answer picked (fewest
  parts besides); a bare town two places share -> ASK; no places -> ASK with the page's own words.
  `SEARCHED_AS_TYPED`: the letters go to the employer's Teamtailor site (its own list).
- Consent boxes (`consent_given`, future jobs, SMS) -> yes/no questions left on the page, never
  ticked. Other files -> ASK.

## Read back (2026-10)

What `teamtailor.holds` reads off the page (`form.recheck`: refilled once, still gone -> FAIL to
fill by hand) - what shows, never the answer it was given.

| Kind | Read back |
|---|---|
| box (contact, text, number, letter) | its value; number by its digits; phone by digits of the `+...` form |
| radios / ticks | every one in the group: on exactly when its value (yes/no) or words are an answer |
| slider | its value equals the number |
| address | the place id the page kept + the town in the box |
| resume | the drop box shows the file name + Teamtailor's link for it, no error words |
| box not on the page | not held |

Upload: the file leaves on choosing (`/uploads/presigned_data`, then S3). `put_file`: page idle (15
s cap), file chosen, name + link shown -> ok; the drop box's error words -> FAIL with them; neither
in 15 s -> ASK.

## Try (2026-10-07)

`apply-form try` on 3 postings, 3 tenants (one on its own domain), synthetic answers, canary ok
each (0 of 9 test writes through), 0 writes sent:

- tenant A (15 questions: qualifying, address, number, LinkedIn): texts + number ok; resume FAIL
  "Failed to fetch" (upload blocked by the try); address ASK with the page's words (place search
  blocked by the try); phone ASK (synthetic 7 digits). Qualifying "No" first read ok - the
  message's `aria-hidden` stays "true" when shown (only its `hidden` class drops); fixed, re-try
  ASK naming the message.
- tenant B (18: range, choice, 8 yes/no): radios + choice ok; every text box FAIL shows '' - the
  takeover cookie box held the keyboard; fixed (`write`), re-try every box ok; slider ASK (synthetic
  1, steps of 50).
- tenant C (own domain, 6): texts ok; resume FAIL (blocked), phone ASK.

Page loads per site (with the 2 measure loads each): A 4, B 7, C 3 of 10.

## In the window (plan-k8n.38)

Measured in a tab of the Job Finder window (route 2), 3 tenants (A, B, C own domain), 2026-10-07, 1 page load each:
form up 1.6 / 2.1 / 3.3 s after navigate, 0 `debugger;` pauses, 0 frames, no captcha or AWS WAF; proof-of-work box
answered by the page itself (80 / 975 / 2200 ms). A click on the first-name box never focused it (focus stays on the
cookie notice's link): on A + C, focus by script + typing held "Test Applicant"; on B the takeover cookie notice held
the keyboard, every typing landed nowhere, set by script with the box's own events held it (= the filler's `write`,
as in Chrome). Dummy resume: sent at once to `/uploads/presigned_data` (blocked), then the drop box shows "TypeError:
Failed to fetch" - as Chrome's try (FAIL with the page's words). Parity test: same report + page as Chrome on A + B
(B with a cookie notice holding the keyboard) after one adapter fix (`wait_for(state=...)`, as Playwright). Not in
`--in-window` yet - owner decides (plan-k8n.41). Numbers: `vscode-browser.md` "Teamtailor - route 2".

## Cost

Filler took 1 bead (6 contexts). Estimated before: ~1 bead (BambooHR / Workable size): stable names + real labels, form by plain GET,
proof-of-work runs itself, upload on choose. Watch: yes/no ids change per load, knockout greys
the form, location box on 2 of 9.
