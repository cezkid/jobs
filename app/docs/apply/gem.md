# Gem application forms - measured facts

Gem = a recruiting platform whose job boards host employers' postings at `jobs.gem.com/<board>/<posting
id>`. Measured 2026-10-26: 12 links on one user's job list (freehire `source` gem), 11 open, 9 boards
(tenants A-I), each form read by the page's own GraphQL read over plain HTTP; one application filled by
hand through the Claude Chrome extension and sent by the user (tenant A); `apply-form measure` on tenant
B (2 loads, canary ok, 9 of 9 blocked); `apply-form try` on 3 postings, 3 tenants (B, C, D), 0 writes.
Tenant named by letter, never board. Saved reads: `app/tests/fixtures/gem/tenant-<a-c>.json` (employer
names -> Acme, titles -> Software Engineer); saved form: `fixtures/gem/form.html` (the measured parts,
words anonymised, a small script in place of Gem's React).

## Links

`https://jobs.gem.com/<board>/<id>?utm_source=freehire.me` (12 of 12). Id = base64 of `jobpost:` + bytes,
so it starts `am9icG9zdD` (12 of 12), letters, digits, `-` and `_` only. The form is on the posting page
itself, under the description ("Ready to apply?"): `application_url` = the link without its tail.

## Where the form comes from

