---
title: "Is AI resume screening biased? What the studies show"
description: AI models judge resumes differently by name, gender, age and disability in tests. The direction changes by model and test. Real-hiring data is scarce.
published: 2026-10-03
modified: 2026-10-04
status: published
og_title: "Is AI resume screening biased? What the studies show"
uncited:
  - "No study found that measures"
  - "We found no study showing"
  - "We searched the web, arXiv and news"
---
**Short answer**

- AI models judge identical resumes differently by name, gender, age or disability (Lab study, many tests) [@wilson-caliskan-2024; @an-2025; @rozado-2026; @bone-2026; @glazko-2024].
- Who gets favored flips between models, versions and test designs (Lab study, preprints) [@gao-2026; @chen-xiao-2026].
- One large real-hiring data set: one vendor's game tests, not resumes; some jobs' tests passed fewer Black applicants (Real records) [@bommasani-2026].
- No study found showing a resume change protects you from a biased screener. Apply widely.

## Do AI resume screeners treat people differently by name?

Yes, in many lab tests, though some tests find no gap. Researchers give AI models resumes that are the same except for the name. The models then often pick, rank or score them differently.

In a 2024 test, three AI text-matching models ranked over 500 resumes with 120 names added. The models favored names linked with white people in 85.1% of tests. Names linked with Black people were favored in 8.6% of tests. White men's names beat Black men's names in 100% of tests [@wilson-caliskan-2024].

The same study's gender result was corrected in August 2026. Another team tried to repeat the study and found a coding error. The authors' note says the gender numbers should be swapped. Swapped as the note directs, female names were favored in 51.9% of tests and male names in 11.1%. The published 2024 paper still prints the reverse. The race results held up when repeated [@wilson-caliskan-2024].

A larger 2025 study scored about 361,000 made-up resumes with five AI models. Four of the five models scored women or Black applicants higher on average. Black men were the exception: most of the models scored them lower than white men. GPT-3.5, for example, scored Black men 0.3 points lower, out of 100. With a pass mark of 80, GPT-3.5 cut Black men's chance of passing by 1.4 percentage points. In that test, Black women's chance rose 1.7 points and white women's rose 1.4. The gaps look small per resume, but the authors call them economically significant across many applicants [@an-2025].

In 2024, Bloomberg ran its own test of GPT-3.5 and GPT-4. GPT ranked eight equally qualified resumes, 1,000 times for each of four jobs. Some groups' names came first less often than an even share of one in eight. For a software engineer job, GPT-3.5 put Black women's names first 11% of the time. Bloomberg published its method and code. OpenAI said the test may not reflect how its customers use the models [@bloomberg-2024].

For you, these tests show what models can do with a name. They do not show what any employer's system does.

## Does the bias always go against the same people?

No. The direction changes with the model, its version and how the test is built.

A 2026 study tested 22 AI models on 70 jobs, swapping names between matched resumes. Every one of the 22 models picked the female-named resume more often. Overall, female names won 56.9% of picks [@rozado-2026].

The same study found a stronger pull from order. The resume listed first won 63.5% of picks. Order mattered in 21 of the 22 models. When each resume was rated alone, the gender gap almost vanished [@rozado-2026].

A 2026 preprint tested 14 models released from 2023 to 2026. GPT-3.5, from 2023, gave white names a 2.12 percentage point higher call-back rate. Every model from 2024 on showed no race gap or favored Black names [@gao-2026]. The study is not yet peer-reviewed.

Gao's gender results moved the same way. GPT-3.5 gave men a 1.92 percentage point higher call-back rate. Ten of 12 later models favored women, and the other two showed no gap [@gao-2026].

Test design can create a gap or hide one. A 2026 preprint asked nine openly released AI models to choose between two resumes. Forced to choose, the models looked biased. Allowed to call a tie, most models did so in at least 94% of cases [@chen-xiao-2026].

A headline that says "AI favors group X" describes one test. Another model or test may show the opposite.

## Does removing your name stop the bias?

Not reliably, in one preprint. The team built 620 made-up resumes with no names. They added clues to a person's background: community groups, activities and interests. Some clues were plain and some were faint. Nine AI models guessed the background every time when the clue was plain. With faint clues, they guessed right 9% to 69% of the time [@chen-xiao-2026]. The test covered five groups in an Australian setting.

The same preprint found the score differences between groups were very small [@chen-xiao-2026]. So the models could often tell, but in that test barely acted on it.

In practice, leaving your name off may not hide your background if other lines point to it. Cutting those lines has a cost: they may be real experience.

## Are other groups affected - age, disability?

Lab tests say yes. A 2026 conference paper tested 10 openly released AI models, each before and after extra training. That extra training is how makers turn a raw model into a chat assistant. Age showed through the graduation year. After training, the models were 3.6% less likely to call back older applicants than before. Older meant over 45 in that test. The drop held in 8 of the 10 models [@bone-2026].

