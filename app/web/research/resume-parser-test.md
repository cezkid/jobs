---
title: "Are two-column resumes ATS friendly? We tested 7 layouts"
description: "We read one resume in 7 layouts with 3 free PDF readers. Plain one column never broke; spaced-out headings always did; columns and tables sometimes."
published: 2026-10-04
status: draft
uncited:
  - "13 of 35"
  - "35 readings"
  - "7 layouts"
  - "5 ways"
  - "0 of 5"
  - "2 of 5"
  - "4 of 5"
  - "5 of 5"
  - "all 35"
  - "all four headings"
  - "3 jobs"
  - "two of the five"
  - "Two readings"
  - "two readings"
  - "Two others"
  - "two other readings"
  - "No study found"
---
**Short answer**

- Our measurement: one made-up resume, 7 layouts, 3 free PDF text readers, 35 readings.
- Plain one column: 0 of 5 broke. Spaced-out headings: 5 of 5. Text boxes: 4 of 5. Sidebar, table: 2 of 5 each.
- Email and phone read exactly in all 35. Damage = order and word shape, not lost words.
- Free readers only; no employer's hiring system tested. Greenhouse's help page warns against the same layouts (Maker's docs) [@greenhouse-parse].

## Are two-column resumes ATS friendly?

A two-column resume is a gamble, not a sure failure. In our test, a sidebar layout broke 2 of 5 readings. The plain one-column page broke 0 of 5.

We wrote one made-up resume: "Your Name", 3 jobs at "Company A" to "Company C", a degree and two skill lines. We laid the same words out in 7 layouts. Only the arrangement on the page changed. Then we read each file 5 ways with three free PDF text readers: PyMuPDF, pdfminer.six and pypdf. Every file, script and result is on [the data page](resume-parser-test-2026-10.md).

An applicant tracking system, or ATS, is the software employers use to collect applications. Greenhouse, one such system, scans an uploaded resume and fills in the applicant's fields from it [@greenhouse-parse]. Reading the file's text is the first step of that chain. If the text comes out scrambled, every later step works from scrambled text.

Our measurement found 13 of 35 readings broke. A reading counted as broken if any word was split or merged, or if a job title, employer and dates fell onto different lines. It also counted as broken if a section's lines came out of order or mixed with another section, or if the name was not the first line.

```bars
How often each layout broke, out of 5 readings. Our measurement, October 2026 ([data](resume-parser-test-2026-10.md)).
Layout | Broke
Plain one column | 0 of 5
Name and contact in header and footer | 0 of 5
Icons in place of contact labels | 0 of 5
Two columns with a sidebar | 2 of 5
Table | 2 of 5
Placed text boxes | 4 of 5
Spaced-out headings | 5 of 5
```

For you, the safest layout in our test was the plainest one.

## What broke, layout by layout?

Each layout failed in its own way. The summary below comes from the committed results file.

| Layout | Broke | How it broke |
|---|---|---|
| Plain one column | 0 of 5 | Nothing |
| Header and footer | 0 of 5 | No break, but every reader put the contact line last |
| Icons for contact labels | 0 of 5 | Nothing |
| Sidebar | 2 of 5 | Read across both columns line by line |
| Table | 2 of 5 | Job dates split from the job title |
| Placed text boxes | 4 of 5 | Name read last, or columns mixed |
| Spaced-out headings | 5 of 5 | Every heading split into single letters |

**Spaced-out headings.** Every reader split all four headings into single letters, such as "E X P E R I E N C E". A search for "Experience" would not find that heading. This was the only layout that broke every reading.

**Placed text boxes.** Designer templates often place boxes on the page in one order and save them in another. Two readings kept the saved order, so the name and contact line came last. Two other readings mixed the education and skills column into the job bullets.

**Sidebar.** Two readings read across both columns, one line at a time. In one of them, a sidebar word ran into a job line as "PresentCity". The other three readings read the sidebar and the main column as separate blocks, in order.

**Table.** Two readings put each job's dates on a different line from its title and employer. One of them also read the whole left column first, so "Summary" came before the name.

**Header and footer.** No reading broke by our rules. Still, all 5 read the email, phone and city last, after Skills. A system that expects contact details near the top could miss them.

In practice, the damage was to order and word shape. No reading lost a word outright, and all 35 kept the email and phone exact.

## Do hiring systems say the same thing?

Hiring-system makers warn against the same layouts. Greenhouse, one hiring system, lists what can make a resume fail to parse. Its list includes spaces between letters, tables, headers and footers, and columned layouts. It also lists a name and contact details placed in a header, footer or text box [@greenhouse-parse]. Those are the layouts that broke readings or moved the contact line in our test.

Greenhouse's page adds a warning our test could not cover. Its parser skips names it takes for fake data, such as "First Last" or "Company 1" [@greenhouse-parse]. Our made-up resume used "Your Name" and "Company A". A commercial parser might have skipped those names for that reason alone.

A university career office gives the same advice. MIT's career office says "boring is better" and tells students to avoid tables, text boxes and icons [@mit-capd-ats]. That is a guide, not a study.

We found no public help page from Workday or Lever that says how their resume readers handle layout. Lever's help page did not load for our scripts in October 2026.

## Do modern resume readers handle columns fine?

Some vendors say their readers now handle columns well. Textkernel sells a resume reader used inside other hiring systems. In 2023, Textkernel wrote that at least 15% of resumes use a column layout. It reported that better column detection raised its share of well-rendered test resumes from 62% to 90% [@textkernel-2023]. That is the maker's own test, and the post describes its method only in outline.

The strongest outside test we found also says columns are not the real problem. Resumap, a company that makes resume templates, ran one made-up resume in 36 of its templates. It loaded each file into commercial systems: Zoho Recruit, Manatal, Workable and Textkernel [@resumap-2026].

In that test, email and phone came back 36 of 36 on every system checked. Workable split all 3 jobs correctly on all 36 templates; Textkernel did so on 31 [@resumap-2026]. Resumap concluded "the failure mode isn't columns. It's text-stream order." Two-column templates did as well as one-column ones when the file stored the text in reading order [@resumap-2026]. The test was run by a template seller and is not peer-reviewed.

Our results fit that finding. Two text-box readings broke because the file stored the blocks out of reading order. The sidebar broke only for readings that sorted text by position across the whole page.

An older peer-reviewed benchmark found the same weak spot outside resumes. Bast and Korzen tested 14 PDF text readers on 12,098 scientific articles. Some readers had trouble with two-column articles [@bast-2017, p. 9]. A PDF stores the position of each letter, not words or paragraphs [@bast-2017].

For you, the point is simple: a column is risky because you can't see the order your file stores the text in.

## What we don't know

- How Workday, Greenhouse, Lever or iCIMS read these 7 layouts. We tested free readers only. No study found that tests the big hiring systems side by side with a published method.
- Whether a broken reading costs interviews. No study found links parse errors to callbacks.
- How layouts saved from Word, Google Docs or Canva read. Our files came from one tool, Typst. Each tool stores text in its own order.
- How often recruiters read the parsed text instead of the file. Greenhouse keeps the file attached even when its parse fails [@greenhouse-parse].
- Whether placeholder names changed the results. Greenhouse says its parser skips names that look fake [@greenhouse-parse].

## What helps

- Use one column, top to bottom. It broke 0 of 5 readings in our test.
- Write headings with normal letter spacing. Spaced-out headings broke 5 of 5 readings in our test.
- Keep each job's title, employer and dates on one line, outside any table.
- Put your name, email and phone in the body of the page, not the header or footer. Greenhouse lists both places as parse risks [@greenhouse-parse].
- Skip text boxes and designer templates when applying online. Keep those for resumes you hand over directly, as MIT's career office suggests [@mit-capd-ats].
- Check your file's text, not its looks: copy all of it into a plain text editor. Resumap gives the same advice for its own test [@resumap-2026]. If the text reads like your resume, top to bottom, the order is right.

Why a plain page is the safe choice: [What makes a good resume?](what-makes-a-good-resume.md#does-layout-matter). Whether software rejects most resumes: [Do hiring systems reject 75% of resumes?](ats-rejection-myth.md). The full data and method: [Seven resume layouts, three PDF text readers](resume-parser-test-2026-10.md). How we grade evidence: [How we research](methods.md).

## How CEZ Job Finder uses this

- Makes every resume one column, with plain headings and black text.
- Checks each page before you get it: no tables, images, header or footer text, or spaced-out letters.
- Reads each page back and checks the text comes out in the same order you see it.

CEZ Job Finder is a free job-search app for Windows and Mac: [see how CEZ Job Finder works](https://jobs.enrriquez.com/).
