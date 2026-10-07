---
title: "Are two-column resumes ATS friendly? A 7-layout PDF test"
description: "We read one resume in 7 layouts with 3 free PDF readers, not an employer's system. Our plain page never broke; spaced-out headings always did."
published: 2026-10-04
modified: 2026-10-07
status: published
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
  - "Two readings"
  - "two readings"
  - "Two other readings"
  - "4 of our 13"
  - "2 more"
  - "We found no Workday help page"
  - "No study found"
  - "We searched"
  - "reject 75% of resumes"
  - "a quarter of a letter"
---
**What to do**

- Use one column, top to bottom.
- Keep normal letter spacing in headings.
- Put your name, email and phone in the body of the page, not the header or footer.

**What the evidence says**

- Our measurement: one made-up resume, 7 layouts, 3 free PDF text readers, 35 readings. No employer's hiring system tested.
- Our plain one-column page: 0 of 5 broke. Spaced-out headings: 5 of 5. Text boxes: 4 of 5. Sidebar, table: 2 of 5 each.
- No lost words, email and phone exact. A bigger vendor test agrees, and saw some one-column pages break too (Vendor survey) [@enhancv-2026].
- Greenhouse's help page warns against most of the same layouts (Maker's docs) [@greenhouse-parse].

## Are two-column resumes ATS friendly?

**A two-column resume is a gamble, not a sure failure.** In our test, a sidebar layout broke 2 of 5 readings. Our plain one-column page broke 0 of 5.

We wrote one made-up resume: "Your Name", 3 jobs at "Company A" to "Company C", a degree and two skill lines. We laid the same words out in 7 layouts. Only the arrangement on the page changed. Then we read each file 5 ways with three free PDF text readers: PyMuPDF, pdfminer.six and pypdf. Every file, script and result is on [the data page](resume-parser-test-2026-10.md).

An applicant tracking system, or ATS, is the software employers use to collect applications. Greenhouse, one such system, scans an uploaded resume and fills in the applicant's fields from it [@greenhouse-parse]. Turning the file into plain text is the first step of that chain. A mistake in that step carries into every later step [@textkernel-2023].

Our measurement found 13 of 35 readings broke. A reading broke if any word was lost, split or merged. It broke if the name was not the first line, or the email or phone was not exact. It broke if a job's title, employer and dates fell onto different lines. It also broke if a section's lines came out of order or mixed with another section.

```bars
How often each layout broke, out of 5 readings. Our measurement, October 2026 ([data](resume-parser-test-2026-10.md)).
Layout | Broke
Plain one column | 0 of 5
Name and contact in header and footer | 0 of 5
Drawn icons in place of contact labels | 0 of 5
Two columns with a sidebar | 2 of 5
Table | 2 of 5
Placed text boxes | 4 of 5
Spaced-out headings | 5 of 5
```

For you, the safest layout in our test was the plainest one.

## What broke, layout by layout?

**Each layout that broke did so in its own way.** The summary below comes from the committed results file.

| Layout | Broke | How it broke |
|---|---|---|
| Plain one column | 0 of 5 | Nothing |
| Header and footer | 0 of 5 | No break, but every reader put the contact line last |
| Drawn icons for contact labels | 0 of 5 | Nothing (icon fonts not tested) |
| Sidebar | 2 of 5 | Read across both columns line by line |
| Table | 2 of 5 | Job dates split from the job title |
| Placed text boxes | 4 of 5 | Name read last, or columns mixed |
| Spaced-out headings | 5 of 5 | Every heading split into single letters |

**Spaced-out headings.** We spaced heading letters a quarter of a letter's width apart. Every reader split all four headings into single letters, such as "E X P E R I E N C E". A word search for "Experience" would not find that heading. This was the only layout that broke every reading.

**Placed text boxes.** Our text-box page saves its boxes in a different order than they appear, as placed-box designs can. Two readings kept the saved order, so the name and contact line came last. Two other readings mixed the education and skills column into the job bullets.

**Sidebar.** Two readings read across both columns, one line at a time. In one of them, a sidebar word ran into a job line as "PresentCity". The other three readings read the sidebar and the main column as separate blocks, in order.

**Table.** Two readings put each job's dates on a different line from its title and employer. One of them also read the whole left column first, so "Summary" came before the name.

**Header and footer.** No reading broke by our rules. Still, all 5 read the email, phone and city last, after Skills. A system that expects contact details near the top could miss them. Greenhouse lists contact details in a header or footer as a risk [@greenhouse-parse].

**Icons.** Our icons were drawn shapes, not letters, and no reading broke. Many templates draw icons with a special icon font instead. We did not test icon fonts.

In practice, the damage was to order and word shape. No reading lost a word outright, and all 35 kept the email and phone exact.

## Do ATS read tables?

**Not always in the right order.** In our test, a table layout broke 2 of 5 readings. Both put each job's dates on a different line from its title. Greenhouse lists tables among the things that can stop its resume reader filling in its fields [@greenhouse-parse].

## Can ATS read a PDF?

**Yes, when the PDF holds real text.** None of our 35 readings lost a word from a PDF. Greenhouse names .pdf as a file type it reads. It lists a resume uploaded as an image as a cause of failure [@greenhouse-parse].

## Do hiring systems say the same thing?

**One hiring-system maker warns against most of the same layouts.** Greenhouse, one hiring system, lists what can stop it reading a resume into its fields. Its list includes spaces between letters, tables, headers and footers, and columned layouts. It also lists a name and contact details placed in a header, footer or text box [@greenhouse-parse]. Those are the layouts that broke readings or moved the contact line in our test.

