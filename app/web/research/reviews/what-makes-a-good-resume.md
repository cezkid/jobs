---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session, bead plan-xsy.28 (no drafting context; sources opened before the draft was read)
---
# Review: What makes a good resume? The evidence, rule by rule (`what-makes-a-good-resume.md`)

Verdict **publish** after revision (plan-xsy.29): 2 high, 8 medium, 15 low findings, each fixed or rebutted below; first-pass verdict was revise. Numbers are mostly copied right - every
figure checked matched its source, page cites included. The problems are framing. The gap section
says Kroft 2013 shows "the same shape" as the meta-analysis when it shows the opposite for short
gaps, and the "under 6 months is a weak worry" advice rests on that. Typos are sold as the
strongest evidence when every typo study is a rating exercise. The ResumeGo critique gets the page
wrong, and a few citations hold up claims their source does not make (Levinson, MIT in the short
answer, two-column "as above").

## Sources, read before the draft (all opened 2026-10-03)

PDFs read as text (pymupdf): IZA DP 17141, NBER w18387, HBS Hidden Workers (Wayback copy), TheLadders 2012
(Wayback), Ruffle-Shtudiner 2011 WP, PLOS ONE Sterkens. Kristal via PubMed Central; web pages via
curl. No source contained text addressing an AI. The Onrec page carries unrelated spam links (not
instructions) - ignored.

