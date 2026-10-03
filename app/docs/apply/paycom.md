# Paycom application forms - measured facts

Paycom = payroll + hiring system for many small and mid-size employers; 5.3% of freehire's US
postings (42.9k, 2026-10-03). `app/apply/systems/paycom.py` reads the page the user is on (start
box, then the form behind it, read generically by `dom`); shared steps in `apply-systems.md`.
Tenant named by letter, never employer; add yours as a new line.

**Measured: links, the job page, what Apply does (from Paycom's own page code). Not measured: the
start box's page (it doesn't open while writes are blocked - below) and every page after it.**
The start box's labels below were seen once by hand (2026-10-03, one tenant, planning); the
first real application checks them (owner's live check).

## Links

- `www.paycomonline.net/v4/ats/web.php/portal/<key>/jobs/<id>` - every freehire `paycom` link
  (30 of 30 newest US, 2026-10-03). `<key>` = 32 hex, one per employer.
- Older: `.../web.php/jobs/ViewJobDetails?job=<id>&clientkey=<KEY>` - same key + job.
- One host serves every employer, and one job id can name jobs at two employers (two tenants'
  newest postings shared one, 2026-10-03): this application's tab = key + job id (`on_tab`),
  never the host alone.

## Job page (tenants A, B, C, D; 2026-10-03)

React app ("sprawl" bundle from `portal-applicant-tracking.<region>.paycomonline.net`). Reads its
posting, company name, portal settings and an hCaptcha site key as JSON GETs. No form controls
(0 read on 4 tenants); buttons: Sign In, Create Account, Apply, Accept Cookies.

## Start box

What Apply does (Paycom's public page code, 2026-10-03): fetches the employer's privacy policy
(GET `api/ats/privacy-policy?id=<job>`), then opens the quick-apply box with an hCaptcha. A tab
in a frame opens the box in a new tab instead (`#!apply-sign-in`).

Not measurable while blocked: Apply clicked on tenants A + B (`measure --click Apply`, 2 loads
each) - page unchanged, 0 controls; the click's only write was a POST to `api/analytics`
(blocked). The privacy-policy read came back empty (200, 0 bytes) - likely why the box never
opened; not proved. `#!apply-sign-in` on tenant C: blank page, 0 controls. `try` on tenant D:
"form never showed". Never worked around (apply-systems.md: no allow-lists).

Seen by hand (one tenant, 2026-10-03), heading "Getting You Started":

| Box | Required | Filler |
|---|---|---|
| Legal First Name, Legal Last Name | yes | `contact.legal_*`, else asked (`key_from_title`) |
| Email, Confirm Email | yes | resume email, both (typed as email by label: their input type unmeasured) |
| Primary Phone (+ country) | yes | resume phone; country list as the page offers it |
| "Do you consent to receiving text communications ... (SMS)" Yes / No | yes | never answered - the applicant's own (`questions.signs`) |
| hCaptcha | - | the applicant's own (`dom.user_steps`) |
| Continue To Application | - | the applicant's click; it creates their applicant record |
| Already have an account? Sign In / Create Account | - | the applicant's own |

Page code names the phone parts `primaryPhoneNumber`, `primaryPhoneIsoCode`, `primaryPhoneOptIn`
- the box's own ids unmeasured. `read` recognises the box by its labels (Legal First Name +
Confirm Email) and tags each box `page="Getting You Started"`.

## Pages after Continue - unmeasured

After Continue the page code sends the user to `applications/<id>` (same portal). `read` takes
whatever page shows as plain boxes (`dom.questions`), page = its first heading, and prints
"unmeasured system - check every box". Owner's first real application = the live check.

## Form definition

None public. The page code fetches questions after the record exists (`getQuestions`,
`getApplicationForRequisition`) - behind the applicant's sign-in, unmeasured.

## What leaves the computer, when

| What | When |
|---|---|
| Listing id (posting + privacy policy reads) | opening the job page, clicking Apply |
| Page-view analytics (job, screen size, referrer) | page load + Apply click (POST `api/analytics`) |
| Name, email, phone (+ SMS answer) | the user's own click on Continue To Application - before the form |
| Everything after | unmeasured - first real application |

## Tenant notes

- A, B: Apply opens nothing while blocked (2026-10-03).
- C: `#!apply-sign-in` link renders blank while blocked (2026-10-03).
- D: `try` - "form never showed" (2026-10-03).
