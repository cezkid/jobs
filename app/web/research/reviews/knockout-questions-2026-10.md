---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session (Claude), plan-xsy.57
---
# Review: Knockout questions on 143 job application forms: the data (`knockout-questions-2026-10.md`)

Verdict **revise**: 1 high, 2 medium, 7 low. The CSV reproduces exactly from the raw sample and
every number on the page matches the CSV. The problem is upstream of both: the counting code reads
only the form's `questions` list, but on some Workable forms freehire puts the employer's own
screening questions in the `basics` list. Those questions are never counted, so several published
counts (page and article) are a little low, and the page's method sentence "every other question
on the form" is not what the code does.

## What was checked (2026-10-04)

- Copied `~/.cache/plan-xsy-18/ko/raw.json` to `/private/tmp/claude-502/ko/raw.json`; ran
  `uv run app/web/knockout_count.py table` on the copy; output is byte-identical to the committed CSV.
  stderr: 143 forms of 840 postings; 104 employers; middle form 4 beyond basics, 26 none.
- `raw.json` vs `raw.orig.json`: every posting identical apart from the added `company` field.
- `knockout.py sample` vs the original `sample.py`: same 14 fields, same query (US, 14 days),
  `random.Random(20261003)` gives the same offsets as `random.seed(20261003)`, same 60 per page,
  same readable test (HTTP 200). Each field returned 60 postings (14 x 60 = 840).
- `table` counts vs `refine.py` (address-only rule, BASIC): same rules, same results (54 location
  hits, 11 address-only, 43 screens; any 105).
- Recounted every column from the CSV with python3 (below).

## Claim table

| # | Claim on the page | Source | What the source actually says | Verdict |
|---|---|---|---|---|
| 1 | 143 readable forms from 840 US postings | raw.json, knockout.py | 840 postings, 143 with HTTP 200 form | Supported |
| 2 | File has 143 rows | CSV | 143 data rows + header | Supported |
| 3 | 104 employers; same letter = same employer | CSV, `letters()` | 104 distinct letters, keyed on company slug | Supported |
| 4 | No titles, links or answers in the file | CSV | Columns: form, employer letter, field, system, counts, 0/1 flags | Supported |
| 5 | Form systems: Greenhouse, Lever, Ashby, Workable, Recruitee | CSV | 96 / 19 / 15 / 12 / 1 | Supported |
| 6 | `any_knockout` = 1 if any of the six before it is 1 | code, CSV | Consistent on all 143 rows | Supported |
| 7 | `questions_beyond_basics` = all but name, contact, address, profile links | BASIC regex | Also excludes resume, CV, cover letter, pronouns boxes; and never sees questions listed in `basics` | Partly (F1, F4) |
| 8 | `work_permit` = right to work "in the US" | RULES | Rule matches right-to-work wording for any country | Slightly overstated (F8) |
| 9 | Sampled 3 Oct 2026, US, last 14 days, 14 fields | knockout.py / sample.py | Same | Supported |
| 10 | One page of 60 at a random point; fixed starting number, rerun picks same points | code | Offset from seed 20261003; capped at the first 9,900 results (sales had 16,232) | Supported; cap unstated (F7) |
| 11 | Readable = freehire returned the form's questions | code | Readable = HTTP 200; 20 of 143 readable forms returned no `questions` list at all | Imprecise (F6) |
| 12 | The rest on Workday, Oracle, iCIMS or job boards | raw.json | 697 unreadable: Workday 188, Oracle 94, iCIMS 56, Adzuna 52, Paycom 34, UKG 24, USAJobs 24 ...; 3 were Workable | Supported ("such as"); see F6 |
| 13 | Phrase lists per column, form counted once per column | RULES, `categories()` | Same | Supported |
| 14 | Plain address box not a location screen; 11 such forms | code, refine.py | 54 forms with a location hit, 11 address-only -> 0 | Supported; rule wider than described (F5) |
| 15 | Any of six: 105 of 143 | CSV | 105 | Matches CSV; low by ~4 (F1) |
| 16 | Work permit or sponsorship: 96 of 143 | CSV | 96 (permit 67, sponsorship 89) | Matches CSV; low by ~3 (F1) |
| 17 | Location: 43 of 143 | CSV | 43 | Matches CSV; low by ~2 (F1) |
| 18 | Years of experience: 21 of 143 | CSV | 21 | Supported |
| 19 | License/certificate or clearance: 11 of 143 | CSV | 5 + 6, no overlap = 11 | Matches CSV; misses a "Florida Bar Status" question on 2 forms (F1) |
| 20 | Nothing beyond basics: 26 of 143 | CSV | 26 | Matches CSV; ~22 once basics-list questions count (F1) |
| 21 | Sales + customer success + HR + backend = 92 of 143 | CSV | 33 + 26 + 17 + 16 = 92 | Supported |
| 22 | Healthcare, finance one form each; design none | CSV | 1, 1, 0 | Supported |
| 23 | Sample leans tech/office "because freehire.me does" | raw.json | Each field gave exactly 60 postings; the lean comes from which forms are readable | Cause wrong (F2) |
| 24 | "A few employers" have more than one row | CSV | 16 employers hold 55 of 143 rows; one employer 8 rows | Understated (F3) |
| 25 | Phrase lists checked by reading matched questions, not every question | - | Consistent with classify.py `all` mode; not independently verifiable | Fine as a stated limit |
| 26 | Same counts as the article | ats-rejection-myth.md | 105, 96, 43, 21, 11, 26, 92, median 4 all match | Supported |