A small 2024 test gave GPT-4 one resume and the same resume plus disability-related awards. The version with awards was the stronger resume, so it should have come first. GPT-4 ranked the disability version first in only 15 of 60 trials. An autism-related version came first in none of 10 trials. A custom GPT-4 given disability-justice instructions did better, at 37 of 60 [@glazko-2024]. Each disability got only 10 trials, on a GPT-4 version from early 2024.

Anthropic's own 2023 preprint tested its Claude 2.0 model on made-up decisions, including job offers. The model favored women and non-white people, and was less positive about people over 60. Those gaps were much smaller when the model had to infer the person from a name. Telling the model that discrimination is illegal cut the gaps [@tamkin-2023].

Age and disability can count against you in some models' choices. Those tests use made-up applicants, not real hiring.

## What happens with real applicants?

Real-hiring data is rare, and the largest set is not about resumes. A 2026 study looked at 4.2 million applications scored by one vendor's game-based tests. The applications came from 3.4 million people, to 1,746 jobs at 156 employers. The data run from December 2018 to December 2022, before chat AI was common [@bommasani-2026].

In 10.62% of jobs, the tests recommended Black applicants at a rate below the US "four-fifths" benchmark. That benchmark flags a group passing at under 80% of the top group's rate. 25.87% of Black applicants' applications went to those jobs [@bommasani-2026].

A separate finding concerns individual people, not groups. Some people were turned down everywhere. Of those who applied to 10 jobs, 4% were not recommended for any of them. That happened more often than chance would give. The employers all used the same vendor, and a person's game results were reused across applications [@bommasani-2026].

The study is real records, so it shows a link, not a cause. It covers one vendor's tests, not AI reading resumes.

One field experiment compared an algorithm with human resume screeners at one company. For a random share of applicants to a software engineer job, the algorithm replaced the human screeners. Applicants it picked that people would have passed over were 14% more likely to pass interviews and get an offer than those both picked. The algorithm picked more people human screeners tended to pass over, including women and racial minorities [@cowgill-2020]. That was one job at one company, with an older kind of algorithm, not today's chat AI. The paper is a working paper, not peer-reviewed.

People also follow a biased AI. In a 2025 study, 528 people screened resumes with help from a simulated AI. With no AI or a neutral AI, people picked groups about equally. With a biased AI, they followed its lean up to 90% of the time [@wilson-2025]. So "a person makes the final call" may not remove the bias. That study used a simulated AI in a lab, not a real hiring tool.

Our reading: when many employers use one tool, the same person can be shut out many times. Applying through different routes may spread that risk.

## What real cases are there?

Three cases are often cited, and none has proven an AI broke a law.

In 2018, Reuters reported Amazon dropped a resume-ranking tool it had built. The tool reportedly marked down resumes with the word "women's". It learned from 10 years of resumes, mostly from men. Sources said recruiters looked at its ratings but never relied on them alone. Amazon said its recruiters never used the tool to evaluate candidates [@dastin-2018]. That account comes from unnamed sources in a news report.

In 2023, iTutorGroup settled a US agency lawsuit for $365,000. The agency alleged its software rejected women 55 and over and men 60 and over [@eeoc-itutorgroup-2023]. That was a fixed age rule, not AI.

Mobley v. Workday is a US lawsuit still in progress. The plaintiffs allege Workday's screening tools discriminated by race, age and disability [@mobley-2026-order, p. 1]. In May 2025 the court let the age claim go forward for a wider group of applicants, at a preliminary stage [@mobley-2025-order]. In June 2026 the court let California state-law claims and a disability claim go on. The same order dismissed a newly added race claim by one plaintiff [@mobley-2026-order, p. 11]. In September 2026 the plaintiffs asked to add four groups to the case, with a hearing set for March 2027. Workday denies the claims, and nothing has been proven as of October 2026 [@lawyer-monthly-2026]. More on that case: [Do hiring systems reject most resumes?](ats-rejection-myth.md).

## What do the laws say?

As of October 2026, a few places set rules, and some may change. This is general information, not legal advice.

- **New York City**: employers using these tools need a yearly bias audit, a public summary and notice to applicants. Enforced since July 2023 [@nyc-ll144]. A 2024 check of 391 employers found only 18 posted audits [@wright-2024]. The state comptroller called the city's enforcement ineffective in December 2025 [@nys-comptroller-2025].
- **California**: since October 2025, state rules say an automated hiring tool can break anti-discrimination law if it harms people by race, gender, disability or another protected trait. Employers must keep the tool's data for four years. Whether an employer tested its tool for bias can count in a claim [@ca-crc-ads-2025].
- **Illinois**: since January 2026, using AI that has a discriminatory effect in hiring is a civil-rights violation. Employers must give notice [@il-hb3773].
- **Colorado**: from January 2027, applicants get notice and a plain explanation after a rejection. They can correct wrong data and ask for a human review. The state attorney general enforces it and still has to write the detailed rules [@co-sb26-189]. A December 2025 executive order set up a federal task force to challenge state AI laws, and it names Colorado's [@eo-14365].
- **European Union**: AI that filters applications is high-risk under the AI Act [@eu-ai-act]. Those rules now start in December 2027 [@eu-omnibus-2026].
- **US federal**: a 2025 executive order tells agencies to move away from "disparate impact" cases [@eo-14281]. Those are cases about unequal results without intent. Private lawsuits like Mobley v. Workday still use that idea [@mobley-2026-order, p. 2].

