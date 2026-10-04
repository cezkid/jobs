---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session, bead plan-xsy.19 (no drafting context; sources opened before the draft was read); revision checked in plan-xsy.20
---
# Review: Do ATS reject 75% of resumes? (`ats-rejection-myth.md`)

Verdict **publish** (after revision, 2026-10-03; first verdict was revise): 3 high, 15 medium, 12 low findings, all fixed - see Revision below. The origin trail is right and
well sourced. The problems are the headline answer (stated firmer than 25 vendor interviews
allow), one sentence that puts words in the court's mouth, and our own measurement, which
leaves out a much larger published count that points the other way.

## Sources, read before the draft (all opened 2026-10-03)

No source contained text addressing an AI. `resume-genius-2026` and `jobscan-2026` answer 403
to a plain download; both read through a browser-style fetch.

| id | What it actually supports | Sample / design | Limits |
|---|---|---|---|
| levinson-2012-cio | CIO, 2012-03-04: ATS "kill 75% of candidates' chances of landing an interview", credited to Preptel. Also a Bersin & Associates test: one ideal resume in Taleo lost a job and degrees to misreading, scored 43% relevance | Journalist repeating a vendor; one-resume test | No method for 75%. Says ATS "screen incoming resumes" and rank misread resumes as bad matches |
| levinson-2012-preptel | CIO, 2012-02-29: Preptel sells ResumeterPro at $24.95/month; CEO Jon Ciampi ex-SumTotal; Preptel's own figures (90% keyword accuracy, 50% interview rate on 13,000 jobs) | Product review | No 75% figure in this one |
| preptel-2012 | Preptel news page (Wayback 2012-12-27) reposts the CIO "kill 75 percent" paragraph; also announces Preptel 2.0 free, "forgoing their previous monthly subscription fees" | Company page | Repost date not shown; only "by December 2012" is provable |
| fuller-2021 | Hidden Workers, HBS + Accenture, Sept 2021. 2,275 executives (US/UK/DE), Jan-Feb 2020. p.20: >90% use their RMS to initially filter or rank middle-skills (94%) and high-skills (92%) candidates. p.25-26 + Fig. 10: 88% (high-skills) / 94% (middle-skills) answer yes always/often/sometimes to "your organization's hiring system filters out ... who could successfully perform the job, but don't fit the exact criteria"; RMS users only | Executive self-report survey | "Sometimes" is the biggest single answer (26-32%); always + often = 62% high-skills, 63% middle-skills. Opinion, pre-generative-AI, pre-Covid |
| enhancv-2025 | 25 US recruiters, Sept-Oct 2025, structured interviews, coded yes/no. 23/25 (92%) no auto-reject for formatting/content/design; 2/25 (Bullhorn, BambooHR) set to auto-reject on match/experience thresholds; "Knockouts used when present: 100%" and "84% of recruiters rely on them"; 44% have an AI fit score, 36% use it as a guide, 8% "definitively" incl. one Phenom recruiter who "applies a score threshold for auto-rejecting low-matches"; myth source: 68% LinkedIn/TikTok, 20% coaches/blogs, 12% media | Vendor (sells resume builder), interviews | Recruitment of the 25 not stated; raw data unpublished. Page published 2025-11-03; visible "updated 9/30/2026", JSON-LD modified 2026-01-30 |
| resume-genius-2026 | 1,000 US hiring managers, Pollfish RDE, screened for hiring responsibility. 35% use AI to screen or rank; 19% "use AI to purposefully screen out applications before they get a human review"; 32% AI recommends/ranks but humans make all final decisions; 6% AI can move forward or reject "with limited human review"; 71% screen with ATS | Vendor online panel | Field dates not given; self-report |
| jobscan-2026 | Fortune 500 career pages "reverse-engineered": ATS found at 97.4% (487 of 500) in 2026; 97.8% 2025; 98.4% 2024; Workday >40% | Vendor detection method | Fortune 500 only. Its 76.4% recruiter-search figure cites an unopened report - not usable |
| greenhouse-rules | Application rules fire on answers to custom job-post questions; Auto-Reject (Plus + Pro tiers only) rejects and can auto-email those who miss "certain license or location requirements" | Vendor help page, updated 2026-03-02 | Says what is possible, not how many employers turn it on |
| greenhouse-search | Recruiters can full-text search resumes for keywords and see matching snippets | Vendor help page, updated 2022-06-06 | Feature exists; no usage data |
| ashby-2024 | AI marks each employer criterion Meets / Does not Meet with citations; "it is up to the reviewer to advance or reject"; PII redacted; applicant AI opt-out; unreadable resume = criteria "skipped" | Vendor blog, 2024-09-10 | Maker's own description |
| mobley-2025-order | N.D. Cal. Dkt 128, 2025-05-16. p.1-3: plaintiffs allege Workday's AI recommendation system can "score, sort, rank, or screen"; preliminary collective certification of the ADEA (age 40+) claim GRANTED, can be de-certified later. p.10: Workday "appears to take the position" its AI cannot auto-reject without employer participation. p.18: collective includes results communicated to the employer "or ... an automatic rejection by Workday". p.19: Workday's "1.1 billion applications were rejected using Workday"; court: the estimate "ignores the qualifiers in the definition of the collective" | Court order | Allegations, no finding of fact |
| lawyer-monthly-2026 | 2026-09-21: plaintiffs ask to certify four subclasses (Black applicants, women, 40+, disabilities); hearing 2027-03-09, Judge Rita F. Lin; Workday denies. Also: court later confirmed HiredScore AI features fall in the collective; 356 million applications through Workday Recruiting in 2024 | Trade news, quotes Reuters | Secondary; event only |

