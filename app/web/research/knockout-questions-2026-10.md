---
title: "Knockout questions on 143 job application forms: the data"
description: "Our count of yes/no screening questions on 143 US job application forms, October 2026: one row per form, how we counted, and its limits."
published: 2026-10-04
status: published
data: knockout-questions-2026-10.csv
license: CC BY 4.0
uncited:
  - "840 US job postings"
  - "143 application forms"
  - "143 rows"
  - "109 of the 143 forms"
  - "99 of 143"
  - "45 of 143"
  - "21 of 143"
  - "13 of 143"
  - "22 of the 143 forms"
  - "11 forms"
  - "16 employers"
  - "83 of the 104 employers"
  - "20 of the 143 forms"
  - "9,900"
  - "104 employers"
  - "92 of the 143 forms"
  - "one form each"
  - "60 postings"
  - "14 job fields"
---
**Short answer**

- Our measurement: 143 readable application forms from 840 US job postings, October 2026.
- One row per form: job field, form system, which yes/no screening questions it asks.
- Counts questions on the form; can't see whether an employer set any to reject automatically.

This page holds the data behind the measurement in [our article on where the resume-rejection figure came from](ats-rejection-myth.md#how-common-are-knockout-questions-our-measurement). The article explains what the counts mean for applicants. This page says how we counted, so anyone can check the numbers or count again.

## What is in the file?

The file has 143 rows, one per application form we could read. Each row says which kinds of screening question the form asks. Employers appear as letters only, and the same letter means the same employer. Our measurement covered 104 employers. The file holds no job titles, links or answers.

| Column | What it holds |
|---|---|
| `form` | Row number, 1 to 143 |
| `employer` | A letter per employer (A, B ... AA, AB ...) |
| `job_field` | The job field the posting was drawn from |
| `form_system` | The hiring system that runs the form (Greenhouse, Lever, Ashby, Workable, Recruitee) |
| `questions_beyond_basics` | Questions on the form other than the basics (see below) |
| `work_permit` | 1 if a question asks about the right to work |
| `sponsorship` | 1 if a question asks about visa sponsorship |
| `location_screen` | 1 if a question asks about on-site work, moving or living nearby |
| `years_experience` | 1 if a question asks for years of experience |
| `license_certificate` | 1 if a question asks about a license or certificate |
| `security_clearance` | 1 if a question asks about a security clearance or export rules |
| `any_knockout` | 1 if any of the six columns before it is 1 |
| `age_18` | 1 if a question asks whether you are 18 or older |
| `degree` | 1 if a question asks about a degree or level of education |
| `background_or_drug` | 1 if a question asks about a background check or drug test |

A 1 means at least one question on the form matched; a 0 means none did.

## How did we draw the sample?

On 3 October 2026 we searched freehire.me, a free job search, for US postings from the last 14 days. We searched 14 job fields, from healthcare and sales to law and education. For each field we took one page of 60 postings at a random point in the first 9,900 results. The random points came from a fixed starting number, so a rerun picks the same points. The postings at those points change every day.

That gave 840 US job postings. For each one, we asked freehire.me for the application form's questions, the way the form shows them to an applicant. We read questions only and sent nothing about anyone.

A form was readable when freehire.me returned it. Our measurement found 143 application forms that way. Most of the rest sat on hiring systems whose forms freehire.me does not read, such as Workday, Oracle and iCIMS, or on job boards that copy postings from elsewhere.

## How did we count the questions?

We matched each question's wording against a fixed list of phrases per column. Some forms, mostly on Workable, list the employer's own questions next to the name and email boxes; we counted those too. Our measurement found 20 of the 143 forms with no separate question list at all. A form counts once per column, however many of its questions match. The phrase lists are in [the counting code](../knockout_count.py), so the counts can be rerun.

- Work permit: phrases like "authorized to work", "legally eligible" or "right to work".
- Sponsorship: "sponsor" or "visa".
- Location: phrases like "relocate", "on-site", "in office", "commute" or "located in".
- Years of experience: "years" next to "experience", or a number of years.
- License or certificate: "license", "certification", "registered nurse", "CPA" or "bar status".
- Security clearance: "clearance", "polygraph" or "export control".

A plain address box is not a location screen. Our measurement found 11 forms whose only location questions were an address, city, state, country or zip code box, or "where are you located". Those 11 forms have a 0 in `location_screen`.

Basics are name, pronoun, email, phone, address, resume, cover letter and profile-link boxes, such as LinkedIn or a website. `questions_beyond_basics` counts every other question on the form.

## What does the data show?

The counts below come straight from the file, and the article reports the same ones.

- Any of the six screening columns: 109 of the 143 forms.
- Work permit or visa sponsorship: 99 of 143 forms.
- On-site work, moving or living nearby: 45 of 143 forms.
- Years of experience: 21 of 143 forms.
- License, certificate or security clearance: 13 of 143 forms.
- Nothing beyond the basics: 22 of the 143 forms.

Counted by employer instead of by form, 83 of the 104 employers asked at least one of the six kinds of question.

## What are the limits?

The sample is small and leans toward tech and office jobs. Every field gave 60 postings, but readable forms were far more common in some fields. Sales, customer success, HR and backend software jobs gave 92 of the 143 forms. Healthcare and finance gave one form each, and design gave none.

Five form systems are covered; Workday and iCIMS are not. Forms on those systems may ask different questions.

A question on a form is not a rejection. The data shows which questions employers ask, not whether any employer set a wrong answer to reject an applicant automatically.

Matching phrases can miss a question worded in an unusual way, or count one that only looks similar. We checked the phrase lists by reading the questions they matched, not every question on every form.

Some employers posted several jobs. Our measurement found 16 employers with more than one row, and one employer with eight, so those employers weigh more in the counts by form.

## How can you use it?

You can download the file, open it in any spreadsheet and count it yourself. When you cite it, name the page and its date: "Knockout questions on 143 job application forms, CEZ Job Finder Research, October 2026".

If you find a mistake in the data, [report it here](https://github.com/cezkid/jobs/issues/new?title=Research%20correction). We fix the file, note the change on this page and say what changed. How we research and correct pages: [our methods](methods.md).
