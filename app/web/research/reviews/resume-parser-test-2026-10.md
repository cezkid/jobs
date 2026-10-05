---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session (Claude), plan-xsy.63
---
# Review: Seven resume layouts, five PDF text readers: the data (`resume-parser-test-2026-10.md`)

Verdict **revise**: 0 high, 4 medium, 5 low. The data checks out. A rerun of the readers and
the scorer gives byte-identical files, and every count on the page matches the CSV and the raw
reader text. The problems are in the words around the numbers. The title says five readers when
there are three. One column is described as something the code does not measure. The "broke" rule
leaves out one of its checks. And one sentence makes an unsourced claim about other resume readers.

## What was checked (2026-10-04)

- `uv run app/web/parser_read.py > $D/r.json` then `uv run app/web/parser_test.py score $D/r.json > $D/r.csv`
  (`$D` from `mktemp -d`). `r.json` is byte-identical to the committed `readings.json`. `r.csv` is
  byte-identical to `resume-parser-test-2026-10.csv` and to `results.csv`.
- `uv run app/web/parser_test.py build --check`: exit 0, so the PDFs and `truth.json` rebuild unchanged.
- PDFs opened with PyMuPDF: all 7 are 1 page, 612 x 792 pt (US Letter), Caladea Regular + Bold
  only, 0 images.
- Reader versions in `readings.json` (`pdfminer.six 20260107`, `pymupdf 1.28.2`, `pypdf 6.19.0`) and
  the pins in `parser_read.py` match the page and METHOD.md. The five calls in `READERS` match the page's list.
- Recounted every claim from the CSV with python3. Then read the raw text of every broken reading,
  plus header-footer and icons, against each "how each one broke" bullet.
- Read `score()`, `word_damage()`, `locate()` and `in_order()` against each column description.
  Compared the page's "broke" sentence with METHOD.md "What counts as broke" and the code's `why` list.
  Compared the page's limits with METHOD.md "Limits".
- `uv run pytest app/tests/test_parser_test.py app/tests/test_pages.py app/tests/test_site.py`:
  293 passed, 1 failed. `test_generated_files_are_fresh` fails only because this review file was
  missing ("published page needs an adversarial review"). No other lint or citation error was
  raised. `git status` was unchanged by the run.
- Privacy: only placeholders appear ("Your Name", `your.name@example.com`, `(555) 010-0199`,
  "Company A-C", "University A"). The text inside the PDFs and readings was treated as data. No
  text in them addressed an AI.

## Claim table