Also checked (not cited in the draft): `app/apply/readahead.py:11-12` and `app/docs/apply/answers.md:15` -
freehire's own published count, ~100k forms (2026-08): 67% ask nothing beyond a resume + contact
details. Clearinghouse case page (summary updated 2025-12-17): HiredScore ruling 2025-07-07, notice
plan approved 2025-12-02. A web-search summary also named 2026 events (discovery order, partial
dismissal, interlocutory appeal) - not confirmed on any opened page.

Our measurement, re-run 2026-10-03 from `~/.cache/plan-xsy-18/ko/classify.py raw.json`: every count
in the draft reproduces (143 forms of 840 postings; median 6; permit/sponsor 96; location 54; years
21; licence 5 + clearance 6, no form has both, so 11; any 106). Reviewer probes: of the 54 location
forms, ~10 match only an address, zip, city or "where are you located" box; dropping plain
address boxes leaves 105 forms with any knockout-type question. "Questions" include Address, City,
LinkedIn and Website boxes; with those removed the median is ~4. Forms by field: sales 33,
customer success 26, HR 17, backend 16, devops 12, data 11, legal 9, hospitality 5, admin 5,
marketing 5, education 2, healthcare 1, finance 1, design 0. Unreadable 697: Workday 188, Oracle
94, iCIMS 56, plus job boards (Adzuna 52, USAJobs 24, WhatJobs 16, Himalayas 15) and others.

## Claim table

37 citation markers in the article (12 distinct ids); 77 rows below.

