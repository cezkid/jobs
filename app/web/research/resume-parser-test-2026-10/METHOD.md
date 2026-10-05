# Resume parser test, October 2026 - method

Written 2026-10-04, before any reader was run on the corpus (plan-xsy.62). The run, the analysis
and the article follow this file. A result never changes it: any later change gets a dated line
under **Changes** saying what moved and why.

## Question

When the same resume is laid out in different ways, do open-source PDF text readers get the
reading order and the key fields right?

Search wording this answers: "are two column resumes ATS friendly", "do ATS read tables",
"resume format ATS test", "can ATS read PDF".

## Corpus

One made-up person in one facts file (`facts.yml`): "Your Name", a made-up email at example.com,
a 555-01xx phone number (reserved for fiction), "City, State", a summary, 3 jobs at "Company A",
"Company B", "Company C" (title, employer, dates, 3 bullets each), one degree at "University A",
2 skill lines. No real person, employer or school.

The same text goes into every layout: same words, same headings (Summary, Experience, Education,
Skills), same order inside each section. Only the page arrangement changes. Each layout is a
Typst source in `layouts/`, built by `uv run app/web/parser_test.py build`. Same typeface as the
app (Caladea, `app/resume/fonts/`), US Letter, one page, ligatures off, no hyphenation.

| Layout | What it copies | How it is built |
|---|---|---|
| `one-column` | control: the plain one-column page we recommend | one flow, top to bottom; job title, employer and dates on one line |
| `sidebar` | two-column template with a sidebar | name + summary across the top; left column (about a third): contact, education, skills; right: experience |
| `table` | layout built from a table | one 2-column table: section names + dates in the left cell, content in the right |
| `header-footer` | contact details in the page header/footer | name in the page header, email, phone and city in the page footer |
| `icons` | icons in place of contact labels | small drawn icons (envelope, phone, pin) before email, phone and city |
| `text-boxes` | designer template of placed boxes | each block placed at a fixed spot; the file draws them in a different order than they appear (experience first, header last) |
| `spaced-headings` | letter-spaced headings | the control with section headings spaced out (+0.25em between letters) |

In every layout a job's title, employer and dates sit on one visual row. All text is real text
(no images of text). The icons are vector drawings, not characters.

Ground truth (`truth.json`) is written from the facts file by the same script, never by reading
a PDF: the ordered list of text blocks (name, each contact item, summary, each heading, each job
header, each bullet, the education line, each skill line), each tagged with its section.

Rerun = byte-identical PDFs and truth file (`build --check`; a test runs it). By default Typst
stamps each file with the clock (CreationDate, ModDate, XMP dates); the layouts set the document
date to none, so no date is written. Nothing else in the files varied between two builds.

## Readers