| # | Claim on the page | Source | What the source says | Verdict |
|---|---|---|---|---|
| 1 | One made-up resume, 3 jobs, Company A-C, one degree, two skill lines | facts.yml | Same; placeholders only | Supported |
| 2 | Same words in 7 layouts; only arrangement changes | layouts/, truth.json, METHOD.md | One facts file feeds every layout | Supported |
| 3 | Every layout fits one US Letter page, same typeface, real text | PDFs | 7 x 1 page, 612x792, Caladea only, no images | Supported |
| 4 | A rerun gives the same files | `build --check`, rerun | PDFs, truth, readings and CSV all byte-identical | Supported |
| 5 | Layout table (7 rows) | METHOD.md corpus table | Same descriptions | Supported |
| 6 | 3 free readers, 5 ways; versions and calls | parser_read.py, readings.json | pymupdf 1.28.2 (plain and sort), pdfminer.six 20260107, pypdf 6.19.0 (plain and layout) | Supported |
| 7 | Title and citation line: "five PDF text readers" | same | 3 readers, 5 ways of reading | Wrong (F1) |
| 8 | 35 rows | CSV | 35 data rows | Supported |
| 9 | Words compared ignoring case and punctuation | `WORD = [^\W_]+`, casefold | Same | Supported |
| 10 | `lost_words` = words on the page the reading lacks | `word_damage()` | Counted after split and merged words are set aside | Incomplete (F7) |
| 11 | `split_words`, `merged_words`, `name_*`, `email`, `phone`, `job_headers_together`, `blocks_not_found`, `sections_mixed`, `within_section_order` | `score()` | Match the code | Supported |
| 12 | `page_order` = share read in page order, top to bottom | `score()` | Longest in-order run against the truth (one-column) order, over all blocks including not-found ones | Wrong (F2) |
| 13 | Broke = lost/split/merged word, name line, email/phone, job split, section out of order or mixed | METHOD.md, `score()` | Also "any block not found"; "out of order" means within a section | Incomplete (F3) |
| 14 | 13 of the 35 readings broke | CSV | 13 rows with `broke` true | Supported |
| 15 | Per layout: 0, 0, 0, 2, 2, 4, 5 of 5 | CSV | one-column 0, header-footer 0, icons 0, sidebar 2, table 2, text-boxes 4, spaced-headings 5 | Supported |
| 16 | Spaced headings: every reader split all four headings into letters | readings | All 5 read "S U M M A R Y", "E X P E R I E N C E", "E D U C A T I O N", "S K I L L S"; split_words 4 each | Supported |
| 17 | Text boxes: two readers kept file order, so the name came last | readings (pymupdf, pypdf) | Experience first; name is next to last; the contact line comes after it | Slightly imprecise (F6) |
| 18 | Text boxes: two others mixed the skills column into the job bullets | readings (pymupdf-sort, pypdf-layout) | The right column holds Education and Skills; both interleave with Experience; sections_mixed 3 | Slightly imprecise (F6) |
| 19 | Sidebar: two readers read across both columns line by line; one made "PresentCity" | readings (pymupdf-sort, pypdf-layout) | Same; merged_words 1 in pymupdf-sort | Supported |
| 20 | Table: two readers put dates on a different line from the title; one read all left cells first, so "Summary" came before the name | readings (pdfminer, pymupdf) | Same; pdfminer reads SUMMARY ... SKILLS, then "Your Name" | Supported |
| 21 | Every reading kept email and phone exact | CSV | email and phone true in all 35 | Supported |
| 22 | None lost a word outright | CSV | lost_words 0 in all 35 | Supported |
| 23 | Header-footer 0 of 5 (no further comment) | readings, CSV | All 5 read the contact line last; page_order 0.88 each | Supported; context missing (F5) |
| 24 | First line as name "is common among resume readers" | none | METHOD.md says "many parsers" with no source | Unsourced (F4) |
| 25 | Limits: free readers, our layouts, Typst, one run, first-line name | METHOD.md Limits | All five present | Supported |
| 26 | Method written before the first run; two scoring changes listed | METHOD.md | Header and Changes say the same | Supported (taken on its word) |
| 27 | No employer's hiring system tested | METHOD.md, code | Only the 3 open-source readers run | Supported; no overclaim found |

## Findings

**F1 - medium - title and citation line say "five PDF text readers".** The test used 3 readers,
two of them in 2 ways. The body says this correctly ("3 free PDF text readers in 5 ways"). But
the title is the most quoted line, and an AI answer lifting it would say five readers.
Fix: title "Seven resume layouts, three PDF text readers: the data" (54 chars). Change the
citation line to match.

**F2 - medium - `page_order` description does not match the code.** The page says "Share of
pieces read in page order from top to bottom". The code measures something else. It compares the
reading with the truth order (name, contact, summary, experience, education, skills), which is
the one-column order, not each layout's own top-to-bottom order. It also divides by every piece,
including pieces not found. Example: header-footer prints the contact line at the bottom of the
page. Every reader reads it last, which is true top-to-bottom order, yet each scores 0.88.
Spaced-headings scores 0.83 only because its 4 headings were not found.
Fix: "Share of pieces read in the plain one-column order (name, contact, summary, experience,
education, skills); pieces not found count as out of order (reported, not scored)".

**F3 - medium - the "broke" rule on the page leaves out a check.** METHOD.md and the code also
mark a reading broke when any block is not found. The page sentence omits that. Its words "a
section out of order" also read as whole-section order, which the next sentence says is never
scored. No row changes: every row with blocks not found also has split or merged words. But this
sentence defines the page's main column.
Fix: "... A job split over lines breaks it. So does a section whose own pieces come out of order,
a section with another section read into its middle, or a piece whose opening words can't be
found together." Keep the sidebar sentence after it.

**F4 - medium - unsourced claim about other resume readers.** "Taking the first line as the
name is common among resume readers" is a claim about systems the test never ran. It has no
citation, is not in `uncited:`, and is not our measurement.
Fix: cite a maker's doc that says so, or reword to what we did: "We scored the name by the first
line. We did not check which hiring systems read the name that way."