| # | Line | Claim | Source | What the source says | Verdict | Sev |
|---|---|---|---|---|---|---|
| 1 | 2 | Title: "Do ATS reject 75% of resumes? Where the number came from" | - | Article delivers the origin | Supported | - |
| 2 | 3 | Description: "yes/no questions do the rejecting" | greenhouse-rules, enhancv-2025 | Possible on Greenhouse Plus/Pro; 25 interviews say knockouts are the main auto filter; no count of auto-rejections anywhere | Overstated (F3) | high |
| 3 | 19 | 75% = one 2012 sales claim, no method ever published | levinson-2012-cio | No method given; "ever" unprovable | Overstated wording (F5) | medium |
| 4 | 20 | Software stores, searches, ranks; a person usually decides | (none inline) | enhancv-2025 23/25; resume-genius 32% humans decide all, 6% limited review | Needs citation + label (F4) | medium |
| 5 | 21 | Automatic rejections come mostly from yes/no questions | (none inline) | As row 2 | Overstated (F3) | high |
| 6 | 22 | AI match scores spreading; how often they reject alone unknown | - | No trend data in any source | "Spreading" unsupported (F12) | medium |
| 7 | 26 | Number traces back to a single 2012 magazine article | levinson-2012-cio | Earliest copy found; origin is Preptel's claim | Supported, minor wording (L1) | low |
| 8 | 26 | CIO March 2012: ATS "kill 75% of candidates' chances" of an interview | levinson-2012-cio | Verbatim, 2012-03-04 | Supported | - |
| 9 | 26 | Credited to Preptel, a company selling help to beat ATS | levinson-2012-cio | Yes | Supported | - |
| 10 | 28 | Preptel sold a resume service for $24.95 a month | levinson-2012-preptel | ResumeterPro $24.95/month | Supported | - |
| 11 | 28 | Its news page reposted the 75% line later that year | preptel-2012 | Repost present in 2012-12-27 capture; repost date not shown | Supported (by Dec 2012) | low |
| 12 | 28 | Neither page says how the number was measured | levinson-2012-cio, preptel-2012 | True | Supported | - |
| 13 | 28 | No study, sample or data published since | (none) | Universal negative; nothing searched is cited | Overstated (F5) | medium |
| 14 | 30 | Original wording "kill chances", not "reject" | levinson-2012-cio | True | Supported | - |
| 15 | 30 | Many retellings now say "rejected"; 2012 article never claimed it | (none) | No retelling cited; article does say ATS "screen" resumes and kill chances "as soon as they submit" | Unsupported + overstated (F6) | medium |
| 16 | 32 | 2025 Enhancv survey: 68% of recruiters said job seekers picked up the myth on LinkedIn/TikTok | enhancv-2025 | 68% pointed to job seekers who saw it there; 25 interviews; recruiters' guess | Needs caveat (F9) | low |
| 17 | 32 | Enhancv sells a resume builder, so vendor survey | enhancv-2025 | True | Supported | - |
| 18 | 34 | 75% is not evidence; a sales line nobody backed up | levinson-2012-cio | Fair reading | Supported | - |
| 19 | 38 | Almost every big employer has an ATS | (none) | jobscan: Fortune 500 only | Needs caveat (L2) | low |
| 20 | 38 | Resume-tool company found one at 97.4% of Fortune 500 in 2026 | jobscan-2026 | 487/500, career-page detection | Supported | - |
| 21 | 40 | Software does four main jobs; stores each application | (none) | General description | Supported (definition) | - |
| 22 | 40 | Recruiters can search resumes for words | greenhouse-search | True | Supported | - |
| 23 | 40 | Filters applicants by answers to the form's questions | greenhouse-rules | True; Plus/Pro tiers only | Supported, tier caveat (L3) | low |
| 24 | 40 | Newer versions rank or score applicants | ashby-2024 | Meets/Does not Meet per criterion | Supported | - |
| 25 | 42 | Storing and searching are not rejecting; unseen resume "was not thrown out. Nobody read it" | (none) | fuller-2021: >90% use the RMS to filter or rank; a filtered-out resume is excluded, not just unread | Overstated (F10) | medium |
| 26 | 48 | Yes/no questions are the most common automatic filter | (none) | As row 2 | Overstated (F3) | high |
| 27 | 48 | Greenhouse, a widely used system, lets employers auto-reject on custom-question answers | greenhouse-rules | Auto-reject on answers: yes. "Widely used": not in source | Supported; "widely used" uncited (L3) | low |
| 28 | 48 | Its own example is a license or location requirement | greenhouse-rules | Verbatim example | Supported | - |
| 29 | 50 | Those rules act on your answers, not your resume text | greenhouse-rules | True for Greenhouse application rules | Supported (Greenhouse only) | - |
| 30 | 50 | Same page says it can send a rejection email automatically | greenhouse-rules (no marker) | True | Supported; add marker (L4) | low |
| 31 | 52 | 23 of 25 said no auto-reject for formatting, content or design | enhancv-2025 | True | Supported | - |
| 32 | 52 | Two said their systems reject on resume content, e.g. low match score | enhancv-2025 | Bullhorn + BambooHR; but a third (Phenom) "applies a score threshold for auto-rejecting low-matches" | Cherry-picked / needs caveat (F7) | medium |
| 33 | 54 | Page gives two different figures for knockout use, 84% and 100% | enhancv-2025 | 100% = "used when present" (of those whose system has them); 84% = "rely on them". Different bases, not a contradiction | Misread (F8) | medium |
| 34 | 54 | Knockouts were the main automatic filter described | enhancv-2025 | True | Supported | - |
| 35 | 54 | Small sample; how the 25 were chosen is not stated | enhancv-2025 | True | Supported | - |
| 36 | 60 | October 2026 sample of US postings from last 14 days, 14 fields | own measurement | Reproduced | Supported | - |
| 37 | 62 | 840 postings yielded 143 readable forms | own measurement | Reproduced | Supported | - |
| 38 | 62 | The rest used systems whose forms we can't read, such as Workday | own measurement | 188 Workday, but many are job boards (Adzuna, USAJobs ...), not form systems | Needs caveat (L5) | low |
| 39 | 62 | Median six questions beyond name and contact details | own measurement | Count includes Address, City, LinkedIn, Website boxes; ~4 without | Misdescribed (F11) | medium |
| 40 | 64 | Most forms asked a knockout-type question; 106 of 143 | own measurement | Reproduced; ~105 with plain address boxes dropped | Supported, see F11 | low |
| 41 | 66 | Work permit or visa sponsorship: 96 of 143 | own measurement | Reproduced | Supported | - |
| 42 | 67 | Where you live, on-site or moving: 54 of 143 | own measurement | ~10 of 54 are only an address/zip/"where located" box, not a yes/no screen | Needs caveat (F11) | medium |
| 43 | 68 | Years of experience: 21 of 143 | own measurement | Reproduced | Supported | - |
| 44 | 69 | License, certificate or clearance: 11 of 143 | own measurement | 5 + 6, no overlap | Supported | - |
| 45 | 71 | Limits: leans tech and office; 5 systems; can't see auto-reject settings | own measurement | True, but omits that healthcare + finance gave 1 form each, design 0, and freehire's 100k-form count (67% ask nothing extra) | Missing counter-evidence (F2) | high |
| 46 | 73 | 106 of 143 does not confirm the 75% claim | levinson-2012-cio | Good framing | Supported | - |
| 47 | 79 | No published study shows a formatting slip alone causes automatic rejection | (none) | Universal negative; enhancv-2025 2/25 (+1 Phenom) reject on content; levinson-2012-cio Bersin test: misread resume scored 43% | Overstated + missing evidence (F13) | medium |
| 48 | 79 | Recruiters mostly said formatting did not trigger rejection; vendor survey of 25 | enhancv-2025 | True | Supported | - |
| 49 | 81 | Spaced heading letters came back "EXP E R I ENC E" in one conversion | page-format.md:13 | True, in a PDF-to-HTML conversion; PyMuPDF, pdfminer and pypdf read it whole | Needs caveat (F14) | medium |
| 50 | 81 | A garbled word can't match a recruiter's search | (inference) | No source shows an ATS uses that conversion | Needs caveat (F14) | medium |
| 51 | 81 | Workday test: school + degree on one line landed in wrong boxes | page-format.md:60 (unlinked) | True | Supported; link it (L4) | low |
| 52 | 83 | Ashby autofill filled contact boxes only, left questions empty | ashby.md:10-13 | True, tenant A, Sept 2026 | Supported | - |
| 53 | 83 | Applicants can read that as rejection; it did not | ashby.md:12 | Our doc says users read it so | Supported (our notes) | low |
| 54 | 89 | Hidden Workers: 2,275 executives, US/UK/DE, early 2020 | fuller-2021 | True (Jan-Feb 2020) | Supported | - |
| 55 | 89 | Over 90% use software to first filter or rank middle- and high-skills applicants | fuller-2021 p.20 | 94% / 92% | Supported | - |
| 56 | 91 | Most executives "admitted the filters cost them good people" | fuller-2021 p.26 | Asked whether the hiring system filters out such people; belief, not cost | Overstated (F15) | medium |
| 57 | 91 | 88% high-skills / 94% middle-skills at least sometimes; question about exact criteria | fuller-2021 p.26 | True; always + often = 62% / 63% | Supported; add split (F15) | low |
| 58 | 93 | Survey of what executives said; "still the strongest published sign that rigid filters drop qualified people" | fuller-2021 | Self-report caveat right; "strongest" uncompared; survey is 2020, before AI screening | Overstated + outdated caveat (F16) | medium |
| 59 | 99 | 2026 survey of 1,000 US hiring managers: 35% use AI to screen or rank | resume-genius-2026 | True | Supported | - |
| 60 | 99 | 19% use AI to screen some out before a human looked | resume-genius-2026 | True; omits 6% "AI can ... reject them with limited human review" and 32% "humans make all final decisions" - the numbers that answer the section question | Cherry-picked / missing (F12) | medium |
| 61 | 101 | Ashby: AI marks meets criteria or not, with reasons; "up to the reviewer to advance or reject" | ashby-2024 | True | Supported | - |
| 62 | 103 | Mobley plaintiffs allege Workday's AI scored, sorted or screened, disadvantaging older people | mobley-2025-order p.3 | True; full case also alleges race + disability | Supported | - |
| 63 | 103 | Workday's position: its AI cannot reject anyone without the employer taking part | mobley-2025-order p.10 | Court: Workday "appears to take the position" it cannot auto-reject without "some degree of participation" | Supported, soften (L6) | low |
| 64 | 105 | May 2025: court let the age claim go forward as a collective action | mobley-2025-order | Preliminary certification; can be de-certified | Needs caveat (F17) | medium |
| 65 | 105 | Workday told the court 1.1 billion applications were rejected using its software | mobley-2025-order p.19 | True | Supported | - |
| 66 | 105 | Court noted that figure counts rejections recorded in Workday, not AI rejections | mobley-2025-order p.19 | Court said the estimate "ignores the qualifiers in the definition of the collective"; it did not say what the figure counts | Misattributed (F1) | high |
| 67 | 107 | As of October 2026 plaintiffs ask to widen the case to more groups | lawyer-monthly-2026 | Four subclasses, Sept 2026 | Supported; add recheck date (F17) | low |
| 68 | 107 | Hearing set for March 2027; Workday denies | lawyer-monthly-2026 | 9 March 2027; denies | Supported | - |
| 69 | 113 | No public data counts auto-rejections across employers | - | Consistent with all sources | Supported | - |
| 70 | 115 | No vendor publishes how AI match scores are calculated | (none) | Universal; Ashby publishes a bias audit and criteria design | Overstated (L7) | low |
| 71 | 116 | No large study has tested whether posting-tuned resumes get more interviews | (none) | Universal negative, uncited | Needs "we found none" (L7) | low |
| 72 | 121 | Work permit and sponsorship answers are checked once hired | (none) | Work permit: Form I-9 (law), uncited; sponsorship is not "checked" the same way | Unsupported (F18) | medium |
| 73 | 122 | Recruiters search for skills words | greenhouse-search | Search exists; use frequency unknown | Supported (feature) | low |
| 74 | 124 | Autofill "often" leaves questions blank | ashby.md | One test, one tenant | Overstated (F19) | low |
| 75 | 125 | Rigid filters drop qualified people, so one rejection says little | fuller-2021 p.26 | Executive opinion | Overstated (L8) | low |
| 76 | 131 | App reads each form's questions and names the yes/no ones | `app/apply/readahead.py` | Only 5 systems, only listed jobs; lists topics ("Asks about: ..."), not yes/no questions as such | Overstated (F20) | medium |
| 77 | 132-134 | Keeps permit answer; one-column resume checked to read back; posting words only where backed | `app/apply/questions.py`, `resume/render.py:346` single-column gate, AGENTS.md keyword rule | True | Supported | - |