| id | What it actually supports | Sample / design | Limits |
|---|---|---|---|
| hireright-2025 | Press release: "more than three-quarters of businesses have found candidate discrepancies" in the last 12 months; "Undisclosed criminal convictions and education and employment discrepancies were the most common types" (listed, not ranked) | Vendor survey, 1,000+ HR / risk / TA staff worldwide, Feb 11 - Mar 9 2025 | Seller of background checks; respondents are its market (firms that screen); wording unpublished; press release only |
| hireright-2025-sept | Sept 15 2025 release on the same survey: "Employment verifications remain the area most likely to reveal discrepancies across all regions - reported by 72% of respondents in APAC and 64% in EMEA" | Same vendor survey | No North America figure given; added plan-xsy.49 (opened 2026-10-03) |
| mit-capd-resumes | "accomplishments and contributions, not just responsibilities"; "Quantify if you can"; one page "unless you have extensive experience or an advanced degree"; no age, religion, health, marital status; photos "generally not preferred for U.S. resumes"; keyword scanning - use relevant words; proofread | Career office guide | Convention. Says nothing on 10-15 years, street address, 1-2 pages |
| harvard-ocs-resume | Top five mistakes incl. "Not demonstrating results", spelling and grammar errors; don't include a picture, age or gender | Career office guide | Convention |
| greenhouse-search | Full Text Search toggle on All Candidates; enter terms; matching candidates shown with a snippet. Updated June 6, 2022 | Maker's help page | Says nothing about synonyms or how often recruiters search |
| levinson-2012-cio | Repeats Preptel's claim that ATS "kill 75% of candidates' chances"; Preptel sells job-search help | 2012 trade article | Origin of the myth, not evidence against it |
| indeed-experience-2025 | Senior candidates in a similar field: reverse-chronological "up to the last 10-15 years"; most relevant qualifications at the top; less detail for older jobs; also suggests a functional format for gaps | Job-site advice, updated Dec 11 2025, republished by U. Wyoming | Convention; one guide |
| dhert-2024 | Meta of correspondence tests: ~67,000 applicants, 7 countries (p. 4, p. 8), 90 effects. Unemployed vs employed: 1-6 months +8.23% CI [-5.31, 23.69] (adjusted +16.72%, CI above 0); 13-18 months adjusted -21.38%; 19-36 months adjusted -27.02% (p. 15). Penalty clear after ~12 months; stronger in tight labor markets. Inactivity penalty heavier, few studies | IZA discussion paper, July 2024; still a discussion paper in search 2026-10-03 | Spells of *current unemployment* mostly; only 7 studies on former unemployment, 4 on inactivity. Outcome = positive callbacks, not interviews or hires. Funnel asymmetry in 7-12 and 19-36 months |
| kroft-2013 | ~12,000 resumes, ~3,000 US postings, 100 cities, sales / customer service / admin / clerical; callbacks fall sharply in first 8 months of unemployment then flatten; at 8 months ~45% lower than at 1 month (about 7% -> 4%); stronger when the labor market is tight | Large field experiment, 2011 | Compared with the newly unemployed, not the employed; one job band |
| fuller-2021 | p. 22: "48% of employers filtered middle-skills candidates based on employment gaps of more than six months"; Fig. 7 (p. 23) asked only those whose system ranks or filters | Survey, 2,275 executives US/UK/DE, Jan-Feb 2020 | Self-report; middle-skills figure; high-skills figure differs |
| namingit-2021 | 2018 conference abstract: 3,771 resumes, 1,257 sales / admin / accounting-assistant jobs, Mar-Sep 2016. Callbacks: newly unemployed 27.4%; illness gap explained 25.6%; unexplained 23.3%. Illness signalled by a cover-letter line + a cancer-support-group line on the resume | Field experiment | Numbers from the 2018 abstract, not the 2021 published paper (paywalled); no significance test in the abstract; gap length not stated there |
| kristal-2023 | UK, 9,022 applications (4 x ~2,255), pre-registered, mothers. Explained gap ("Left to become a full-time mother ...") b = -0.050 vs unexplained -0.049, both vs Years: no gain from the reason. Years-per-job format beat No Gap (b = -0.029 for No Gap, p = .038); abstract "approximately 8%". 2.5-year gap; 8 sectors | Large field experiment + lab follow-ups (N = 2,650) | One reason (childcare), mothers in the field study; Years format removes dates; funded via UK Government Equalities Office (design input) |
| sterkens-2023 | Vignette ("scenario") experiment, 445 Flemish HR professionals, graduate resumes with 0 / 2 / 5 errors. Interview item rated 0-10 ("I think that I will invite this applicant"): 2 errors -0.730 (= 7.3 points on 100), 5 errors -1.850 (p. 10). About half of the penalty via perceived interpersonal skills, conscientiousness, mental ability. Authors: measures "behavioural intentions rather than actual behaviour". Table 1: earlier studies all rating studies too | Lab study (survey experiment), April 2020 | Not real hiring; Belgium, Dutch; graduates only |
| resumego-2018 | 482 recruiters / HR / managers / execs; simulation; 5,375 of 7,712 picks were two-page (2.3x); entry 1.4x, mid 2.6x, manager 2.9x; scores 8.6 vs 7.1; 2:24 vs 4:05 reading. States one- and two-page versions "designed to showcase similar levels of work experience"; each one-page has a two-page counterpart | Vendor simulation (resume-writing firm) | Not peer-reviewed; two-page versions likely hold more detail; picks per participant not independent; registry label "vendor survey" fits poorly - it is a vendor test |
| ruffle-2015 | Israel, 5,312 CVs in pairs to 2,656 ads; one without photo, one with attractive or plain photo. Attractive men > no-photo men > plain men (attractive nearly double plain). No-photo women highest: 22% above plain, 30% above attractive. Photos optional in Israel ("some do, while others don't") | Large field experiment (2011 WP copy) | Israel; effect depends on gender and looks |
| ladders-2012 | 30 recruiters, 10 weeks, eye tracking; "6 seconds" on initial fit / no-fit; ~80% of time on name, titles, companies, dates, education; ends selling resume rewrites | Vendor test, not peer-reviewed | Small; sales document |
| ladders-2018 | Press release (Onrec repost, Nov 7 2018): 7.4 s initial screen; "top-performing resumes - where recruiters spent most time and focus": simple layouts, clear headers; worst: "Cluttered layouts characterized by long sentences, multiple columns, and very little white space", missing headers, keyword stuffing. Recruiter count not stated | Vendor test, press release | "Top" = attention, not ratings or hires; method unseen |

Also found (not cited; leads, open before citing):
- ResumeGo, "How Resume Employment Gaps Affect Interview Chances" - vendor test reporting a gap
  reason raised callbacks 6.8% vs 4.3%. Vendor, method unseen; contrary to Kristal. Name it in
  "What we don't know" only if opened and labelled.
- Behavioural Insights Team 2021 "CV trial report" (bi.team PDF) - likely the Kristal field
  study's own report; not opened.
- Weisshaar 2018 (US, opt-out parents) and Van Belle et al. 2018 - in D'hert's sample; open if
  the gap section is expanded.
- Search 2025-2026 found no newer meta-analysis on gaps, no field experiment on spelling errors
  with real employers, no study testing results lines vs duty lines, and no peer-reviewed study
  of resume length. D'hert still listed as IZA DP 17141 (not yet in a journal).

## Claim table

42 citation markers in the article (42 id citations, 16 distinct ids); 88 rows below.

