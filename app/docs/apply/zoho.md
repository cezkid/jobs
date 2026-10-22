# Zoho Recruit application forms - measured facts

Filled by `app/apply/systems/zoho.py` - `apply-form`, Job Finder's own Chrome.

Zoho Recruit = hiring system, one careers site per employer: `<tenant>.zohorecruit.com/jobs/<page>/<id>`
(`<page>` = the portal page's name, `Careers` on 13 of 13 sites read; `<id>` = 18 digits). The form
opens on the posting page itself, no address of its own. Page built from Zoho's "Lyte" web components
(`window.Lyte`, `crux-*` / `rec-*` / `lyte-*` elements). Tenant named by letter, never employer.

Measured 2026-10-21:
- tenant A: by hand in the user's own Chrome (one posting, nothing sent - the facts the task brief
  gave; checked again below wherever another tenant shows the same box);
- tenants B-G: Job Finder's lab Chrome (`apply-form measure` / `try` + scratch runs on the same
  throwaway profile, every write blocked, canary first: 0 of 9 received each run), synthetic
  answers only. Per site: B 3 browser loads + 5 plain GETs, C 3 + 4, D 1 + 8 (the live test reads the newest posting), E 2 + 4, F 2 + 4, G 1 + 4
  (budget 10). `try` on B, C, E, F: every box ok, 0 writes fired; D: a scratch run of the same fill
  path with two synthetic jobs for Experience Details;
- 13 form definitions read by plain GET (tenants B-G + 7 more, 2 s apart, 0 errors).
Saved runs: `.data/measure/*zohorecruit*` (private, not shipped).

## Links