## Findings

All fixed in plan-xsy.20; how each was fixed is under Revision.

- **F1 (high, status: fixed) - court note misattributed.** Line 105: "The court noted that figure counts
  rejections recorded in Workday, not AI rejections." The order (p.19) says only that Workday's
  estimate "ignores the qualifiers in the definition of the collective that will limit its scope".
  Fix: "The court said that estimate ignores the limits of who is in the case." Our own reading
  (rejections recorded in Workday, by employers or otherwise) may follow as ours, labelled.
- **F2 (high, status: fixed) - our measurement ignores a larger count that points the other way.** freehire
  published (2026-08) that of ~100k captured forms, 67% ask nothing beyond resume + contact details
  (`app/docs/apply/answers.md:15`). Our sample has 20 of 143 (14%) with no questions. The draft's
  "Most forms asked at least one knockout-type question" reads as typical of forms; it may only be
  typical of this sample. Fix: report both, side by side; say the two differ and why we think so
  (our "questions" include address/LinkedIn boxes; field mix; 60 postings per field at one random
  offset). Also state the field skew in numbers: sales + customer success + HR + backend = 92 of
  143 forms; healthcare 1, finance 1, design 0. Or cite freehire's page as a source if public.
- **F3 (high, status: fixed) - headline answer firmer than the evidence.** Description, Short answer line 3
  and line 48 say yes/no questions are "the most common" / "mostly" / "do the rejecting". Evidence:
  25 vendor-run interviews + one help page saying the feature exists. "What we don't know" itself
  says nobody counts auto-rejections. Fix: "Where software rejects on its own, it is mostly on
  yes/no answers, in recruiter interviews (Vendor survey, 25 recruiters)." Same in description.