## Findings

**F1 - high - questions listed under `basics` are never counted.** freehire's form record has a
`basics` list and a `questions` list; `table()` reads only `questions`. On 6 Workable forms
(rows 41, 42, 84, 118, 119, 130) the employer's own screening questions sit in `basics`, e.g.
"Are you legally eligible for employment in the United States?", "Will you now, or in the future,
require sponsorship ...", "Are you currently commutable to the office location ...", "Florida
Bar Status ...", "Are you 18 years of age or older?". Row 128 (Lever) has two EEO questions there.
Recount treating question-like `basics` entries (ending "?" or over 40 chars) as questions:
any knockout 105 -> 109, permit or sponsorship 96 -> 99, location 43 -> 45, work permit 67 -> 70,
sponsorship 89 -> 90, age 18 10 -> 12, background 7 -> 8, nothing beyond basics 26 -> 22; the
license column would also pick up "Bar Status" if the rule had a "bar" phrase (5 -> 7). One
`basics` entry, "Clearance/Resignation letter (Form 6)", would be a false security-clearance hit
- exclude it. The page's method ("counts every other question on the form") does not match the
code today.
Fix: in `knockout.py table()`, also read `basics` entries that are not plain basics (anything
`BASIC` does not match, minus standard Workable profile boxes like Headline, Summary, Education,
Experience, Photo, Current company) as questions; decide whether "bar status/bar admission" joins
the license rule; rerun, update the CSV, every count on this page and in the article (published
article: correction line under `## Changes`, bump `modified`, re-review). Add a test with one
Workable form carrying a question in `basics`.

**F2 - medium - the cause of the lean is misstated.** "The sample is small and leans toward tech
and office jobs, because freehire.me does." Every field gave exactly 60 postings, and freehire's
own totals are not tech-heavy (sales 16,232, marketing 6,146, healthcare 4,785 vs backend 1,007).
The lean comes from which forms freehire can read: Greenhouse, Lever, Ashby and Workable are used
mostly by tech and office employers, while hospitals and banks use Workday, Oracle or iCIMS.
Fix: "The forms we could read lean toward tech and office jobs. Every field gave 60 postings, but
hospitals, banks and other large employers mostly use Workday, Oracle or iCIMS, which we can't
read." Same sentence fix in the article (it says the job search leans that way).

**F3 - medium - "a few employers have more than one row" hides real clustering.** 16 employers
account for 55 of the 143 rows (38%); one employer has 8 rows (all with no extra questions), two
have 6. Repeat forms from one employer are near-identical, so shares are partly shares of
employers' templates. Fix: "16 employers gave more than one form; together they make up 55 of the
143 rows, and one gave 8." Add the employer-level figure: 81 of 104 employers asked at least one
knockout-type question on at least one form (recount after F1).

**F4 - low - "basics" definition incomplete.** `BASIC` also excludes resume, CV, cover-letter,
phone, email and pronouns boxes. Fix: "Basics are name, contact details, address, pronouns,
profile links such as LinkedIn, and resume or cover-letter uploads."