| # | Line | Claim | Source | What the source says | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|---|
| 1 | 2 | Title "What makes a good resume? The evidence, rule by rule" | - | 52 chars; matches intent | Supported | - | - |
| 2 | 3 | Description: "Strongest - typos and long gaps cost interviews" | sterkens; dhert | Typos: rated intention; gaps: callbacks | Overstated | medium | F4 |
| 3 | 3 | Description: most format rules are convention | mit; harvard | Yes | Supported | - | - |
| 4 | 7 | og_title | - | 62 chars | Supported | - | - |
| 5 | 17 | Employer, title, dates must match; mismatches get found (Vendor survey) | hireright-2025 | 3/4+ found discrepancies; vendor | Supported | low | F21 |
| 6 | 18 | Typos: 2 errors, 7 points lower chance (Lab study) | sterkens-2023 | 7.3 points on a 0-100 rating of intention | Needs caveat | medium | F3: "rated", "out of 100" |
| 7 | 19 | Long breaks cost replies; 1-6 months no clear cost (Big study) | dhert-2024 | True for current unemployment vs employed; Kroft finds the steepest drop in months 1-8 | Needs caveat | high | F1, F2 |
| 8 | 20 | Results over duties, 1-2 pages, 10-15 years, no photo: convention, no study | mit-capd-resumes | MIT: results yes; one page; nothing on 10-15 years; photo has a field experiment (Ruffle) | Misattributed | medium | F8 |
| 9 | 24 | Four jobs; order is our rule | - | Stated as our rule | Supported | - | - |
| 10 | 26 | Most resume advice never tested in real hiring | - | Consistent with search; no source | Supported, uncited | low | F9 |
| 11 | 28 | Rules with studies: accuracy, typos, breaks | - | Accuracy = vendor survey only; typos = rating studies | Overstated | low | F3 |
| 12 | 32 | Employers check work history; mismatches common enough to get caught | hireright-2025 | Respondents are firms that buy screening | Needs caveat | low | F21 |
| 13 | 32 | 2025 HireRight survey: 3/4+ found a mismatch in past year | hireright-2025 | "More than three-quarters ... last 12 months" | Supported | - | - |
| 14 | 32 | Most common: criminal records, education, work history; work history checks find most in every region (72% APAC, 64% EMEA) | hireright-2025, hireright-2025-sept | June lists three types unranked; Sept gives the regional figures (plan-xsy.49) | Supported | - | - |
| 15 | 34 | Wording not published; shows employers check, not cost | hireright-2025 | Correct limit | Supported | - | - |
| 16 | 36 | Match what a past employer would confirm; anything can come up in interview | - | Advice | Supported (advice) | - | - |
| 17 | 40 | Guides: show achievements | mit; harvard | Yes | Supported | - | - |
| 18 | 40 | MIT quote "accomplishments and contributions, not just responsibilities" | mit-capd-resumes | Exact, 6 words | Supported | - | - |
| 19 | 40 | Harvard lists "not demonstrating results" | harvard-ocs-resume | Exact, top five mistakes | Supported | - | - |
| 20 | 42 | No study tested results vs duty lines | - | None found in this review's search either | Supported, uncited | medium | F9: record searches |
| 21 | 44 | A result needs no number; unexplainable number hurts more | - | Our reasoning; MIT says "Quantify if you can" | Needs caveat | low | F16 |
| 22 | 50 | Recruiters can search stored resumes for words | greenhouse-search | Full Text Search | Supported | - | - |
| 23 | 50 | "much like a web search" | greenhouse-search | Not stated; gloss | Supported (gloss) | low | - |
| 24 | 50 | Skill named differently may not come up | greenhouse-search | Inference from word search | Needs caveat | low | "may" fine; say it is our reading |
| 25 | 52 | Rule rests on software design; no large study on interviews | - | Consistent with search | Supported, uncited | medium | F9 |
| 26 | 52 | Claim that software rejects most resumes does not hold up | levinson-2012-cio | Levinson *repeats* the 75% claim | Misattributed | medium | F5 |
| 27 | 54 | Lacked skill = gap; adding word invites questions | - | Advice | Supported (advice) | - | - |
| 28 | 58 | Career guides suggest last 10-15 years | indeed-experience-2025 | One guide, senior candidates, similar field | Overstated | low | F18 |
| 29 | 58 | Quote "up to the last 10-15 years" | indeed-experience-2025 | Exact | Supported | - | - |
| 30 | 58 | Put most relevant work first | indeed (implied) | Indeed: relevant qualifications at top, jobs reverse-chronological | Needs caveat | low | F18 |
| 31 | 60 | Convention, no study; older jobs as short lines | indeed (implied) | Indeed: less detail for older jobs | Supported | low | cite it |
| 32 | 66 | Long gaps cost replies; short showed no clear cost | dhert-2024 | Yes vs employed; Kroft differs | Needs caveat | high | F1 |
| 33 | 66 | 2024 review, ~67,000 applicants, 7 countries, p. 8 | dhert-2024 | 67,000 on p. 8; "seven countries" on p. 4 | Supported | low | F20 |
| 34 | 66 | 1-6 months no clear effect, p. 15 | dhert-2024 | +8.23% CI incl. 0 (adjusted +16.72%, above 0) | Supported | low | optional: "if anything, slightly more replies" |
| 35 | 66 | 13-18 months cut ~21% | dhert-2024 | Adjusted -21.38% (unadjusted -20.78%, CI incl. 0) | Supported | - | - |
| 36 | 66 | 19-36 months cut ~27% | dhert-2024 | Adjusted -27.02% | Supported | - | - |
| 37 | 66 | "gap" = the measured thing | dhert-2024 | Mostly current unemployment, not a past break between jobs | Needs caveat | medium | F2 |
| 38 | 66 | Discussion paper, not peer-reviewed | dhert-2024 | Still IZA DP | Supported | - | - |
| 39 | 68 | Kroft found "the same shape" | kroft-2013 | Steepest fall in first 8 months (~45% lower at 8 vs 1 month) | Misstated | high | F1 |
| 40 | 68 | ~12,000 made-up resumes | kroft-2013 | "roughly 12,000" | Supported | - | - |
| 41 | 68 | Fell over first 8 months, then flat | kroft-2013 | Yes | Supported | - | - |
| 42 | 70 | Some screening software filters gaps | fuller-2021 | Executives say so | Supported | - | - |
| 43 | 70 | 48% of executives whose software ranks or filters said it filtered gaps over 6 months | fuller-2021, p. 22-23 | 48% for middle-skills candidates | Needs caveat | low | F12 |
| 44 | 70 | Answers, not a measurement | fuller-2021 | Right | Supported | - | - |
| 45 | 72 | Gaps under ~6 months a weak worry | dhert; kroft | Contradicted by Kroft | Overstated | high | F1 |
| 46 | 76 | Studies disagree | namingit; kristal | Yes | Supported | - | - |
| 47 | 76 | US field experiment, cover letter illness + recovered did a little better | namingit-2021 | Yes, plus a cancer-support line on the resume | Needs caveat | low | F10 |
| 48 | 76 | 25.6% vs 23.3% | namingit-2021 | From 2018 abstract | Needs caveat | medium | F10 |
| 49 | 76 | Open summary silent on chance | namingit-2021 | Correct | Supported | - | - |
| 50 | 78 | Larger UK experiment: no gain from a reason | kristal-2023 | b -0.050 vs -0.049 | Supported | low | F11: one reason, mothers |
| 51 | 78 | 2.5-year gap, full-time childcare reason | kristal-2023 | Exact | Supported | - | - |
| 52 | 78 | Years per job raised replies ~8% over no-gap resumes | kristal-2023 | Abstract "approximately 8%" | Supported | low | say the format drops dates |
| 53 | 80 | One-line reason cheap; no study shows it reliably helps | namingit; kristal | Fair | Supported | - | - |
| 54 | 80 | Bias is the employer's | - | Framing rule | Supported | - | - |
| 55 | 80 | Forms often ask for exact dates | - | Uncited, plausible | Supported, uncited | low | our measurement (Workday) or drop "often" |
| 56 | 84 | Typos among the best-tested resume rules | sterkens-2023 | All tests are rating studies (Table 1) | Overstated | medium | F3 |
| 57 | 84 | 445 recruiters in Belgium rated graduate resumes | sterkens-2023 | HR professionals in Flanders | Supported | low | F25 |
| 58 | 84 | 2 errors: rated chance -7.3 points | sterkens-2023 | -0.730 on 0-10 | Supported | low | "out of 100" |
| 59 | 84 | 5 errors: -18.5 points, p. 10 | sterkens-2023 | Exact, p. 10 | Supported | - | - |
| 60 | 86 | About half via less careful / able / worse with people | sterkens-2023 | Conscientiousness, mental ability, interpersonal | Supported | - | - |
| 61 | 86 | Rated, not hired -> lab study | sterkens-2023 | Authors say intentions | Supported | - | - |
| 62 | 92 | One page students; two common with experience | mit-capd-resumes | MIT: one page unless extensive experience | Supported | - | - |
| 63 | 92 | MIT quote | mit-capd-resumes | Exact | Supported | - | - |
| 64 | 94 | ResumeGo simulation, 482 people | resumego-2018 | Yes | Supported | - | - |
| 65 | 94 | 5,375 of 7,712 picks two-page | resumego-2018 | Exact | Supported | - | - |
| 66 | 94 | Page doesn't say whether two-page held more experience | resumego-2018 | Page says versions designed to show similar experience | Misstated | medium | F6 |
| 67 | 96 | Our measurement: 98 cpl = 2 pages; 91 cpl = 3 pages, 19 near-empty lines | typeface.md:18-31 | Matches table (Caladea vs Gelasio / Charis) | Supported | low | F22: say when + how |
| 68 | 102 | MIT: no age, religion, health, marital status; photos "generally not preferred" | mit-capd-resumes | Exact | Supported | - | - |
| 69 | 104 | Israel, 5,312 resumes, 2,656 ads; attractive men more replies with photo; no-photo women most | ruffle-2015 | Exact | Supported | - | - |
| 70 | 104 | Photos common in Israel | ruffle-2015 | Optional; some do | Overstated | low | F19 |
| 71 | 106 | Street address adds little; city + state usual; convention | - | No guide cited | Unsupported | low | F17 |
| 72 | 112 | 2018 Ladders: top-rated had simple layouts; poor had clutter, several columns, missing headings | ladders-2018 | "Top-performing" = most attention; columns listed | Needs caveat | low | F13 |
| 73 | 114 | Our measurement: "EXP E R I ENC E"; right-edge dates read after bullets; Workday degree box | page-format.md:13, :60; bullets.md:90-95 | Match; three PDF readers read the heading whole | Supported | low | F15, F22 |
| 74 | 116 | Use one column, plain headings, black text | ladders-2018; own | Weak support | Needs caveat | low | label "vendor test" |
| 75 | 120 | 6 seconds: 2012, 30 recruiters, job site; first glance | ladders-2012 | Yes; 2018 update says 7.4 s | Supported | low | F14 |
| 76 | 121 | 75%: 2012 sales claim, no method | levinson-2012-cio | Yes | Supported | - | - |
| 77 | 122 | Number-every-line advice pushes people to make up numbers | - | Causal, no source | Unsupported | low | F16 |
| 78 | 123 | Keywords only for skills you have | - | Advice | Supported | - | - |
| 79 | 124 | No published method links 0-100 scores to interviews | - | Absence; searches not recorded | Supported, uncited | medium | F9 |
| 80 | 125 | Two-column templates read worse by software and invite bias, "as above" | - | No two-column measurement above; bias = photo only | Unsupported | medium | F7 |
| 81 | 126 | Some PDF readers split spaced headings | page-format.md:13 | One PDF-to-HTML converter; three extractors read it whole | Overstated | low | F15 |
| 82 | 130-134 | What we don't know list | - | Good; missing Kroft vs D'hert disagreement, typo studies all ratings | Needs caveat | medium | F1, F3 |
| 83 | 138 | Match records | hireright-2025 | Ok | Supported | - | - |
| 84 | 139 | Proofread | sterkens-2023 | Ok | Supported | - | - |
| 85 | 140 | Keep gaps short where you can; longer cost more | dhert-2024 | Ok on data; reads as advice the reader often can't act on | Needs caveat | low | F24 |
| 86 | 141 | Leave off photo + personal details | mit-capd-resumes | Ok | Supported | - | - |
| 87 | 142 | Plain one-column page | ladders-2018 | Vendor press release | Needs caveat | low | F13 |
| 88 | 148-152 | Tool box | app code | `lint.py` spelling (one-letter typos) + `british()`; gates `single-column`, `no-images`, `text-color`, `split-words`; `street-address` warning | Supported | - | - |