- **F4 (medium, status: fixed) - Short answer lines 2-3 carry labels but no citations.** Add
  [@enhancv-2025] / [@greenhouse-rules] / [@resume-genius-2026] markers, or drop the label.
- **F5 (medium, status: fixed) - "no method ever published", "no study ... since".** Universal negatives.
  Fix: "We found no method, study or data behind it" (and say where we looked).
- **F6 (medium, status: fixed) - "Many retellings now say 'rejected'" is uncited, and "never claimed" is too
  strong.** The 2012 article says ATS "screen incoming resumes" and kill chances "as soon as they
  submit". Fix: cite one retelling (Enhancv quotes the "ATS rejects most resumes" claim), and say
  the 2012 line was about chances of an interview, not a count of rejections.
- **F7 (medium, status: fixed) - third content auto-rejecter left out.** Enhancv's own page names a Phenom
  recruiter who "applies a score threshold for auto-rejecting low-matches", besides Bullhorn and
  BambooHR. Fix: "Two, possibly three, of 25 ..." and note Enhancv's page counts them differently.
- **F8 (medium, status: fixed) - 84% vs 100% is not a contradiction.** "Knockouts used when present: 100%"
  is among recruiters whose system has knockouts; "84% rely on them" is of all 25. Fix: drop
  "two different figures"; say 84% (21 of 25) rely on knockout questions.
