---
title: "Is AI resume screening biased? What the studies show"
description: AI models judge resumes differently by name, gender, age and disability in tests. The direction changes by model and test. Real-hiring data is scarce.
published: 2026-10-03
modified: 2026-10-03
status: draft
og_title: "Is AI resume screening biased? What the studies show"
uncited:
  - "No study found that measures"
---
**Short answer**

- AI models judge identical resumes differently by name, gender, age or disability (Lab study, many tests) [@wilson-caliskan-2024; @an-2025; @rozado-2026].
- Who gets favored flips between models, versions and test designs (Lab study, preprints) [@gao-2026; @chen-xiao-2026].
- One large real-hiring data set: one vendor's game tests, not resumes; some groups shut out more (Real records) [@bommasani-2026].
- No resume trick shown to beat a biased screener. Apply widely.

## Do AI resume screeners treat people differently by name?

Yes, in lab tests. Researchers give AI models resumes that are the same except for the name. The models then pick, rank or score them differently.

In a 2024 test, three AI text-matching models ranked over 500 resumes with 120 names added [@wilson-caliskan-2024]. The models favored names linked with white people in 85.1% of tests [@wilson-caliskan-2024]. Names linked with Black people were favored in 8.6% of tests [@wilson-caliskan-2024]. Resumes with Black men's names were disadvantaged in up to 100% of cases in some comparisons [@wilson-caliskan-2024].

The same study's gender result was corrected in August 2026. Another team tried to repeat the study and found a coding error [@wilson-caliskan-2024]. After the fix, female names were favored in 51.9% of tests and male names in 11.1% [@wilson-caliskan-2024]. The published 2024 paper says the reverse. Many articles still repeat the old gender result. The race results held up when repeated [@wilson-caliskan-2024].

A larger 2025 study scored about 361,000 made-up resumes with five AI models [@an-2025]. Four of the five models scored women or Black applicants higher on average [@an-2025]. Black men were the exception: GPT-3.5 scored them 0.3 points lower than white men, out of 100 [@an-2025]. The gaps were small per resume. With a pass mark of 80, Black men's chance of passing fell 1.4 percentage points [@an-2025]. Black women's chance rose 1.7 points and white women's rose 1.4 [@an-2025].

For you, these tests show what models can do with a name. They do not show what any employer's system does.

## Does the bias always go against the same people?

No. The direction changes with the model, its version and how the test is built.

A 2026 study tested 22 AI models on 70 jobs, swapping names between matched resumes [@rozado-2026]. Every one of the 22 models picked the female-named resume more often [@rozado-2026]. Overall, female names won 56.9% of picks [@rozado-2026].

The same study found a stronger pull from order. The resume listed first won 63.5% of picks [@rozado-2026]. Order mattered in 21 of the 22 models [@rozado-2026]. When each resume was rated alone, the gender gap almost vanished [@rozado-2026].

A 2026 preprint tested 14 models released from 2023 to 2026 [@gao-2026]. GPT-3.5, from 2023, favored white names by 2.12 points [@gao-2026]. Every model from 2024 on showed no race gap or favored Black names [@gao-2026]. The study is not yet peer-reviewed.

Gao's gender results moved the same way. GPT-3.5 favored men by 1.92 points [@gao-2026]. Ten of 12 later models favored women, and the other two showed no gap [@gao-2026].

Test design can create a gap or hide one. A 2026 preprint asked nine open models to choose between two resumes [@chen-xiao-2026]. Forced to choose, the models looked biased [@chen-xiao-2026]. Allowed to call a tie, they did so in at least 94% of cases [@chen-xiao-2026].

For you, a headline that says "AI favors group X" describes one test. Another model or test may show the opposite.

## Does removing your name stop the bias?

Not reliably, in one preprint. The team removed names and other personal details from 620 made-up resumes [@chen-xiao-2026]. Nine AI models still guessed the person's ethnicity correctly 75.7% of the time on average [@chen-xiao-2026]. Clues like a school, a language or a club gave it away [@chen-xiao-2026].

The same preprint found the score differences between groups were very small [@chen-xiao-2026]. So the models could tell, but in that test barely acted on it.

For you, leaving details off your resume may not hide them from a model. It also has a cost: those lines may be real experience.

## Are other groups affected - age, disability?

Lab tests say yes. A 2026 conference paper tested 10 open AI models, each in a base and a trained version [@bone-2026]. Age showed through the graduation year [@bone-2026]. The trained versions were 3.6% less likely to call back older applicants [@bone-2026]. That held in 8 of the 10 models [@bone-2026].

A 2024 test gave GPT-4 one resume and the same resume plus disability-related awards [@glazko-2024]. GPT-4 ranked the disability version first in only 15 of 60 trials [@glazko-2024]. An autism-related version came first in none of 10 trials [@glazko-2024]. A version of GPT-4 told to avoid disability bias did better, at 37 of 60 [@glazko-2024].