Source-id check: all 17 ids cited in the article appear above (dhert-2024, fuller-2021,
greenhouse-search, harvard-ocs-resume, hireright-2025, hireright-2025-sept, indeed-experience-2025, kristal-2023,
kroft-2013, ladders-2012, ladders-2018, levinson-2012-cio, mit-capd-resumes, namingit-2021,
resumego-2018, ruffle-2015, sterkens-2023).

## Findings

Status after revision (plan-xsy.29): each finding marked fixed or rebutted, with what changed.

- **F1 (high, fixed)** Kroft is not "the same shape". Kroft: callbacks fall about 45% over the
  first 8 months (vs the newly unemployed); D'hert: 1-6 months no cost vs the employed. Fix:
  say the studies differ and why (different comparison group; Kroft US sales/admin 2011, tight
  markets). Soften line 72 "under about 6 months are a weak worry" and the short-answer gap line;
  add the disagreement to "What we don't know".
  -> gap section opens "for short spells, the two main studies disagree"; Kroft paragraph says it found something different, gives the ~45% at 8 vs 1 month and its comparison group; "weak worry" line + short-answer bullet softened; disagreement added to What we don't know
- **F2 (medium, fixed)** D'hert and Kroft measure *current* unemployment, not a past break
  between jobs. Article says "gap" / "break" throughout. Fix: one sentence naming what was
  tested; D'hert has only 7 studies on former unemployment, 4 on inactivity (penalty heavier).
  -> one paragraph says most studies tested people out of work now, only 7 on a past break, inactivity tested less and cost more; What we don't know line added; body says "time out of work" where the studies did
