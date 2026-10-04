---
title: "Seven resume layouts, three PDF text readers: the data"
description: "One made-up resume in 7 layouts, read by 3 free PDF text readers in 5 ways, October 2026: one row per layout and reader, how we scored, limits."
published: 2026-10-04
status: published
data: resume-parser-test-2026-10.csv
license: CC BY 4.0
uncited:
  - "7 layouts"
  - "5 ways"
  - "35 rows"
  - "13 of the 35"
  - "0 of 5"
  - "5 of 5"
  - "4 of 5"
  - "2 of 5"
  - "3 jobs"
  - "four headings"
  - "pdfminer.six 20260107"
---
**Short answer**

- Our measurement: one made-up resume, same words in 7 layouts, read by 3 free PDF text readers in 5 ways.
- Plain one-column page: read right every time. Spaced-out headings: broke every reader.
- Free readers only - no employer's hiring system was tested.

This page holds the data from our resume layout test. It says what we built, how we scored each reading and where the test stops. Anyone can rerun it and get the same file. Why we recommend a plain page: [what makes a good resume](what-makes-a-good-resume.md#does-layout-matter) and [where the resume-rejection figure came from](ats-rejection-myth.md#do-formatting-errors-get-resumes-rejected).

## What did we test?

We wrote one made-up resume: "Your Name", 3 jobs at "Company A" to "Company C", one degree and two skill lines. No real person, employer or school is in it. We then laid the same words out in 7 ways. Only the page arrangement changes; the words, headings and order inside each section stay the same.

| Layout | What it copies |
|---|---|
| `one-column` | The plain one-column page, top to bottom (our control) |
| `sidebar` | Two columns: contact, education and skills in a narrow left column |
| `table` | A two-column table: headings and dates on the left, content on the right |
| `header-footer` | Name in the page header, email, phone and city in the page footer |
| `icons` | Small drawn icons in place of the words "Email" and "Phone" |
| `text-boxes` | A designer template of boxes placed on the page, saved in a different order than they show |
| `spaced-headings` | The control with section headings spaced out letter by letter |

Every layout fits one US Letter page in the same typeface. All text is real text, not pictures of text. The files are made by a script from one facts file, so a rerun gives the same files.

## Which readers did we run?

We ran three free PDF text readers. Two of them have a second way to read a page, so each layout was read 5 ways.

- `pymupdf`: PyMuPDF 1.28.2, reading in the order the file stores the text.
- `pymupdf-sort`: PyMuPDF 1.28.2, sorting text from the top left to the bottom right.
- `pdfminer`: pdfminer.six 20260107, with its default settings.
- `pypdf`: pypdf 6.19.0, its default reading.
- `pypdf-layout`: pypdf 6.19.0, keeping the page's spacing.

We did not test any employer's hiring system, such as Workday, Greenhouse or Lever. Their resume readers are closed, so this test can't stand in for them.

## What is in the file?

The file has 35 rows: each of the 7 layouts read 5 ways. Words are compared ignoring case and punctuation, so a missing bar or bullet never counts.

| Column | What it holds |
|---|---|
| `layout` | Which layout (table above) |
| `reader` | Which reader and way of reading (list above) |
| `broke` | true if any check below failed |
| `broke_because` | The checks that failed, in words |
| `lost_words` | Words on the page that the reading lacks, not counting split or merged words |
| `extra_words` | Words in the reading that the page lacks (reported, not scored) |
| `split_words` | Words broken into pieces, such as "S U M M A R Y" |
| `merged_words` | Words run together, such as "PresentCity" |
| `name_first_line` | true if the first line read is exactly "Your Name" |
| `name_found` | true if "Your Name" appears anywhere |
| `email` | true if the email address appears exactly |
| `phone` | true if the phone number appears exactly |
| `job_headers_together` | How many of the 3 jobs kept title, employer and dates on one line |
| `blocks_not_found` | Pieces of the resume whose opening words were not found together |
| `sections_mixed` | Sections with text from another section read into their middle |
| `within_section_order` | Share of pieces read in the right order inside their own section (1.0 = all) |
| `page_order` | Share of pieces read in the one-column order: name, contact, summary, experience, education, skills; pieces not found count as out of order (reported, not scored) |

A reading counts as broke when any word is lost, split or merged. It also breaks when the name is not on the first line or the email or phone is not exact. A job split over lines breaks it. So does a section whose own pieces come out of order, or one mixed with another. So does a piece whose opening words are not found together. Reading a whole sidebar before the main column is fine: we never scored which section comes first.

## What does the data show?

Our measurement found 13 of the 35 readings broke. How often each layout broke, out of 5 readings:

- Plain one column: 0 of 5.
- Name and contact in the header and footer: 0 of 5.
- Icons in place of contact labels: 0 of 5.
- Two columns with a sidebar: 2 of 5.
- Table: 2 of 5.
- Placed text boxes: 4 of 5.
- Spaced-out headings: 5 of 5.

How each one broke:

- Spaced-out headings: every reader split all four headings into single letters, such as "E X P E R I E N C E".
- Text boxes: two readers kept the file's own order, so the name and contact line came last. Two others mixed the education and skills column into the job bullets.
- Sidebar: two readers read across both columns line by line. One ran a sidebar word into a job line, as "PresentCity".
- Table: two readers put each job's dates on a different line from its title. One also read every left-hand cell first, so "Summary" came before the name.
- Header and footer: no reading broke, but all 5 read the email, phone and city last, after Skills.

Every reading kept the email and phone number exact. None lost a word outright; damage was to word shape and order.

## What are the limits?

These are free text readers, not an employer's hiring system. A commercial reader may do better or worse.

We made the layouts ourselves, from one made-up resume, in one typeface, on one page. A two-column page saved from Word, Google Docs or Canva stores its text differently and may read differently.

Our files come from a tool called Typst, not Word or a browser. The order text is stored in a file depends on the tool that made it.

Each reader ran once per layout: they give the same text every time, so repeats add nothing.

We scored the name by the first line. We did not check which hiring systems read the name that way.

## How can you rerun it?

The full method, written before the first run, is in [the method file](resume-parser-test-2026-10/METHOD.md). It also lists the two scoring changes made after reading the first results. The [scoring code](../parser_test.py) and the [reader script](../parser_read.py) are public, with the made-up resume and the 7 files they read.

You can download the file and open it in any spreadsheet. When you cite it, name the page and its date: "Seven resume layouts, three PDF text readers, CEZ Job Finder Research, October 2026".

If you find a mistake in the data, [report it here](https://github.com/cezkid/jobs/issues/new?title=Research%20correction). We fix the file, note the change on this page and say what changed. How we research and correct pages: [our methods](methods.md).
