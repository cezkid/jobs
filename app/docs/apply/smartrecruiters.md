# SmartRecruiters application forms - measured facts

SmartRecruiters = careers site for many employers (`jobs.smartrecruiters.com/<Company>/<postingId>-<slug>`).
Measured 2026-10-03 on 4 open US postings, 4 tenants (A-D), through `apply-form measure` (block on, page 1
only); filled by `apply-form try` on 3 (A, B + new tenant E). Shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer;
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
after Next on a later page - not measurable while blocked (Pages).
`api.smartrecruiters.com/postings/<uuid>/configuration` (the documented apply API) -> 401
"Authentication data missing" without a partner key (2026-10-03): no public question list.

Kinds: names / email / phone / links -> text (email, phone by type), City -> location, resume ->
file, message -> longtext, phone country -> choice. Experience / Education "Add" lists are not
read as questions (optional in 4 of 4; editors unopened) - left to the applicant.

## Widgets (tenants A-D, 2026-10-03)

Angular page; every box sits inside Spark `spl-*` web components with OPEN shadow roots
(`in_shadow` 15 of 16 controls, tenant A). Locators that pierce shadow roots reach them.

| Box | On the page | Filler rule |
|---|---|---|
| First / Last name | `#first-name-input`, `#last-name-input` (`autocomplete` given-name / family-name) | by id |
| Email + Confirm | `#email-input`, `#confirm-email-input` - both required | same value in both |
| City | `spl-autocomplete` combobox, label "City*", id `spl-form-element_<n>` | hook = role + label. Options: `<spl-select-option value="US_NY_CITY_new_york_city">` in the list the box's `aria-controls` names, label in an inner `title="New York, NY, US"` (3 tenants, 2026-10-03) | type the town, wait for the list, click the option whose label starts with it by script - never the first offered |
| Phone | `spl-phone-field`: button combobox "Country code" + hidden search box "Search by country/region or code" + `input[type=tel]` "Phone number" (required) | by label. Country = host `<spl-select value="US">`, options `<spl-select-option value="AF" label="Afghanistan">`; set to US on load (4 of 4 US postings) | left as is when it already shows the answer; else Enter opens it, search typed, option clicked by script |
| LinkedIn / Facebook / X / Website | `#linkedin-input`, `#facebook-input`, `#twitter-input`, `#website-input` | by id; absent when hidden (tenant C: LinkedIn + Website only) |
| Message to hiring manager | `textarea#hiring-manager-message-input` | by id |
| Resume | 2 hidden `input[type=file]#file-input` in shadow roots, both labelled "Choose a file or drop it here" - one = easy-apply resume parsing (top), one = resume field | the file box after `#first-name-input` in page order (shadow roots walked) = the field; the one above = parsing, fills boxes from the file - never used. Took = the file's name shows on the page |
| Profile image | hidden `input[type=file]` "Upload profile image", light DOM (tenant A only) | left alone (no photo) |
| Experience / Education | "Add" buttons open editors | unmeasured: whether saving an entry sends anything |

Pointer clicks on City, the phone country and Next waited 30s and failed (another layer over the
form's foot, 2 of 3 tenants, 2026-10-03): those are chosen by script / keyboard.

`ids changed between loads`: 0 of 16 (tenant A) - the `spl-form-element_<n>` numbers held across 2
loads, still generated, never a hook.

## Pages

Page 1 as above, then Next (a Spark button: its label is slotted text, found by accessible name).
`try --next` with every write blocked: Next pressed, page unchanged (tenant E, 2026-10-03) - page 2
not measurable while blocked (the resume upload or the bot check needs its write). So screening
questions are read off the user's own tab once they press Next: `read(page)` names any step
without the name boxes "Screening questions", fills what it shows, LATER for page-1 boxes.

## What leaves the computer, when

Blocked on load alone, nothing typed (2026-10-03, 4 tenants, 12-20 POSTs per run): DataDome
(`api-js.datadome.co/js/`), Cloudflare challenge (`/cdn-cgi/challenge-platform/...`), SmartRecruiters
RUM (`rum.smartrecruiters.com/sink/`), TrackJS, Google Analytics (tenants A, D; tenant A's
named the event `applicationStarted`), DoubleClick ad tag (tenant D), LinkedIn apply widget frame POST
(tenants A-C - not D, which hides LinkedIn easy apply). Form still rendered with all blocked (4 of 4).
Per box (`apply-form try`, tenants A, B, E, 2026-10-03, all blocked):

- Resume: `POST /oneclick-ui/api/company/<companyId>/attachment/resume` the moment the file is chosen
  (3 of 3) - the EARLIEST send of anything the applicant typed or chose. Upload only after the user's yes.
- City: Google Analytics POST while typing it (1 of 3, tenant A) - an event, no value seen. The
  place list arrives after a pause in typing = a search read (reads aren't blocked or logged):
  the typed town goes to SmartRecruiters then (inferred, request unlogged).
- Names, email, links, message, phone: no write fired.
- Everything else leaves at Submit (not pressed).

Bot checks: DataDome + Cloudflare challenge scripts load on every form; no captcha shown on page 1
(4 of 4).

## Closed posting

Page wording unmeasured. The public posting record carries `active`: `questions` reads it first and
stops on `false` ("posting not active - it may have closed").

## Tenant notes

| Tenant | Measured 2026-10-03 |
|---|---|
| tenant A | `try`: all 13 boxes ok, analytics POST while typing City; all fieldSets visible; resume required; profile image upload present; Seek easy-apply visible |
| tenant B | `try`: all 13 boxes ok; resume optional |
| tenant C | Facebook, X, message to hiring manager hidden; education dates required |
| tenant D | LinkedIn easy-apply hidden; DoubleClick ad tag POST on load |
| tenant E | `try`: all 13 boxes ok; `--next` page unchanged while blocked |