- **F3 (medium, fixed)** Typos oversold. Every typo study (Sterkens Table 1) asks raters, none
  real employers. "Among the best-tested" + description "Strongest" + short answer "lower
  chance" read as hiring evidence. Fix: "best-studied in rating tests"; short answer "rated
  chance, 7 points out of 100".
  -> section opens "Probably, though no study has tested them in real hiring. Every typo study we found asked people to rate resumes"; short answer says "rated interview chance 7 points lower out of 100"; description says typos "lower recruiter ratings"; What we don't know line added
- **F4 (high, fixed)** Description says gaps and typos "cost interviews". Gaps cost callbacks;
  typos lowered ratings. Search snippets quote the description alone. Fix wording, e.g. "long
  gaps cost callbacks, typos lower recruiter ratings".
  -> description now "Long gaps cost callbacks; typos lower recruiter ratings"
- **F5 (medium, fixed)** Line 52 cites Levinson as showing the claim does not hold up; Levinson is
  where the claim appears. Fix: cite it as the origin, keep the link to the ATS article for the
  rebuttal.
  -> Levinson cited as where the claim traces to (a 2012 trade article repeating a sales pitch); rebuttal left to the ATS article link
- **F6 (medium, fixed)** Line 94 says ResumeGo doesn't say whether two-page resumes held more
  experience; the page says each pair was designed to show similar experience. Fix: real limits -
  vendor, simulation, two-page versions carry more detail, not peer-reviewed. Consider a registry
  label other than "vendor survey" for vendor tests (ResumeGo, Ladders 2012/2018) - research.md has
  no row for a vendor experiment; Lab study + vendor note fits the design better.
  -> sentence now says the company states both versions showed similar experience, the two-page ones held more detail, seller's own test, not peer-reviewed, not real hiring. Registry label kept as `vendor survey`: research.md has no vendor-experiment row, and its "company selling the service" caution is the one that matters; text calls it a test, never a study