Anthropic's own 2023 preprint tested its Claude 2.0 model on made-up decisions, including job offers [@tamkin-2023]. The model favored women and non-white people, and was less positive about people over 60 [@tamkin-2023]. Telling the model that discrimination is illegal cut the gaps [@tamkin-2023].

For you, age and disability can count against you in some models' choices. Those tests use made-up applicants, not real hiring.

## What happens with real applicants?

Real-hiring data is rare, and the largest set is not about resumes. A 2026 study looked at 4.2 million applications scored by one vendor's game-based tests [@bommasani-2026]. The applications came from 3.4 million people, to 1,746 jobs at 156 employers [@bommasani-2026].

In 10.62% of jobs, the tests recommended Black applicants at a clearly lower rate [@bommasani-2026]. 25.87% of Black applicants' applications went to those jobs [@bommasani-2026]. Some people were turned down everywhere. Of those who applied to 10 jobs, 4% were not recommended for any of them [@bommasani-2026]. That is more often than chance would give, because employers used the same tool [@bommasani-2026].

The study is real records, so it shows a link, not a cause. It covers one vendor's tests, not AI reading resumes.

People also follow a biased AI. In a 2025 study, 528 people screened resumes with help from a simulated AI [@wilson-2025]. With no AI or a neutral AI, people picked groups about equally [@wilson-2025]. With a biased AI, they followed its lean up to 90% of the time [@wilson-2025]. So "a person makes the final call" does not remove the bias.

For you, the same tool used by many employers can shut the same people out many times. Applying through different routes spreads that risk.

## What real cases are there?

Two cases are often cited, and neither proves an AI broke a law.

In 2018, Reuters reported Amazon dropped a resume-ranking tool it had built [@dastin-2018]. The tool reportedly marked down resumes with the word "women's" [@dastin-2018]. It learned from 10 years of resumes, mostly from men [@dastin-2018]. Sources said recruiters never relied on it alone [@dastin-2018]. That account comes from unnamed sources in a news report.

In 2023, iTutorGroup settled a US agency lawsuit for $365,000 [@eeoc-itutorgroup-2023]. The agency alleged its software rejected women 55 and over and men 60 and over [@eeoc-itutorgroup-2023]. That was a fixed age rule, not AI.

Mobley v. Workday is a US lawsuit still in progress. The plaintiffs allege Workday's AI screened out older applicants [@mobley-2025-order, p. 3]. Workday denies the claims, and nothing has been proven as of October 2026 [@lawyer-monthly-2026]. More on that case: [Do hiring systems reject most resumes?](ats-rejection-myth.md).

## What do the laws say?

As of October 2026, a few places set rules. This is general information, not legal advice.

- **New York City**: employers using these tools need a yearly bias audit, a public summary and notice to applicants [@nyc-ll144]. Enforced since July 2023 [@nyc-ll144]. A 2024 check of 391 employers found only 18 posted audits [@wright-2024]. The state comptroller called the city's enforcement ineffective in December 2025 [@nys-comptroller-2025].
- **Illinois**: since January 2026, using AI that has a discriminatory effect in hiring is a civil-rights violation [@il-hb3773]. Employers must give notice [@il-hb3773].
- **Colorado**: from January 2027, applicants get notice and a plain explanation after a rejection [@co-sb26-189]. They can correct wrong data and ask for a human review [@co-sb26-189].
- **European Union**: AI that filters applications is high-risk under the AI Act [@eu-ai-act]. Those rules now start in December 2027 [@eu-omnibus-2026].
- **US federal**: the anti-discrimination laws are unchanged. A 2025 executive order tells agencies to move away from "disparate impact" cases [@eo-14281]. Those are cases about unequal results without intent.

For you, in New York City, Illinois and soon Colorado, you can ask whether AI is used.

## What we don't know

- How often employers let AI screen resumes without a person. No study found that measures it across employers.
- Whether lab results match real hiring. Almost all evidence uses made-up resumes.
- Which way today's models lean. Results changed between model versions within two years [@gao-2026].
- How much the test design drives the result [@chen-xiao-2026; @rozado-2026].
- Whether AI is more or less biased than human screeners in real hiring. We found no study that compares them directly.

## What helps

- Apply widely. When many employers use one tool, one "no" can repeat everywhere [@bommasani-2026].
- Keep your resume accurate, relevant and easy to read. No resume trick has been shown to beat a biased screener.
- Use your rights where they exist: notice in New York City and Illinois, an explanation in Colorado from 2027 [@nyc-ll144; @il-hb3773; @co-sb26-189].
- Remember bias in a screener is the employer's problem, not a flaw in you.

How we grade evidence: [How we research](methods.md). More articles: [Research](index.md).

## How CEZ Job Finder uses this

- Ranks jobs by the posting and your search settings, never by your name, age, gender or background.
- Never invents or changes a fact on your resume to get past a screener.
- Lists every match from your search, so you can apply widely.