- **F9 (low, status: fixed) - 68% is recruiters' guess at where applicants heard the myth.** Say "17 of 25
  recruiters guessed ..." and call it interviews, not a survey.
- **F10 (medium, status: fixed) - "Storing and searching are not rejecting ... Nobody read it."** Filtering
  and ranking (the draft's own third and fourth jobs; >90% of employers in Hidden Workers) can drop
  a resume without a person. Fix: "A resume no recruiter searched up was not rejected by a rule;
  a filter or ranking can still keep it from being read."
- **F11 (medium, status: fixed) - our counts describe "questions" loosely.** The "median of six questions
  beyond name and contact details" counts Address, City, LinkedIn and Website boxes (median ~4
  without). About 10 of the 54 "where you live" forms only ask an address or city, not a yes/no
  screen. Fix: reword ("a median of six extra boxes, including address and profile links"), and
  either recount location as yes/no only or label the line "asks where you live (some only an
  address box)". The 106 headline barely moves (~105).
- **F12 (medium, status: fixed) - AI section omits the numbers that answer it.** Same survey: 6% say AI can
  advance or reject "with limited human review"; 32% say humans make all final decisions. "AI
  scoring is spreading" (line 99, Short answer) has no trend data. Fix: add both numbers; replace
  "spreading" with "In 2026, about a third of hiring managers in one vendor survey said ...". Add
  that field dates aren't given and answers are self-report.
- **F13 (medium, status: fixed) - formatting section misses evidence already in a cited source.** CIO 2012
  reports Bersin's one-resume Taleo test: misreading cut its relevance score to 43%. That is
  ranking harm from parsing (one resume, 2011, old Taleo), the very "quieter way" the section
  describes. And "No published study shows ..." is a universal negative (see F5). Fix: add Bersin,
  labelled as a one-resume test; "We found no study showing ...".
- **F14 (medium, status: fixed) - "EXP E R I ENC E" needs its limit.** page-format.md:13 says that came from a
  PDF-to-HTML conversion; three common PDF readers read it whole. We don't know any ATS reads that
  way. Fix: say so; soften "can't match a recruiter's search" to "would not match if a system read
  it that way".
- **F15 (medium, status: fixed) - "admitted the filters cost them good people".** The question asked whether
  their hiring system filters out people who could do the job. Fix: "said their system filters out
  qualified people at least sometimes"; add "always or often: 62% / 63%".
- **F16 (medium, status: fixed) - "strongest published sign" + age.** Uncompared superlative; survey ran
  Jan-Feb 2020, before AI screening tools were common. Fix: drop "strongest"; add "The survey
  predates today's AI screening tools."
- **F17 (medium, status: fixed) - Mobley status needs "preliminary" + re-check date + later rulings.** May
  2025 was preliminary certification (Workday can seek de-certification). Since then: HiredScore
  AI features ruled in (July 2025, Clearinghouse + Lawyer Monthly), notice plan approved (Dec 2025,
  Clearinghouse). A search summary claims 2026 events (discovery order, partial dismissal,
  interlocutory appeal) - unverified; check the docket before publishing. Add "as of <date>,
  re-check by 2027-01-03".
- **F18 (medium, status: fixed) - "checked once you are hired" uncited.** Work permit: Form I-9 (law) - cite a
  primary source (USCIS I-9 page) or fair-screening.md. Sponsorship: say a false "no" surfaces when
  a visa is needed, or drop it.
- **F19 (low, status: fixed) - "autofill often leaves them blank".** One test of one Ashby tenant. Fix: "can
  leave them blank (our Ashby test did)".
- **F20 (medium, status: fixed) - tool box overstates the app.** `readahead.summary` reads questions only for
  listed jobs on Greenhouse, Lever, Ashby, Workable, Recruitee, and lists topics, not "the yes/no
  ones". Fix: "Reads a form's questions ahead when it can (5 systems) and lists what they ask about."
- **L1 (low, status: fixed)** Line 26 "traces back to a single 2012 magazine article": "earliest copy we
  found is a 2012 magazine article quoting a resume-help company".
- **L2 (low, status: fixed)** "Almost every big employer has one": "almost every Fortune 500 company".
- **L3 (low, status: fixed)** Greenhouse: auto-reject is Plus and Pro tiers only; "widely used" uncited -
  drop or cite.
