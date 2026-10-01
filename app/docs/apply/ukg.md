# UKG Pro Recruiting application forms - measured facts

UKG Pro Recruiting (formerly UltiPro) = careers site for many mid-size employers
(`recruiting<N>.ultipro.com/<tenant>/JobBoard/<board>/OpportunityDetail?opportunityId=<id>`).
`app/apply/systems/ukg.py` reads the form off the signed-in page, types answers into its widgets;
shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer; add
yours as a new line.

## Sign-in first (tenant A, 2026-09)

`OpportunityApply` redirects to `signin-us.ultipro.com` (email + password, "Sign up" link). No
public form definition: the posting page carries no questions, so `prepare` opens the apply link
in Job Finder's Chrome and stops on the sign-in page. User signs in or creates the account there
(never typed for them - job-apply hard limits); sign-in stays in Job Finder's Chrome profile, so
`prepare` and `fill` after it go straight to the form.

## One long page

Every section on one page: contact, work experience, education, skills, behaviors, motivations,
licenses, links, documents, availability, questions, voluntary self-identification, Submit.
Footer: "Once you leave this page, you won't be able to edit the information you entered."

## Form definition

Page = Knockout. `ko.contextFor([data-automation=application-knockout-question]).$parent.opportunity
.ApplicationQuestions` = employer's screening questions: `Id` (GUID, stable - used as question id),
`Question`, `ResponseType` (MultipleChoice, Text, Numeric), `ResponseConfiguration.Choices[].Text`.
The rest read by element id / `data-automation` (below). `SNAPSHOT` in `ukg.py` returns both.

## Widgets (tenant A)

| What | On the page | Filler rule |
|---|---|---|
| Name, email | `#FirstName`, `#FamilyName`, email as text - from the account | never filled; page says change the name on "My presence" before Submit |
| Phone, address | `#Phone` (tel), `#AddressLine1`, `#City`, `#PostalCode`; address, city, state, zip required | `fill` + `change` event + blur; phone read back by digits. Address = user's: `home_address` in search settings, else asked |
| Country, State | `select#Country`, `select#State` | select by label; State list reloads after Country - wait for the option (up to 10s) |
| How did you hear | `select#ApplicantSource` | asked, never guessed |
| Referral | radios `data-automation=yes-employee-referral-radio` / `no-...` | check; referral name box shows only after Yes |
| Start date | UKG date picker `[data-automation=available-start-date-datepicker]`: 3 inputs Month / Day / Year inside a web component | type each part, Tab out, read back. Required |
| Screening questions | `[data-automation=application-knockout-question]` in `ApplicationQuestions` order; hidden templates inside each block reuse the same `data-automation` | find block by GUID via `ko.dataFor(block).Id`; MultipleChoice = radio w/ `span.radio-text`, click visible one by exact text; Text = visible `textarea[data-automation=text-response]`; Numeric = `input[data-automation=numeric-response]` |
| Resume | `input[type=file][data-automation=upload-file-input]` in `[data-automation=application-documents]`; row shows file name, Document Type defaults to Resume | upload only after user's yes; confirm file name shows |
| Self-identification | `select#Gender`, `#HispanicOrigin`, `#EthnicOrigin` (Race - shown only after "Not Hispanic/Latino"), `#USFederalContractor` (protected veteran); each has an "I decline to say" checkbox in its `.form-group` | select by label; "I decline to say" = tick that checkbox - only when shown: Race hidden (list + box) after "Hispanic/Latino" -> skipped, else ticking waits 30s and fails (2026-09-30). Asked unless user saved answers under `self_identification` |
| Behaviors, Motivations, Availability | tag pickers + day grid, optional | left for the user - self-description, never guessed |

## Work history, education, skills, links (resume sections)

Separate panels: `[data-automation=work-experience-panel]`, `education-panel`, `skills-panel`,
`links-panel`. Upload does NOT fill them (resume attached, panels stayed empty). Each entry: panel's
visible `primary-action-button` opens an editor; its own `save-button` **saves to the user's account
on the site at once** (`POST .../Candidate/InsertWorkExperience`, measured) - before Submit. So one yes/no question
(`resume-sections`), said plainly before they answer.

| Panel | Boxes | Rule |
|---|---|---|
| Work experience | `job-title-textbox`, `company-textbox`, `location-textbox`, `from-month-dropdown` (Jan..Dec), `from-year-textbox`, `to-...` same, `description-textarea` (2000 chars) | To left blank = "Current". Description = this job's tailored lines (same as the PDF), else the resume's |
| Education | `school-textbox` + `degree-textbox` = typeaheads (suggestions `.tt-suggestion`), `major-dropdown` (fixed list, ~270), `description-textarea` | school: site's spelling when listed ("... College (NJ)"), else typed. Degree searched by word: BA -> "Bachelors", AA -> "Associates", M -> "Masters", PhD -> "Doctorate"; none -> cancel + ASK. Major: exact or longest prefix of the field, else blank; field goes in description |
| Skills | pencil `primary-action-button`, `item-typeahead` + `item-add-button`, each skill gets a level select (default Not Specified) | type, click Add; **never Escape - it closes the editor**. Level left Not Specified (a self-rating) |
| Links | rows `#LinkName<i>` / `#LinkUrl<i>`, `primary-action-button` adds a row | needs `change` event - without it Save says "Link name must not be empty" |

- First typeahead search after an editor opens comes back empty while its list loads
  ("Bachelor" -> nothing, same again -> "Bachelors"): wait, retype once.
- Saved = editor closes. Refused entry stays open, reason under the box in `.has-error
  .help-block`; hint lines ("Leave this blank if you currently work here") share `.help-block`.
- Rerun safe: work entry skipped when "Title, Company" already listed, school by name, skill by
  text, link by `href`.

## Sent or not

No sent page in history. Signed in: My Presence (`.../Candidate/ViewPresence`) -> Applications
tab lists Job / Status / Date applied, or "You have not yet applied to any opportunities". Detail
page keeps "Apply now" either way - not a sign. `app/docs/apply/sent.md`.

## Browser

Shared w/ every system: `apply-systems.md`, `app/apply/browser.py`. `navigator.webdriver` false on
the form (measured, Chrome 154).

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | 5 screening questions (federal employment, current state as free text, US work eligibility, visa sponsorship "at <employer>", pilot); sponsorship worded per employer - asked, not from setup |
