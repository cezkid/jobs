# Oracle Recruiting Cloud application forms - measured facts

Oracle Recruiting Cloud = the recruiting part of Oracle's HR suite (Fusion HCM), used by large
employers; 5.1% of freehire's US postings (41.0k, 2026-10-03). `app/apply/systems/oracle.py` reads
the page the user is on (start box, then the form behind it, read generically by `dom`); shared
steps in `apply-systems.md`. Tenant named by letter, never employer; add yours as a new line.

**Measured: links, the start box (4 tenants, writes blocked, 2026-10-03). Not measured: what Next
does, and every page after it.** The owner's first real application checks them (owner's live check).

## Links

- `<pod>.fa.<dc>.oraclecloud.com/hcmUI/CandidateExperience/<lang>/sites/<site>/job/<id>` - every
  freehire `oracle` link (300 of 300 newest US, 2026-10-03). Hosts: `<pod>.fa.us2` (147),
  `fa-<x>-saasfaprod1.fa.ocs` / `<x>.fa.ocs` (83), `.fa.us6` (46), `.fa` (19), `em5`, `us1`, `us8`;
  1 on the employer's own domain - matched by Oracle's path, any host.
- `<id>` may carry letters (`REQ_814278`); ids are per employer, so the tab = host + site + id
  (`on_tab`), never the host alone.
- `application_url` = `.../<lang=en>/sites/<site>/job/<id>/apply/email`: the start box opens
  straight from it (4 of 4), in English - its steps are named by the English words.
- `measure --click "Apply Now"` on the job page (tenant A) clicked, but the read stayed on the job
  page; why unmeasured. `recover` opens the start box's link instead (a read), never clicks.

## Start box (tenants A, B, C, D)

"Job application form" - "Authentication screen. You don't need to have an account". The page's
own words: "Get started right away by providing us an email address. ... Your profile will be
created and kept up to date automatically as you enter details for each of your job applications."

| Box | Required | Filler |
|---|---|---|
| Email Address (`primary-email-<n>`, type email, autocomplete email) | yes | resume email |
| honeypot (`honey-pot-<n>`, text) - read as shown, meant for bots | no | never: not a question (`page_only`), `fill` refuses it. Its id number swaps with the email box's between employers (A: email 0 / trap 1, B: email 1 / trap 0): a stale hook fails on dom's label check |
| I agree with the terms and conditions (`legal-disclaimer-checkbox`) | yes | the applicant's own tick, never ours (`signs`) |
| Next, Cancel | - | Next = the applicant's click |
| "Do you want to communicate by phone instead?" (B only) | - | a switch to a phone box; not clicked - unmeasured |
| Cookie banner (A, C, D: Accept / Decline, Opt Out) | - | the applicant's choice; nothing clicks it |

Also on every page: a hidden digital-assistant box (`oda-work-summary-text-area`, required) -
dropped (`page_only`). No password box (4 of 4). Captcha: none on 4 start boxes (2026-10-03); an
invisible hCaptcha + a `g-recaptcha-response` box on 2 of 7 start boxes (2026-10-06, 2 tenants) - the
applicant's own, listed as their step.

Easy Apply route (1 tenant, 2026-10-06): `.../apply/email` redirects to `.../easy-apply/email`, label
"What's your email?", heading "Authentication screen. Let's get started", button "Next" - same email
box name (`primary-email`), so `on_tab` + `read` treat it as the start box. The "communicate by phone
instead?" switch showed on a second tenant too.

`try`, 3 tenants (A, B, D): Email ok, terms left as the applicant's step, 0 writes sent.
`read` recognises the start box by its email box (`name=primary-email`), page = "Job application form".

## Read back (2026-10)

What `oracle.holds` reads off the page once the form had time to keep it (`form.recheck`: refilled
once, still gone -> FAIL to fill by hand) - what shows, never the answer it was given. `dom.holds` on
the page without the bot trap. Fixtures `app/tests/fixtures/oracle/start-box.html` +
`start-box-easy-apply.html` (rebuilt from measure reads); Chrome tests in `test_apply_oracle.py`.