- **F7 (medium, fixed)** Line 125 "two-column ... read worse by software and invite bias, as
  above": no two-column measurement is shown above, and bias applies to photos. Fix: cite the
  right-edge dates measurement + Ladders 2018 (vendor) for columns; bias for photos only.
  -> split into two bullets - two-column cites our right-edge dates measurement + Ladders 2018 as a vendor test; photo bullet cites Ruffle for bias
- **F8 (medium, fixed)** Short answer bullet 4 cites MIT for "1-2 pages, last 10-15 years, no
  photo ... no study". MIT says one page; 10-15 years is Indeed; photos have a field experiment
  (Ruffle). Fix: split the bullet or cite each.
  -> short-answer bullet split - results + one page cite MIT; 10-15 years cites Indeed; photo cites Ruffle (Big study)
- **F9 (medium, fixed)** "No study found" claims (results vs duties, keywords, 0-100 scores) have
  no search record. research.md: list what was searched in the page's `uncited:` list. Fix: add
  the searches (this review's: field experiments on achievements vs duties, keyword match vs
  callbacks, resume-score validation; none found).
  -> body says "we searched ... and found none" for results vs duties, posting words, 0-100 scores; the searches are listed in the page's `uncited:` list
- **F10 (medium, fixed)** Namingit numbers come from a 2018 conference abstract, not the 2021 paper.
  Say so in the sentence ("an early summary"). Also: the illness signal included a cancer
  support-group line on the resume.
  -> sentence says "an early summary of that study reports"; illness signal described as on the resume and cover letter; registry venue already names the 2018 abstract
- **F11 (low, fixed)** Kristal tested one reason (full-time motherhood) for mothers. Say "a
  childcare reason" rather than "a reason".
  -> "no gain from a childcare reason"; "Mothers' resumes"; years format noted as hiding the gap