**F5 - low - header-footer result has no context.** All 5 readers kept the name first but read
the email, phone and city last, after Skills. The rule passes this, since section order is not
scored. Header and footer placement is one of the most searched layout questions, so a reader
should not have to dig the answer out of `page_order`.
Fix: add one bullet under "How each one broke" (or right after it): "Header and footer: not
broke, but every reader read the email, phone and city last, after Skills."

**F6 - low - two text-box details are a little loose.** In the file-order readings the name is
next to last; the contact line follows it. The column mixed into the job bullets is the education
and skills column, not only skills.
Fix: "so the name and contact line came last" and "mixed the education and skills column into
the job bullets".

**F7 - low - `lost_words` description is incomplete.** The code counts lost words only after it
sets aside split and merged words (METHOD.md measure 1). Without that, a reader could expect
"S U M M A R Y" to count as lost too.
Fix: "Words on the page that the reading lacks, not counting split or merged words".

**F8 - low - page is `status: published` before its review passed.** research.md step 1 says a
draft stays `status: draft` until revise. The site gate (`test_generated_files_are_fresh`) fails
until a `verdict: publish` review exists.
Fix: set `status: draft` until the revise bead lands, or leave it and make sure the revise bead
reruns `pages.py` and the gate after this review turns to publish.

**F9 - low - few links in or out.** The page's only link to another research page is
`methods.md`. `ats-rejection-myth.md` already advises "a plain one-column page that reads back
cleanly", and this data backs that advice. Wave 1 lessons ask for >= 2 links in and >= 2 out to
published pages.
Fix: link this page to the ats-rejection-myth section on layout, and that section back here.
Add a second sibling (for example what-makes-a-good-resume) in both directions.

## Not findings

- Plain words: sentences are short. No AGENTS.md jargon appears. Column names are in code
  format, which is right for a data page. "Typst" is explained as a tool.
- No overclaiming. The short answer, the readers section and the limits each say that no
  employer's system was tested.
- "Broke" is used as an adjective ("counts as broke"). It is informal, but it matches the column
  name. Leaving it is fine.

## Re-review (2026-10-04)

A fresh session re-checked the revised page against the CSV, the raw readings, METHOD.md and the
code. The data files were not touched by the edit; the CSV is still the byte-identical rerun.

| Finding | Status | Checked against |
|---|---|---|
| F1 title "five readers" | Fixed | Title and citation line now say "three PDF text readers" (title 54 chars); no "five" left on the page |
| F2 `page_order` description | Fixed | Now "one-column order ... pieces not found count as out of order"; matches `score()` (in-order run over truth order / all blocks) |
| F3 broke rule | Fixed | Now names within-section order, mixed sections and pieces not found; matches METHOD.md "What counts as broke" and the code's `why` list; whole-section order still stated as not scored |
| F4 unsourced first-line claim | Fixed | Replaced with what we did ("We scored the name by the first line. We did not check which hiring systems read the name that way.") |
| F5 header-footer context | Fixed | New bullet: all 5 read email, phone and city last, after Skills. Raw text: last line of all 5 header-footer readings is the contact line; CSV `broke` false for all 5 |
| F6 text-box details | Fixed | "name and contact line came last" and "education and skills column" match the pymupdf / pypdf and pymupdf-sort / pypdf-layout readings |
| F7 `lost_words` | Fixed | "not counting split or merged words" matches `word_damage()` |
| F8 status published before review | Answered | Author keeps `status: published`; the gates run after this verdict. Acceptable: the build gate blocks a published page without a `publish` review, so nothing ships early |
| F9 links | Partly fixed (accepted) | Two outbound links added; `what-makes-a-good-resume.md#does-layout-matter` exists ("## Does layout matter?"), `ats-rejection-myth.md` exists. Inbound links deferred to plan-xsy.64, which is right: editing published articles needs their own re-review |

New text introduced by the edits: no new numbers. The lead paragraph's two links go to published
pages. No jargon, no overclaiming, placeholders only. One optional nicety (not a finding): the
`ats-rejection-myth.md` link could point at its `#do-formatting-errors-get-resumes-rejected` section.

Re-review verdict: **publish** - 0 high, 0 medium open; F9 inbound links carried by plan-xsy.64.