| Link | Answer |
|---|---|
| `/jobs/Careers/<id>` (freehire's, `?utm_source=freehire.me`) | posting page, 200, ~1.7 MB (the whole site's job list inline) |
| `/jobs/Careers/<id>/<Slug>?source=CareerSite` | the page's own link (`og:url`), same page |
| `<tenant>.zohorecruit.eu`, `.in`, `.com.au` (Zoho's other data centres) | not matched - none among freehire's 50 newest US links (50 of 50 `.com`); unmeasured |

## Posting page

| Part | Measured | Filler rule |
|---|---|---|
| apply button | `lyte-button#detail-page-applybtn` (a second one lower down has no id), words the tenant's own (`applynow` setting: "I'm interested" on A-C) | found by id, never by words |
| form | appears on the same URL after the button (header "Job listing / Job details / Job application"); its definition fetched then (below) | `recover` presses the button, waits for `[name^=rec-form_]` |
| cookie notice | "Accept all" / "Decline non-essential" / "Manage cookies"; `.cw-cookie-freeze-layer` (full width, pointer-events auto) covers the page until a choice - real clicks on the apply button, list buttons, Add buttons time out (C, 6 of 6) | the user's choice, never clicked: the apply button, list buttons and Add buttons get their own click event (`dispatch_event` / `el.click()`); typing is not blocked (focus works under the layer) |
| job record | `var jobs = JSON.parse('<JSON, \x22 escaped>')`: `id`, `Publish`, `Keep_on_Career_Site`, `$read_only_job` ... | closed check (below) |
| form id | `var meta = {... "webform_id":"<id>", "page_name":"Careers" ...}` (13 of 13) | definition read |
| Autofill Application | `rec-easyresume_file` upload above the form: Zoho parses the resume into the boxes (optional) | never used - it would overwrite typed answers |
| Apply with Indeed / LinkedIn | buttons per tenant (`apply_with_details`) | never |

## Form definition

`GET https://<tenant>.zohorecruit.com/recruit/v2/public/Job_Openings/<job>/apply/<webform_id>?pagename=<page_name>&source=CareerSite`
- the page's own read (C, captured), plain HTTP from Python too (13 of 13). Without `pagename`: 400
`REQUIRED_PARAM_MISSING`. `prepare` = 2 GETs (posting page, definition); nothing about the user.

`webforms[0].sections[]` (13 forms):

| Section | Seen | Filler rule |
|---|---|---|
| Basic Info | First Name (required 7), Last Name (13 of 13 required), Email (8), Mobile (11; required 7), Salutation list (12, optional) | shared keys by `api_name`; Salutation asked, optional |
| Address Information | Street, Zip_Code, City, State (text, required on 4-5), Country (text) | home address from search settings; Country asked |
| Professional Details | Current Job Title (list of the tenant's own titles, 4: tenant A "-None-, Fresher, Project-Lead, Project-Manager"), Skill Set (6), Expected Salary (currency, 2), employer boxes (multi-pick lists: 8 on 3 forms) | asked - never a title they don't hold, never their pay unasked |
| Educational Details | table (`istabular`), 8: Institute / School, Major / Department, Degree (text), Duration (`monthrange`), Currently pursuing (tick); up to 10 rows | one row per school on the resume (`EDUCATION_ENTRIES`), answered from Resume details |
| Experience Details | table, 7: Occupation / Title, Company, Summary (textarea, 6000), Work Duration, I currently work here, Reason for Leaving (1) | one yes / no; yes -> a row per job (`questions.form_roles`); Reason for Leaving left theirs |
| Social Links | LinkedIn (`website`), Facebook (`website`), X / Twitter (text, "@" in front) | LinkedIn from the resume; the rest asked |
| employer sections | ticks with `termsandconditions` (3 required on 1 form), SMS consent (2), work authorization lists | ticks: the applicant's own (titled so, never drafted); lists asked |
| Attachment Information | `attachmenttypes[]`: RESUME (13; required 6), COVERLETTER (1), `$photo_id` Photo (6, optional); `$limit` 10485760, `$instant` false (13 of 13) | resume / cover letter after the user's yes; photo never (AGENTS.md "Photo: can't") |
| CAPTCHA | `$Captcha` text box under a picture + "Load new CAPTCHA", required (9 of 13) | the applicant's own; `ids_on_page` counts it as theirs on the page |

`Assessments.questions[]` ("Pre-Screening Assessment", same page, under the form; 2 of 13 forms, 19
questions): `type` 2 text area, 3 Yes / No radios, 4 radios, 5 ticks, 6 list; `ismandatory`. Another
type -> asked as text, never filled.

`meta.layout_rules` (1 of 13): a box shown (and made required) only for some answers of a list.
Hidden at fill -> "skipped - hidden by the form's own rule". Live: unmeasured.
`meta.is_eeo_enabled` (1 of 13): the page names a `portal-eeo-survey`; where it shows (after Submit?)
unmeasured - never filled.

## Closed posting

The page's detail template (Zoho's script, read 2026-10-21): `$read_only_job` -> "No longer accepting
applications" in place of the apply button (matched by `form.CLOSED` too); `!Publish &&
Keep_on_Career_Site` -> "Position filled". No record of the job on its page -> "may have closed".
Live: not seen - 13 of 13 postings read were open (2 of them 2-3 weeks old).

## Widgets (tenants B-G, 2026-10-21)

Each box: `<crux-*-component | rec-*-component id="rec-form_<field id>">`; a `<template>` copy carries
the same id (find with `:not(template)`). Labels are attributes (`cx-prop-label`), never `<label for>`.
What the form keeps = the component's `getValue()` - Submit's `getFormDataAndCheckValidation` reads
exactly that from each visible box (Zoho's script). Read back from it, never from the box's text.

| Box | On the page | Filler rule | Read back |
|---|---|---|---|
| text, email, website, currency | `<input name="rec-form_<id>">` in `lyte-input` | Playwright fill + blur (A: native setter + events works too) | `getValue()` = typed (C, D, B, E, G) |
| mobile | same + a country list `(+1)` beside it (tenant's country) | typed without a leading +1; another country's number -> ASK | `getValue()` = `+1` + typed |
| zip / city / state | most tenants: `lyte-autocomplete#<id>` > `input#inputId` (no name, ids repeat); E: same | typed key by key, Tab, never a suggestion picked (a zip pick fills city, state, country with Zoho's words - C) | `getValue()` = typed (C, D, B, E); A: JS value alone did not bind - typing does |
| list (picklist, screening list) | `lyte-dropdown#<id>`; items `lyte-drop-item[data-value]` drawn in the body | button clicked (its own click under the cookie layer), item by its words clicked | `getValue()`; the button shows the words |
| multi-pick list | `lyte-dropdown` type `multisearch` (F, `try` ok) | each item clicked; the list stays open | `getValue()` = array of values |
| radios (screening 3, 4) | `rec-multi-radio-component` > `lyte-radiobutton[lt-prop-label][lt-prop-value]` > input | the input's own click (label click, mouseup, `ltProp('checked')` also took - C) | `getValue('actual_value')` = the option's id (`getValue()` stays null) |
| ticks (screening 5) | `rec-multi-checkbox-component` > `lyte-checkbox` | each changed input clicked (E) | `getValue()` = JSON array of option ids |
| tick (boolean) | `lyte-checkbox` | consent / terms: never; others the input's click | input checked |
| Skill Set | `rec-skills-component` > `input#addSkills` (name `-add-skills`); suggestions `.skl-suggested-skill li`; chips `.skl-selected-skill` | per skill: words set + key-up (typed key by key, letters went missing while the search came back - D: "proj" + "t management"); the suggestion with its exact words clicked - Zoho offers the typed words themselves when it has no such skill (G); Enter added one on G, not on A | `getValue()` = `[{name, id, ...}]` |
| resume / cover letter | `rec-file-upload-component` > hidden `input[name="rec-form_<id>_file"]` | file chosen after the user's yes | `getValue('queueList')` holds the file (C) |
| tables | `rec-tabular-component#rec-form_<layout>_<section>`; button `#crc-tabular-add-btn-<layout>_<section>` "Add", then "Add More" (same button; aria-label "N of 10 entries added currently"); row boxes `<sub id>_<n>` (n from 1); dates `lyte-dropdown#cxd-<duration id>_<n>_from_month / _from_year / _to_month / _to_year` (months 1-12, 0 = -None-; years this year down); ticks `<sub id>_<n>` | rows added by the button's own click; text filled; a date list opened and the item `data-value` clicked, retried (A: first try after Add More found none) | the tabular component's `getValue(true)`: `[{Degree, ..., Duration: {from: "2016-9-01", to: "2020-5-01"}}]` (C, D) |

`I currently work here` ticked -> no "to" date sent (D: `{"from": "2022-3-01"}`).

One page; buttons Cancel, "Submit Application" - never clicked.

## What leaves the computer, when

Read off every request the page made while each box was filled (try + scratch runs, B-E; every
write blocked - none fired: the form's only write is Submit):

| What | Request | When |
|---|---|---|
| form definition | GET `.../Job_Openings/<job>/apply/<form>` | the apply button (nothing about the user) |
| email | GET `.../Job_Openings/<job>/actions/candidate_assessment_available?candidate_email=<email>` | as the Email box is left - forms with screening questions only (C, E: 2 of 2; B, D, G without: 0) |
| zip / city / state | GET `.../public/Locations/search?searchtxt=<words>&field_name=<Zip_Code / City / State>` | 2-3 per box as it is typed (debounced) - search boxes only |
| skills | GET `.../recruit/v2/competency_skills?searchText=<skill>&selectedSkills=[...]` | each skill as it is typed |
| everything else, resume too | Submit's own request (form data + files) | Submit - never pressed here; what it sends: Zoho's script, unmeasured live |

All to the employer's own `<tenant>.zohorecruit.com`. `prepare` tells the AI the zip / city / state /
skills boxes search as typed (`SEARCHED_AS_TYPED`); AGENTS.md privacy table has the rows.

## Unmeasured

- Submit and its answer (never pressed); the EEO survey; a closed posting live; a `layout_rules` box
  shown live; Zoho's other data centres (`.eu`, `.in` ...); a tenant whose phone list is not +1; a
  year-only date in a table row (month left -None-); Experience rows with a real resume (synthetic
  jobs only, D); `--in-window` (not offered).
