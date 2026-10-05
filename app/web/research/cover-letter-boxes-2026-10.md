---
title: "Cover letter boxes on 143 job application forms: the data"
description: "Our count of cover letter boxes on 143 US job application forms, October 2026: one row per form, required or optional, how we counted, and its limits."
published: 2026-10-04
status: published
data: cover-letter-boxes-2026-10.csv
license: CC BY 4.0
uncited:
  - "143 readable application forms"
  - "143 rows"
  - "104 employers"
  - "96 of the 143 forms"
  - "91 of the 96"
  - "2 of the 96"
  - "3 of the 96"
  - "71 of the 104 employers"
  - "85 of 96"
  - "0 of 19"
  - "3 of 15"
  - "7 of 12"
  - "1 of 1"
  - "28 of 33"
  - "10 of 26"
  - "16 employers"
---
**Short answer**

- Our measurement: 143 readable application forms from US job postings, October 2026 - the same forms as our knockout-question count.
- One row per form: job field, form system, whether it has a cover letter box, and whether the box is required.
- Counts the box on the form; can't see whether anyone reads the letter.

This page holds the data behind the measurement in [our article on cover letters](cover-letters-after-ai.md#do-employers-still-ask-for-cover-letters). The article explains what the counts mean for applicants. This page says how we counted, so anyone can check the numbers or count again.

## What is in the file?

The file has 143 rows, one per application form we could read. Our measurement covered 104 employers. Employers appear as letters only, and the same letter means the same employer. The rows, form numbers and employer letters match [the knockout-question data](knockout-questions-2026-10.md), so the two files can be joined on `form`. The file holds no job titles, links or answers.

| Column | What it holds |
|---|---|
| `form` | Row number, 1 to 143, same as the knockout-question file |
| `employer` | A letter per employer, same as the knockout-question file |
| `job_field` | The job field the posting was drawn from |
| `form_system` | The hiring system that runs the form (Greenhouse, Lever, Ashby, Workable, Recruitee) |
| `letter_box` | 1 if the form has a cover letter box, 0 if not |
| `letter_required` | 1 if the box must be filled, 0 if optional, blank if there is no box or we could not check |

## How did we draw the sample?

The forms are the 143 readable forms from our knockout-question count. On 3 October 2026 we drew US postings from the last 14 days across 14 job fields on freehire.me, a free job search. 13 of those fields had a form we could read; design had none. How the postings were picked is on [the knockout-question data page](knockout-questions-2026-10.md#how-did-we-draw-the-sample).

## How did we count the boxes?

A form has a box when freehire.me's read of the form lists an entry named "cover letter". That entry can sit among the basic boxes, such as name and email, or among the questions.

Whether the box is required came from the form itself. Ashby forms carry that flag in freehire.me's read. For Greenhouse, Workable and Recruitee forms, we asked each hiring system's public job page once, on 4 October 2026. We first looked up each posting's number on freehire.me. We sent only that number, nothing about anyone. The answers are saved in our raw file, which is not published, so a rerun from it asks nothing new. The required flags can't be read again once a posting closes. The steps are in [the counting code](../letter_count.py).

Lever forms list no box named cover letter. Some Lever forms show an open "additional information" box whose hint says to add a cover letter. freehire.me's read does not list that box, so we did not count it.

## What does the data show?

The counts below come straight from the file, and the article reports the same ones.

- A cover letter box: 96 of the 143 forms.
- Optional: 91 of the 96 forms with a box.
- Required: 2 of the 96, one Greenhouse form and one Recruitee form.
- Could not check: 3 of the 96, because the hiring system no longer showed the posting.
- By employer: 71 of the 104 employers had a box on at least one form.

By form system, our measurement found a box on 85 of 96 Greenhouse forms and 0 of 19 Lever forms. Ashby forms had one on 3 of 15, Workable on 7 of 12 and Recruitee on 1 of 1.

By job field, sales forms had a box on 28 of 33 and customer success forms on 10 of 26. The field counts mostly follow the form system each field's employers use.

## What are the limits?

The sample is small and leans toward tech and office jobs, like the knockout-question count it shares. Five form systems are covered; Workday and iCIMS are not.

A box on the form is not a letter that gets read. The data shows what forms ask for, not what employers do with the answer.

The required flag was read a day after the forms. An employer could have changed a form in between.

Some employers posted several jobs. Our measurement found 16 employers with more than one row, so those employers weigh more in the counts by form.

## How can you use it?

You can download the file, open it in any spreadsheet and count it yourself. When you cite it, name the page and its date: "Cover letter boxes on 143 job application forms, CEZ Job Finder Research, October 2026".

If you find a mistake in the data, [report it here](https://github.com/cezkid/jobs/issues/new?title=Research%20correction). We fix the file, note the change on this page and say what changed. How we research and correct pages: [our methods](methods.md).