Greenhouse's page adds a warning our test could not cover. Its resume reader skips names it takes for fake data, such as "First Last" or "Company 1" [@greenhouse-parse]. Our made-up resume used "Your Name" and "Company A". A commercial resume reader might have skipped those names for that reason alone.

A university career office gives the same advice. MIT's career office says "boring is better" and tells students to avoid tables, text boxes and icons. It says text boxes or columns can put the text in the wrong order [@mit-capd-ats]. That is a guide, not a study.

We found no Workday help page on how its resume reader handles layout. Lever has a help article we could not open in October 2026, so we do not cite it.

## Do modern resume readers handle columns fine?

**Some vendors say their readers now handle columns well.** Textkernel sells a resume reader used inside other hiring systems. In 2023, Textkernel wrote that about 10-15% of resumes use a column layout. It said better column detection raised its share of resumes read in the right order from 62% to 90%. Its own staff judged about 700 resumes side by side for that figure [@textkernel-2023]. That is the maker's own test, described only in outline.

The largest outside test we found used the same free readers we did. Enhancv, a resume builder that sells two-column templates, ran 3 resumes through 17 of its templates. It read each file 7 ways with pdftotext, PyMuPDF, pdfminer.six and pypdf: 357 readings [@enhancv-2026].

In Enhancv's test, one-column and two-column pages kept nearly all their words, within half a point. Email and phone came back right in all 357 readings. Under the worst reading method, sections stayed whole in 35% of two-column readings and 60% of one-column ones [@enhancv-2026]. So its one-column pages broke too, just less often. Under another method the gap was about one point.

Enhancv also had AI models read the scrambled text. The gap in whole sections shrank to about three points. Employer names still dropped from 100% to 83% [@enhancv-2026]. That AI test used 10 resumes. It is a seller's test of its own templates, not peer-reviewed.

A second template seller, Resumap, ran one made-up resume in 36 of its templates. It loaded each file into Zoho Recruit, Workable and Textkernel, and Manatal's match scoring. Email and phone came back 36 of 36 on every reader shown. Workable split all 3 jobs correctly on all 36 templates; Textkernel did so on 31 [@resumap-2026].

Resumap concluded "the failure mode isn't columns. It's text-stream order." By that it means the order the file stores the text in. Resumap says column count did not predict which layouts failed, but gives no counts [@resumap-2026]. The test was run by a template seller and is not peer-reviewed.

Our results show both causes. Columns broke readers that sort text by where it sits on the page. That was 4 of our 13 breaks, on the sidebar and text-box pages. Stored order broke readers that keep the file's own order: 2 more, on the text-box page. Our sidebar file stored its text in the right order, and those readers read it fine.

An older peer-reviewed benchmark found the same weak spot outside resumes. Bast and Korzen tested 14 PDF text readers on 12,098 scientific articles in 2017. Most readers got the reading order right, but some had trouble with two-column articles [@bast-2017, p. 9]. A PDF stores the position of each letter, not words or paragraphs [@bast-2017].

For you, a column is risky because you can't control which kind of reader an employer uses.

## What we don't know

- How Workday, Greenhouse, Lever or iCIMS read these 7 layouts. We tested free readers only. No study found that tests those systems side by side with a published method.
- Whether a broken reading costs interviews. No study found links reading errors to callbacks. Enhancv says the same of its own test [@enhancv-2026].
- How a hiring system's AI step changes the result. Enhancv's small test says AI models repair most scrambled order [@enhancv-2026]. Our test stops at the plain text.
- How icon fonts read. Our icons were drawn shapes; a font icon may come out as a stray character.
- How layouts saved from Word, Google Docs or Canva read. Our files came from one tool, Typst. Each tool stores text in its own order.
- How often recruiters read the text a system pulled out instead of the file. Greenhouse keeps the file attached even when it can't fill in the fields [@greenhouse-parse].
- Whether placeholder names changed the results. Greenhouse says its resume reader skips names that look fake [@greenhouse-parse].
- What else exists. We searched in October 2026 for hiring-system layout tests, studies linking reading errors to callbacks, and Workday and Lever help pages.

## What helps

- Use one column, top to bottom. It broke 0 of 5 readings in our test.
- Write headings with normal letter spacing. Spaced-out headings broke 5 of 5 readings in our test.
- Keep each job's title, employer and dates on one line, outside any table.
- Put your name, email and phone in the body of the page, not the header or footer. Greenhouse lists both places as risks [@greenhouse-parse].
- Skip text boxes and designer templates when applying online. If your field values design, MIT's career office suggests keeping those for resumes you hand over directly [@mit-capd-ats].
- Check your file's text: save it as plain text, or copy it into a plain text editor. MIT says text in the wrong order points to text boxes or columns [@mit-capd-ats]. Your check shows one reader's view only. Other readers may read columns across, so one column is still the safer choice.

Why a plain page is the safe choice: [What makes a good resume?](what-makes-a-good-resume.md#does-layout-matter). Whether software rejects most resumes: [Do hiring systems reject 75% of resumes?](ats-rejection-myth.md). The full data and method: [Seven resume layouts, three PDF text readers](resume-parser-test-2026-10.md). How we grade evidence: [How we research](methods.md).

## How CEZ Job Finder uses this

- Makes every resume one column, with plain headings and black text.
- Checks each page before you get it: no tables, images, header or footer text, or spaced-out letters.
- Reads each page back with one reader, two ways, and checks the text keeps the order you see.

CEZ Job Finder is a free job-search app for Windows and Mac: [see how CEZ Job Finder works](https://jobs.enrriquez.com/).

## Changes

- October 2026 - added a short What to do list at the top, renamed the Short answer box "What the evidence says" and set each section's answer in bold. The findings are unchanged.
- October 2026 - two section answers now match their sections: only the layouts that broke failed in their own way, and the warnings come from one hiring-system maker.