- **L4 (low, status: fixed)** Add [@greenhouse-rules] to line 50's second sentence; link page-format.md for
  the Workday test (line 81).
- **L5 (low, status: fixed)** "The rest used systems whose forms we can't read, such as Workday": many of the
  697 are job-board copies (Adzuna, USAJobs ...), not form systems. Say "Workday, Oracle, iCIMS or
  job boards".
- **L6 (low, status: fixed)** Mobley p.10: "Workday argued its AI cannot reject anyone without the employer
  taking part" (the court's words: "appears to take the position").
- **L7 (low, status: fixed)** "None publish their method", "No large study has tested it": "we found none".
- **L8 (low, status: fixed)** "one rejection says little about you": "one rejection may say more about the
  filter than about you".
- **L9 (low, status: fixed) - style.** "median" is a stats term (research.md Style: explain or avoid - "the
  middle form asked six"). Sentences leaning on "This"/"It" across sentences (lines 42, 83, 93) -
  research.md asks to name the subject.
- **L10 (low, status: fixed) - publish blocker, known.** Links to `what-makes-a-good-resume.md` and
  `ai-resume-screening-bias.md` point at unwritten articles; publish fails until they exist or the
  links drop.

## Plain words, SEO, privacy

- Title 56 chars, description ~148: fit. Title answers the search intent; body never states a yes/no
  answer to "Do ATS reject 75%?" in one quotable sentence - add one near the top ("No study shows
  that ATS reject 75% of resumes.").
- Jargon lint: "ATS" defined at first body use; "knockout" defined. No app jargon found.
- Quotes: longest is 7 words. All attributed.
- Privacy: no owner data; employers in our tests unnamed ("tenant A"). Clean.
- Tool box sits after the evidence, separate: fine apart from F20.

## Revision (plan-xsy.20, 2026-10-03)

New sources, opened 2026-10-03, no text addressing an AI: `uscis-i9` (USCIS I-9 page, last reviewed
2026-06-03: employers "must properly complete Form I-9 for every individual they hire"), and
`clearinghouse-mobley` (case summary updated 2025-12-17 + filing list: HiredScore ruling 2025-07,
notice plan 2025-12-02, Third Amended Complaint 2026-03-27, order granting in part + denying in part
the motion to dismiss 2026-06-22; case ongoing). Docket on CourtListener/Justia answered 403/401;
the "discovery order" and "interlocutory appeal" from the search summary stay unconfirmed and are not
in the article. Enhancv page re-read for F6/F7/F8: quotes "75% of resumes are rejected by Applicant
Tracking Systems"; Phenom line confirmed; 84% "rely on them" vs "used when present: 100%" confirmed.

Our measurement recounted (`~/.cache/plan-xsy-18/ko/refine.py raw.json`): contact, address and
profile boxes dropped -> middle form 4 questions (quartiles 2 and 8), 26 of 143 ask nothing beyond
them; location hits that are only an address/zip/"where located" box: 11 of 54 -> 43 location
screens; any knockout-type question 105 of 143.

- F1: "The court said that estimate ignores the limits of who is in the case."
- F2: field skew in numbers added (92 of 143 from four fields; healthcare + finance one each, design
  none); 26 of 143 with no extra questions stated; the freehire count is disclosed as a larger
  count reporting far fewer extra questions, without its numbers - its page could not be re-found
  (`app/docs/apply/answers.md:15-17`), and research.md bars citing an unopened source. freehire's
  public measurements (github.com/strelov1/freehire, 01 + 03, 2026-09-09) count fields and exact
  labels, not forms with knockout questions, so they cannot stand in for it. "Most forms" dropped;
  "many forms" / "some" in the reader line.
- F3: description, Short answer and section lead now "where software rejects on its own, recruiters
  say ... (Vendor survey, 25 recruiters)"; added "Nobody publishes a count of automatic rejections".
- F4: Short answer lines carry [@levinson-2012-cio], [@enhancv-2025], [@resume-genius-2026].
- F5: "We searched for a study, sample or data set behind the figure and found none."
- F6: retelling cited (Enhancv quotes it); "about the chances of getting an interview, not a count".
- F7: Phenom recruiter added; "two, possibly three, of the 25".
- F8: "two different figures" dropped; "21 of the 25 ... rely on knockout questions".
- F9: "17 of the 25 recruiters guessed", called interviews.
- F10: filtering/ranking paragraph replaces "Nobody read it", with Hidden Workers p. 20.
- F11: four questions beyond contact/address/profile boxes; location line recounted to 43 and says
  plain address boxes are not counted; headline 105.
- F12: 6% and 32% added; "spreading" dropped; survey dates not given + self-report said.
- F13: Bersin/Taleo one-resume test added, labelled one resume in one system; "We found no study".
- F14: "PDF-to-web conversion", three PDF readers read it whole, "if one did, ... would not match".
- F15: "said their system filters out qualified people at least sometimes"; 62% / 63% always or often.
- F16: "strongest" dropped; "before today's AI screening tools were common".
- F17: "at a preliminary stage", can be undone later, HiredScore July 2025, June 2026 partial
  dismissal, as of October 2026; `recheck_by` 2027-01-03 on both case sources.
- F18: Form I-9 cited (law); sponsorship: "A false 'no' ... shows up when a visa is needed."
- F19: "autofill can leave them blank (our Ashby test did)".
- F20: "Reads a form's questions ahead when it can (5 systems) and lists what they ask about."
- L1-L8: wording as proposed (earliest copy we found; Fortune 500; Greenhouse higher-priced plans,
  "widely used" dropped; citation + page-format link added; Workday, Oracle, iCIMS or job boards;
  "The court described Workday's position"; "we found none/no vendor"; "may say more about the filter").
- L9: "median" -> "the middle form"; "This"/"It" sentences name their subject.
- L10: links to the two unwritten articles dropped; links to methods + the Research hub instead.
- SEO: quotable answer added as the first body sentence ("No study shows that applicant tracking
  systems reject 75% of resumes.").

## Re-review 2026-10-03: citations thinned (plan-xsy.48)

Citation placement only - no wording, number or source changed. A run of sentences citing the
same source now cites it once, at the run's end (build rule: 3 in a row = error). Checked: every
sentence the moved citation now covers comes from that source.
17 repeat citations dropped. Newly under a citation: "Recruiters call them knockout questions"
(enhancv-2025 uses the term). Supported.

## Re-review 2026-10-04: voice pass (plan-xsy.53)

Voice only. Section endings reopened ("In short," / "In practice," / no opener); "searched up" -> "searched for"; Phenom sentence now "The same page reports that a third recruiter ... [@enhancv-2025]" - same attribution as before, matches source table (Enhancv page: one Phenom recruiter "applies a score threshold for auto-rejecting low-matches"); the job search named freehire.me in the limits paragraph and "freehire.me's maker" for the earlier ~100k-form count - matches this file's note (freehire's own published count) and app/docs/jobs/freehire.md (base freehire.me); home-page line; `modified` 2026-10-04. Checked: each changed line keeps its meaning, scope, hedging and evidence label; section endings still say what the finding means for the reader; no new "this"/"it" across sentences; no app jargon; closing line "CEZ Job Finder is a free job-search app for Windows and Mac" matches docs/index.html title + og:title; link is our own home page. No finding.

## 2026-10-04 - data page link (plan-xsy.57)

Added sentence (end of "These counts have limits." paragraph): "The data, one row per form, and
how we counted: [the knockout-question data](knockout-questions-2026-10.md)." Accurate: the data
page holds one row per readable form and the counting method, and its counts match this section
(105, 96, 43, 21, 11, 26, 92, middle form 4). Link target exists. The sentence is fine; header
unchanged.

Carried over from the data page review (`reviews/knockout-questions-2026-10.md`), affecting this
article's numbers, not the new sentence: F1 (questions freehire lists under `basics` on some
Workable forms are not counted; recount gives about 109 / 99 / 45 / 22 instead of 105 / 96 / 43 /
26) and F2 ("The job search we used, freehire.me, leans toward tech and office jobs" - every field
gave 60 postings; the lean comes from which forms are readable). When F1 is fixed, this section
takes the new counts with a `## Changes` line and a fresh review date.

### Re-review 2026-10-04 (plan-xsy.57)

Corrected numbers checked against a fresh rerun of `knockout.py table` and a recount of the CSV:
109 of 143 (any of the six), 99 (permit or sponsorship), 45 (location), 21 (years), 13 (license,
certificate or clearance), 22 (nothing beyond basics), 92 (four fields), middle form 4 - all
right. "Most of the rest" is accurate (Workday, Oracle, iCIMS plus job boards are about 445 of the
697 unreadable postings). The lean sentence now says the readable forms lean toward tech and
office jobs - accurate. `## Changes` line is right: plain words, dated October 2026, says what
was missed and the 105 -> 109 change, and the conclusion (does not confirm the 75% claim) does
stand. `modified: 2026-10-04` bumped, `uncited` snippets match the new text. Header stays
`verdict: publish`.
