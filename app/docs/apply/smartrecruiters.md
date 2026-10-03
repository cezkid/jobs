# SmartRecruiters application forms - measured facts

SmartRecruiters = careers site for many employers (`jobs.smartrecruiters.com/<Company>/<postingId>-<slug>`).
Measured 2026-10-03 on 4 open US postings, 4 tenants, through `apply-form measure` (block on, page 1
only). Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer;
add yours as a new line.

## Form definition

The form is SmartRecruiters' own one-page app ("oneclick-ui"), no account needed (4 of 4 tenants,
2026-10-03):

1. `GET https://api.smartrecruiters.com/v1/companies/<Company>/postings/<postingId>`, no key: `uuid`,
   `applyUrl` (= posting link + `?oga=true`), `active`, `company.identifier` (= `<Company>`). Only the
   listing id goes out - same as opening the posting. Fixture: `app/tests/fixtures/smartrecruiters/posting.json`.
2. Form: `https://jobs.smartrecruiters.com/oneclick-ui/company/<Company>/publication/<uuid>?dcr_ci=<Company>`
   - opened straight, it renders the form (4 of 4).
3. The page then fetches `GET /oneclick-ui/api/company/<companyId>/publication/<uuid>/config`.
   `companyId` = internal 24-hex id, not in the public posting record. The same link from plain
   `curl` -> 403 (bot check) - read it from the page, never fetch it alone.

`config.fieldSets` - each `{required, visible}` (fixtures `config-tenant-a..d.json`):

| Part | Holds | Seen (4 tenants) |
|---|---|---|
| `firstAndLastName`, `email`, `phoneNumber` | contact boxes | required, visible in 4 of 4 |
| `placeOfResidence` | `configuration.locationType` | `CITY`, required in 4 of 4 |
| `resume` | resume upload | required in 3, optional in 1 (tenant B) |
| `experience`, `education` (`institution`, `educationDates`) | "Add" lists | optional in 4 of 4; `educationDates` required in 1 (tenant C) |
| `socialProfiles` (`linkedIn`, `website`, `facebook`, `x`) | link boxes | optional; Facebook + X hidden in 1 (tenant C) |
| `messageToHiringManager` | free text | optional; hidden in 1 (tenant C) |
| `easyApply` (`ResumeParsing`, `Indeed`, `LinkedIn`, `Seek`, `PitchYou`) | prefill buttons from other sites | visible in 4; LinkedIn hidden in 1 (tenant D) |

No employer questions on page 1 in any tenant. Screening questions (+ any EEO / consent) come
after Next on a later page - unmeasured (needs `try --next`, build bead).
`api.smartrecruiters.com/postings/<uuid>/configuration` (the documented apply API) -> 401
"Authentication data missing" without a partner key (2026-10-03): no public question list.

Kinds: names / email / phone / links -> text (email, phone by type), City -> location, resume ->
file, message -> longtext, Experience / Education -> unmeasured (editors not opened).

## Widgets (tenants A-D, 2026-10-03)

Angular page; every box sits inside Spark `spl-*` web components with OPEN shadow roots
(`in_shadow` 15 of 16 controls, tenant A). Locators that pierce shadow roots reach them.

| Box | On the page | Filler rule |
|---|---|---|
| First / Last name | `#first-name-input`, `#last-name-input` (`autocomplete` given-name / family-name) | by id |
| Email + Confirm | `#email-input`, `#confirm-email-input` - both required | same value in both |
| City | `spl-autocomplete` combobox, label "City*", id `spl-form-element_<n>` | id made per page build - never a hook; find by role combobox + label "City"; options unmeasured (typing is the build bead's try) |
| Phone | `spl-phone-field`: button combobox "Country code" + hidden search box "Search by country/region or code" + `input[type=tel]` "Phone number" (required) | ids `spl-form-element_<n>` - by label; country list unmeasured |
| LinkedIn / Facebook / X / Website | `#linkedin-input`, `#facebook-input`, `#twitter-input`, `#website-input` | by id; absent when hidden (tenant C: LinkedIn + Website only) |
| Message to hiring manager | `textarea#hiring-manager-message-input` | by id |
| Resume | 2 hidden `input[type=file]#file-input` in shadow roots, both labelled "Choose a file or drop it here" - one = easy-apply resume parsing (top), one = resume field | same id twice: scope by shadow host (`oc-resume-upload` per planning probe - host tag unmeasured here); first one = parsing, fills boxes from the file - avoid |
| Profile image | hidden `input[type=file]` "Upload profile image", light DOM (tenant A only) | left alone (no photo) |
| Experience / Education | "Add" buttons open editors | unmeasured: whether saving an entry sends anything |

`ids changed between loads`: 0 of 16 (tenant A) - the `spl-form-element_<n>` numbers held across 2
loads, still generated, never a hook.

## Pages

Page 1 as above, then Next. Later pages unmeasured (2026-10-03).

## What leaves the computer, when

Blocked on load alone, nothing typed (2026-10-03, 4 tenants, 12-20 POSTs per run): DataDome
(`api-js.datadome.co/js/`), Cloudflare challenge (`/cdn-cgi/challenge-platform/...`), SmartRecruiters
RUM (`rum.smartrecruiters.com/sink/`), TrackJS, Google Analytics (tenants A, D; tenant A's
named the event `applicationStarted`), DoubleClick ad tag (tenant D), LinkedIn apply widget frame POST
(tenants A-C - not D, which hides LinkedIn easy apply). Form still rendered with all blocked (4 of 4).
Per-question sends: build bead's `try`.

Bot checks: DataDome + Cloudflare challenge scripts load on every form; no captcha shown on page 1
(4 of 4).

## Closed posting

Unmeasured. The public posting record carries `active` - read it first.

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | all fieldSets visible; resume required; profile image upload present; Seek easy-apply visible |
| tenant B | resume optional |
| tenant C | Facebook, X, message to hiring manager hidden; education dates required |
| tenant D | LinkedIn easy-apply hidden; DoubleClick ad tag POST on load |
