---
reviewed: 2026-10-03
verdict: revise
reviewer: fresh AI session, bead plan-xsy.16 (no drafting context)
---
# Review: How we research (`methods.md`)

Page read against what the process really does: `app/web/pages.py` (lints, review gate, `--links`),
`app/docs/site.md`, `app/docs/research.md`, the epic's 3-bead article process, Google's
Who/How/Why + AI-content guidance and the 2026 fake-author rule (`~/code/research/topics/web/seo-2026.md`,
`authority-content.md`). No sources are cited on this page, so no source table; the claim table
checks each promise against the real process.

Measured 2026-10-03:
- `pages.STAT` on sample sentences: catches "48% said so.", "About a third more calls.", "Nine in
  ten recruiters agree."; misses "Over 3/4 of employers found gaps.", "Half of employers use it.",
  "Applicants were twice as likely to get a call.", "It covered 83,000 applications.", "Callbacks
  rose 1.5 times.".
- `https://github.com/cezkid/jobs/issues/new?title=Research%20correction` answers 302 (sign-in
  redirect) when signed out; repo public, issues on (`gh repo view`).
- `pages.body_html` appends `## Sources` after the body, so a `## Changes` list in the body sits
  above Sources, not at the end.
- `pages.reviews()`: gate = review file exists, `verdict: publish`, `reviewed` >= `modified`.
  Nothing records who wrote the verdict or that the owner approved.

## Claim table

| # | Claim on the page | What the process really does | Verdict |
|---|---|---|---|
| 1 | "He makes CEZ Job Finder, a free app" | True (public repo, home page). App needs a paid AI plan (home FAQ "Is it free?") | Supported; see M9 |
| 2 | "He is not a recruiter or a lawyer." | Owner-supplied line (plan-xsy.15 brief); not a public fact | Supported by owner; confirm at ship |
| 3 | "Each article here links every claim to a source you can open." | Convention claims have no study; "Our measurement" has no outside source | Overstated (M5) |
| 4 | Source order, 5 tiers; laws, product behaviour, news rules | Matches `research.md` Sources; enforced by the review step only, not code | Supported (process) |
| 5 | Labels table (9 rows) | Matches `research.md` + `pages.EVIDENCE`. "Our measurement: the article says how" vs `research.md` "method on the methods page" | Mismatch (M8) |
| 6 | "Every source cited was opened and read ... A source we could not open is not cited." | Draft-bead rule + reviewer re-reads sources; no code check | Supported (process) |
| 7 | "Every source is listed in one shared list with the date it was opened." | `sources.yml` `checked` = date last opened (updated on re-check); later section says "date it was last checked" | Minor inconsistency (M10) |
| 8 | "A program checks every DOI ... An invented or mistyped reference fails this check." | `--links` checks DOI + arXiv ids; run by hand, never in the build or tests; nothing records that it ran. Book/report/web entries without DOI get only a link status check - an invented one with a real-looking URL is not caught | Overstated (M3) |
| 9 | "Every number in an article must name its source in the same sentence. The program that builds the site refuses a page where one does not." | `STAT` lint catches %, percent, points, "N in M", n=, fraction words. Misses "3/4", "half", "twice as likely", "83,000 applications", "1.5 times" (measured above) | Overstated (M2) |
| 10 | AI step 1: AI searches, reads, drafts | True (bead 1) | Supported |
| 11 | AI step 2: "A second AI session, started fresh with none of the drafting notes, reads every source first" | Fresh context, yes. But the review bead can read the draft bead's notes (`bd show`), which list sources opened - those are drafting notes. Same AI model drafts and reviews | Overstated wording (M4) |
| 12 | "An article it does not pass goes back for changes." | True. But bead 3 (an AI session, not the reviewer) fixes findings and itself sets `verdict: publish`; no second review of the revision | Incomplete (M1) |
| 13 | AI step 3: "Cesar reads each article and approves it before it goes up." | Ship bead (r36, needs-human) only; GitHub Pages deploys `main` on push; nothing in code or files records approval per article | Unenforced promise (M1) |
| 14 | "AI never makes images of people for these pages." | Lint bans every image in the body; share card is generated text | Supported |
| 15 | "No quote, number or study is invented: the checks above exist to catch that." | Checks catch invented DOIs/arXiv ids, and the reviewer re-reads sources; not quotes or numbers by code | Supported as worded ("exist to catch") |
| 16 | Injected text treated as text | Bead rule + `research.md` | Supported (process) |
| 17 | Correction "adds a dated line to a Changes list at the end" | Changes list renders above the Sources list (measured) | Inaccurate (M10) |
| 18 | "A corrected article is reviewed again before it goes back up." | Gate only needs `reviewed:` >= `modified` - a date anyone can set; no fresh-session requirement in code | Unenforced (M1) |
| 19 | Report a mistake: issue on GitHub, plain-text URL | URL not clickable (body links to other sites rejected by `pages.rewrite`; markdown linkify off); needs a GitHub account (302 sign-in); "issue" is GitHub jargon | Route works only for GitHub users (M6) |
| 20 | Laws + settings re-checked every 3-6 months; studies yearly | `recheck_by` required for laws only, warns when passed; nothing tracks the yearly study re-check or product-setting dates unless `recheck_by` is set by hand | Partly unenforced (M7) |
| 21 | "no ads, no affiliate links and no sponsors" | True of the site today (home, privacy checked) | Supported; see M9 |
| 22 | "Each article's last box says how the app uses its findings." | `research.md`: tool box after the evidence; Sources (and Changes) come after it - not "last" | Minor (M10) |
| 23 | Not legal advice / career counselling | Present | Supported |

