---
reviewed: 2026-10-04
verdict: revise
reviewer: fresh AI session, bead plan-xsy.68 (no drafting context; sources opened and the count rerun before the draft was read)
---
# Review: Do cover letters still matter now that AI writes them? (`cover-letters-after-ai.md`)

Verdict **revise**: 1 high, 8 medium, 12 low findings, all open. Every number taken from the
two economics papers, the ResumeGo page and the Insight Global report matches its source, and
the own count reruns byte-identical. The problems: the "2025" ResumeLab survey was already on
its page in February 2020, before chat AI, so it can't speak to letters "now"; the Cui callback
gain is weakly significant and faded after two months, which the draft leaves out; the short
answer misreads a weaker correlation as fewer callbacks; "most forms still ask" rests on a
sample that is two-thirds Greenhouse, whose default form carries a letter box, while a much
larger count (the job search's own, about half of 402,117 postings) is not mentioned; Lever's
open box invites a cover letter by name, so "0 of 19" understates; the Galdin model numbers are
an extreme scenario, not a forecast; one contrary lab result is missing; and "career guides
agree" rests on one guide.

## Sources, read before the draft (all opened 2026-10-04, downloads in `~/.cache/plan-xsy.68/`)

| id | What it actually supports | Limits |
|---|---|---|
| resumego-2020 | ResumeGo page "Cover Letters: Just How Important Are They?", Peter Yang (CEO). Field experiment July 15, 2019 - January 10, 2020; 7,287 fictitious applications to openings on ZipRecruiter, Glassdoor, Indeed. Group 1 no letter ("left blank or filled in simply with 'N/A'"), Group 2 generic, Group 3 tailored. Callbacks within 30 days (chart image, read): 10.7% / 12.5% / 16.4%; text: tailored "53% higher callback rate" than none (16.4/10.7 = 1.53) | Company "offers resume writing services" (page's words; letter writing not stated). No group sizes, no job types, no test for chance, no statement that groups were assigned at random, no peer review. Pre-chat-AI. "N/A" put in letter fields when present, required or not |
| resumego-2020-survey | Same page, 236 recruiters + hiring managers, yes/no (svg images): read letters at all 87/13; "materially influence your decisions on who to interview or hire" 65/35; regularly reject solely for poor letter 24/76; value tailored significantly more 81/19; hard/easy to tell generic 22/78; punish missing optional letter 26/74. Time reading (chart): 0-10 s 32%, 10 s-1 min 52%, 1-5 min 16%, over 5 min 0 | Vendor survey; recruitment method + dates not given; self-report |
| resumelab-2025 | Archive copy 2026-03-11 of resumelab.com page. OnePoll for ResumeLab, 200 recruiters, HR specialists, hiring managers; online self-report after screening; "some questions and responses have been rephrased". 83% letter important to decision; 74% prefer applications with a letter; 77% prefer candidates who sent an optional letter; 72% expect one even if optional; 13% will process an application missing a required letter; 77% read even if not required; 74% read when required; motivation to join 63% top use; candidates attach optional letter 35%, required 38% (recruiters' estimate). JSON-LD `datePublished` 2019-04-24, `dateModified` 2025-12-09. **The same survey and every figure above is in the archive copy of 2020-02-27 (`dateModified` 2020-02-12); the copy of 2019-12-06 does not have it** -> survey ran about Dec 2019 - Feb 2020 | Vendor survey (sells a letter builder); dates, wording, sampling not given; pre-ChatGPT despite the 2025 page date. Internal oddity: more say they read optional letters (77%) than required ones (74%) |
| cui-2025 | arXiv v2 (12 Nov 2025; PDF dated 13 Nov), latest; author-site copy same. Freelancer.com "AI Bid Writer" launched 2023-04-19; 8 months, PHP + Internet Marketing, 5 million letters, 100,000+ jobs. 84.9% of bids from plans with access; 62% of eligible used it at least once; 17% of letters AI-assisted (p. 2). Access: tailoring +0.16 SD, callbacks +0.43 pp ITT (about 6% of 7.02% base); usage +3.56 pp LATE (51% of base) - "significant at the 10% level but not at the 5% level"; dynamic effect "tapered off after two months" (pp. 2-3, 25). Tailoring = TF-IDF keyword overlap. Correlation tailoring-callback fell 51%, tailoring-offer 79%; review-score-callback rose 5%; "no evidence of changes" in hiring, interviewing, completion, "a preliminary result" (p. 3). Over 75% of AI letters finalised within one minute of clicking, about 5% after 5+ minutes (p. 33); editing = click-to-submit time. 1 SD more editing (3.5 min) -> +0.31 pp offer, about 52% of 0.6% offer rate, worker fixed effects, "should not be interpreted as ... causal" (p. 35). Footnote: Galdin and Silbert first measured letter-post similarity on the same platform | Preprint; one freelance platform, two job categories; callback effect weak + temporary; offers too imprecise (p. 3) |
| galdin-silbert-2025 | arXiv v1 (11 Nov 2025) = only arXiv version; "latest version" link (author site, 14 Nov 2025) has the same abstract + numbers. Job Market Paper. Sample (p. 13): roughly 61,000 coding job postings (fixed-price, hired + paid, one worker, 25+ word description), about 2.7 million applications, 212,000 workers, Jan 2021 - Jul 2024, split at ChatGPT release. Pre-LLM: 1 SD higher signal = same hire chance as a $26 lower bid (multinomial logit, p. 3). After: willingness to pay "falls sharply", signals no longer predict completion conditional on hire (p. 3). Signal = an LLM-based tailoring measure. Counterfactual "in which LLMs render written applications useless in signaling" -> top quintile hired 19% less, bottom quintile 14% more (abstract) | Preprint; same platform as Cui; the 19%/14% is a simulated extreme (no signal at all), not observed; sample is jobs that hired someone |
| insight-global-2025 | PDF p. 9: 88% "say they can tell when candidates are using AI to help with applications, cover letters, or resumes"; 54% would care / 46% would not care "if a job candidate applied with a resume or cover letter that was written by AI" (page rendered to image to pair numbers with labels). p. 14: Atomik Research online survey, 1,005 US HR/TA executives at firms with 100+ staff, fieldwork Oct 17-22, 2024, +/-3 pts | Vendor survey (staffing firm); question wording not published; resume and letter asked together |
| mit-capd-cover-letters | MIT CAPD guide: letter aimed at a specific position; interest "genuine and specific"; "no longer than one page"; intro "Specify why you are interested"; "Try not to simply repeat your resume in paragraph form" | Convention; one career office; undated |
| mit-capd-ai-cover-letters | MIT CAPD "Using AI for cover letters": AI as brainstorm partner + editor; limit generated content; recruiters spot "em dashes", formulaic, over-polished letters (no evidence given); AI can "oversell your qualifications" and hallucinate; "That story needs to come from you" | Convention; one career office; its AI-tell claims are unsourced |
| wiles-2025 | arXiv 2301.08083 abstract (Management Science version via DOI 10.1287/mnsc.2024.04528, redirects): field experiment, nearly half a million jobseekers, algorithmic writing assistance on resumes, hires +8%, no drop in employer satisfaction | Not generative AI (registry: spelling + grammar suggestions); profile text, not letters |

No text in any source addressed an AI (all nine scanned, plus the three found below).

### Searched for newer or contrary work (2026-10-04)

Queries: "cover letter field experiment callbacks study 2025 2026 generative AI applicants" (extended),
"correspondence study motivation letter effect on callback rate peer-reviewed", "survey hiring
managers read cover letters 2025 methodology AI-written cover letters". Found and opened:

- **Kleine-Allekotte 2024, "Spot the difference! Recruiter reaction to ChatGPT in cover letters"** (Tilburg University MSc thesis, submitted April 7, 2024; arno.uvt.nl/show.cgi?fid=176589). 86 raters (285 responses, 199 dropped; recruited on LinkedIn, word of mouth, SurveyCircle; screened only by self-report) each rated six letters (self-written / ChatGPT-enhanced / ChatGPT-created x native / non-native writer). Mean hireability before being told AI might be involved: self-written 2.38-2.74, enhanced 3.28-3.43, created 3.66-3.69; after the reveal almost unchanged (created 3.69-3.71). Lab study, unpublished thesis, hypothetical decisions - weak, but it runs against the draft's framing that AI letters are judged worse.
- **freehire's own count** (github.com/strelov1/freehire, `internal/candidate/coverletter/AGENTS.md`, read 2026-10-04): "Of the 402,117 open postings whose apply form we have captured, 209,297 ask for a letter" (52%). Maker's docs, undated, no method; same figure already in `app/docs/resume/cover-letter.md`.
- **Lever's form**: a live Palantir Lever apply page (jobs.lever.co, fetched 2026-10-04) shows an "Additional information" box with the placeholder "Add a cover letter or anything else you want to share." A second Lever form in the sample (employer from the CSV) shows no such box. So some Lever forms ask for a letter by name in that box.
- Not usable: Resume Genius 2026 report (already `resume-genius-2026`) returns 403 to scripts; search snippets claim cover-letter figures in it - open in a browser before citing. Novoresume / TopResume / Crown Staffing pages = vendor blogs repeating other surveys. No peer-reviewed field test of letter vs no letter turned up, and none since 2020 - the draft's gap statement holds as far as this search reaches.

## Own measurement rerun

- `uv run app/web/letter_count.py ~/.cache/plan-xsy.67/raw.json > scratch/letters.csv` -> exit 0; `cmp` with `app/web/research/cover-letter-boxes-2026-10.csv`: identical.
- Summary printed: forms 143; box 96; required 2; optional 91; unknown 3; Greenhouse 96/85 (1 req, 83 opt, 1 unk); Workable 12/7 (5 opt, 2 unk); Ashby 15/3; Lever 19/0; Recruitee 1/1 (req). Employers: 104, 71 with a box on at least one form (counted from the CSV). All match the draft.
- The rerun needs `raw.json`, which sits only in `~/.cache/` (not committed), and the required flags were read live from postings that have since closed - see L9.

## Claim table

Article: 28 citation groups, 30 id-citations (9 distinct ids). Rows below: 64.

| # | Line | Claim | Source | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|
| 1 | 3 | Description: "a 2019 test found more callbacks with one" | resumego-2020 | needs caveat (ran Jul 2019 - Jan 2020; table calls it 2020) | low | "a 2019-20 test" (L1) |
| 2 | 3 | "most forms we checked had a letter box" | own | supported for this sample; see M3 | medium | M3 |
| 3 | 3 | "AI-written letters now tell employers less" | cui-2025 | supported (signal of all letters fell; one platform) | low | - |
| 4 | 24 | 96 of 143 US forms had a box, nearly all optional | own | supported (rerun); "Most forms still ask" overstated (box != ask; Greenhouse-heavy) | medium | M3 |
| 5 | 25 | Tailored beat none in 2019 test of 7,287; vendor, not peer-reviewed | resumego-2020 | supported; date (L1) | low | L1 |
| 6 | 26 | "letters that matched the job post went with callbacks 51% less" | cui-2025 | overstated / misread: the correlation fell 51%, not callbacks | medium | M2 |
| 7 | 27 | Own reasons + facts only you know still count; edit any AI draft | cui-2025; mit-capd-ai-cover-letters | needs caveat: Cui shows editing *correlates* with offers; "own reasons" is MIT convention, not Cui | low | keep labels; say "linked with" |
| 8 | 31 | 143 forms, US postings, October 2026 | own (data page) | supported | - | - |
| 9 | 31 | 96 of 143 (67%) had a box | own | supported (rerun) | - | - |
| 10 | 31 | Optional on 91, 2 required, 3 unknown (closed) | own | supported | - | - |
| 11 | 31 | 71 of 104 employers had a box | own | supported (CSV count) | - | - |
| 12 | 33 | "The form system mattered more than the job" | own | unsupported as stated: system and field not separated (field rates also range 10/26 to 8/9) | medium | M8 |
| 13 | 33 | Greenhouse 85/96, Ashby 3/15, Workable 7/12 | own | supported | - | - |
| 14 | 33 | Lever 0/19, "which offer an open 'additional information' box instead" | own | needs caveat: Lever's box placeholder says "Add a cover letter" | medium | M4 |
| 15 | 35 | No study found measures how often optional letters are opened | search | supported (none found here either) | - | - |
| 16 | 41 | "the one large test we found" | resumego-2020 | needs caveat: registry label field experiment = Small study; group sizes unknown | low | L2 |
| 17 | 41 | ResumeGo, a resume-writing company, 7,287 made-up applications, Jul 2019 - Jan 2020, three boards | resumego-2020 | supported | - | - |
| 18 | 41 | No / generic / tailored groups | resumego-2020 | supported; random assignment not stated | low | L3 |
| 19 | 41 | 10.7%, 12.5%, 16.4% within 30 days | resumego-2020 | supported (chart read) | - | - |
| 20 | 41 | "about half again as many as no letter" | resumego-2020 | supported (53%) | - | - |
| 21 | 44-48 | Bars figure caption + three values | resumego-2020 | supported | - | - |
| 22 | 51 | "ResumeGo sells resume and letter writing" | resumego-2020 | partly unsupported: page says "resume writing services" | low | L12 |
| 23 | 51 | No group sizes, job types, test for chance; pre-chat-AI | resumego-2020 | supported | - | add "or whether groups were random" (L3) |
| 24 | 53 | No peer-reviewed field test of letter vs none turned up | search | supported by this review's search too | - | - |
| 25 | 57 | Surveys by companies that sell letter help | both surveys | supported (ResumeLab sells a builder; ResumeGo resume writing) | low | L12 |
| 26 | 57 | 236 recruiters + hiring managers; 87% read letters | resumego-2020-survey | supported | - | - |
| 27 | 57 | 65% said letters had real weight in who gets an interview or job | resumego-2020-survey | supported ("materially influence") | - | - |
| 28 | 57 | 32% under 10 s; 52% 10 s - 1 min | resumego-2020-survey | supported (chart) | - | - |
| 29 | 57 | 26% hold a missing optional letter against an applicant | resumego-2020-survey | supported | - | - |
| 30 | 59 | "A 2025 survey of 200 US recruiters and hiring managers" | resumelab-2025 | **outdated / misdated**: same survey on the page by Feb 2020 | high | H1 |
| 31 | 59 | Run for ResumeLab, which sells a letter builder | resumelab-2025 | supported | - | - |
| 32 | 59 | 77% read letters even when not required | resumelab-2025 | supported; note 74% when required (odd) | low | H1 |
| 33 | 59 | The same share (77%) prefer applicants who sent an optional letter | resumelab-2025 | supported | - | - |
| 34 | 59 | Only 13% would still consider an application missing a required letter | resumelab-2025 | supported ("will process") | - | - |
| 35 | 59 | No survey dates or question wording | resumelab-2025 | supported, and page says answers were "rephrased" | low | H1 |
| 36 | 61 | Both report what recruiters say, not do | - | supported | - | - |
| 37 | 65 | "AI letters raised callbacks a little" | cui-2025 | needs caveat: usage effect only 10%-significant, faded after two months | medium | M1 |
| 38 | 65 | One freelance platform, AI letter writer April 2023 | cui-2025 | supported (April 19, 2023) | - | - |
| 39 | 67 | 5 million letters; 62% of those who could use it did | cui-2025 | supported ("at least once") | - | - |
| 40 | 67 | Access raised callbacks 0.43 per 100 from about 7 per 100 | cui-2025 | supported (ITT); missing the two-month fade | medium | M1 |
| 41 | 67 | Match-callback link 51% weaker; match-offer 79% | cui-2025 | supported ("match" = shared keywords, TF-IDF) | low | say "shared words with the post" once |
| 42 | 67 | Employers leaned a little more on past reviews | cui-2025 | supported (+5%) | - | - |
| 43 | 67 | "The study found no change in overall hiring" | cui-2025 | slightly overstated: "no evidence of changes", "preliminary" | low | L8 |
| 44 | 69 | Most AI letters went out unedited; 3 in 4 within a minute; ~5% 5+ min | cui-2025 | numbers supported; "unedited" is inferred from click-to-submit time | low | L4 |
| 45 | 69 | Longer editing went with more offers; not proof; preprint | cui-2025 | supported | - | - |
| 46 | 71 | 2.7 million applications to coding jobs | galdin-silbert-2025 | supported (61,000 postings, jobs that hired) | - | - |
| 47 | 71 | Before chat AI employers "paid more" for close fit; premium mostly gone; fit no longer predicted finishing well | galdin-silbert-2025 | "paid more" overstates a model-estimated willingness to pay; rest supported | low | L5 |
| 48 | 71 | Model: most able hired 19% less, least able 14% more; from the model | galdin-silbert-2025 | needs caveat: an extreme scenario where letters carry no signal; "most able" = top fifth | medium | M5, L7 |
| 49 | 73 | Both studies one platform; both point the same way | cui-2025; galdin-silbert-2025 | needs caveat: same platform's data, not two independent confirmations | low | L6 |
| 50 | 79 | 2024 vendor survey, 1,005 US hiring leaders, 88% can tell | insight-global-2025 | supported (fieldwork Oct 2024) | - | - |
| 51 | 79 | 54% would care if resume or letter AI-written | insight-global-2025 | supported | - | - |
| 52 | 77-81 | Section frames AI letters as judged worse | - | missing contrary lab evidence (raters scored ChatGPT letters highest) | medium | M6 |
| 53 | 89-95 | Study table rows | all | supported except ResumeLab year (H1), ResumeGo "Can show" should add "not whether the gap is chance" | high (via H1) | H1, L3 |
| 54 | 97 | Only letter-vs-none test is a pre-chat-AI vendor study | search | supported | - | - |
| 55 | 101-105 | What we don't know bullets | cui-2025; galdin-silbert-2025 | supported | - | - |
| 56 | 106 | "We searched the web, arXiv and Google Scholar in October 2026" | - | a method line, not an unknown; Scholar search not recorded in drafter notes | low | L11 |
| 57 | 110 | Write one when the form asks; tailored beat none | resumego-2020 | supported (with its limits) | - | - |
| 58 | 111 | "Career guides agree the reason must come from you" | mit-capd-ai-cover-letters | overstated: one guide cited for "guides agree" | medium | M7 |
| 59 | 112 | "Career guides agree on this too" (add, don't repeat) | mit-capd-cover-letters | overstated: one guide | medium | M7 |
| 60 | 113 | Spelling/wording help raised hires in a large test of profiles, not letters | wiles-2025 | supported | - | - |
| 61 | 114 | Longer editing went with more offers, one study | cui-2025 | supported | - | - |
| 62 | 115 | A guide warns AI can oversell or make up claims | mit-capd-ai-cover-letters | supported | - | - |
| 63 | 116 | Keep it to one page; convention | mit-capd-cover-letters | supported ("no longer than one page") | - | - |
| 64 | 122-125 | App behaviour: offered only with a box; motive verbatim; 250-400 words | app/docs/resume/cover-letter.md | supported (lines 9, 17, 18, 24) | - | - |

## Findings (all status: open)

- **H1 (high) - ResumeLab survey is from about 2020, not 2025.** The page's own markup says first published 2019-04-24; the Internet Archive copy of 2020-02-27 (`dateModified` 2020-02-12) already has OnePoll, 200 respondents and every figure the draft uses; the copy of 2019-12-06 has none of them. The draft calls it "a 2025 survey" (line 59) and "ResumeLab 2025" (table), in an article about letters *after* AI. Fix: "a survey of 200 ... run for ResumeLab around 2020 (page updated 2025)"; set `resumelab-2025` year 2020 (rename id to `resumelab-2020` if the registry allows; it is cited only by this draft), say in `sample` the survey was on the page by Feb 2020 with that snapshot; table row "ResumeLab 2020"; "Can't show" add "anything after chat AI". Optional: note that it reports more reading optional letters (77%) than required ones (74%), and that answers were "rephrased".
- **M1 (medium) - Cui's callback gain is weak and temporary; the draft omits both.** The usage effect is significant at 10% not 5%, and the access effect "tapered off after two months" (pp. 3, 25). Fix: after line 67 add "That gain faded after about two months." and "a little" stays. Same fact in `app/docs/resume/cover-letter.md` line 17 ("an AI letter tool raised callbacks") - revise bead fixes it there too, per the brief.
- **M2 (medium) - Short answer misreads the 51%.** "letters that matched the job post went with callbacks 51% less" reads as fewer callbacks. Fix: "the link between a letter matching the job post and callbacks fell 51%".
- **M3 (medium) - "Most forms still ask" is the sample's system mix, and a bigger count is left out.** 96 of 143 forms are Greenhouse, whose form lists a "Cover Letter" basic box on 85 of 96; no Workday or iCIMS. A box (91 of 96 optional) is not the employer asking. The job search's own notes count a letter asked on 209,297 of 402,117 postings with a captured form (52%; maker's docs, already in cover-letter.md). Fix: short answer "Many forms have a box: 96 of 143 we read, mostly Greenhouse; nearly all optional"; one sentence citing the 52% count as Maker's docs (add to sources.yml with the GitHub file URL at a commit), or say why it is left out.
- **M4 (medium) - Lever's "additional information" box invites a letter.** On a live Lever form its placeholder reads "Add a cover letter or anything else you want to share." (another sampled Lever form has no such box). "0 of 19 ... instead" implies Lever forms offer no letter route. Fix: article + data page line 57: "Lever forms have no box named cover letter; many show an open box whose hint says to add one. We did not count those." Better: count from the raw forms how many of the 19 show that box if freehire's read lists it; else say not counted.
- **M5 (medium) - Galdin's 19% / 14% is an extreme scenario.** The counterfactual is one "in which LLMs render written applications useless in signaling" - letters carry no signal at all. "Those two numbers come from the model" is right but a reader takes them as the forecast. Fix: "In a model where letters tell employers nothing at all, the top fifth of workers were hired 19% less often ..."
- **M6 (medium) - Contrary lab evidence missing.** Kleine-Allekotte 2024 (Tilburg MSc thesis, 86 self-screened raters): ChatGPT-created letters got the highest hireability ratings, and still did after raters were told AI may have been used. Weak (thesis, lab, hypothetical), but the "Can employers tell" section shows only the say-they-mind side. Fix: one line as Lab study ("in one small lab test, raters scored AI-written letters highest, even after being told") with sources.yml entry, or record in the review resolution why it is left out.
- **M7 (medium) - "Career guides agree" on one guide.** Lines 111-112 cite only MIT CAPD. The Convention label means "career guides agree". Fix: open + cite a second career-office guide for each (e.g. another university career centre), or reword "MIT's career office says ...".
- **M8 (medium) - "The form system mattered more than the job" was not tested.** Systems and fields overlap in the sample (field rates range from 10 of 26 to 8 of 9). Fix: "The form system made the biggest difference we saw: Greenhouse forms list a letter box by default." or show a field split.
- **L1 (low)** "2019 test" (description, short answer) vs "2020" (table) vs Jul 2019 - Jan 2020: use "2019-20" everywhere.
- **L2 (low)** "the one large test" (line 41) while the registry label prints as Small study (field experiment) and group sizes are unknown: drop "large".
- **L3 (low)** ResumeGo does not say groups were assigned at random, and put "N/A" in letter fields: add to the limits sentence and the table's "Can't show" (also "whether the gap is chance").
- **L4 (low)** "Most AI letters went out unedited": the measure is time from click to submit. Say "were sent within a minute, so most had little or no editing".
- **L5 (low)** "employers paid more" (line 71): a model-estimated willingness to pay (a close fit was worth as much as a $26 lower bid). Say "were willing to pay more".
- **L6 (low)** Both AI studies use the same platform's data (Cui credits Galdin and Silbert for the measure): "both point the same way" should say same platform, two teams, not two independent tests.
- **L7 (low)** "most able / least able" = top / bottom fifth by the model's ability score: say "top fifth".
- **L8 (low)** "found no change in overall hiring": authors say "no evidence of changes" and call it "preliminary".
- **L9 (low)** Own count rerun needs `raw.json`, kept in `~/.cache/` only; the required flags came from postings now closed. The data page says "the answers are saved" without saying where. Fix: say the raw file is not published (or publish it) and that the required flags can't be re-read once postings close.
- **L10 (low)** Line 31 "Of those, 96 of the 143 forms ..." repeats the 143 - reword ("96 had a cover letter box (67%)").
- **L11 (low)** Last "What we don't know" bullet is a search-method line; move it under the gap sentence (line 53) and list the search terms; Google Scholar search is not in the drafter's notes - keep only what was run.
- **L12 (low)** "ResumeGo sells resume and letter writing": the page says "resume writing services". Say "a resume-writing company".

Checked, no finding: quotes (none over 15 words); privacy (no owner data, no employer named); jargon (none from the AGENTS.md list); "For you," used twice; title 54 chars and close to the searched wording ("do cover letters matter"); preprint said in text for Cui and in the table for both; internal links to ai-written-resumes, what-makes-a-good-resume, methods, the data page all exist; the tool box ("How CEZ Job Finder uses this") matches `app/docs/resume/cover-letter.md` and stays separate from the evidence.
