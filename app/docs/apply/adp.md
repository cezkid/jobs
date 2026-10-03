# ADP Workforce Now application forms - measured facts

ADP Workforce Now = ADP's payroll + HR suite for mid-size employers, with its own recruitment pages;
2.6% of freehire's US postings (21.0k, 2026-10-03). (`myjobs.adp.com` is another ADP product - not
this system.) `app/apply/systems/adp.py` reads the page the user is on (start box, then the form
behind it, read generically by `dom`); shared steps in `apply-systems.md`. Tenant named by letter,
never employer; add yours as a new line.

**Measured: links, the job page, the start box (5 tenants, writes blocked, 2026-10-03). Not
measured: what Continue does, and every page after it.** The owner's first real application checks
them (owner's live check).

## Links

- `workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?ccId=<id>&cid=<uuid>&jobId=<id>&lang=en_US`
  - every freehire `adp` link (10 of 10 newest US, 2026-10-03). Params come in any order; `ccId`
  and `lang` may be missing, `selectedMenuKey` may be added. `cid` = one per employer.
- `application_url` keeps `cid`, `ccId`, `jobId` and sets `lang=en_US`: the start box is
  recognised by its English labels.
- One host serves every employer, and one `jobId` was listed under two employers' `cid`s
  (freehire, 2026-10-03): this application's tab = `cid` + `jobId` (`on_tab`), never the host alone.

## Job page (tenants A-H; 2026-10-03)

One-page app; reads the posting, the employer's settings (`client-features`), `allow-login` and
content links as JSON GETs. Only controls: the cookie panel's (OneTrust) hidden preference boxes -
Functional, Analytics, Advertising, "Cookie list search", "checkbox label" x4. Buttons: Join Our
Talent Community, Apply (twice), Back.

Cookie choices are the applicant's consent: `read` drops the panel's boxes and `fill` refuses them
(`page_only`). A `try` before that ticked them on tenant C (blocked run, nothing sent).

## Start box (tenants C, D, E, F, H)

Apply opens "Tell us about yourself." over the job page - same link, no navigation, no write in
the click. `recover` clicks that Apply once when the tab is still on the job page; nothing else.

The page's own words: "Please be advised that the mobile number or email associated with this
verification process is intended to be unique to you. Any subsequent use of the same mobile number
or email by another user will become associated with the new user and override the first name,
last name, work history, education, or skills associated with your profile."

| Box | Required | Filler |
|---|---|---|
| First Name (`guestFirstName`), Last Name (`guestLastName`) | yes | resume name |
| Email (`guestEmail`, a plain text input) | yes | resume email (typed as email by label) |
| Mobile Number (`login_view_phone`, tel, prefilled "+1") + country picker | yes - the employer's setting (`PhoneNumberRequiredIndicator`, 3 of 3 tenants read), not marked on the box | resume phone, the box's own code in front (`with_code`: the box keeps "+1", typed digits alone never matched) |
| Continue (carries reCAPTCHA, class `g-recaptcha`) | - | the applicant's click; the security check is theirs |
| Sign in with LinkedIn / Google / Facebook | - | the applicant's own; never by us |

`try`, 5 tenants: 4 of 4 boxes ok, 0 writes sent. No consent, terms or SMS box on the start box.
`read` recognises it by its four labels and tags each box `page="Tell us about yourself"`.

Not measurable while blocked - tenants A, B, G: Apply opens nothing (`measure --click Apply` on A,
B; `try` on A, B, G: "form never showed"). A + B both list an employer privacy document in their
settings, C none - likely the reason (a privacy step first); not proved. Never worked around
(apply-systems.md: no allow-lists).

## Pages after Continue - unmeasured

Settings read on 3 tenants: `NewExperienceOTPDisabled` false (a one-time code likely follows
Continue), `ENABLE_RECAPTCHA_V3` false, `PrivacyStatementIndicator` true. What Continue sends and
shows: unmeasured. `read` takes whatever page shows as plain boxes (`dom.questions`), page = its
first heading, and prints "unmeasured system - check every box". Owner's first real application =
the live check.

## Form definition

None public. Questions come after the applicant is verified - behind Continue, unmeasured.

## What leaves the computer, when

| What | When |
|---|---|
| Listing id (`cid` + `jobId`: posting + employer settings reads) | opening the job page |
| Bot-defense check (POST to an F5 / Shape host), cookie-consent receipt | page load (blocked in every run) |
| Name, email, mobile number | the user's own click on Continue - before the form |
| Everything after | unmeasured - first real application |

## Tenant notes

- A, B, G: Apply opens nothing while blocked (2026-10-03); A + B carry a privacy document.
- C, D, E, F, H: start box opens, 4 of 4 boxes filled by `try` (2026-10-03).