The page draws itself from GraphQL reads; the HTML holds no form. `jobs.gem.com/api/public/graphql`
(and `/batch`, the page's own route) answers a plain POST, no cookie, no token:

- `ExternalJobPosting($boardId, $extId)`: `oatsExternalJobPosting` (title, `isApplicationFormHidden`) +
  `oatsJobPostFieldsAndQuestions` - `fields` (Gem's own boxes: `fieldType`, `isRequired`), `questions`
  (the employer's: `extId`, `answerType`, `displayType`, `text`, `isRequired`, `options {extId value}`),
  `demographicSurvey` (`surveyType`, its own `questions`). Query text read from Gem's
  `jobBoards.*.min.js` + `PublicQuestionFragment.*.min.js` (2026-10-26).
- Unknown posting: `oatsExternalJobPosting: null` (tenant E, 1 of 12) - read as "may have closed".

`questions` = that read, sent by `prepare` - only the board + posting id go out, as when the page opens.

What the page sends while it loads (measure, try): the read above batched with `JobBoardTheme`
(colours), then `OneClickApplyEnabled`, `OatsTeamSettingExternalPublic`, `FormAutofillData` (the
applicant's saved Gem details, by cookie - empty in a fresh browser) and
`OatsIsJobBoardSeoStructuredDataEnabled` in a second batch. Both blocked -> "Job not found" or no form.
`lab.NAMED_READS` lets those 6 reads through, only as GraphQL queries with exactly their variables
(owner OK 2026-10-26, `apply-systems.md` #Measuring safely). Also sent at load, blocked, nothing drawn
missing: Google Analytics, Sentry, `/api/wpt`; tenant C: hCaptcha's site check.

## Boxes

Gem's own boxes (`fields`, page order), each a plain text box under its label:

| fieldType | Label on the page | Seen | Shared kind / key |
|---|---|---|---|
| FIRST_NAME, LAST_NAME, EMAIL | First name, Last name, Email | 11 of 11, required | text `first_name` / `last_name`, email |
| LINKEDIN_URL | LinkedIn URL | 11 of 11 (required on 8) | url `linkedin` - see LinkedIn URL |
| PHONE | Phone number | 8 of 11, required | phone (typed "(555) 010-0100" style kept; Gem stores it as +1 and the digits) |
| LOCATION | Location | 8 of 11, required | text `location` - a plain box, no place search (tenant A) |
| RESUME | Resume | 11 of 11, required | file `resume` |
| COVER_LETTER | Cover letter | 6 of 11, optional | file `cover_letter` |
| COMPANY, JOB_TITLE | (in Gem's code, on no form seen) | 0 of 11 | text, labels guessed: unmeasured |

Employer questions (`questions`), 42 on 11 forms:

| answerType / displayType | Seen | Widget | Shared kind |
|---|---|---|---|
| LONG_TEXT | 16 | textarea | longtext |
| SINGLE_SELECT / DROPDOWN | 14 | button "Select an option" -> list | choice |
| SINGLE_SELECT / RADIO_BUTTON | 9 | radios, `id` = the option's `extId` | choice; Yes / No only -> yesno |
| SHORT_TEXT | 8 | text box | text |
| SINGLE_SELECT / null | 2 | radios (Gem's code: anything not DROPDOWN) | choice / yesno |
| MULTI_SELECT | 2 | ticks, `id` = the option's `extId` | multichoice - both were consent / text opt-ins |
| NUMERIC_RATING, FILE, DISPLAY_ONLY | 0 (in Gem's code) | number row, file box, words only | number (ASK, by hand), file (the user's own), skipped |

Titles print as typed: one employer wrote `**...**` for bold and the page shows the asterisks (tenant A) -
the shared title drops them. Seen: work permit, sponsorship (3 wordings), how you heard, which state, AI
tools used, expected pay, a non-compete, relocation to an office, privacy notice ticks, a text opt-in.

## Voluntary survey

`demographicSurvey.surveyType` picks a fixed survey under "Voluntary Self-Identification" (Gem's
`getEeocConfig`): EEO = gender + race (4 of 11), EEOV = + veteran status (3 of 11), EEOC = + disability
(0 of 11 - its label and options unmeasured: `ids_on_page` names it as a box the file lacks), none
(4 of 11). `survey.questions` was empty on every form. Options read off tenant C's open lists, nothing
picked (2026-10-26): Gender - Male, Female, Decline to self-identify; Race - Hispanic or Latino, five
"(Not Hispanic or Latino)" groups, Two or more races, Decline to self-identify; Veteran status - "I
identify as one or more of the classifications of a protected veteran listed above", "I am not a protected
veteran", "I decline to self-identify for protected veteran status". Never required. Filled from saved
answers only after the user's yes, like every system (`answers.md` #Saved voluntary answers).

## Widgets

No `<form>`, no names, no ids on blocks. Each block: a label (`span` with a red `*` span inside when
required; the survey's a `div`), then its box in the next element - or, when help words sit under the
label (an `em` description), in the label header's next sibling. `box_of` finds the label by its words and
marks its block (`data-jf`); `ids_on_page` matches labels to a fresh read (the page gives no ids) and
names any other label as `label:<words>`. A chosen file's name shows over its drop area like a label -
skipped.

- Text, textarea: React inputs; `fill` + change + blur kept the value (try, 3 of 3).
- Dropdown: a `button[type=button]` ("Select an option"; survey: "Please select") opens a list in
  `#floating-ui-portal` - questions `li[role=option]`, the survey `li[role=menuitem]`. A script `click()`
  on the button opens nothing: Playwright's real click does. After a pick the button shows its words.
- Radios + ticks: `input[id=<option extId>]` + `label[for]` with the option words; a click ticks.
- Resume: hidden `input[type=file]` (tabindex -1, never visible - READY waits on a text box instead)
  inside a drop area "Click to upload or drag and drop here"; the file's name + "×" shows above it.
- hCaptcha, invisible, at Apply (tenant C loaded it; Gem's code runs it on Apply) - the user's step.

## LinkedIn URL

Gem's check (`isLiUrl`, its `useSelfSchedulingLink.*.min.js`): `^(.+\.)?linkedin\.com/in/([^/?#]+)`, the
handle 3+ characters. Anything before `linkedin.com` must end in a dot: `linkedin.com/in/x`,
`www.linkedin.com/in/x` and `https://www.linkedin.com/in/x` pass; `https://linkedin.com/in/x` fails with
"Please enter a valid LinkedIn URL." (tenant A, typed by hand 2026-10-26 - the user added the `www.`).
Every system's LinkedIn answer is now written `https://www.linkedin.com/...` (`questions.link`); `fill`
refuses one Gem would reject (ASK) rather than type it.

## What leaves the computer, when

- Nothing as boxes are filled or the file is chosen: try on 3 tenants sent no write while filling (only
  Google Analytics page events, blocked). The page's own code keeps the resume in the page; Gem's
  "Parsing resume..." upload belongs to its recruiter-side form, not the job board's (read 2026-10-26).
- At Apply: everything - contact, answers, resume, cover letter - in one POST to Gem for the employer.
- The user's own Chrome showed two buttons: "Apply and save" (Gem keeps the contact details for the next
  Gem form - after it, other boards' forms opened filled in, LinkedIn as the user had typed it) and
  "Apply without saving". The fresh test browser shows one, "Apply". What decides it: unmeasured. Which
  button is the user's click.

## After Apply

Same address; the form gives way to "Congratulations! Your application for <title> has been received!"
(tenant A, 2026-10-26). No page of its own, so browser history can't tell a sent application (`sent.md`).
