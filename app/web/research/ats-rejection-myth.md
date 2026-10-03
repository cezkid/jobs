---
title: "Do ATS reject 75% of resumes? Where the number came from"
description: The 75% figure traces to a 2012 sales claim with no method. Hiring software mostly stores and searches resumes; yes/no questions do the rejecting.
published: 2026-10-03
modified: 2026-10-03
status: draft
og_title: "Do hiring systems reject 75% of resumes? Where the claim came from"
uncited:
  - "143 application forms"
  - "106 of the 143 forms"
  - "96 of 143"
  - "54 of 143"
  - "21 of 143"
  - "11 of 143"
  - "a median of six questions"
---
**Short answer**

- "75% rejected by ATS": one 2012 sales claim, no method ever published (Vendor survey) [@levinson-2012-cio].
- Hiring software stores, searches and ranks; a person usually decides (Vendor survey, help pages).
- Automatic rejections come mostly from yes/no questions: work permit, location, license (Vendor survey).
- AI match scores are spreading; how often they reject alone is unknown.

## Where does the 75% number come from?

The number traces back to a single 2012 magazine article. In March 2012, CIO magazine wrote that applicant tracking systems "kill 75% of candidates' chances" of an interview [@levinson-2012-cio]. The article credited that figure to Preptel, a company selling help to beat those systems [@levinson-2012-cio].

Preptel sold a resume service for $24.95 a month at the time [@levinson-2012-preptel]. Its own news page reposted the 75% line later that year [@preptel-2012]. Neither page says how the number was measured. No study, sample or data behind the figure has been published since.

The original wording was "kill chances", not "reject" [@levinson-2012-cio]. Many retellings now say "rejected", which the 2012 article never claimed.

In a 2025 survey by Enhancv, 68% of recruiters said job seekers picked up the myth on LinkedIn or TikTok [@enhancv-2025]. Enhancv sells a resume builder, so that survey is a vendor survey.

For you, the 75% figure is not evidence [@levinson-2012-cio]. The figure was a sales line, and nobody has backed it up.

## What does an applicant tracking system actually do?

An applicant tracking system, or ATS, is the software employers use to collect and manage job applications. Almost every big employer has one. A resume-tool company found one on the careers pages of 97.4% of Fortune 500 companies in 2026 [@jobscan-2026].

The software does four main jobs. It stores each application. It lets recruiters search resumes for words, like a search engine [@greenhouse-search]. It filters applicants by their answers to the form's questions [@greenhouse-rules]. Newer versions also rank or score applicants against the job [@ashby-2024].

Storing and searching are not rejecting. A resume that never shows up in a recruiter's search was not thrown out. Nobody read it, which is a different problem.

For you, the useful question is not "will a robot reject me?" It is "will a recruiter searching for this job find me, and will my answers pass the form?"

## What gets rejected automatically?

Yes/no questions on the application form are the most common automatic filter. Recruiters call them knockout questions. Greenhouse, a widely used system, lets employers reject applicants automatically based on answers to custom questions [@greenhouse-rules]. Its own example is a license or location requirement [@greenhouse-rules].

Those rules act on your answers, not on your resume text [@greenhouse-rules]. The same help page says the system can send a rejection email automatically.

Recruiters in the Enhancv interviews described the same split. 23 of the 25 recruiters said their system did not reject automatically for formatting, content or design [@enhancv-2025]. Two said their systems were set up to reject on resume content, such as a low match score [@enhancv-2025].

Enhancv's page gives two different figures for knockout use: 84% of recruiters in one place, 100% in another [@enhancv-2025]. Either way, knockouts were the main automatic filter those recruiters described. The sample is small, and how the 25 were chosen is not stated.

For you, the answers on the form matter more than the layout of the page.

## How common are knockout questions? Our measurement

We wanted to know how often real application forms ask these questions. In October 2026 we drew a sample of US job postings from the last 14 days. The sample covered 14 job fields, from healthcare and sales to law and education.

Our measurement: 840 postings yielded 143 application forms we could read. The rest used systems whose forms we can't read, such as Workday. The forms asked a median of six questions beyond name and contact details.

Most forms asked at least one knockout-type question. Our measurement found 106 of the 143 forms asked about work permit, visa sponsorship, location, years of experience, a license or a security clearance.

- Work permit or visa sponsorship: 96 of 143 forms.
- Where you live, on-site work or moving: 54 of 143 forms.
- Years of experience: 21 of 143 forms.
- License, certificate or security clearance: 11 of 143 forms.

These counts have limits. The job search we used leans toward tech and office jobs. Five form systems are covered; Workday and iCIMS are not. We can see the questions, not whether an employer set any of them to reject automatically.

