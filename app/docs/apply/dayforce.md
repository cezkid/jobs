# Dayforce application forms - measured facts

Dayforce = payroll + hiring system (2.6% of freehire's US postings, 7 on the owner's list,
2026-10-03). Posting `jobs.dayforcehcm.com/<lang>/<tenant>/<board>/jobs/<id>` - one host for every
employer, Next.js app; tenant + board in the link (board = a word like `candidateportal` or a
number). Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer.

Measured 2026-10-03 with `apply-form measure` on 4 employers (tenants A-D), 12 page loads in all
on the shared host (budget reached): tenants A-C at the apply choice page, D at the posting page.
Saved: `app/tests/fixtures/dayforce/` (`tenant-<a..d>.json` page outline, reads, blocked writes;
`site.json` site settings + feature flags). Measure keeps the first 2048 B of each JSON reply:
keys past that are unmeasured.

**The form itself did not render while writes were blocked (2 of 2 tenants that offer it):** it
is not measurable while blocked, so every form fact below marked "planning probe" is unverified.

## Form definition

Unmeasured - the form page never loaded under the block (Pages). What was seen on the way:

| Source | Holds | Seen |
|---|---|---|
| `GET /api/geo/<tenant>/sitecontext/<tenant>/<board>/<lang>` (+ `?jobPostingId=`) | site settings per tenant: `enableApplyWithoutAccount`, `enableApplyWithPhoneNumber`, `hasActiveSMSProvider`, `privacyPolicy` (consent text shown at Submit), `candidateConversionTracking` (pixels, below), `isoCultureCodes` (en-US, fr-CA, es-MX on B, C) | 4 of 4 |
| `GET /api/geo/<tenant>/jobposting/<tenant>/<lang>/<boardId>/<id>` | the posting: `jobPostingId`, `jobReqId`, `jobTitle`, dates, `isEvergreen`, `isInternal`, `reapplyPeriodDays`, `jobPostingContent` (HTML) | D; questionnaire keys, if any, past the 2048 B kept - unmeasured |
| `GET app.launchdarkly.com/sdk/evalx/...` | feature flags, same on B + C: `anonymous-applications-enabled` true, `captcha-enabled` true, `authentication-enabled` true | 3 of 3 flow pages |
| `GET /_next/data/<build>/<lang>/<tenant>/<board>/jobs/<id>/apply/manualApplication.json?applicationSource=Manual` | the form page's data | fetched on the "Apply without an Account" click, 200 with empty body read (B, C); page stayed on the choice |

Planning probe (2026-10-03, one tenant, outside `apply-form` - not re-measured): steps Candidate
Info -> Questionnaire -> Submit; Candidate Info boxes are Ant Design with ids
`jobPostingApplication_personalInfo_<field>` (`email`, `confirmEmail`, `prefixId`, `firstName`,
`middleName`, `lastName`, `suffixId`, `linkedInURL`, `homePhone`, `mobilePhone`, `fax`, `pager`,
`preferredContactMethod`, `countryCode`, `stateCode`, `address1`, `address2`, `city`, `county`,
`postalCode`, `candidateSource`), files `jobPostingApplication_files_{resume, coverLetter,
additionalDocument}`, `jobPostingApplication_educationHistory_<i>_*`,
`jobPostingApplication_workHistory_<i>_*`, references; "Import Resume"; Update / Cancel per
section. Questionnaire definition: unmeasured.

## Widgets

Form boxes: unmeasured (not rendered while blocked). On the pages that did render (2026-10-03):

| Box | On the page | Filler rule |
|---|---|---|
| apply choice | `.../jobs/<id>/apply?flowSelection=true`: button "Apply without an Account", heading "Already Have an Account?", "Sign In", link "Create one now." (B, C); only "Sign In" (A) | "Apply without an Account" only - never sign in or create an account (applicant's own act). Tenant without it (A: `sitecontext` reply cut before `enableApplyWithoutAccount`) = account wall: say so, no fill |
| form link opened directly | `.../apply/manualApplication?applicationSource=Manual` lands back on the choice page (A) | open the choice page, not the form link |
| posting page | button "Apply", "Share", map; language box `lang-select` (D) | Apply leads to the choice page (planning probe) |
| cookie banner | "Cookie Preferences": "Accept", "Reject", "Cookie Settings" (4 of 4) | "Reject" - never "Accept". A `--click "Reject"` on the choice page timed out (A, 15 s): banner rendered after the click was tried |
| planning probe | dialing-code selects get generated `rc_select_<n>` ids | never a hook (unverified) |

## Pages

Choice page -> form; form steps Candidate Info -> Questionnaire -> Submit (planning probe).
Not measurable while blocked (B, C, 2026-10-03): the "Apply without an Account" click fetches the
form page's data (GET, 200) and the page stays on the choice - no box rendered, no write tried
after the click. Blocked at every load: Cloudflare bot check `POST /cdn-cgi/challenge-platform/
.../jsd/oneshot/...` (4 of 4) - likely what the form page waits on; unmeasured which.

## What leaves the computer, when

Measured on load only (nothing typed), 2026-10-03:

- Opening the posting or the choice page: GETs to Dayforce + feature flags (LaunchDarkly).
- Blocked at every load (4 of 4): Cloudflare bot check (POST, above), Azure Application Insights
  (`.../v2/track`, page-use telemetry), LaunchDarkly diagnostics.
- Tenant D's site settings list "candidate conversion" pixels: an ad network's image link with
  `{CandidateID}`, `{JobRequisitionID}`, `{JobPostingApplicationID}`, at start and at finish
  (`candidateConversionType` 3; B, C: none, type 1). An image is a GET - the block lets it through.
  When it fires: unmeasured.
- Email, resume, anything typed: unmeasured (form not rendered).

## Closed posting

Unmeasured.

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | choice page shows "Sign In" only - no "Apply without an Account"; form link opened directly lands on the choice page |
| tenant B | "Apply without an Account" offered (`enableApplyWithoutAccount` true); click: form data fetched, page stays (blocked); no SMS, no conversion pixels |
| tenant C | same as B: choice offered, form not rendered while blocked |
| tenant D | posting page only: Apply + Share; conversion pixels at application start + finish; privacy-consent text shown with the form |
