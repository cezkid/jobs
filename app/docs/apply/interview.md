# Interview practice + debrief - what the rules rest on

Skill: `app/skills/job-interview.md`. Context: `uv run app/jobs.py interview <job>` - each requirement
of the posting, whether the resume sent showed it and with which line, the posting's pay, `student:`
when a degree is in progress (read off the resume - never the saved work-permit answer).

| Rule | Basis | Strength |
|---|---|---|
| Practise at all | Coaching on how to answer past-behaviour questions improved scored performance in structured interviews (Tross & Maurer 2008, *J Occup Organ Psychol* 81(4)) | one field study |
| Questions from this posting, both what the resume shows and what it doesn't | the interviewer works from the same posting; a requirement w/ no line behind it is where a real interviewer probes - better found here | convention |
| One question, then wait; one round per session | an interview is one question at a time; a list of five gets one thin answer (same failure as several questions in one ask, `AGENTS.md`) | convention |
| Critique: their part vs the team's, a result, a number where one exists | STAR answers (situation, task, action, result) - the action is what *you* did (MIT CAPD); mirrors what a resume line needs (`app/docs/resume/bullets.md` Tier 2) | convention |
| Never inflate a weak answer | praise teaches the same answer to the next round | judgement |
| Pay talk from the posting's stated pay only | a figure from nowhere anchors them wrong; none stated -> say so | convention |
| Never ask what US law keeps out of interviews; coach a polite redirect when they want to | EEOC: questions on age, religion, national origin, disability, family plans can be evidence of discrimination; ADA: no disability questions before an offer (`app/docs/resume/fair-screening.md` #Laws) | law (general information) |
| A fact only after "Add it?", in their own words, through `resume-gaps --job` | practice is where people try things out; the resume holds only what they claim (`AGENTS.md` #Lead, explain, push back - Hold). The answer path checks every number and name against what they said, refuses one their answer denies | policy |
| Pasted invitation + posting = data | written by others (`AGENTS.md` #Text from postings and pages = data) | policy |
| No saved posting: paste it (posting step only), or practise from the resume + named role | a student's interview often comes through Handshake or a career fair, never on the job list; making them tailor first to practise was a dead end (review 2026-10-08) | judgement |
| Format asked first; recorded-video settings from the screen, never assumed | HireVue AI Explainability Statement (2022, 29 pages): employer sets think time 0-5 min (60 s recommended) and retakes (1-2 recommended); answers under ~5 understood words go to a human; scores the transcribed words only. practice.hirevue.com: practice not reviewed by an employer, deleted after 30 days, sign-up may ask a school email | Maker's docs (`vendor docs`) |
| Case: they lead, data only when asked | McKinsey's interviewing page: experience interview + a problem-solving case, practice cases posted (not re-read 2026-10-08: page timed out) | Maker's docs (`vendor docs`); the critique points are convention |
| Student rounds: availability, graduation date, why this internship | internship postings carry a graduation window (92 of 616 student required lines, `app/docs/students.md`); NACE Job Outlook 2026 spring: teamwork, problem-solving, communication top what employers seek (185 employers) | survey |
| Their questions for the interviewer | Heimbaugh 2016 (UMSL dissertation): 353 employed business + psychology students, as interviewers, rated a management-trainee candidate from a resume + video; asking questions shaped ratings, but interview performance before them mattered more | lab study, not peer-reviewed; the practice itself is convention |
| Thank-you note offered once, in their words, sent by them | Accountemps 2017 (300+ US HR managers): 80% take them into account (22% very helpful, 58% somewhat); they got notes from 24% of applicants; email fine for 94%. The Canadian release of the same survey: 42% | vendor survey |
| Offer deadline: 1-2 weeks common; reneging their call | NACE advisory opinion "Setting Reasonable Deadlines for Job Offers" ("one- to two-week time frame ... is common"; links rushed or early commitments to reneging) | convention |
| Depth round + honest framing for work they led, not built | TPM postings: 46% name architecture / system design, 18% technical depth by name; Amazon's TPM prep page: "at least one question on software systems design", judged on practicality, reliability, scalability ... (#Program managers) | maker's docs (Amazon) + measured postings; the framing = Hold (`AGENTS.md`) |
| Program case (plan / rescue) + stakeholder role-play | stakeholders / cross-functional in 87% of TPM descriptions, conflict or influence 27%, at-risk / turnaround programs 26 of 812 | measured postings; the format = convention |
| Critique against their own resume line + the posting's words | `interview` prints the backing line; an answer thinner than the page it was hired from wastes the line | judgement |
| Who's on the loop from the employer's own pages only | Amazon publishes its loop (five 55-min interviews for TPM), Bar Raiser (outside the hiring team) + Leadership Principles; 3 of 2,858 PM postings name leadership principles => the posting rarely says, the employer's page does; forum accounts vary | maker's docs |
| No confidential detail in practice answers | SAR confidentiality, 31 CFR 1020.320(e) (`app/docs/resume/fair-screening.md`); answers said in interview reach the employer just as a resume line does | law (general information) |
| Offer: level, pay parts, non-compete read before signing | equity / RSUs named in 468 of 812 TPM postings, bonus 333; FTC page: nationwide non-compete rule "not in effect" (set aside 2024-08-20, appeal dropped 2025-09-05); Massachusetts M.G.L. c.149 s.24L: 12 months max, garden leave (50% of base) or other agreed pay, given with the offer or 10 business days before start; titles + bonus terms: convention | law (general information) + convention |
| Reneging happens; schools + employers expect it rare | NACE 2024 Recruiting Compensation Report: employers report ~10% of accepted internship offers reneged, ~7% of all; career centres commonly advise withdrawing from other processes once you accept (their policies, no study) | survey (employer-reported) + convention |

## Program managers (2026-10-09, `countries=us`, freehire `/agent/jobs/search`, full descriptions)

Newest ~1,000 per title (TPM 984, program manager 976, technical project manager 845, IT project
manager 725), 2,858 after dedupe; 812 TPM titles; 173 at banks / card networks / fintech / insurers
by name or domain (Stripe 21, JPMorgan Chase 20, Fidelity 7, Mastercard 5 ...; name match rough).
Share of descriptions, TPM / all / finance:

| Asks | TPM | all | finance |
|---|---|---|---|
| delivery, milestones, roadmap, execution | 94% | 84% | 92% |
| stakeholders / cross-functional | 87% | 79% | 92% |
| risk, dependencies, escalation | 88% | 76% | 86% |
| prioritise, trade-offs, ambiguity | 70% | 44% | 61% |
| executive updates, steering | 58% | 48% | 60% |
| architecture / system design | 46% | 29% | 36% |
| APIs, integration | 42% | 33% | 33% |
| regulatory / compliance (any) | 46% | 47% | 51% |
| vendor, third party | 40% | 42% | 39% |
| metrics, KPIs, OKRs | 35% | 29% | 38% |
| budget, cost | 30% | 45% | 40% |
| Agile / Scrum (SAFe) | 27% (11%) | 32% (13%) | 46% (14%) |
| conflict, influence w/o authority | 27% | 24% | 24% |
| change management, adoption | 26% | 25% | 37% |
| incident, outage, root cause | 12% | 11% | 13% |
| audit, remediation | 9% | 10% | 13% |
| AML / KYC / fraud | 11% | 7% | 9% |
| SOX; Basel / CCAR / stress testing | 1%; 1% | 1%; 1% | 0; 0 |

- Required lines (521 of 812 TPM postings have them) carry far less: stakeholders 33%, delivery
  25%, risk 20%, system design 14%. Engineering background named in 256 TPM descriptions; "no
  coding" / "non-engineering role" said outright in 3 of 2,858.
- Interview format named in the posting: "panel interview" 0, "leadership principles" 3 => the
  employer's own hiring pages, not the posting, say who's on the loop.
- Finance-specific regulation is rare by name (SOX 0, Basel / CCAR 0 of 173 finance) - so the
  depth + case rounds stay posting-led, no finance question bank. Regex counts, rough (`onsite`
  also = work location; finance by company name).

## Compliance and risk (measured 2026-10-09)

852 US postings, 100 newest per title (compliance, AML, KYC, risk manager, risk analyst, credit
risk, model risk, third-party risk, internal audit, SOX; KYC 38, SOX 61), full text from the job
search; 498 carried a requirement list (the rest not yet read by the job search - newest rows).
What `interview` printed before this change = the requirement list only (14 at most, what to HAVE).
Same 498, a topic in the requirement list vs anywhere in the posting's text:

| Topic | Requirement list | Posting text |
|---|---|---|
| exam or audit work (regulatory exams, findings, remediation) | 47 | 179 |
| escalating, challenging the business | 113 | 341 |
| ethics, integrity, judgement | 63 | 212 |
| Basel / CCAR / CECL / stress tests | 10 | 35 |
| RCSA / KRIs / risk appetite | 11 | 36 |
| BSA / AML | 51 | 83 |
| background / credit check, fingerprinting | 3 | 26 |
| case study, take-home, written exercise | 0 | 0 |

=> `interview` quotes the posting's own sentence per kind (`posting_says`) - the "from the posting,
never a bank" rule stood; the input was the gap. After the change, hand-read 44 outputs: misreads
fixed before shipping - "data accuracy and integrity", "sample integrity" read as ethics (now a
person's integrity only), "regulatory issues" as exam work, "credit history" in a lending duty as a
check, drug screens (no record question). Left in: boilerplate "highest ethical standards" quotes,
an escalation that is a product's workflow - the posting's words, the AI picks.
Of the 498: rules named 260, risk methods 127, escalating 114, exam or audit 84, judgement 73,
checks 28; confidential work (posting or title) 275.
No posting named a case or take-home -> the Excel / SQL format is keyed to the invitation only.

| Rule | Basis | Strength |
|---|---|---|
| Duty sentences quoted from the posting, beside the requirement list | measurement above | our measurement |
| Ethics, escalation, rules, exam work, methods each tied to a quoted line | the posting's own duty; interviewers work from the same posting | convention |
| Confidential work: volume + outcome, no name, case or anything showing a SAR - in an answer too | 31 U.S.C. 5318(g)(2)(A)(i): no notice to anyone involved that a transaction was reported; 31 CFR 1020.320(e) (banks), 1023.320(e) (broker-dealers): "A SAR, and any information that would reveal the existence of a SAR, are confidential" | law (checked 2026-10-09) |
| Licences said as the resume says them | FINRA: representative exam valid 2 years after registration ends, up to 5 in MQP (`app/docs/resume/fair-screening.md`); BrokerCheck public | law (FINRA rules) |
| A firm sponsors representative exams; SIE needs none | FINRA SIE page: "Association with a firm is not required to take the SIE ... The individual must be associated with a member firm to take a qualification exam" | Maker's docs (`vendor docs`, regulator's page, checked 2026-10-09) |
| Record questions answered truthfully, matching U4 | FINRA Rule 3110(e): firm verifies a Form U4 within 30 calendar days, incl. a public-records search; Notice 15-05: at least criminal records, bankruptcies, judgments, liens (effective 2015-07-01). Form U4 Q14 areas: `fair-screening.md` | law |
| Bank record: FDIC consent, some records excluded | FDI Act Section 19 (12 U.S.C. 1829), FDIC page; 7-year + sealed / expunged exclusions (`fair-screening.md`) | law |
| Background / credit check consent | 15 U.S.C. 1681b(b)(2): standalone written disclosure + written OK; (b)(3): copy of the report + rights before adverse action. EEOC/FTC "Background Checks: What Employers Need to Know" (2014-03-11): same standards for everyone | law; agency guidance |
| Fingerprinting | 17 CFR 240.17f-2: broker-dealers' partners, directors, officers, employees (exceptions in (a)) | law |
| Form U5 | FINRA Form U5 page: filed within 30 days of the end date, states why they left, copy to the individual within 30 days | Maker's docs (regulator's page) |
| Personal trading, outside work | FINRA 3210 (prior written consent, accounts elsewhere; amended 2026-06-17, Notice 26-13); 3270 + 3280 (prior written notice) - Rule 3290 replaces both, SEC approved 2026-09-15, effective date to come (FINRA weekly archive 2026-09-16); 17 CFR 275.204A-1 (code of ethics, holdings report within 10 days, quarterly transactions within 30, pre-approval for IPOs + limited offerings) | law (recheck 3290's date) |
| Non-compete | FTC: "The Noncompete Rule is not in effect and it is not enforceable" (set aside 2024-08-20; appeal dropped 2025-09-05; removal notice 2026-02-12, title read only); FINRA 2140: no interfering w/ a customer's account transfer when the rep moves | law |
| Clawback | 17 CFR 240.10D-1: executive officers of listed issuers, accounting restatement, 3 prior fiscal years. Dodd-Frank 956 incentive-pay rule: not final (SEC agenda 2025, long-term actions; 2024 re-proposal by FDIC, OCC, NCUA, FHFA) | law |
| Model risk guidance | SR 26-2 (2026-04-17, Fed + OCC + FDIC) "supersedes and replaces SR letter 11-7" | law (agency guidance) |
| No pay or negotiation figure | as above: the offer's own figures; no dated source for compliance pay negotiation found or searched for in chat | convention |

Not covered: bankruptcy and private employers' hiring (11 U.S.C. 525(b) bars firing or discrimination
"with respect to employment" by a debtor's private employer; "deny employment" sits only in (a),
government) - courts split on hiring; never said in chat. Banks fingerprinting staff for Section
19: not verified from a primary page - never said.

Second pass (2026-10-09, fresh fetch: 743 postings, same 10 titles; 424 w/ a requirement list):
- Rule names the list missed, in the text: SAR 13, COBIT 14, GAAP / IFRS 15, FFIEC 11, FISMA / FedRAMP
  9, PATRIOT Act 8, PCAOB 8, CTR 7, CMMC 7, NYDFS 5; 21 of 424 got no `rules it names` line for it.
  Added, each hit read by hand; left out: CMS ("Compliance Management System"), SCRA (a job title's
  initials), the spelled-out Export Administration Regulations (hiring boilerplate), CRA, DORA,
  regulators. ITAR kept: 1 of 3 hits boilerplate. After: 251 of 424 carry the line (245 before).
- Lapsed licence (plan-2tk): "Series 7 (passed 2019; not currently registered)", "CPA (inactive)"
  counted as held - the job list said the ask was met. Now held = named w/o a lapse word in its own
  bracket or clause; ranking says "not current on your resume" + sorts it lower (never hidden), the
  pre-tailoring check + `interview` say it as the page does. A FINRA exam inside its 2-year window
  could count once a firm re-registers them (Rule 1210.08) - the resume carries no end date, so
  "not current" is what it says. Decision: our judgement, reversible.
- Rule 3290: no effective date yet - finra.org weekly archive 2026-09-16 ("FINRA will issue a
  regulatory notice to announce the effective date"), Regulatory Notices list read 2026-10-09 (latest
  26-17, on Rule 4515.01). 3270 + 3280 still apply.
- Students: 63 compliance / risk / audit internship + co-op postings, 44 w/ requirements: no SIE or
  Series ask; Excel 25, graduation timing 21, work authorization 16, GPA 12, ethics or integrity 11
  (text + requirements). Existing #Students rounds cover these; no new rule.

## During - never help in a live interview or open test

| Employer | Rule | Source |
|---|---|---|
| Anthropic | AI to prepare: encouraged; live interviews + take-homes: no AI unless told otherwise | "Candidate AI Guidance", 2025-07-10 |
| McKinsey | AI to practise or learn frameworks: fine; real-time answers + during assessments: no unless permitted; turn off AI note-takers in virtual interviews | McKinsey interviewing page (research pass 2026-10-08; review couldn't re-open it - recheck before quoting) |
| Amazon | no GenAI during interviews unless permitted, "may result in disqualification"; candidates acknowledge it | Business Insider via ITPro, 2025 (secondary - original not reached) |
| Google | at least one in-person round back, mainly engineering, over AI misuse in virtual rounds | Pichai, 2025 (secondary, accounts differ) |
| Test vendors | HackerRank, CodeSignal: tab monitoring, screen + video recording, AI-pattern flags (HackerRank advises a human review, not auto-reject) | vendor pages |

Not found: a count of candidates disqualified, or NACE data on it. NACE class of 2025: 33% of seniors
used AI in their search, 63.8% of those users for interview prep (a spring 2026 NACE report: 46% -
another year, never mixed); 15.9% of non-users feared the employer
would find out. Rule = Hold: the help itself is the risk, whatever the odds of being caught.

## Work permit + accommodation in interviews (general information, not legal advice)

| Question | What the sources say | Source |
|---|---|---|
| "Authorized to work in the US?" / "Now or in the future require sponsorship (e.g. H-1B)?" | DOJ's preferred wording; recommends asking about sponsorship rather than citizenship or immigration status - a best practice, not a ban; an employer may say it won't sponsor. F-1 holders aren't protected from citizenship-status discrimination (IER), are from national-origin discrimination | DOJ OSC (now IER) technical assistance letter 2013-09-06 (a scan - read via summaries: natlawreview.com); IER FAQ |
| F-1 answers | CPT / OPT = authorized for that time once approved, no employer sponsorship needed for it; "without restriction" No; "in the future" Yes for most (H-1B after OPT); give the CPT / OPT details; never misstate status; the DSO has the final word | CU Boulder career services, CMU OIE |
| Accommodation | before an offer: no questions likely to reveal a disability; may ask whether they can do the job + ask everyone whether they need an accommodation for the process; applicant asks orally or in writing, as soon as they know; documentation may be asked if not obvious; examples: extra time, test read aloud, a sign language interpreter; no change when the tested skill is the job | EEOC "Job Applicants and the ADA" (2003); 29 CFR 1630.13-.14 |
| Past pay | no federal ban; Virginia bars asking from 2026-07-01 (SB 215 / HB 636) | law (as of 2026-10-08) |
| "Many states and cities" | Fit Small Business tracker 2024-11: 22 states (counting DC) + 23 localities; other trackers 20-22 - so "many", never a count in chat. Offering what they're looking for instead: convention | news report + convention |

## Declined

- **A score for the interview.** No evidence a number helps; it invites gaming the score.
- **Model answers w/ facts filled in.** Words they could say may reframe their own facts, never add one.
- **Help during a live interview or open test, "just a hint".** Hold (#During).
- **A generic question bank for students.** Same as everyone: the posting or, without one, their resume.
- **A TPM / finance question bank** (SOX, Basel, CCAR cases). Rare in postings (above); questions stay
  posting-led for every occupation.
- **"System design for non-engineers" scripts from prep sites + forums** (Blind, Glassdoor, prep
  vendors): accounts disagree (coding asked or not, which level's bar); employer's own pages only.
- **A state-by-state non-compete list in chat.** Changes often; California's statute page (B&P
  16600, 16600.5) wouldn't open to check (2026-10-09) - say "states set their own rules", one example.
- **A count of states banning pay-history questions in chat.** Trackers disagree (20-22 states, DC counted in some); "many".

## Sources (checked 2026-10-08; program managers + compliance and risk 2026-10-09)

amazon.jobs/content/en/how-we-hire/tpm-interview-prep (five 55-min interviews, system design, STAR);
amazon.jobs/content/en/how-we-hire/interview-loop; aboutamazon.com/news/workplace/amazon-bar-raiser
(outside the hiring team, 16 Leadership Principles; undated); ftc.gov/legal-library/browse/rules/noncompete-rule;
malegislature.gov M.G.L. c.149 s.24L; freehire `/agent/jobs/search` 2026-10-09.


HireVue AI Explainability Statement (2022, 29 pages, served at hirevue.com/wp-content/uploads/2022/04/HV_AI_Short-Form_Explainability_1pager.pdf);
anthropic.com/candidate-ai-guidance (2025-07-10); mckinsey.com/careers/interviewing; ITPro on Amazon's
interview AI rule (2025); DOJ OSC letter 2013-09-06 (justice.gov/crt/about/osc/pdf/publications/TAletters/FY2013/171.pdf);
colorado.edu/career/how-answer-work-authorization-questions; cmu.edu/oie/employment/resources/work-authorization.html;
eeoc.gov/laws/guidance/job-applicants-and-ada; 29 CFR 1630.13-.14; NACE: student AI use (class of 2025),
Job Outlook 2026 spring update (2026-04-23), advisory opinion on offer deadlines, 2024 Recruiting
Compensation Report; practice.hirevue.com; natlawreview.com on the 2013 OSC letter + Virginia's law;
Robert Half / Accountemps press release 2017-11-20; Heimbaugh 2016 (irl.umsl.edu/dissertation/46);
fitsmallbusiness.com/salary-history-ban (2024-11). 2026-10-09: law.cornell.edu 31 U.S.C. 5318, 31 CFR
1020.320 + 1023.320, 15 U.S.C. 1681b, 17 CFR 240.17f-2, 17 CFR 275.204A-1, 17 CFR 240.10D-1, 11 U.S.C.
525; finra.org Rules 3110, 3210, 3270, 3280, 2140, Notices 15-05 + 26-13, weekly archive 2026-09-16,
SIE + Form U5 pages; fdic.gov Section 19; ftc.gov noncompete rule page; eeoc.gov background checks;
federalreserve.gov SR 26-2; reginfo.gov RIN 3235-AL06.
