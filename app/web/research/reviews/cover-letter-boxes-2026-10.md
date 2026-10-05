---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session (Claude), plan-xsy.69 re-review
---
# Review: Cover letter boxes on 143 job application forms: the data (`cover-letter-boxes-2026-10.md`)

Verdict **publish**: 0 high, 0 medium, 5 low. The data checks out. A rerun of the counting code
gives a byte-identical CSV, and every number on the page matches the CSV and the raw forms. The
lows are small gaps in the method text: one field had no forms, the "closed" reason is not
recorded by the code, and one lookup step goes unmentioned. Plus one missing inbound link and a
stale heading name in a code comment.

## What was checked (2026-10-04)

- Copied `~/.cache/plan-xsy.67/raw.json` into a `mktemp -d` folder, then ran `uv run
  app/web/letter_count.py <copy> > letters.csv`. Exit 0, no network (every flag cached). The
  output is byte-identical to `cover-letter-boxes-2026-10.csv` (`cmp`). The raw copy is unchanged.
- Printed summary: forms 143; box 96; required 2; optional 91; unknown 3. Greenhouse 96 / 85
  (1 required, 83 optional, 1 unknown); Workable 12 / 7 (5 optional, 2 unknown); Ashby 15 / 3
  (3 optional); Lever 19 / 0; Recruitee 1 / 1 (required).
- Recounted every number on the page from the CSV with python3: rows, employers, box,
  optional / required / unknown, employers with a box, systems, the two field counts, and
  employers with more than one row.
- Joined on `form` with `knockout-questions-2026-10.csv`: all 143 rows match on employer, field
  and system.
- Read `letter_count.py` against the method text. `box()` matches an entry whose text starts with
  "cover letter", in the questions or the basics. Ashby questions carry their own flag (3 of 3,
  all optional). Greenhouse, Workable and Recruitee flags come from `required()`, one request each.
- Raw forms: all 85 Greenhouse boxes and all 7 Workable boxes sit in the basics. None of the 19
  Lever forms lists an "additional information" entry or any letter-like question. No question
  that mentions "cover" or "letter" was missed by the pattern (5 checked; none is a letter box).
- The 3 unknowns (1 Greenhouse, 2 Workable): asked again 2026-10-04 by listing number. freehire.me
  still answers for all three; each hiring system now returns 404. Consistent with "closed".
