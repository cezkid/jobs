# VMock - what it scores, and what Job Finder does about it

VMock is the resume scorer many universities and career-transition services license to the
people they serve. A user uploaded an untailored Job Finder resume on 2026-09-24 and it scored
**65/100**: Impact 21/40, Presentation 9/20, Competencies 35/40. Every tab, sub-tab, hover and
modal was read the same day. This file records what VMock measures, which of its findings were
real defects in Job Finder (all fixed), and which of its advice was rejected - so none of it is
re-derived or re-proposed. The user's own feedback, with their resume text, stays private in
`.data/vmock/<date>/`.

## How it reads a PDF

VMock converts the PDF to HTML with **pdf2htmlEX** (its highlights carry pdf2htmlEX's class
names: `t m0 ff1 fs0 fc0 sc0 ls0 ws0`) and scores the text of that HTML. That converter guesses
word breaks from glyph positions, and it is the only reader found that split our headings:
PyMuPDF, pdfminer and pypdf all read them whole. So Job Finder cannot run VMock's reader; it
measures the thing the reader trips on instead (`split-words` below).

Its dashboard marks every Job Finder upload so far "there may be an inherent conversion issue
in the resume uploaded by you", with advice to re-export from Word. It is **not** the
letterspaced headings: the re-score without them still carries the notice, and scored 89 with
every Presentation check passing. Cause unknown - plausibly any PDF not made by Word. Open.

## What it scores

| Module | Check | What it wants | Weight / effect |
|---|---|---|---|
| Impact (40) | Action Oriented | bullets open with an action verb | 32/32 passed |
| | Specifics | a number or metric per bullet - scope or outcome. Resumes scoring 85+ average 25-29 specifics over 25 bullets | 27 good, 6 weak |
| | Language: spelling | **hygiene: "full language score will be deducted if errors found"** | cost most of Impact |
| | Language: overuse | one word repeated as an opener ("Built" x8 = On Track) | warning tier |
| | Language: avoided words | filler list: the, that, which, their, successfully, my, actively, pronouns, passive voice | flagged "lazy" in "lazy loading" |
| | Language: grammar | - | not scored |
| Presentation (20) | Overall Format | hygiene checks below; **+10 bonus once all pass** | 2 failed |
| | Number of pages, Essential sections, Section specific | pages <= 3; Skills, Experience with bullets, Education; bold non-italic dates and titles | passed |
| Competencies (40) | Leadership, Initiative, Analytical, Communication, Team effort | matched against its own phrase lists | 35/40, Leadership "On Track" |

Presentation hygiene checks, and ours:

| VMock check | Result 2026-09-24 | Cause | Job Finder now |
|---|---|---|---|
| Color Check - "all text should be black"; email and LinkedIn may be blue | **fail**: name, headings, job titles, schools, project name | template set them in navy `#1F3A5F` | all text in the page ink `#1A1A1A`, which passed; gate `text-color` |
| Section Spacing - "consistent space after section headings" | **fail**: after EXPERIENCE, PROJECTS | a job opened 10pt lower than a line did: 28.0pt below the heading vs 20.5pt | first thing under every heading at one distance; gate `heading-gap` |
| (not a check - found in its highlights) | headings read as `EXP E R I ENC E`, `SKI L L S`, `EDUCATIO N` | headings letterspaced +0.08em (0.92pt a letter); body at +0.015em read whole | headings unspaced; gate `split-words` fails any gap inside a word over 0.04em |
| Branding Title, Bullet Check, Bullet Count, Date Formatting, Font Size, Margins 0.5-1in, Length, Section Styling, Images, Name, one phone, one email, Job-title and Degree styling | pass | - | unchanged |

Its unscored recommendations: a customised LinkedIn URL, a "City, ST Zip" address, a headline
above the summary. The headline is now an optional field (`headline`, printed bold under the
contact line); the ZIP is not added - `street-address` still warns on one, since a city and
state is all US hiring needs.

## Result after the fixes

Same resume, re-scored the same day with the template fixed and the user's approved wording
(US spelling, hyphenated compound, fewer "Built" openings, four numbers they supplied):

| | Before | After |
|---|---|---|
| Overall | 65 | **89** (Green Zone) |
| Impact | 21/40 | 34/40 - Language Needs Work -> Good Job (spelling 2 -> 0, overuse cleared) |
| Presentation | 9/20 | **20/20** - Color Check and Section Spacing pass, +10 hygiene bonus |
| Competencies | 35/40 | 35/40 - Leadership still On Track |

Its Grammar check (not scored) then flagged *retuning* ("tuned again") as a typo of
*returning* - a false positive, left as written.

## Which checks map to which rule

| VMock | Job Finder | Where |
|---|---|---|
| Spelling Error | `spelling`: British forms, typo-shaped words | `lint.py` |
| (Spelling, "live streaming") | `compound-modifier` | `lint.py` |
| Overuse | `overused-opening` (4+ bullets, the user's threshold) | `lint.py` |
| Avoided Words | `filler-word` (successfully, actively, first person) | `lint.py` |
| Specifics | `specificity` (report only) + `resume-gaps`, which asks the user | `lint.py`, `gaps.py` |
| Color Check | `text-color` | `render.py` |
| Section Spacing | `heading-gap` | `render.py` |
| its text extraction | `split-words` | `render.py` |

## Advice rejected, and why

| VMock says | We do | Why |
|---|---|---|
| Add a number to every bullet, with templates like "for {{count}} screens" | ask the user for the real number (`resume-gaps`); skipped questions change nothing | a template filled by anyone but the user is an invented number, and any number gets asked about in interview (`bullets.md` Tier 1) |
| Add its competency keywords (tool and topic names it links to the field) with sample bullets | never | they are phrase-list matches, not the user's facts (`bullets.md`, "What did not survive") |
| 6-12 key skills | keep the full list, the user's call | the skills block is where a recruiter's search terms land (`bullets.md` Tier 3) |
| Avoid "the", "that", "which", "their", passive voice | not flagged | ordinary English; flagging them pushes toward stilted text |
| "lazy" is an avoided word | never flagged | "lazy loading" is a technique; no filler word is matched inside a compound |
| "City, ST Zip" | city and state | a ZIP adds nothing a US employer asks for and exposes more |
| 4-6 line summary | up to 4 lines | the user's call |

## Re-scoring

`uv run app/jobs.py vmock upload <pdf>` uploads a resume in Job Finder's own Chrome (the user
signs in to VMock there once) and reads the feedback back; `vmock read <feedback url>` reads an
existing report. Both write `.data/vmock/<VMock resume number>/feedback.json` and a plain-words
`My Resume/Vmock feedback.md`, compared against the previous read. Each upload spends one of the
user's licensed uploads, so the assistant asks before every one. Neither command ever clicks
VMock's Auto-fix, Save, Load Suggestions or Add to Dictionary.
