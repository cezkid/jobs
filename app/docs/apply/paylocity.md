# Paylocity application forms - measured facts

Paylocity = payroll + hiring system for many small and mid US employers (2.4% of freehire's US
postings, 2026-10-03). Posting `recruiting.paylocity.com/Recruiting/Jobs/Details/<id>`, form at
`/Recruiting/Jobs/Apply/<id>` - one host for every employer, no account, no sign-in. Shared steps
(`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer; add yours as a new line.

Measured 2026-10-03 with `apply-form measure` on 7 postings from 7 employers (tenants A-G), first
page only. Saved definitions: `app/tests/fixtures/paylocity/` (`tenant-<a..g>.json` + `options.json`).
Filler tried 2026-10-03 with `apply-form try` on 3 more employers (tenants H-J), step 1, every
write blocked: results under Widgets + What leaves.

## Form definition

Whole form in the apply page's own HTML: inline script `window.pageData = {...}` (80-105 KB, 7 of
7). No JSON fetched for it - opening the form sends the same as opening the posting. Only JSON
the page fetched: cookie banner text (OneTrust) + `publicAddressComponentConfig` (398 B, address box).

| Part | Holds | Filler rule |
|---|---|---|
| `customJobApplication.sections[]` | 6 sections, same 6 everywhere: `info`, `workHistory`, `educationHistory`, `references`, `acknowledgements`, `expandedIdentityQuestions`; `isIncluded`, `isOneRequired`, `displayOrder` | page of each question = its section name; a section with `isIncluded` false not asked |
| `sections[].fields[]` | `name` (fixed: `emailAddress`, `cellPhone`, `desiredSalary` ...), `displayName`, `isIncluded`, `isRequired`, `group`, `values[]` (choice options: `value`, `label`) | one question per included field; `type` null on every field (7 of 7) - kind comes from the field name, not the definition |
| `screener.questions[]` | employer's own questions: `title`, `isRequired`, `questionType` (`multi` / `text`), `allowsMultipleResponses`, `answers[].title`; `hasScreener` | `multi` -> choice (Yes/No only -> yesno), multi-answer -> multichoice; `text` -> text |
| `...Options` | `genderOptions`, `raceOptions`, `disabilityOptions`, `militaryServiceOptions`, `degreeOptions`, `desiredSalaryTypeOptions`, `referenceTypeOptions`, `graduationOptions`, `schoolTypeOptions`, `statesOptions` (70), `countriesOptions` (238) | option text for those boxes; identical on 7 of 7 |
| `newItemTemplates` | blank `workHistory`, `education`, `reference`, `school` records | the boxes one "Add" makes |
| flags | `requireResume`, `requiredReferencesCount`, `shouldIncludeEeoSection` / `...EeoQuestions` / `...OfccpQuestions`, `displayAcknowledgement`, `displayEVerify`, `smsEnabled`, `brandingModel.leadApplyEnabled`, `desiredSalaryInputType` (1 or 2) | read, never changed |

Seen across 7 tenants (R required, I included, - left out; A-G):

| Field | A B C D E F G | Note |
|---|---|---|
| `name`, `emailAddress` | R everywhere | |
| `smsOptedIn` ("Do you give us permission to text you?") | R R R R R R R | consent - the applicant's own answer, never filled |
| `cellPhone` | I R I R R I R | |
| `howDidYouHear` | I R - R I I I | options are the employer's own list |
| `desiredSalary` | - R - - - R R | |
| `appliedBefore` / `workedHereBefore` | - - - R - I I / - I - R - I R | |
| `workHistory` `companyName`, `educationHistory` `schoolName` | R R R R R - R | F has neither section; `workHistory` `isOneRequired` on D: one job entry open on load |
| `references` `referenceName` / phone | - R - - R - R / - R - - - - R | other people's details: always asked, never invented |
| `eeoGenderEthnicity` / `eeoDisability` (CC-305) / `ofccp` (veteran) | I R I R - R I / I R - R - - - / I R - R - - I | voluntary self-ID; options from `...Options` |
| `authorizedToWork` | I I - R - - R | the setup answer, only for this same US question |
| `priorConviction` / `priorFelony` / `priorMisdemeanor`, `dateOfBirth` | left out on 7 of 7 | unmeasured when included |
| `expandedIdentityQuestions` (gender identity, pronoun, sexual orientation, ethnicity) | I on 7 of 7, never R | voluntary - left for the applicant |

Screener on 5 of 7. Types seen: `multi` (Yes/No, Yes/No/N/A) and `text` - no multi-answer seen.
Graded screeners (2 of 5) carry `answers[].isCorrect` in the public page data, and one question
`isAutoReject`: the filler never reads either - answers are the applicant's truth, not the
employer's preferred reply.

## Widgets (tenants A-G, 2026-10-03)

| Box | On the page | Filler rule |
|---|---|---|
| contact + info text | `input[id="info.<name>"]` (`info.firstName`, `info.email`, `info.cellPhone`, `info.linkedIn`, `info.referredBy`), `data-automation-id="info<Name>"`, `data-for="<label>"` | find by id via `[id="..."]` (dot in the id). Label = sibling `<label>` w/o `for` in the same `.form-group`, "(required)" in an `<em>` - not found by a reader looking for `label[for]` (12-18 boxes per page read nameless). `data-for` holds the label text |
| required | `.form-group.form-required` + "(required)" in the label | not `required` / `aria-required` on the box |
| address | `public-site-address-<part>` (`country`, `address-1`, `address-2`, `city`, `county`, `us-state`, `zip`); job address `public-candidate-work-history-address-<n>-<part>` | `address-1` is a combobox (address lookup, `publicAddressComponentConfig`); state + country are text inputs that open a list |
| yes/no, SMS, pay type | react-widgets `div[role=combobox]` `[id="info.smsOptedIn"]`, `info.haveYouWorkedWithUsBefore`, `info.haveYouAppliedWithUsBefore`, `info.desiredSalaryType`; list = `aria-owns` `<id>__listbox`, `[role=option]` (11 per page, tenant H) | open, click the option, read the box's text back: ok on H-J. A layer took the click on 2 boxes of tenant J (30 s timeout): then clicked on the box itself (`e.click()`) - ok |
| How did you hear | native radios `name="info.howDidYouHearAboutUs"` inside `role=radiogroup` (no `[role=radio]`) | one choice question; the group's text holds the options too - title = the field's `displayName` |
| skills | `react-tagsinput` input `info.skills`, "Type a skill and press enter" | each item typed + Enter, tags read back: ok on H, J |
| country / state | `public-site-address-country` / `-us-state`: text input under a "Select a state" layer; the chosen value shows over the input (`input_value` stays '') | the layer takes a click (30 s timeout, H): focus, type, pick the option, read the `.form-group` text back - ok on I, J. Definition options are UPPER ("UNITED STATES"), page shows "United States": compared case-blind |
| start date | `info.dateAvailableToStart`, masked "MM/DD/YYYY" input + calendar button (flyout dialog) | typed keys don't take: whole fill, key by key with slashes, digits only - all read back '' (3 of 3, H-J). ASK: the user picks it in the calendar. Escape after, so the flyout never covers the boxes below |
| work history | `workHistory.<field>.<n>` (`companyName`, `position`, `companyUrl`, `companyPhone`, `responsibilities` textarea, `reasonForLeaving`, `currentlyWorkingHere` checkbox, `mayWeContactSupervisor` combo); dates `txt-workHistory-startDate-<n>` "MM/YYYY" + picker button; boxes appear after "Add Work History" (tenant H) | jobs from `questions.form_roles`; dates typed MM/YYYY. Reason for leaving, supervisor, employer phone: the user's. Live add unmeasured (`try` answers No) |
| education | `educationHistory.name.<n>`, `areaOfStudy`, `gpa`, `city`, `state`, `country`; `type` + `didYouGraduate` combos; after "Add Education" (tenant H) | school + area of study from the resume; type, graduated, dates: the user's |
| resume / cover letter | hidden `input[type=file]` `btn-resume`, `btn-coverLetter` (`.doc,.docx,.pdf`), buttons "Select Resume to Upload" / "Select Cover Letter" | upload via the file input, only after the user's yes. Choosing the file POSTs it at once (below): under `try` blocked, so ASK "not confirmed" there (3 of 3) |
| "Fill out application with my resume" | checkbox `useAttachedResumeToFillOutApplication`, ticked on load (7 of 7) | resume parse would overwrite typed answers: upload first, then fill. What it sends: unmeasured |
| ids made per load | none: 0 changed between two loads on 7 of 7 | ids are stable hooks |
| cookie banner | OneTrust: "Cookies Settings", "Accept All Cookies" | never "Accept All"; decline route unmeasured |

## Pages

Wizard, "Step 1 of N" on the page: N = 2, 4, 4, 5 on the 4 tenants it was recorded for; Next
button "Next Step" (never "Submit"). Page 1 = info, then "Add Work History" / "Add Education"
buttons on the same page. References, screener, EEO + acknowledgements, identity questions: on
later steps - which step each lands on, and what the last step's button says, unmeasured. Not
measurable while blocked: `try --next` on tenant J - "Next Step" (`btn-submit`,
`data-automation-id=btnNext`) sat under an "Upload Resume" dialog (resume required, its upload
blocked) and the cookie banner. Page has no step headings (`h1`-`h4`): page of a question comes
from its section in the definition; boxes not on the user's step -> LATER.

## What leaves the computer, when

Measured on load only (nothing typed), 2026-10-03:

- Opening the form: GETs only (page, scripts, cookie banner, address config).
- Datadog browser monitoring (`browser-intake-datadoghq.com/api/v2/rum`, POST) on 2 of 7 tenants
  at load - page-use telemetry, blocked; nothing typed yet.
- Email: `POST /Recruiting/Jobs/GetEnhancedEmailValidation` as the email box is left (3 of 3,
  H-J) - the address goes to Paylocity before Submit. Earliest point anything typed leaves.
- Resume / cover letter: `POST /Recruiting/Jobs/FileUpload` as the file is picked (3 of 3) - the
  file leaves before Submit; with "Fill out application with my resume" ticked the page may then
  fill boxes from it (unmeasured: blocked).
- Name, phone, address, pay, skills, choices: nothing sent while typed (3 of 3).
- At Next Step and Submit: unmeasured (Next not reachable while blocked, above).

## Read back (2026-10)

What `paylocity.holds` reads off the page once the form had time to keep it (`form.recheck`: refilled
once, still gone -> FAIL to fill by hand) - what shows, never the answer it was given. Hand-built step
`app/tests/fixtures/paylocity/form.html` (Widgets above, small synthetic `pageData`, Paylocity's own
upload words; no live page's markup); Chrome tests in `test_apply_paylocity.py`.

| Box | Read back |
|---|---|
| text boxes (name, email, LinkedIn, city, zip, address line 1) | box value as typed |
| phone | by digits (the page's dialling code allowed in front) |
| start date | by digits (the mask adds the slashes) |
| yes/no, pay type (react-widgets) | text the combobox shows, case-blind |
| How did you hear (native radios) | text beside the one ticked |
| Country / State | the input's value, else what its `.form-group` shows (the pick shows over an empty input) |
| skills | every item a tag |
| labelled questions (acknowledgements, self-ID, screener) | found by label in its `.form-group`: its combobox text, ticked radio or box value |
| work history / education | the first entry's company / school box not empty |
| resume / cover letter | the chosen file's name shown on the page |
| references, box not on this step | not held |

Upload (`put_file`): page idle first (15 s cap), then the file chosen - it goes to Paylocity at once.
Ok = its name shows for 2 s with no new error in Paylocity's own words; one of those -> FAIL with them;
nothing either way in 20 s -> ASK. Words (its form script, plain GET, 2026-10-07): a 5 s toast "Error
uploading Resume <reason>", "Error attaching Resume / Cover Letter / Additional File <reason>"; the file
box's checks "File cannot be larger than <N>MB.", "File type <ext> is not allowed.", "A maximum of <N>
file(s) is allowed.". Not a failure: "Sorry, we cannot complete the application using your resume. A
copy of the resume has been attached ..." (attached; only its read into the boxes failed). Where the
live page shows them: unmeasured - every `try` blocks the upload.

## Closed posting

Apply link of a missing / closed job: 302 to `/Recruiting/Jobs/JobNotFound`, page says "We're
sorry, that job does not exist or is not currently active" (2026-10-03, a made-up id) -
`form.CLOSED` matches the wording.

`paylocity.closed(url)` (2026-10-07): plain GET of the apply page, redirect not followed (the same GET
as opening the form - not a page load). 301 / 302 / 404 or a JobNotFound redirect -> closed, its
`window.pageData` -> open, a 200 without it -> "no form ... may have closed", other answer or no
answer -> can't tell. `pageData` has no active flag (only `lastStatusToActive`, a date).

Measured over freehire's listed links (2 employers): open list 3 -> 2 with their form, 1 JobNotFound
(freehire's list stale, closed per Paylocity); closed list 2 -> 1 JobNotFound, 1 still with its form
(Paylocity still takes it - read open). 0 links with a form read closed
(`.data/measure/paylocity-closed-check-2026-10-07.json`).

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | no screener, no references; 5 required fields |
| tenant B | screener 4 (Yes/No + text), references included, salary required, SMS enabled, resume required |
| tenant C | screener 2 (text only); Datadog telemetry at load |
| tenant D | work history `isOneRequired`: one job entry open on load; 16 required fields; Step 1 of 4 |
| tenant E | references included, no screener, resume required; Step 1 of 2 |
| tenant F | no work history or education section; screener 9, graded, incl. background + drug screening yes/no; Step 1 of 4 |
| tenant G | screener 3 graded, one auto-reject, answers marked correct in page data; references; Step 1 of 5 |
| tenant H | no screener; Step 1 of 4, 60 controls; `try`: 39 questions, all step-1 boxes ok but start date + uploads |
| tenant I | references 3 required; `try`: 35 questions, ok but start date, upload, references (other people's details) |
| tenant J | 47 questions, 23 on later steps; resume required; `try`: ok but start date + upload; Next blocked by resume dialog |