- `uv run app/web/pages.py --check`: the only error for this page was this missing review file.
  Its links resolve (the article's `#do-employers-still-ask-for-cover-letters` heading, the
  knockout page's `#how-did-we-draw-the-sample`, `methods.md`, `../letter_count.py` is tracked).
- Privacy: the CSV has 6 columns (form, employer letter, field, system, two flags). No title, link,
  company name or answer. The page names no employer. The raw file stays in `~/.cache/`.
- Text addressed to an AI: none in the raw forms read here.

## Claim table

| # | Claim on the page | Source | What the source says | Verdict |
|---|---|---|---|---|
| 1 | 143 readable forms, same as the knockout count | CSV, knockout CSV | 143 rows; rows match on form, employer, field, system | Supported |
| 2 | 104 employers, letters only, same letter = same employer | CSV, `letters()` | 104 distinct letters, shared with the knockout file | Supported |
| 3 | File holds no titles, links or answers | CSV header | 6 columns, none of those | Supported |
| 4 | Column table | CSV, code | Matches; `letter_required` blank when no box (0 rows break this) or unknown | Supported |
| 5 | Drawn 3 October 2026, US, last 14 days, 14 job fields | knockout page, `FIELDS` | 14 fields searched; only 13 have a readable form (design none) | Incomplete (D1) |
| 6 | Box = an entry named "cover letter", basics or questions | `box()` | Text starting "cover letter", either list | Supported |
| 7 | Ashby flag from freehire's read; others asked once, 4 October | code, raw | Ashby questions carry `required`; others cached as `letter_required` | Supported |
| 8 | "We sent only the posting's own number" | `count()` | Sends the listing id to freehire.me first, then the hiring-system number | Incomplete (D3) |
| 9 | Raw file not published; flags can't be re-read once a posting closes | repo, rerun | Raw only in `~/.cache/`; 3 postings already 404 | Supported |
| 10 | Lever: no box named cover letter; open box not listed, not counted | raw | 0 of 19; no "additional information" entry in any | Supported |
| 11 | Box on 96 of 143 | CSV | 96 | Supported |
| 12 | Optional 91 of 96 | CSV | 91 | Supported |
| 13 | Required 2 of 96, one Greenhouse, one Recruitee | CSV | Recruitee + Greenhouse | Supported |
| 14 | Could not check 3 of 96, "because the posting had closed by the next day" | code, raw, recheck | Code stores None for a closed posting and for no matching label alike; all 3 now 404 | Supported, not recorded (D2) |
| 15 | 71 of 104 employers had a box on at least one form | CSV | 71 | Supported |
| 16 | Greenhouse 85/96, Lever 0/19, Ashby 3/15, Workable 7/12, Recruitee 1/1 | CSV | Same | Supported |
| 17 | Sales 28 of 33, customer success 10 of 26 | CSV | Same | Supported |
| 18 | Field counts mostly follow the form system | CSV | Sales 31 of 33 Greenhouse; customer success 11 of 26 Lever | Supported |
| 19 | Small sample, leans tech and office; Workday and iCIMS not covered | CSV | 5 systems only | Supported |
| 20 | Required flag read a day after the forms | code, knockout page | Forms 3 October, flags 4 October | Supported |
| 21 | 16 employers with more than one row | CSV | 16 | Supported |

## Findings

- **D1 (low) - "14 job fields", but the file has 13.** Design had no readable form, so no row.
  A reader counting `job_field` finds 13 values. Sentence: "On 3 October 2026 we drew US postings
  from the last 14 days across 14 job fields on freehire.me, a free job search." Fix: add "13 of
  them had a form we could read; design had none." status: fixed
- **D2 (low) - The code does not record why a flag is missing.** `required()` returns None for a
  posting that no longer answers and also for one that answers without a matching label. The raw
  file keeps only None. All three now return 404, so the page's reason holds. But a rerun can't
  show it. Sentence: "Could not check: 3 of the 96, because the posting had closed by the next
  day." Fix: store the hiring system's answer code with the flag next time. Or say "because the
  hiring system no longer showed the posting". status: fixed
- **D3 (low) - One lookup step is left out.** Before asking each hiring system, the code asks
  freehire.me for the posting's hiring-system number. Sentence: "We sent only the posting's own
  number, nothing about anyone." Fix: "We first looked up each posting's number on freehire.me. We
  sent only that number, nothing about anyone." status: fixed
- **D4 (low) - One link in.** Only the article links here. The knockout data page shares every row
  and could link it. Wave 1 lessons ask for 2 links in. Fix: when the knockout page is next edited
  (with its own re-review), link this page from its "What is in the file?" section. status: fixed
- **D5 (low) - Stale heading in the code comment.** `letter_count.py` line 3 names the article
  section "How many application forms ask for a cover letter?". The heading is now "Do employers
  still ask for cover letters?". Fix: update the comment. status: fixed

## Not findings

- Plain words: short sentences, no AGENTS.md jargon, column names in code format (right for a
  data page).
- No overclaim: the page says twice that a box is not a letter that gets read.
- `status: published` before this review: the build gate blocks it until this verdict, so nothing
  ships early.

## Resolution (plan-xsy.69, 2026-10-04)

- D1 fixed: "13 of those fields had a form we could read; design had none."
- D2 fixed: "because the hiring system no longer showed the posting" (data page + article). Recording the answer code is left for the next count.
- D3 fixed: "We first looked up each posting's number on freehire.me. We sent only that number, nothing about anyone."
- D4 fixed: the knockout-question data page links here from "What is in the file?" (link-only edit).
- D5 fixed: `letter_count.py` docstring names the heading "Do employers still ask for cover letters?".
