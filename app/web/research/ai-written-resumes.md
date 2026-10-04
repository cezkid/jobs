---
title: "Can employers tell if AI wrote your resume?"
description: Mostly no, in tests - most people can't spot AI writing. About half of hiring managers say they'd care. What studies show, and what to do.
published: 2026-10-03
modified: 2026-10-04
status: published
og_title: "Can employers tell if AI wrote your resume? What studies show"
uncited:
  - "No study found that tests"
  - "We found no study"
  - "We searched the web, arXiv and news"
---
**Short answer**

- In tests with older AI models, most of 4,600 people couldn't tell AI writing from human writing; 5 readers who use AI often spotted whole AI-written texts far better (Lab studies) [@jakesch-2023; @russell-2025].
- Early detectors misfired and flagged non-native writers; one paid 2025 tool did far better; none tested on resumes (Lab studies; maker's docs) [@openai-2023; @liang-2023; @russell-2025].
- About half of hiring managers say they'd care; they name generic, vague lines as AI signs (Vendor surveys) [@insight-global-2025; @resume-genius-2026].
- Spelling and grammar help raised hires (2021, not chat AI); AI-tailored letters now count for less (Big study; Real records, preprint) [@wiles-2025; @cui-2025].

## Can people tell if a resume was written by AI?

Most people couldn't, in the largest test. In 2023, 4,600 people judged short self-descriptions written by people or by AI. The texts included freelancer profiles of the kind used to win work. People picked the right source only 50% to 52% of the time, about as good as a coin toss. Paying people for right answers barely helped, at 51.6%. Telling them after each answer whether they were right gave 51.2% [@jakesch-2023].

People relied on wrong clues. They took first-person words, contractions and family topics as signs of a human writer. AI text tuned to those clues was judged human more often than real human text, 65.7% against 51.7%. The AI models in that study were older ones, GPT-2 and GPT-3 [@jakesch-2023].

The strongest counter-evidence comes from a 2025 study of practiced readers. Nine paid readers labeled 300 articles as human or AI. Four readers who rarely used AI for writing did about as well as chance. They flagged 56.7% of AI articles but also about half of human ones. Five readers who used AI for writing often were far better. Their majority vote got 299 of the 300 articles right. Those five were picked because they resembled the best reader in a first round. Their most common clue was "AI vocabulary," words like "vibrant" and "crucial". The AI articles were written wholly by AI, not human drafts edited with AI. They were news-style articles, not resumes [@russell-2025].

For you, a reader who uses AI often may notice text written wholly by AI. Most readers will guess, and some will guess wrong about text you wrote yourself.

## Do AI detectors work on resumes?

Early detectors did not work well, and no detector has been tested on resumes. OpenAI released its own AI-text detector in January 2023. In its maker's test, the detector caught 26% of AI text. It wrongly flagged human text 9% of the time. OpenAI withdrew the detector in July 2023, citing "its low rate of accuracy" [@openai-2023].

A 2023 study ran seven detectors on essays all written by people. The detectors were nearly perfect on essays by US eighth graders. On essays by non-native English writers, they flagged 61% as AI on average. Of those essays, 97.8% were flagged by at least one detector. Plainer word choice made human writing look like AI to those 2023 detectors [@liang-2023].

A 2026 follow-up found no such bias with detectors of 2025, including a paid one. It tested essays in Czech, not English, and is a preprint. Its authors conclude the bias depends on the language [@al-ali-2026].

Detectors have changed since 2023. In the 2025 reader test above, one paid detector, Pangram, caught 99.3% of AI articles even after a rewording tool. That matched the practiced readers. Another popular detector, GPTZero, caught 85.3% of AI articles and wrongly flagged 0.7% of human ones. Two free, openly released detectors caught only 6.7% and 23.3% of AI articles reworded by a rewording tool. All of these were whole articles, not resumes [@russell-2025].

We found no study that tests detectors on resumes. We also found no study showing how many employers run them. A widely repeated survey figure on employer use led to no source we could open.

A detector's "AI" label is untested on resumes. Older detectors were tripped by plain, simple English [@liang-2023].

## What do hiring managers say about AI-written resumes?

They say they can tell, and about half say they care. Both surveys below are vendor surveys, run for companies in the hiring or resume business.

In an October 2024 survey of 1,005 US HR and hiring leaders, 88% said they can tell when applicants use AI. Of those leaders, 54% said they would care if a resume or cover letter was written by AI. The other 46% said they would not care [@insight-global-2025].

A 2026 survey of 1,000 US hiring managers was run for a resume-builder company. In it, 80% said they can often tell when AI wrote a resume. Most, 76%, said AI-written resumes make it harder to see what a person actually did. And 72% said heavy reliance on AI makes applicants seem less skilled. Asked about disclosure, 79% said applicants should say when AI helped [@resume-genius-2026].

Most signs they named were about wording quality. The top ones were unnatural phrasing (51%), repetitive or generic wording (44%), and vague or inflated descriptions and buzzword-heavy writing (41% each). Formatting habits such as long dashes were named by 32% [@resume-genius-2026].

```bars
Signs of an AI-written resume that hiring managers named, 2026; each could name more than one (Vendor survey, 1,000 US hiring managers) [@resume-genius-2026]
Sign | Share who named it
Unnatural phrasing or tone | 51%
Repetitive or generic wording | 44%
Vague or inflated descriptions | 41%
Buzzword-heavy writing | 41%
Perfect grammar with no variation | 39%
Formatting habits such as long dashes | 32%
Incorrect or irrelevant details | 27%
```

Saying you can spot AI is not the same as spotting it. In one lab test, readers who rarely used AI felt sure but did no better than chance [@russell-2025].

The warning signs managers name are generic, vague and inflated lines. Those are worth cutting whoever wrote them.

## Does using AI on your resume hurt your chances?

Writing help raised hiring in the largest real test. That test used spelling and grammar help, not today's chat AI [@wiles-2025].

In 2021, an online freelance platform ran an experiment with 480,948 new job seekers. Half got automatic suggestions on spelling, grammar and wording for their profile. Those who got the help were hired about 8% more often, within a range of 3% to 13%. They got 10% higher pay, too. Employers rated the people they hired just as highly afterward. The authors' reading: clearer writing helped employers see what people could do. The platform funded the authors' work [@wiles-2025].

Chat AI that writes the whole text is different. Two 2025 studies looked at one freelance platform after it added an AI letter writer in April 2023 [@cui-2025; @galdin-silbert-2025]. Both are preprints, not yet peer-reviewed.

The first studied 5 million cover letters to over 100,000 jobs. Having the tool raised callbacks by 0.43 per 100 letters. For people who chose to use it, the estimate was 3.56 more callbacks per 100 letters. Neither estimate was certain enough to rule out chance, and the gain faded after two months. The authors found no evidence of a change in overall hiring [@cui-2025].

Before the tool, a letter that closely matched the job post went with more callbacks. After the tool, that link was 51% weaker. The link between a close match and a job offer fell 79%. Employers leaned a little more on each worker's past reviews on the platform. Longer editing of the AI draft went with a higher chance of a job offer. Most AI letters were sent with little or no editing [@cui-2025].

The second studied about 2.7 million applications to coding jobs. Before chat AI, employers were willing to pay more for workers whose applications fit the job closely. After chat AI, that premium mostly disappeared. The authors then used a model of the market to test an extreme case: applications that tell employers nothing about how able a worker is. In that case, the top fifth of workers were hired 19% less often. The bottom fifth were hired 14% more often. Those two numbers come from the model, not from counting real hires [@galdin-silbert-2025]. What this means for cover letters: [Do cover letters still matter now that AI writes them?](cover-letters-after-ai.md)

For you, fixing errors in your own wording helped in a large test. A letter that only echoes the job post now tells employers less.

## Does AI wording help with AI screeners?

In one lab test, it did, when the screener was the same AI. A 2025 study took 2,245 real resumes and had AI models rewrite each summary section. Each AI model then picked between the person's own summary and one the same model wrote. In the updated June 2026 version, eight of the nine models picked their own version more often. In simulated hiring for 24 jobs, applicants using the screener's own AI were 23% to 60% more likely to be shortlisted. Simple changes to the screener's instructions cut this preference by more than half [@xu-2025]. That is a lab test, not a real employer's system.

An AI screener's preference for its own wording cuts both ways for job seekers. An AI screener may like AI wording, while a human reader may dislike it. Clear, specific lines are our advice for both; no study tests it.

## What words make writing sound like AI?

Some words became much more common after chat AI arrived. A 2025 study counted words in over 15 million science paper summaries from 2010 to 2024. "Delves" appeared 28 times more often in 2024 than its earlier trend predicted. "Underscores" rose 13.8 times and "showcasing" 10.7 times. Common words like "crucial" and "potential" also jumped. The authors estimate at least 13.5% of 2024 summaries were processed with AI [@kobak-2025]. That study is about science writing, not resumes. It shows which words AI overuses, not whether employers notice them.

Words like "delve," "showcase" and "pivotal" add no facts. Cutting them makes a line clearer, whoever wrote it.

## What we don't know

- How often employers run AI detectors on resumes. We found no study measuring it.
- How well detectors work on resumes, which are short and full of lists. No study found that tests this.
- Whether hiring managers who say they can tell actually can. The surveys report what they say.
- Whether today's chat AI helps or hurts resumes in real hiring. The large field test used spelling and grammar help, in 2021 [@wiles-2025]. The chat AI study covered cover letters on one platform [@cui-2025].
- Whether the freelance platform results hold for regular jobs. Both studies come from one platform [@cui-2025; @galdin-silbert-2025].
- We searched the web, arXiv and news in October 2026 for studies on these gaps, including surveys of employer detector use.

## What helps

- Use AI for wording, not facts. Fixing errors and making lines clearer raised hires in the largest test [@wiles-2025].
- Put in your own facts and numbers. AI can't know them, and managers name vague lines as AI signs [@resume-genius-2026].
- Edit what AI drafts. More editing time went with more job offers, in one study [@cui-2025].
- Cut generic, vague and inflated lines. Hiring managers name these as AI signs [@resume-genius-2026].
- Be able to explain every line. Anything on the page can come up in an interview; that is common advice, not a study finding.
- Never let AI invent a skill, job or number. That is a false claim, whoever typed it.

How we grade evidence: [How we research](methods.md). How AI screeners treat applicants: [Is AI resume screening biased?](ai-resume-screening-bias.md). Whether software rejects most resumes: [Do hiring systems reject most resumes?](ats-rejection-myth.md). Keeping your resume out of AI training: [Keep your chats out of AI training](keep-chats-out-of-ai-training.md).

## How CEZ Job Finder uses this

- AI rewords your resume for each job, from your own facts only. It never adds a skill, job or number you didn't give.
- You confirm every changed line before you get the resume.
- A check flags overused AI words like "delve" and "showcasing", from a list built on studies like the one above. The list is in the program's [resume checks](../../resume/lint.py).
- A posting term goes in only where your experience backs it.

CEZ Job Finder is a free job-search app for Windows and Mac: [see how CEZ Job Finder works](https://jobs.enrriquez.com/).

## Changes

- October 2026 - reworded the two cover letter studies. The hiring shifts by ability come from an extreme case in the authors' model, and both callback estimates were too weak to rule out chance; the numbers are unchanged.
