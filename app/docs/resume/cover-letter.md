# Cover letter - what the checks hold a draft to, and why

`uv run app/jobs.py letter prepare|check <job>` (`app/resume/letter.py`): AI drafts from the
user's facts, code checks, the user confirms each paragraph. Outputs in the job folder:
`Cover letter.md` (paste into a text box) + `First_Last_Cover_Letter.pdf` (upload).

## When

Offered only when the application has a cover letter box (read ahead - `app/docs/apply/answers.md`).
No box or unknown -> not offered; written if the user asks. Demand: freehire.me (the job search) counted a
letter asked for on 209,297 of 402,117 open postings whose form it captured (2026-09, its
repo github.com/strelov1/freehire, internal/candidate/coverletter/AGENTS.md) - about half, tech-heavy.

| Rule | Basis | Strength |
|---|---|---|
| Write one when the form asks | ResumeGo 2019-20: 7,287 fictitious applications (ZipRecruiter, Glassdoor, Indeed), tailored letter 53% more callbacks than none | vendor study, not peer-reviewed |
| The user's own sentence on why this job, verbatim; never AI-written motive | Cui, Dias & Ye 2025 (*preprint*): an AI letter tool raised callbacks, but the link between a letter matching the posting and callbacks then fell 51%, and time spent editing the AI draft went w/ getting hired - generic tailoring stops signalling; the user's own words still do | preprint, observational |
| 3-4 paragraphs, 250-400 words, one page; "Dear Hiring Team" | Harvard FAS career guide (2026): one page, 3-4 short paragraphs, 250-400 words, shorter usually better; MIT CAPD: at most a page, 3-4 paragraphs | convention |
| Add what the resume doesn't show; never restate a line | career guides: a letter is not a resume summary | convention |
| Every number, tool, name from the facts each paragraph cites; never a word the resume never shows | `bullets.md` Tier 1 - anything on paper gets asked about | policy (FAIL) |
| At most 5 facts | more reads as the resume again | judgement |
| No "passionate", "excited to apply", "To Whom It May Concern" | generic, unverifiable self-description (Insight Global 2025: generic content is what readers reject) | vendor survey + convention |

Over 400 words fails; under 250 is said, never padded.

## Declined

- **AI-written enthusiasm or reasons.** The user's sentence, or the letter opens with the role + their strongest fact.
- **A letter for every application.** Only where a box asks; no evidence an unasked one helps.