Our share of 106 of 143 forms does not confirm the old 75% claim [@levinson-2012-cio]. The two numbers measure different things.

For you, expect a work-permit or sponsorship question on most forms, and a location question on many.

## Do formatting errors get resumes rejected?

No published study shows that a formatting slip alone causes automatic rejection. Recruiters in the Enhancv interviews mostly said formatting did not trigger rejection [@enhancv-2025]. That evidence is a vendor survey of 25 people, so it is weak in both directions.

Formatting can still hurt in a quieter way. Our own tests found that widely spaced heading letters came back as "EXP E R I ENC E" in one conversion ([page-format.md](../../docs/resume/page-format.md)). A garbled word can't match a recruiter's search. In one Workday test, a school and degree written on one line landed in the wrong boxes.

Blank questions are not rejections either. Ashby's "Autofill from resume" filled only contact boxes in our test, leaving the employer's questions empty ([ashby.md](../../docs/apply/ashby.md)). Applicants can read that as the system rejecting their resume. It did not.

For you, a plain one-column page that reads back cleanly is the safe choice. Fancy layouts are a risk to being found, not a sure rejection.

## Do employers' filters screen out people who could do the job?

Yes, by executives' own account. The Hidden Workers survey asked 2,275 executives in the US, UK and Germany in early 2020 [@fuller-2021]. Over 90% said they used their software to first filter or rank middle-skills and high-skills applicants [@fuller-2021, p. 20].

Most of those executives admitted the filters cost them good people. 88% said their system filtered out qualified high-skills applicants at least sometimes; for middle-skills jobs it was 94% [@fuller-2021, p. 26]. The question asked about candidates who could do the job but did not match exact criteria [@fuller-2021, p. 26].

This is a survey of what executives said, not a measurement of what the software did. It is still the strongest published sign that rigid filters drop qualified people.

For you, gaps between your experience and the exact wording of a posting can matter. The fix is the posting's words for skills you really have, not words you lack.

## Is AI now rejecting resumes on its own?

AI scoring is spreading, but how often it rejects alone is unknown. In a 2026 survey of 1,000 US hiring managers, 35% said they used AI to screen or rank applications [@resume-genius-2026]. 19% said they used AI to screen some out before a human looked [@resume-genius-2026]. The survey was run by a resume-builder company.

Vendors describe their AI as an aid to a human reviewer. Ashby says its AI marks each applicant as meeting an employer's criteria or not, with reasons [@ashby-2024]. Ashby says it is then "up to the reviewer to advance or reject" [@ashby-2024].

A US lawsuit alleges otherwise for one vendor. In Mobley v. Workday, the plaintiffs allege Workday's AI scored, sorted or screened applicants in a way that disadvantaged older people [@mobley-2025-order, p. 3]. Workday's position is that its AI cannot reject anyone without the employer taking part [@mobley-2025-order, p. 10].

In May 2025 a federal court in California let the age claim go forward as a collective action [@mobley-2025-order]. Workday told the court 1.1 billion applications were rejected using its software [@mobley-2025-order, p. 19]. The court noted that figure counts rejections recorded in Workday, not AI rejections [@mobley-2025-order, p. 19].

As of October 2026, the plaintiffs are asking to widen the case to more groups of applicants [@lawyer-monthly-2026]. A hearing is set for March 2027, and Workday denies the claims [@lawyer-monthly-2026]. Nothing has been proven. Not legal advice.

For you, AI scores are real and growing, but a person usually still makes the call.

## What we don't know

- How many applications any system rejects automatically. No public data counts it across employers.
- How many employers turn on auto-reject rules, and for which questions.
- How AI match scores are calculated, for any vendor. None publish their method.
- Whether a resume tuned to a posting's words gets more interviews. No large study has tested it.
- Systems we could not read, like Workday and iCIMS, may ask different questions.

## What helps

- Answer yes/no questions truthfully. Work permit and sponsorship answers are checked once you are hired.
- Use the posting's own words for skills you really have. Recruiters search for them [@greenhouse-search].
- Use a plain one-column page that a computer reads back correctly.
- Fill every question yourself; autofill often leaves them blank.
- Apply widely. Rigid filters drop qualified people [@fuller-2021, p. 26], so one rejection says little about you.

More on what recruiters look for: [What makes a good resume](what-makes-a-good-resume.md). On AI screening and bias: [Does AI screening treat applicants unfairly?](ai-resume-screening-bias.md). How we grade evidence: [How we research](methods.md).

## How CEZ Job Finder uses this

- Reads each form's questions before you apply and names the yes/no ones.
- Keeps your work-permit answer exactly as you give it.
- Makes a one-column resume and checks it reads back cleanly.
- Uses a posting's words only where your own experience backs them.
