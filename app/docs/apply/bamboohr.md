# BambooHR application forms - measured facts

BambooHR = careers site for many small + mid employers (`<co>.bamboohr.com/careers/<id>`; 1.5% of
freehire's US postings, 2026-10-03). Measured 2026-10-03: the form definition (plain GET, below) on
12 postings from 12 tenants; `apply-form measure --click "Apply for This Job"` (2 loads each,
canary ok, 9 of 9 blocked) on 4 of them, tenants A-D. Tenant E: definition only (its page read
failed before the reader fix below; site budget spent). Tenant named by letter, never employer; add
yours as a new line. Saved: `app/tests/fixtures/bamboohr/tenant-<a-e>.json` (definition, employer
-> Acme, values emptied) + `tenant-<a-d>.snapshot.json` (page read after the Apply click).

## Form definition

`GET https://<co>.bamboohr.com/careers/<id>/detail` -> 200 JSON, no key, no cookie (12 of 12). The
page fetches the same URL itself on load (measure, 4 of 4). Only the listing id goes out, same as
opening the posting. `result.jobOpening.jobOpeningStatus` = `"Open"` (12 of 12);
`result.formFields` = every box the form shows, each `{isRequired, value, label, options}`; a field
the employer turned off is an empty list `[]` instead of an object (e.g. `genderId: []`, 7 of 12).

| Field (key) | Seen (12 tenants) | Shared kind / key |
|---|---|---|
| `firstName`, `lastName`, `email`, `phone` | 12, always required | text `first_name` / `last_name`, email, phone |
| `streetAddress`, `city`, `state`, `zip`, `countryId` | 10, required all 10 | text `street`, `city`, `state`, `zip`; country = choice (256 options `{id, text}`, `value` `"1"` = United States preset on 3 of 4 measured) |
| `state` options | 60 `{id, text}` two-letter codes (states + DC + territories); ids are not alphabetical (`AK` = 2, `AL` = 1) | not offered: the page lists full names ("Alabama", "New York"; 4 of 4 tries) - typed / picked by name |
| `resumeFileId` | 12, required 12 | file `resume` |
| `coverLetterFileId` | 3, required 1 | file, cover letter |
| `dateAvailable` | 11, required 5 | date; mm/dd/yyyy typed took (4 of 4 tries) |
| `desiredPay` | 9, required 6 | text, asked |
| `linkedinUrl` / `websiteUrl` | 9 / 7, required 1 / 1 | text |
| `educationLevelId` | 7, required 4 | choice: 14 fixed options (GED ... Doctorate, Medical Doctor, Other), same on all 7 |
| `educationInstitutionName` | 3, never required | text |
| `referredBy` | 4, never required | text, asked |
| `references` | 5, required 2 | longtext, asked |
| `genderId`, `ethnicityId` | 5, never required | choice, voluntary - left for the user; "Decline to answer" first |
| `veteranStatusId` | 5, required 5 in the definition; 6 options | voluntary - left for the user (page shows 3 options, not required - Widgets) |
| `disabilityId` | always `[]` (12 of 12) | none seen |
| `customQuestions` | list, 0-15 per form | per item below |

`customQuestions` item: `{id, isRequired, question, type, value, isValueOther, hasOther, options}`.

| `type` | Seen (81 questions, 12 tenants) | Shared kind |
|---|---|---|
| `yes_no` | 42 | yesno |
| `short` | 22 | text |
| `long` | 15 | longtext |
| `multi` | 1 (tenant E); options `{id, option}` - key `option`, not `text` | choice or multichoice: single vs several on the page unmeasured |
| `file` | 1 (tenant B, "Please upload a project list", required) | file, asked - not the resume |

`hasOther` = `"no"` and `value` empty on all 81. Employer questions seen: sponsorship now / later,
right to work, security clearance, lives near the office, on-site full time, desired salary as
text, how did you hear (free text with suggestions in the question), referrer name, non-compete,
driver licence + violations, schedule flexibility, start date as free text, experience yes/no, and
one attestation (tenant E: "Do you affirm that the information you've provided ... true and
complete?", yes_no, not required) - applicant's own act, never answered for them.

Unknown posting id: `/detail` -> 404 `{"type": "not_found", "title": "Resource not found."}` (1
tenant, 2026-10-03). A closed posting's own wording: unmeasured (12 of 12 open).

## Widgets (4 tenants, 2026-10-03)

The page is a React app (BambooHR's own "Fabric" kit, MUI underneath). "Apply for This Job" opens
the form on the same URL; before the click the page has no form box (measure, tenant E).

| Box | On the page | Filler rule |
|---|---|---|
| contact | `input#firstName`, `#lastName`, `#email`, `#phone` (type text, 4 of 4) | find by id |
| address | `input[name="streetAddress.value"]`, `city.value`, `zip.value`; ids `FabricTextField-<n>` changed between two loads on 1 of 4 | find by name, never id |
| lists: State, Country, education, gender, ethnicity | Fabric list (`div.fab-Select`): a hidden native `select` (`name="state.value"` / `countryId.value`, `id="educationLevelId"` ...) with one empty option, + a `button[aria-haspopup]` whose `data-menu-id` names the menu that opens on click: `role=menu`, items `role=menuitem` with the option text (4 of 4 tries). The button shows the choice in `.fab-SelectToggle__content` (Country preset "United States" shows there, the select stays empty). State read as a text box in the measure snapshot, as a list on all 4 tries | find the select by name / id, click its button, click the item whose text is the answer, read the button back |
| optional system fields | `#desiredPay`, `#websiteUrl`, `#linkedinUrl`, `#referredBy`, `#educationInstitutionName` inputs; `textarea#references` | find by id |
| Date Available | text input, no name, id `FabricTextField-<n>` (changed on 1 of 4), label "Date Available" | find by label; mm/dd/yyyy typed, read back as typed (4 of 4) |
| employer question | name `customQuestionAnswers.<type>_<id>` - `<id>` = the definition's question id (`short_1018`, `yes_no_175`, `long_761`) | find by name from the definition |
| yes_no | two native radios Yes / No sharing that name, inside a `role=radiogroup` with no `role=radio` inside | tick by option text |
| file (resume, cover letter, file question) | `input[type=file]`, no name, no label (reads "file-input"), inside a `FileUpload` block under a `<p>` heading "Resume*" / "Cover Letter" (3 tenants); order on the page = cover letter (optional), resume (required), then a file question in place (tenant B). React empties the input once it has the file | find under its heading, else by place; read back = the file's name shown in the block (unmeasured while the upload is blocked: try reports it ASK) |
| Veteran Status | native radios named `:r<n>:` (React id, changes per page), 3 options "Decline to Answer" / "Not a Veteran" / "Veteran", not required on the page (4 of 4) though the definition says required + 6 options | voluntary - left as the page has it |
| honeypot | `input#nickname_hpcsaf`, label "Please leave this field blank", hidden (4 of 4) | never filled |
| MUI shadow textarea | unlabelled `textarea` with value `x` next to each textarea (MUI autosize copy) | not a question |

Visibility: every form box read hidden (`checkVisibility` with opacity) right after the click, 4 of
4; the shared page reader (`dom.questions`) drops hidden boxes, so it found only the radios and the
file inputs. They show once the form finishes opening: try typed into each (4 of 4). The
filler builds its questions from the definition, not from the page read.

Reader fix found here: a `role=radiogroup` holding native radios crashed the whole page read
(`TypeError ... getAttribute`, 1 tenant); now read as plain radios (`app/apply/dom.py`, test in
`test_dom.py`).

Captcha: a hidden `g-recaptcha-response` box on the form (4 of 4 tries; nothing to tick seen) - the
applicant's own step; what it checks at Submit unmeasured.

## What leaves the computer, when

Measured 2026-10-03, every write blocked + logged: `apply-form measure` (load + Apply click) on 4
tenants, then `apply-form try` (load, Apply click, files chosen, every box typed / picked / ticked)
on the same 4.

| Step | Writes | Tenants |
|---|---|---|
| page load | 1: `POST api.rollbar.com/api/1/item/` (BambooHR's error report; nothing typed yet) | 4 |
| resume or cover letter chosen | the file, at once: `POST <co>.bamboohr.com/ajax/files/attachTemporary.php` (A, C, D - once per file), `POST pandabox.bamboohr.com/us-east-2/` (B) | 4 |
| typing, choices, ticks | 0 | 4 |
| Submit | the form - never clicked, unmeasured live | - |

Earliest point anything the applicant chose leaves: choosing the resume (or cover letter) file -
before Submit. Typed answers: Submit. GETs the page makes: `/careers/<id>/detail`,
`/careers/company-info`, `/ajax/get_countries`, `/ajax/get_currency`, `/ajax/get_states` (1 of
4), Pendo analytics (`data.bhrpendo.bamboohr.com`); what Pendo sends after Submit is unmeasured.

## Closed posting

`jobOpeningStatus` other than `"Open"` -> "may have closed" (the value a closed one carries is
unmeasured; 12 of 12 open). Unknown id -> 404, same message.

## Try (2026-10-03)

`apply-form try` on 4 postings, 4 tenants, synthetic answers, canary ok, 0 writes sent: every box
`ok` except the uploads (A 21 of 23, B 25 of 27, C 29 of 30, D 18 of 20). Each upload reads ASK
because its own write was blocked - the file never reached BambooHR, so the page never named it.
Left on the page, each the applicant's own: the employer's file question (tenant B, "Please upload
a project list"), the reCAPTCHA. Tenant E's attestation yes/no ("Do you affirm ...") is never
answered (`questions.signs`).

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | address + country; cover letter + resume; education; 5 questions (salary range short, why-interested long, how-heard short, 2 sponsorship yes_no); gender, ethnicity, veteran |
| tenant B | Date Available + Desired Pay required; education + institution; referredBy; references; 6 questions, all required, incl. a file question; ids changed between loads; gender, ethnicity, veteran |
| tenant C | Date Available, Desired Pay, education + references required; 12 questions, 1 required (bilingual); driving + schedule; gender, ethnicity, veteran |
| tenant D | Desired Pay required; cover letter optional; referredBy; 1 question (security clearance); gender, ethnicity, veteran |
| tenant E | definition only: no address boxes; Date Available + Desired Pay required; 17 questions (16 required) incl. the only `multi` and an attestation yes_no; no EEO |