**F5 - low - address-only rule wider than described.** `ADDRESS` also covers boxes starting with
city, state, country, location or "current location", and "where are you based". Fix: "only an
address, city, state, zip code, country, or 'where are you located' box".

**F6 - low - "readable" wording.** Code counts a form readable when freehire answers with a form
(HTTP 200); 20 readable forms had no question list at all. 3 Workable postings were unreadable,
so "the rest sat on systems freehire.me does not read" is not quite all of them. Fix: "A form was
readable when freehire.me returned it." and "Most of the rest ...".

**F7 - low - random point limited to the first 9,900 results.** For sales (16,232 postings) the
offset could not fall in the last third. Fix: one clause, "within the first 9,900 results", or
leave as is and note it in the code docstring (which also says "newest US postings", while the
page is drawn at a random offset - align the docstring).

**F8 - low - `work_permit` column says "in the US".** The rule matches right-to-work wording for
any country. Immaterial for a US sample. Fix: "1 if a question asks about the right to work".

**F9 - low - privacy: re-identification possible only with a same-day copy of the job list.** No
names, titles or links; employers are letters. Rows are in freehire's result order and letters
are given in order of appearance, and 88 of 143 rows have a unique combination of field, system
and counts, so someone holding a snapshot of freehire's 3 October results could match letters to
companies. These are companies, not people, and nothing personal is in the file, so this is
acceptable under research.md Privacy. Optional fix: keep as is; do not publish `raw.json`.

**F10 - low - no license line yet.** `pages.py` now accepts `license:` (CC BY 4.0 or CC0 1.0).
Owner to pick; CC BY 4.0 fits the "cite it" request on the page. Not a blocker.

## Style + plain words

Short answer: 3 fragments, fine. Sentences short and quotable; no app jargon. H2s question-led.
Internal links: article, methods, counting code. The citation line ("name the page and its date")
is good. Column names are code-style (`work_permit`) but explained in the table - fine for a data
page.

## Re-review 2026-10-04

Verdict now **publish**. Rerun on a fresh copy of `raw.json`: `knockout.py table` output is
byte-identical to the committed CSV (stderr: 143 forms of 840, 104 employers, middle form 4,
22 none; permit 70, sponsorship 90, location 45, years 21, license 7, clearance 6, any 109).
Recount from the CSV: permit or sponsorship 99, license or clearance 13, nothing beyond basics
22, 16 employers with more than one row (55 rows, max 8), 83 of 104 employers with any of the six,
92 forms from the four fields, `any_knockout` consistent on every row. Every number on the page
and in the article matches.

| Finding | Status |
|---|---|
| F1 high | Fixed. `asks()` counts basics entries that are not plain boxes and end in "?" or run 4+ words; clearance rule skips "Clearance/Resignation letter"; license rule adds bar status/admission/membership. Counts match my own earlier recount (109 / 99 / 45 / 22; license 7). Page now says forms list questions next to the name boxes and these were counted. |
| F2 medium | Fixed. Lean attributed to readable forms ("Every field gave 60 postings ..."), on both pages. |
| F3 medium | Fixed. 16 employers, one with eight, weighting stated; employer-level 83 of 104 added. |
| F4 low | Fixed. Basics list names pronoun, email, phone, resume, cover letter boxes. |
| F5 low | Fixed. Address rule lists address, city, state, country, zip, "where are you located" (code also takes "where are you based" - close enough). |
| F6 low | Fixed. "returned it", "Most of the rest", 20 forms with no separate question list (checked: 20). |
| F7 low | Fixed. "first 9,900 results" on the page and in the docstring; accurate (offset < 9,900 - 60). |
| F8 low | Fixed. "in the US" dropped. |
| F9 low | No change needed; still holds (raw file stays unpublished). |
| F10 low | Open, owner's pick; not a blocker. |

Remaining, low, not blocking:
- R1 - `asks()` also lets a few profile-style entries through as "questions beyond basics"
  ("Please provide your LinkedIn URL", "Current/Most Recent Employer - Name of Company",
  "Availability: ..."). They touch no screening column and leave the 22 "none" count unchanged
  (those forms have other questions). Fix if wanted: add them to `BASIC`; no number on either page
  moves.
- R2 - no test covers `app/web/knockout_count.py` (`app/tests/test_knockout.py` tests the app's own
  knockout module). Fix: one test with a Workable form whose screening question sits in `basics`
  and one with the "Clearance/Resignation letter" entry.