In New York City and Illinois, employers must tell you when they use these tools. From 2027, Colorado employers must also explain a rejection. In New York City you can ask for another way to be assessed or an accommodation [@nyc-ll144].

## Which studies found what?

The table sums up the main AI studies in this article. Most rows are lab tests: AI models, or people helped by one, judging test resumes, not real hiring. The last two rows look at real applicants: one company's algorithm, and one vendor's game tests, not resumes.

| Study | Year | Models | Result | Evidence |
|---|---|---|---|---|
| Wilson and Caliskan | 2024 | 3 text-matching models | White-linked names favored in 85.1% of tests; gender result corrected in 2026 [@wilson-caliskan-2024] | Lab study |
| Bloomberg | 2024 | GPT-3.5, GPT-4 | Some groups' names ranked first less often than one in eight [@bloomberg-2024] | Lab study |
| Glazko and others | 2024 | GPT-4 | The disability version, the stronger resume, ranked first in only 15 of 60 trials [@glazko-2024] | Lab study |
| An and others | 2025 | 5 models | Four of five scored women or Black applicants higher on average; most scored Black men lower than white men [@an-2025] | Lab study |
| Wilson and others | 2025 | A simulated AI, 528 people | People followed a biased AI up to 90% of the time [@wilson-2025] | Lab study |
| Rozado | 2026 | 22 models | Female names won 56.9% of picks; the first resume listed won 63.5% [@rozado-2026] | Lab study |
| Gao and others | 2026 | 14 models | GPT-3.5 favored white names; models from 2024 on showed no race gap or favored Black names [@gao-2026] | Lab study, not yet peer-reviewed |
| Chen and Xiao | 2026 | 9 open models | Forced to choose, models looked biased; allowed a tie, most tied in at least 94% of cases [@chen-xiao-2026] | Lab study, not yet peer-reviewed |
| Bone and others | 2026 | 10 open models | After extra training, 3.6% less likely than before to call back applicants over 45, in 8 of 10 models [@bone-2026] | Lab study |
| Cowgill | 2020 | An older screening algorithm, one company | Picked more women and minorities than human screeners did, for one job [@cowgill-2020] | Small study, not yet peer-reviewed |
| Bommasani and others | 2026 | One vendor's game tests, not resumes | In 10.62% of jobs, Black applicants were recommended below the four-fifths benchmark [@bommasani-2026] | Real records |

Only one row, one job at one company with an older algorithm, shows a real employer's system reading resumes.

## What we don't know

- How often employers let AI screen resumes without a person. No study found that measures it across employers. Surveys ask employers, but they report what employers say.
- Whether lab results match real hiring. Almost all evidence uses made-up resumes.
- Which way today's models lean. Results changed between model versions within two years [@gao-2026].
- How much the test design drives the result [@chen-xiao-2026; @rozado-2026].
- Whether AI is more or less biased than human screeners. We found one field test, at one company, with an older algorithm [@cowgill-2020].
- Whether any resume change protects you. We found no study showing that one does.
- We searched the web, arXiv and news in October 2026 for studies on these gaps.

## What helps

- Apply widely. When many employers use one tool, one "no" can repeat everywhere [@bommasani-2026].
- Keep your resume accurate, relevant and easy to read. We found no study showing a resume change that beats a biased screener.
- Use your rights where they exist: notice in New York City and Illinois, an explanation in Colorado from 2027 [@nyc-ll144; @il-hb3773; @co-sb26-189].
- Remember bias in a screener is the employer's problem, not a flaw in you.

How we grade evidence: [How we research](methods.md). More articles: [Research](index.md). Whether an AI-written resume hurts: [Can employers tell if AI wrote your resume?](ai-written-resumes.md). Keeping your resume out of AI training: [Keep your chats out of AI training](keep-chats-out-of-ai-training.md).

## How CEZ Job Finder uses this

- Ranks jobs by the posting and your search settings, never by your name, age, gender or background.
- Never invents or changes a fact on your resume to get past a screener.
- Checks for new jobs from your search every day, so you can apply widely.

CEZ Job Finder is a free job-search app for Windows and Mac: [see how CEZ Job Finder works](https://jobs.enrriquez.com/).