- **F12 (low, fixed)** Fuller 48% is for middle-skills candidates; add the words.
  -> "filtered middle-skills applicants"; sentence split, now under 20 words each
- **F13 (low, fixed)** Ladders 2018 "top-performing" = where recruiters looked longest, not rated
  best; name it a vendor test in the sentence.
  -> "resumes that held recruiters' attention longest"; "It is a vendor's test"
- **F14 (low, fixed)** 6-second bullet: add the 2018 update (7.4 s) and that a resume-writing firm,
  ResumeGo, timed 2-4 minutes in a simulation - the number depends on the task.
  -> 6-second bullet adds the 2018 update (7.4 s) and ResumeGo's 2-4 minutes, "the number depends on the task"
- **F15 (low, fixed)** Line 126 "Some PDF readers split the word": our own note says three
  extractors read it whole; one PDF-to-HTML conversion split it. Say that.
  -> "one PDF-to-web-page converter"; "Three other PDF text readers read it whole"; myths bullet matches
- **F16 (low, fixed)** Line 122 "pushes people to make up numbers": causal, no source. Reword as
  our reason ("invites made-up numbers").
  -> "Our view: the advice invites made-up numbers"; MIT's "add numbers where you can" now cited next to our view
- **F17 (low, fixed)** Street address rule uncited; cite a guide that says it or call it our rule.
  -> "Leaving it off is our rule"
- **F18 (low, fixed)** "Career guides suggest" 10-15 years rests on one guide for senior
  candidates; and "most relevant first" may read as breaking reverse-chronological order.
  -> "One job-site guide tells senior candidates"; newest-first order + less detail for older jobs cited to Indeed; "most relevant first" removed
- **F19 (low, fixed)** Ruffle: photos optional in Israel, not "common".
  -> "Photos are optional in Israel"
- **F20 (low, fixed)** D'hert "7 countries" is on p. 4; p. 8 has the 67,000.
  -> 67,000 cites p. 8; 7 countries cites p. 4
- **F21 (low, fixed)** HireRight respondents are firms that buy screening; "employers check"
  generalizes. Add "firms that run checks" or similar.
  -> short answer "Firms that check find mismatches"; body "Many employers check" and "the people it asked work at firms that run checks"
