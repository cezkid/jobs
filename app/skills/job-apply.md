# job-apply

Fill a Workday job application for the user through the Claude Chrome extension. Any company whose
careers site is `*.myworkdayjobs.com` (or `wd<N>.myworkday...`). Other application systems: not
yet - say so, offer the tailored PDF + answers to paste by hand.
User not technical - `AGENTS.md` #User = not technical binds. What was measured and why each
rule exists: `app/docs/workday.md`. New tenant quirk found -> add it there, same PR as the fix.

## Hard limits (safety rules - never relax)

- User signs in / creates the account themselves. Never type a password.
- Never click **Save and Continue**, **Submit**, or anything irreversible. Fill, then tell them
  to check the page and click it. They say "click it for me" -> still ask once per click.
- Upload the resume PDF only after they say yes (name the file).
- Never answer on their behalf: salary, relocation, start date, voluntary disclosures (gender,
  race, veteran, disability), how-did-you-hear. Ask each with clickable choices; disclosures
  always offer "I don't wish to answer".
- Work authorization + sponsorship: `apply` prints their setup answers. Use one only when the
  form asks that same thing about the US (without restriction; sponsorship now or in the
  future), and name the choice you picked so they check it before Save. Other wording (another
  country, this employer only, which visa, "are you on OPT?") or `not set` -> ask with choices,
  offer to save a new answer to `work_authorization` in search settings. Never pick the answer
  that gets past a filter: employers check it on Form I-9 in the first days of the job, and a
  false answer is grounds to withdraw the offer.
- Cookie banner -> **Decline** (non-essential off).

## Steps

1. Tailored resume for this job exists (`My Jobs/<folder>/`)? No -> `job-tailor` skill first, or
   ask whether to use their own resume as is.
2. `uv run app/jobs.py apply <slug>` (no slug = own resume) -> writes `apply.js`, prints counts.
3. Browser: `tabs_context_mcp` (createIfEmpty), new tab, navigate to the posting's apply link.
   Sign-in page -> step aside (limits). "Autofill with Resume" / "Apply Manually" / "Use My Last
   Application" -> ask which; autofill only pre-fills, our fill overwrites it anyway.
4. On **My Experience**: read `apply.js`, send its whole text in ONE `javascript_tool` call - it
   starts the fill in the background and returns `'started'`. Poll every ~30s with
   `await new Promise(r => setTimeout(r, 25000)); window.__jf.status()` until `done: true`.
   Never send it twice: rerun only parts with `window.__jf.run(<data>, ['skills'])` if needed.
5. `problems` from status: `ASK` = nearest choice picked or none on the form's list -> tell the
   user plainly with the choices, fix per their answer. `FAIL` = field not found -> screenshot
   is blank in a hidden window, so read labels via `read_page`/`find`, fix by hand once, and
   record the new label in `app/docs/workday.md`.
6. `window.__jf.errors()` must be `[]`. Then tell the user: what was filled (counts), each ASK
   item, what is left (resume upload, website, questions), and that nothing is saved until they
   click **Save and Continue**. Later steps (questions, disclosures, review) = ask, never guess.

Token care: send `apply.js` once; poll with the short status call only; no screenshots while the
window is hidden (they come back black) - use `status()`, `errors()` or `find`.
