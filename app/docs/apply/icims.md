# iCIMS application forms - measured facts

iCIMS = a hiring system used by mid-size and large employers (health care, finance, retail); 3.3% of
freehire's US postings (26.5k, 2026-10-03). `app/apply/systems/icims.py` reads the page the user is on
(start box, then the form behind it, read generically by `dom`); shared steps in `apply-systems.md`.
Tenant named by letter, never employer; add yours as a new line.

**Measured: links, the start box (3 tenants, writes blocked, 2026-10-03). Not measured: what Next
does, and every page after it.** The owner's first real application checks them (owner's live check).

## Links

- `careers-<co>.icims.com/jobs/<id>/<slug>/job` - 289 of the 300 newest freehire `icims` US links
  (2026-10-03); also `uscareers-<co>` (3), `dcacareers-<co>` (2), `general-careers-<co>`,
  `<x>-<co>careers` (1 each) - matched as any `*.icims.com` host with `/jobs/<digits>`. 4 sit on an
  employer's own domain (`careers.<co>.com/jobs/<id>`, no iCIMS path) - out of scope, not matched.
- Query: `utm_source` (296), `lang` (4) - dropped.
- Job ids are per employer: the tab = host + job id (`on_tab`), never the host alone.
- `application_url` = `.../jobs/<id>/<slug>/login`: the start box opens straight from it (3 of 3).
  A link without a slug -> `.../jobs/<id>/login` - unmeasured.
- Job page (`.../job`, tenant D): no boxes on the page as read. `recover` opens the start box's link
  instead (a read), never clicks Apply.

## Start box (tenants A, B, C)

The boxes sit in the page's own same-site frame (`?in_iframe=1`), not the page itself (3 of 3):
`dom` reads it; `READY` alone can't see inside it, so `recover` waits for a box in any frame.

| Box | Required (as marked) | Filler |
|---|---|---|
| Email (`id=email`, `name=css_loginName`, type email, autocomplete email) - label "Primary Email Address" (A) or "Email" (B, C) | not marked (3 of 3) | resume email |
| "Yes, I agree to <employer> Candidate Data Privacy Policy" (`accept_gdpr`, B only) | yes | the applicant's own tick, never ours (`signs`) |
| Next (`enterEmailSubmitButton`, a submit input) | - | the applicant's click; not a question (`from_snapshot`, `ids_on_page`) |
| hCaptcha, invisible (`h-captcha`, 3 of 3) | - | the applicant's own; its config calls blocked on load |

Heading: "Enter Your Information" (A, B), "New External Applicants Enter Your Email Below" (C) -
`read` recognises the start box by its email box (`name=css_loginName`), page = "Enter Your Information".
No password box on the start box (3 of 3). The page's own words around the box sit in the frame and
weren't captured - what Next does is described from what's measured only.

`try`, 3 tenants (A, B, C): email ok, the privacy tick (B) + captcha + Next listed as the applicant's
own steps, 0 writes sent (blocked: hCaptcha config, analytics, ad tags - all on page load).

## Pages after Next - unmeasured

Sign in, a password, a new account with the employer, more boxes: per tenant, none measured. `read`
takes whatever page shows as plain boxes (`dom.questions`), page = its first heading, and prints
"unmeasured system - check every box". Owner's first real application = the live check.

## Form definition

None public found: the questions come after Next, per employer - unmeasured.

## What leaves the computer, when

| What | When |
|---|---|
| Listing id (job page, start box reads) | opening the start box |
| Security check config (hCaptcha), analytics + ad tags (B, C), chat widget (C) | page load (blocked in every run) |
| Email | the user's own click on Next - before the form |
| Everything after | unmeasured - first real application |

## Tenant notes

- A (`careers-<co>`): start box, email filled by `try` (2026-10-03).
- B (`careers-<co>`): start box with a privacy-policy tick; email filled by `try`.
- C (`careers-<co>`): start box headed for new external applicants, chat widget on the page; email
  filled by `try`.
- D (`careers-<co>`): job page only, measured (no boxes); not tried.