## Findings

Status: open = for the revise bead (plan-xsy.17) to fix or answer here.

- **M1 (high) - approval and re-review are promised but not enforced or recorded.** status: open.
  The page says the owner approves each article and a corrected article is reviewed again. Code
  checks only a verdict string + a date; the revise bead (an AI session) sets `verdict: publish`
  itself; GitHub Pages publishes whatever reaches `main`. Fix now: word the page to match the real
  steps (e.g. "AI revises the draft to answer every point the review raised. Cesar reads each
  article and approves it before it goes up."). Process fix filed separately (see below): record
  owner approval per article and keep the reviewer's verdict distinct from the reviser's.
- **M2 (high) - "the program refuses a page" over-promises the number lint.** status: open.
  Measured misses: "3/4", "half", "twice as likely", "83,000 applications", "1.5 times". Fix now:
  say "A program flags percentages and 'N in M' numbers without a source; the review checks the
  rest." Lint widening filed separately.
- **M3 (medium) - DOI check is manual and partial.** status: open. `--links` runs by hand, not at
  build; references without a DOI or arXiv id get only a link check. Fix: "Before an article goes
  up, a program checks every DOI ... Sources without one are opened by hand." Don't claim every
  invented reference fails.
- **M4 (medium) - "none of the drafting notes" is not true.** status: open. The review session
  can read the draft bead's notes. Reword: "A second AI session, with none of the drafting
  conversation, ...". Also say it is the same kind of AI as the drafter, so a human (Cesar) is the
  independent check - Google's How guidance asks for candour, and a reader would want to know.
- **M5 (medium) - "links every claim to a source you can open" contradicts the page's own labels.**
  status: open. Convention (no study) and Our measurement have no outside source. Reword: "Every
  claim carries a label, and every claim from a study links to it."
- **M6 (medium) - corrections route needs a GitHub account and is not clickable.** status: open.
  Measured: signed-out visit = sign-in redirect. Plain-text URL with `%20` reads as code to the
  readers this site targets; "open an issue" is GitHub jargon. Fix: let `pages.py` allow links to
  the project's own GitHub (`https://github.com/cezkid/`) in the body, link text "report a
  mistake", and say a free GitHub account is needed; or add an email route (owner's call: needs an
  address they want public). IFCN code + rater guidelines 2.5.3 expect an easy contact route.
- **M7 (low) - re-check cadence partly unenforced.** status: open. Only laws require
  `recheck_by`. Fix: either say "laws carry a re-check date the build warns about" and keep studies
  "yearly" as a stated practice, or require `recheck_by` on product-behaviour (`web`) entries too.
- **M8 (low) - Our measurement: page vs standards disagree.** status: open. Page: "the article
  says how"; `research.md` table: "method on the methods page". Pick one (article-level is more
  useful) and fix the other.
- **M9 (medium) - conflict-of-interest section is silent on the AI companies.** status: open. The
  app needs a paid Claude, ChatGPT or Copilot plan, and articles (keep-chats-out-of-ai-training,
  ai-written-resumes) discuss those companies; the articles are also written with one of their AI
  tools. Readers should learn whether the author gets anything from them. Needs an owner fact
  (any payment, referral, sponsorship or job tie: yes/no) - never assume "none". Then one line,
  e.g. "The app works with Claude, ChatGPT or GitHub Copilot. We get nothing from those companies."
  Also say the app needs one of those paid plans next to "free".
- **M10 (low) - small accuracy slips.** status: open. "date it was opened" vs "last checked" -
  use "date it was last opened and checked" in both; Changes list sits above Sources - say "a
  Changes list at the end of the article, above the Sources"; "last box" -> "a separate box after
  the evidence".
- **M11 (low) - voice.** status: open. "We" throughout, but the byline and About name one person
  plus AI tools. "We" can read as a team that doesn't exist (the 2026 fake-author rule targets
  false impressions of who made a page). Either say once "'We' means Cesar and the AI tools he
  uses" or write "I". Last H2 "What these articles are not" is not question-led (research.md
  Search rule) - "What are these articles not?" or "Is this legal advice?".
- **M12 (low) - pronouns.** status: open. The page uses "He"; the owner's pronouns are not
  recorded anywhere this session could read. Rewrite with the name or confirm with the owner.

## Plain words + search

- Title "How we research" (15 chars), description 123 chars, og_title 46: within limits, unique.
- Sentences all <= 20 words except the correction-report line (URL); fine once M6 lands.
- Jargon: DOI and arXiv explained in place; "peer-reviewed" explained as "checked by other
  researchers". "Open an issue" + "public code page" = GitHub jargon (M6).
- H2s question-led except the last (M11).

## Process changes filed (not page edits)

- Widen the statistic lint (fractions with a slash, "half", "twice", "N times", large counts) -
  M2.
- Owner decision: record owner approval per article, keep reviewer verdict separate from the
  reviser, optional one-line AI note under each article byline linking this page (Google:
  disclosure "self-evident"; library decision said a "How this was made" box) - M1, M4.

## Verdict

revise - M1 and M2 promise checks the process does not make; M5, M6, M9 need fixing before the
page can be trusted as the site's editorial policy. Fixes are wording on this page, except M6
(a `pages.py` link allowance or an owner-given email) and M9 (an owner fact).