| Box | Read back |
|---|---|
| Email | its value exactly as typed, shown + label unchanged; emptied -> not held |
| honeypot | never: a hook or title naming the trap reads as not held, filled or not |
| terms tick | never ours (`signs`) - not held, ticked or not |
| box not on the page | not held |

No upload on the start box; pages after Next unmeasured (their read back = `dom.holds`, untested live).

## Closed posting (2026-10-06)

Measured over `.data/links/oracle-open.txt` + `-closed.txt` (42 links, 21 employers on the open list):
plain GETs of each posting's record + its site's job list, 2 s apart, 0 429; 20 page loads (max 6 per
host, canary ok each). Counts in `.data/measure/oracle-closed-check-2026-10-06.json`.

| List | Links | Record posted, on the job list | Record, no posted date, off list | Record gone (`items` []), off list |
|---|---|---|---|---|
| open | 26 | 19 | 3 | 4 |
| closed | 16 | 2 | 2 | 12 |

Start-box link loaded (9 links + 1 made-up id):

| Record | Links | Start box | "This job is no longer available." |
|---|---|---|---|
| posted (open 1, closed 1) | 2 | 2 | 0 |
| no posted date (open) | 1 | 1 | 0 |
| gone (open 4, closed 2) | 6 | 3 | 3 |
| made-up id | 1 | 0 | 1 |

- Closed page: `.../apply/email` redirects to the job page `.../job/<id>`, no boxes, words "This job is
  no longer available. You may also VIEW ALL JOBS / SEARCH FOR JOBS." (`form.CLOSED` matches).
- Record gone != closed: 3 of 6 gone records still opened a start box (2 tenants, Easy Apply on one).
  So the page decides first (`form.closed`: a box shows -> open; closed words -> closed); the record
  only speaks when neither shows.
- On the job list <=> posted start date past: 42 of 42. `ExternalPostedEndDate` past: 0 seen.
- Rule (`oracle.closed`): record gone -> "Oracle no longer has the posting on record - it may have
  closed"; end date past -> "may have closed"; no / future start date or any error -> "can't tell";
  posted -> None. Start box read as closed: 0 of 7.

## Pages after Next - unmeasured

Apply flow read on 4 tenants (`recruitingCEApplyFlows`, a public GET): `LegalEnabledFlag` 4 of 4,
`EsignEnabledFlag` 4 of 4 (an e-signature step likely follows: typing their name is the applicant's
own act - `read` says so), `TCOptinEnabledFlag` 3 of 4, `OptinEnabledFlag` 2 of 4,
`QuickApplyEnabledFlag` 0 of 4. Settings (tenant A): `ORA_IRC_AUTO_CONFIRM_CANDIDATE_ENABLED` Y,
`SMS_ENABLED_EXTERNAL_CANDIDATES` N. Whether a one-time code follows Next: unmeasured.

`read` takes whatever page shows as plain boxes (`dom.questions`), page = its first heading, and
prints "unmeasured system - check every box". Owner's first real application = the live check.

## Form definition

None public for the questions: they come after the applicant's profile is made, behind Next -
unmeasured. Public GETs, no key, same origin: `recruitingCEJobRequisitionDetails?expand=all&
onlyData=true&finder=ById;Id="<id>",siteNumber=<site>` (the posting) and `recruitingCEApplyFlows?
finder=findByRequisitionNumber;RequisitionNumber="<id>"` (flow flags, legal + e-signature text).

## What leaves the computer, when

| What | When |
|---|---|
| Listing id (posting, apply flow, site settings reads) | opening the start box |
| Visit tracking (`recruitingCEUserTrackings` POST, B), ad tags (Google, C) | page load (blocked in every run) |
| Listing id (posting record read) | only when no box shows, to say why (`closed`) |
| Email | the user's own click on Next - before the form |
| Everything after | unmeasured - first real application |

## Tenant notes

- A (`<pod>.fa.us2`): start box, cookie banner; email filled by `try` (2026-10-03).
- B (`fa-<x>-saasfaprod1.fa.ocs`): start box offers phone instead of email; email filled by `try`.
- C (`<pod>.fa.us2`): start box with an extra note for current workers; measured, not tried.
- D (`<x>.fa.ocs`): start box, cookie banner with Opt Out; email filled by `try`.
