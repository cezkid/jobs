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
| `state` options | 60 `{id, text}` two-letter codes (states + DC + territories); ids are not alphabetical (`AK` = 2, `AL` = 1) | match by `text`, never by id |
| `resumeFileId` | 12, required 12 | file `resume` |
| `coverLetterFileId` | 3, required 1 | file, cover letter |
| `dateAvailable` | 11, required 5 | date; format on the page unmeasured |
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
| address | `input[name="streetAddress.value"]`, `city.value`, `state.value`, `zip.value`; ids `FabricTextField-<n>` changed between two loads on 1 of 4 | find by name, never id. `state` is a text box on the page though the definition lists 60 options - how it takes a value unmeasured |
| Country | native `select[name="countryId.value"]`, id `fab-select<n>` (changed on 1 of 4), no options in the DOM until opened, value empty on the page even where the definition presets 1 | find by name; picking unmeasured |
| optional system fields | `#desiredPay`, `#websiteUrl`, `#linkedinUrl`, `#referredBy`, `#educationInstitutionName` inputs; `textarea#references`; native `select#educationLevelId`, `#genderId`, `#ethnicityId` with no options in the DOM | find by id |
| Date Available | text input, no name, id `FabricTextField-<n>` (changed on 1 of 4), label "Date Available" | find by label; format unmeasured |
| employer question | name `customQuestionAnswers.<type>_<id>` - `<id>` = the definition's question id (`short_1018`, `yes_no_175`, `long_761`) | find by name from the definition |
| yes_no | two native radios Yes / No sharing that name, inside a `role=radiogroup` with no `role=radio` inside | tick by option text |
| file (resume, cover letter, file question) | `input[type=file]`, no name, no label (reads "file-input"); order on the page = cover letter (optional), resume (required), then a file question in place (tenant B) | unmeasured how to tell them apart other than order + required - try bead |
| Veteran Status | native radios named `:r<n>:` (React id, changes per page), 3 options "Decline to Answer" / "Not a Veteran" / "Veteran", not required on the page (4 of 4) though the definition says required + 6 options | voluntary - left as the page has it |
| honeypot | `input#nickname_hpcsaf`, label "Please leave this field blank", hidden (4 of 4) | never filled |
| MUI shadow textarea | unlabelled `textarea` with value `x` next to each textarea (MUI autosize copy) | not a question |

Visibility: every form box read hidden (`checkVisibility` with opacity) right after the click, 4 of
4; the shared page reader (`dom.questions`) drops hidden boxes, so it found only the radios and the
file inputs. Whether the boxes show to a person after the form finishes opening: unmeasured. The
filler builds its questions from the definition, not from the page read.

Reader fix found here: a `role=radiogroup` holding native radios crashed the whole page read
(`TypeError ... getAttribute`, 1 tenant); now read as plain radios (`app/apply/dom.py`, test in
`test_dom.py`).

Captcha: none found on the form (4 of 4); one at Submit unmeasured.

## What leaves the computer, when

Measured 2026-10-03 at load + Apply click, every write blocked + logged (4 tenants): 1 write per
load, a `POST api.rollbar.com/api/1/item/` (BambooHR's error report; nothing typed yet). GETs the
page makes: `/careers/<id>/detail`, `/careers/company-info`, `/ajax/get_countries`,
`/ajax/get_currency`, `/ajax/get_states` (1 of 4), Pendo analytics (`data.bhrpendo.bamboohr.com`).
Writes while typing, choosing, attaching the resume, and at Submit: unmeasured - filled by the try
bead.

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | address + country; cover letter + resume; education; 5 questions (salary range short, why-interested long, how-heard short, 2 sponsorship yes_no); gender, ethnicity, veteran |
| tenant B | Date Available + Desired Pay required; education + institution; referredBy; references; 6 questions, all required, incl. a file question; ids changed between loads; gender, ethnicity, veteran |
| tenant C | Date Available, Desired Pay, education + references required; 12 questions, 1 required (bilingual); driving + schedule; gender, ethnicity, veteran |
| tenant D | Desired Pay required; cover letter optional; referredBy; 1 question (security clearance); gender, ethnicity, veteran |
| tenant E | definition only: no address boxes; Date Available + Desired Pay required; 17 questions (16 required) incl. the only `multi` and an attestation yes_no; no EEO |