| Reader | Version | Calls (each = one "reader" in the results) |
|---|---|---|
| PyMuPDF | 1.28.2 (the app's own) | `page.get_text("text")` (file order); `page.get_text("text", sort=True)` (top-left to bottom-right) |
| pdfminer.six | 20260107 | `pdfminer.high_level.extract_text(path)` (default layout settings) |
| pypdf | 6.19.0 | `page.extract_text()` (default); `page.extract_text(extraction_mode="layout")` |
| poppler `pdftotext` | not installed on the test machine | dropped - not run, not reported |

Readers outside the project run from `app/web/parser_read.py`, a self-contained script that pins
its own versions (`uv run app/web/parser_read.py`); the project's packages are unchanged.
Tool versions used for the build: Typst 0.15.0 (Python package `typst`), uv 0.12.17, macOS 26
(Darwin 25.4), Python 3.14 for the reader script.

Not tested: commercial applicant tracking systems (Workday, Greenhouse, Lever, iCIMS and others).
Their parsers are closed; this test can't stand in for any of them. The article cites what their
makers publish about reading resumes, labelled Maker's docs.

## Measures

Text is compared as words: lower-cased, split on anything that is not a letter or digit (so
`|`, `-`, bullets and spacing never count). Each measure is scored per layout x reader.

1. **Lost words** - words in the truth that the reader's text lacks (counted with repeats),
   after setting aside split and merged words (2, 3). Score: count. Also: extra words the truth
   lacks (reported, not scored - an icon read as a letter shows here).
2. **Split words** - a truth word missing from the output whose letters appear as 2+ output words
   in a row (`EXP E R I ENC E`). Score: count.
3. **Merged words** - an output word not in the truth that is 2+ lost truth words run together
   (`LANGUAGESBachelor`, `PresentCity`). Score: count.
4. **Name** - the first non-empty line of the output is exactly "Your Name" (spacing collapsed).
   Many parsers take the top line as the name. Also reported: name found anywhere.
5. **Email, phone** - the exact strings `your.name@example.com` and `(555) 010-0199` appear in
   the output (spacing collapsed to one space). Score: right / wrong each.
6. **Job headers** - for each of 3 jobs: title, employer and dates all on one output line. Score:
   jobs kept together, of 3.
7. **Reading order** - each truth block is located in the output's word stream by its first
   words (up to 5; every block's opening is unique by design; a job header by its title +
   employer - see Changes). Then:
   - *within sections*: blocks of each section in truth order (longest in-order run / blocks
     found; 1.0 = all in order);
   - *sections kept apart*: no block of one section lands between two blocks of another;
   - *blocks not found*: a block whose opening words aren't in the output as a run (a split, a
     merge, or text interleaved from elsewhere).
   The order of whole sections is not scored: a sidebar read before the main column is a fair
   reading. Also reported: in-order share across the whole page against the truth order.

## What counts as "broke"

A layout x reader **broke** when any of these holds:

- any lost, split or merged word;
- name not on the first line, or email or phone not exact;
- any job header not on one line;
- any section's blocks out of order, any section mixed into another, or any block not found.

Each failure is reported by its kind, so the article can say which layouts broke which readers
and how. If the control (`one-column`) breaks a reader, that reader's baseline is said in the
article and its other failures are read against that baseline.

## Limits (to state in the article)

- Open-source text readers, not any employer's system. A commercial parser may do better or
  worse; this shows what PDF text a reader is handed, and how often plain reading order fails.
- Layouts we made, one made-up resume, one typeface, one page. Real templates (Word, Canva,
  Google Docs exports) build their files differently; a Word-made two-column page may read
  differently from ours.
- Made from Typst, not Word or a browser. File order in other tools differs.
- One run per reader: the readers are deterministic, so repeats add nothing.
- Name on the first line is one convention among parsers, not a universal rule.

## Files

- `facts.yml` - the made-up resume, the one source of its text.
- `layouts/<layout>.typ` - one Typst source per layout; each reads the facts as JSON.
- `pdf/<layout>.pdf` - built files (committed).
- `truth.json` - expected blocks + fields, from `facts.yml`.
- `readings.json` - each reader's raw text of each layout, with reader versions (`parser_read.py`).
- `results.csv` - one row per layout x reader (`parser_test.py score readings.json`).
- `app/web/parser_test.py` - `build` (PDFs + truth), `score` (reader output -> results CSV),
  scoring functions (tested in `app/tests/test_parser_test.py`).
- `app/web/parser_read.py` - runs the readers, writes their text as JSON.

## Changes

- 2026-10-04, after the first scoring pass (plan-xsy.63), before any result was written up.
  Both from reading the raw reader text against the scores; no layout, reader or "broke" rule moved.
  - *Merged words* now also counts lost words run together that are not neighbours in the truth.
    Why: in `sidebar`, PyMuPDF (sorted) read "Present" from a job row and "City" from the sidebar
    as one word, "PresentCity". The first scorer only joined neighbouring truth words, so it
    counted 2 lost words instead of 1 merged word.
  - *Reading order*: a job header is found by its title + employer, not by its first 5 words.
    Why: `table` puts the dates in the left cell, so a reader that keeps the row whole reads
    "Mar 2021 – Present Operations Analyst | Company A". That is the row as printed; the first
    scorer called it "block not found". Whether the dates stay on the title's line is still
    scored, by *job headers* (measure 6).
