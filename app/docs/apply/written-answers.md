# Written answers - why the `job-answers` rules

Free-text boxes on application forms ("why us", "describe a recent project"). Skill:
`app/skills/job-answers.md`. Scale of evidence words: `app/docs/research.md`.

## Owner decision 2026-10-28

A user asked for an AI draft of a "why us" box ("I feel like you always struggle") and a
shared skill for it. Before: motive = user's sentence only (`app/docs/resume/cover-letter.md`
#Declined), so the AI asked an open question and users stalled on it. Now: an AI draft is one of
four choices, offered after one line of evidence, every motive clause confirmed word for word
("Is every word true for you?") before it is filled. The cover letter keeps its own rule (its
"why" sentence stays theirs): a letter is longer and its facts are checked by code.

## Rules + basis

| Rule | Basis | Strength |
|---|---|---|
| The user's own reason beats an AI one; offer theirs first, say the evidence once before drafting | Cui, Dias & Ye 2025: AI letter tool -> link between posting match and callbacks fell 51%, time editing the draft went w/ getting hired (`cover-letter.md`) | preprint, observational |
| Motive clauses read back before filling | a stated feeling is a claim about the user; anything on the page gets asked about in interview (`AGENTS.md` #Lead) | policy |
| Banned words + shapes (em dash, rule of three, "not only ... but", closing summary, "testament", "delve", "align with") | Wikipedia "Signs of AI writing" (WikiProject AI Cleanup), the list the common humanizer skills build on: github.com/blader/humanizer, github.com/tw93/human (checked 2026-10-28) | editors' field guide, convention |
| No skill on GitHub targets application answers | search 2026-10-28: general humanizer skills only, none for forms | search, one day |
| Specific fact w/ its number, in the posting's words | career-centre convention; same Tier 2 rule as bullets (`app/docs/resume/bullets.md`) | convention |
| Company facts only from the posting, never from memory or its site | AI memory can't be checked; site fetch = new off-computer step (`AGENTS.md` privacy table) | policy |
| Length as the form asks; under the character limit | Greenhouse / Ashby cut a longer answer unseen (`job-apply` step 3) | measured |

## Rejected

- **Run a humanizer rewrite pass on the user's own words.** Their wording is the signal; a
  spelling fix is shown, nothing else changed.
- **One stock "why us" saved and reused.** Per-employer by nature; a reused one reads generic,
  the thing readers reject (Insight Global 2025, vendor survey - `cover-letter.md`).