- **F22 (low, fixed)** Our-measurement sentences should say when + with what (research.md: "the
  article says how"): fonts September 2026, pdftotext for the dates, Workday September 2026.
  -> "Our measurement, September 2026" on both; pdftotext named for the dates; PDF-to-web-page converter + three readers named for the heading; Workday measured September 2026 (bullets.md)
- **F23 (low, rebutted)** Link `keep-chats-out-of-ai-training` once that article exists (bead lists
  it); not yet in `app/web/research/`.
  -> keep-chats-out-of-ai-training does not exist yet (plan-xsy.30); a link to it would break the build. Note left on plan-xsy.30 to link back here once it publishes
- **F24 (low, fixed)** "Keep gaps short where you can" reads as on the applicant; gaps are often
  not a choice. Reword to what helps once a gap exists.
  -> What helps now "After a long gap, a short, honest reason costs little. The bias grows with time out of work, and it is the employer's"
- **F25 (low, fixed)** Sterkens: Flemish raters, Dutch-language graduate resumes; one line on
  how far that carries to US hiring.
  -> "The resumes were in Dutch, for recent graduates, so US results may differ"

Plain words + SEO: no jargon from the AGENTS.md list; most sentences under 20 words (line 70 is
21); question-led H2s; 4 internal links; title 52, description 140 chars. Privacy: no owner data
or real employer in examples; measurements cite numbers only. Quotes all <= 15 words and
attributed. Tool box sits after the evidence and matches the code.

## Re-review 2026-10-03: citations thinned (plan-xsy.48)

Citation placement only - no wording, number or source changed. A run of sentences citing the
same source now cites it once, at the run's end (build rule: 3 in a row = error). Checked: every
sentence the moved citation now covers comes from that source.
16 repeat citations dropped. Newly under a citation: "The same study tried listing years worked
per job instead of dates, which hides the gap" (kristal-2023 design). Supported.

## Re-review 2026-10-04: voice pass (plan-xsy.53)

Voice only. Short answer "convention (Convention)" -> "career-guide advice (Convention)" for mit-capd-resumes and indeed-experience-2025 - both registry `convention`; singular "career-guide advice" does not reopen F18 (one guide). Ten section endings lost "For you," (no opener, "So", "In practice,"); "the employer name" -> "Your employer name", same meaning (optional nit: "Each employer name, job title and dates" avoids reading as current employer only). Home-page line; `modified` 2026-10-04. Checked: each changed line keeps its meaning, scope, hedging and evidence label; section endings still say what the finding means for the reader; no new "this"/"it" across sentences; no app jargon; closing line "CEZ Job Finder is a free job-search app for Windows and Mac" matches docs/index.html title + og:title; link is our own home page. No blocking finding.

Optional nit applied: "Each employer name, job title and dates".

Short answer merge (plan-xsy.53): checked the merged bullet 4 (two Convention bullets + photo bullet) against the claim table rows 8, 28 and F8/F18. Photo sentence keeps its own label and citation (Big study, ruffle-2015) - fine. Finding (medium, reopens F8 + F18): the Convention half now runs three claims under one "career-guide advice, no study" with a pooled [@mit-capd-resumes; @indeed-experience-2025]. "No study" was searched for and stated only on results-over-duties / one page (MIT row); it now also covers "last 10-15 years", which had no such search - a broader claim. Pooled citation hides that MIT says nothing on 10-15 years and Indeed nothing on results or one page - the F8 fix was "cite each". Fix, still 4 bullets: replace bullet 4 with "- Results over duties, one page early on: career-guide advice, no study (Convention) [@mit-capd-resumes]. Last 10-15 years in detail: one career guide (Convention) [@indeed-experience-2025]. No photo: one field experiment found photos help some, hurt others (Big study) [@ruffle-2015]."

Revised (plan-xsy.53): bullet 4 replaced with the exact fix above; verdict publish.

## Re-review 2026-10-04: summary table (plan-xsy.54)

New section "Which resume rules have evidence behind them?": lead, an 11-row table (rule | evidence | what it shows) and a closing line. No other text changed. Checked each row against the source table above, sources.yml `evidence`/`sample`/`preprint`, and the body section it sums up. Numbers match source and body (HireRight "more than three-quarters", Sterkens 7.3 of 100, D'hert -21% at 13-18 months p. 15, Kroft first 8 months, Namingit 25.6 vs 23.3, Kristal childcare no gain, Ruffle, Ladders 2018); labels match the registry (hireright + ladders `vendor survey`, sterkens `lab/LLM audit`, dhert `meta-analysis` + preprint, kroft + kristal + ruffle `large field experiment` = Big study, namingit `field experiment` = Small study, greenhouse `vendor docs`, MIT/Harvard/Indeed `convention`); every row carries a citation; no app jargon; lead and closing read alone. No blocking finding. Findings:
1. Medium. Row "Short spells out of work", Evidence cell "Big study; studies disagree" drops the preprint tag the row leans on (the review half is dhert-2024, `preprint: true`; row 3 says it). Replace with: "Big study (the review not yet peer-reviewed); studies disagree".
2. Medium. Row "A reason for a gap helps", What it shows: "found a small gain" drops the body's hedge ("That summary does not say whether the difference could be chance"). Replace with: "One US study's early summary found slightly more replies with an illness reason, without saying if that could be chance; a UK study found none for a childcare reason [@namingit-2021; @kristal-2023]".
3. Low. Row "Use the posting's words for skills you have": "no study of interviews found" is broader than the body ("found none" for a large study) and the `uncited:` search (posting-word match versus callbacks). Replace with: "Recruiters can search stored resumes by word; no large study of interviews found [@greenhouse-search]".
4. Low. Row "Last 10-15 years in detail": the guide says it for senior candidates (source table: "Senior candidates in a similar field"), and "no study found" has no search recorded in `uncited:` (same point as the plan-xsy.53 short-answer finding; the body's "with no study behind it" shares it). Replace with: "One job-site guide says so for senior candidates; no study cited [@indeed-experience-2025]" - or add that search to `uncited:` and keep "no study found".
5. Low. Closing "rest on convention or a seller's test": two of the non-study rows are a survey (HireRight) and a help page (Greenhouse), not tests. Replace with: "Most rules in the table rest on convention or a company's own survey, test or help page. Only a few have studies of real hiring behind them."

Revision (plan-xsy.54, 2026-10-04): findings 1-5 fixed with the proposed wording (finding 4: "no study cited", table only; the body sentence stays as flagged in plan-xsy.53).

## Edit after review (2026-10-04, plan-xsy.63)

Added one link line in "Does layout matter?" to the layout-test data page (resume-parser-test-2026-10). Navigation only; no claim, number or source changed. The article on the test (plan-xsy.64) links it properly.
