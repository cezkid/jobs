---
reviewed: 2026-10-03
verdict: revise
reviewer: fresh AI session, bead plan-xsy.16 (no drafting context)
---
# Review: About the author (`about.md`)

Page read against public facts (repo `cezkid/jobs`, home page footer), the plan-xsy.15 brief
(owner-approved bio lines), `pages.py` ProfilePage JSON-LD (`AUTHOR`, `SAME_AS`), Google's
Who/How/Why guidance, the 2026 fake-author rule, rater guidelines 2.5.2-2.5.3 (who is responsible
+ contact info) via `~/code/research/topics/web/{seo-2026,authority-content}.md`.

## Claim table

| # | Claim on the page | Evidence | Verdict |
|---|---|---|---|
| 1 | "Cesar Enrriquez-Zuniga makes CEZ Job Finder" | Public: GitHub `cezkid/jobs`, home footer "Made by Cesar Enrriquez-Zuniga" | Supported |
| 2 | "a free app that finds jobs and makes a resume for each one" | Home page: app free, needs a paid AI plan | Supported; cost caveat missing (A4) |
| 3 | "Not a recruiter or lawyer" | Owner-supplied (plan-xsy.15 brief); not a public fact, harmless negative | Supported by owner; confirm at ship |
| 4 | "AI tools help find sources and write drafts. A fresh AI session checks every claim, and Cesar reads and approves each article" | Same gaps as methods review M1/M4: approval not recorded; reviser (AI) sets the verdict | Overstated as on methods (A2) |
| 5 | "The app's code is public on GitHub, where you can also report a mistake in any article: https://github.com/cezkid" | Repo public, issues on. The link is the profile, not the issue form; plain text, not clickable; needs a GitHub account | Route mismatch (A3) |
| 6 | JSON-LD ProfilePage, sameAs GitHub only | `pages.SAME_AS`; www.enrriquez.com left out (403 per brief) while the home footer links it | Consistent with brief; see A5 |

## Findings

Status: open = for the revise bead (plan-xsy.17).

- **A1 (medium) - pronouns.** status: open. "Where to find him" assumes the owner's pronouns; none
  are recorded in anything this session read. Rewrite pronoun-free ("Where to find Cesar",
  "Contact and code") unless the owner states them.
- **A2 (medium) - process line repeats methods M1/M4.** status: open. Keep it in step with
  whatever the methods page says after its fix; don't promise approval the process doesn't record.
- **A3 (medium) - correction route points to the wrong page.** status: open. Profile URL instead
  of the issue form; not clickable; GitHub account needed. Link to the methods section
  `methods.md#how-are-mistakes-corrected` (internal link, allowed) instead of repeating a URL.
- **A4 (low) - "free" without the AI-plan cost.** status: open. Home FAQ says the app needs a paid
  Claude, ChatGPT or Copilot plan. On an About page that also carries the conflict-of-interest
  story, add "It needs your own AI plan" or link the methods COI section (methods M9).
- **A5 (medium) - thin "who" + no contact.** status: open. Rater guidelines 2.5.3 want who is
  responsible and how to reach them; Google wants the byline to lead to more about the author.
  Page has name, one line, a GitHub URL - honest, but no contact route other than GitHub and no
  reason given why this person writes on AI + resumes (e.g. "built an app that tailors resumes
  with AI and needed to know which advice holds up"). Never add a credential, title or employer
  the owner hasn't given (brief). Owner input at ship: an email or contact page they want public,
  and www.enrriquez.com in `SAME_AS` once it answers 200 (home footer already links it - a 403
  link on the home page is its own issue).
- **A6 (low) - body style.** status: open. "Not a recruiter or lawyer: the Research section ..."
  is a fragment; body = short full sentences (research.md Style). "Cesar is not a recruiter or a
  lawyer. The Research section summarizes ...".

Bio claims beyond public facts: none invented. Line 3 is owner-given, not public - fine to keep.
No job title, employer, credential or photo. Passes the fake-author rule (real name, real project,
no invented credentials).

## Plain words + search

- Title "About the author" (16), description 140, og_title 28: within limits.
- No jargon hits; "code" is plain enough. Headings fine for an About page (not question-led by
  design).

## Verdict

revise - A1, A3, A5 before publishing; A2/A4 follow the methods fixes.
