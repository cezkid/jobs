---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session, bead plan-xsy.22 (no drafting context; sources opened before the draft was read); revision checked in plan-xsy.23
---
# Review: Is AI resume screening biased? (`ai-resume-screening-bias.md`)

Verdict **publish** (after revision, 2026-10-03; first verdict was revise): 3 high, 7 medium, 10 low findings, all fixed - see Revision below. The study numbers are mostly copied
right, and the Wilson & Caliskan correction is handled well. The problems: the "removing your
name" section misstates what the Chen & Xiao preprint tested, the Mobley + law sections are a
step behind October 2026, and three must-cover items are missing (Bloomberg 2024, California's
rules, a human-vs-algorithm field comparison).

## Sources, read before the draft (all opened 2026-10-03)

No source contained text addressing an AI. EUR-Lex returns a bot challenge to plain fetches;
Annex III point 4 was read word for word on a mirror (artificialintelligenceact.eu/annex/3) -
reviser: open the EUR-Lex page in a browser. Reuters read in the Wayback copy via a plain download.

| id | What it actually supports | Sample / design | Limits |
|---|---|---|---|
| wilson-caliskan-2024 | 3 text-matching (embedding) models pick the top 10% of resumes for a job description. White names preferred in 85.1% of 27 tests, Black names in 8.6%. White male over Black male in 100% of tests; Black female over Black male 66.7%. v3 note (2026-08-29): a code bug - gender-only results "should be inverted"; race-only + intersectional unaffected and replicated by a Salzburg team. Body text of v3 still prints the old gender numbers (male 51.9%, female 11.1%) | 500+ public resumes, 9 occupations, 120 names (20 per group + 40 frequency-matched), lab | Retrieval models, not generative screeners; document length + name frequency also change outcomes |
| an-2025 | 4 of 5 models give "significantly higher" scores to female OR Black candidates vs white men; driven by women; Black men scored lower "by most of the models" (Llama 3-70b not significant). GPT-3.5: Black women +0.379, white women +0.223, Black men -0.303 points of 100. At a score-80 cutoff (~35% pass) Black women +1.7 pp, white women +1.4, Black men -1.4 vs white men (GPT-3.5 example) | ~361,000 made-up resumes, 20 entry-level jobs, 5 models, temperature 0 | US names only; entry-level; one resume format; snapshot |
| rozado-2026 | 22 models, 70 jobs, 30,800 pair decisions: female names picked 56.9%, significant in every model. Gender field added: 58.9%. Candidate A/B labels: 52.3% A. First-listed picked 63.5%, 21 of 22 models significant (Cohen's h 0.55 vs 0.28 for gender). Rated alone 1-10: 8.65 vs 8.61, negligible, no model significant | Lab, made-up CVs closely matched | Synthetic CVs; numbers from arXiv copy, peer-reviewed version unopened |
| gao-2026 | Preprint, June 2026. GPT-3.5 (2023) +2.12 pp pro-White callback; every 2024+ model null or pro-Black (7 at 1%, 2 at 5% that fail Bonferroni, 4 null); gender: GPT-3.5 +1.92 pp pro-male, 10 of 12 later models pro-female (Gemma's -0.18 fails Bonferroni), 2 null | 14 models (13 on gender), 24,024 race pairs per model from 6,007 real entry-level postings, yes/no phone screen, temperature 0 | No limits section; entry-level only; one prompt |
| chen-xiao-2026 | Preprint. Names absent; ethnocultural cues injected into an "Additional Information" section at 3 strengths (explicit, community, subtle); languages held identical. Group recovery 0.757 average, 1.000 at explicit tier, 0.086-0.690 at subtle tier. Forced choice: apparent ratio 0.39 with position + content effects; ties allowed: >= 94% ties "for most models". Scoring: "only very small" differences | 9 open models, 620 resumes, 5 groups (Anglo, First Nations, Chinese, Indian, Vietnamese), Australian context | Authors: recoverability does not show an effect on hiring |
| bone-2026 | COLM 2026. Post-trained models 3.6% less likely to call back older applicants than their base versions, 8 of 10; exclusion from all models 5.6% -> 17.3%. Models tend to prefer Black, female, younger applicants. Age = graduation year, under 35 vs over 45 | 10 open models, base + post-trained, pairs of made-up applicants, US vacancy data | Binary groups; snapshot; no full job text |
| glazko-2024 | GPT-4 web UI: disability-enhanced CV ranked first 15 of 60 (autism 0/10, deaf 1/10, depression 2, cerebral palsy 2, blind 5, general 5). Custom GPT trained on DEI + disability-justice principles: 37 of 60 | 6 disabilities x 10 trials, one resume | Authors: "did not do large-scale testing"; GPT-4 of early 2024 |
| tamkin-2023 | Preprint (Anthropic). Claude 2.0, 70 decision types incl. "making a job offer" (2 of 70). Positive discrimination for non-male genders and non-white races, negative for ages over 60; much smaller when inferred from names; prompt interventions cut both | Model-written prompts with age/race/gender slots | Not hiring-specific; authors do not endorse automated decisions |
| bommasani-2026 | FAccT '26. pymetrics games (12-16), not resumes; scores binarized recommend / not. 10.62% of positions adversely impact Black applicants (US standard); 25.87% of Black applicants' applications go to them (Asian: 14.74%). Of applicants applying to 10 positions, 4% rejected from all, above chance. Gameplay reused for 330 days; 42 models used at several employers | 4,197,168 applications, 3,372,132 applicants, 1,746 positions, 156 employers, Dec 2018-Dec 2022 | One vendor; pre-generative-AI; mostly North America |
| wilson-2025 | 528 people, 1,526 cases, 16 occupations, simulated AI with set race preferences; follow it up to 90%; unbiased or no AI -> equal picks; IAT first raised counter-stereotype picks ~13% | Lab with people | Simulated AI, names only |
| dastin-2018 | Reuters 2018-10-10: built from 2014, 1-5 stars; by 2015 not gender-neutral; trained on 10 years of resumes mostly from men; penalized "women's", downgraded two all-women's colleges; team disbanded by start of 2017; recruiters looked at but "never relied solely"; Amazon: tool "was never used by Amazon recruiters to evaluate candidates" | 5 unnamed sources | News report |
| eeoc-itutorgroup-2023 | 2023-09-11: $365,000; alleged software auto-rejected women 55+ and men 60+, over 200 applicants; training, policy, 5-year monitoring; no admission stated | Agency release | Allegation + settlement |
| mobley-2025-order | 2025-05-16 order: claims of race, age, disability bias; preliminary ADEA collective granted; Workday's "1.1 billion applications were rejected" estimate | Court order | Allegations only |
| lawyer-monthly-2026 | 2026-09-21: class motion, 4 subclasses (Black, women, 40+, disabilities), hearing 2027-03-09, Workday denies | News | Event only |
| nyc-ll144 | Audit within one year before use, public summary, notice 10 business days ahead; enforced 2023-07-05 | Agency page | Page not updated since 2023 |
| wright-2024 | 391 employers checked by 155 student investigators: 18 audits, 13 notices; "null compliance" from employer discretion | Observational | Students as job seekers; FAccT 2024 |
| nys-comptroller-2025 | 2025-12-02: July 2023-June 2025, 2 complaints; city found 1 issue in 32 companies, auditors 17 potential | State audit | About enforcement, not bias |
| il-hb3773 | PA 103-0804, signed 2024-08-09, effective 2026-01-01: AI with discriminatory effect + zip code proxy = violation; notice required | Bill status page | Rules by IDHR not read |
| co-sb26-189 | Signed 2026-05-14; from 2027-01-01; notice, plain explanation within 30 days of adverse outcome, correct data, request human review; repeals + reenacts SB24-205; AG rules due | Bill page | Enforcement depends on AG rules |
| eu-ai-act | Annex III 4(a): AI to "analyse and filter job applications, and to evaluate candidates" = high-risk | Law | - |
| eu-omnibus-2026 | In force 2026-07-27; Annex III rules from 2027-12-02 | Commission notice | - |
| eo-14281 | 2025-04-23: agencies "deprioritize enforcement" of disparate-impact liability incl. Title VII; AG to repeal/amend Title VI rules | Executive order | No AI mention |

Also found (not cited in the draft): Mobley order of 2026-06-22 granting in part Workday's motion to
dismiss - Title VII race, ADA and ADEA disparate-impact claims proceed (Duane Morris blog, 2026-06-24;
Gao 2026 intro cites Reuters/Wiessner 2026 for it) - open the order before citing. California Civil
Rights Council ADS regulations under FEHA, in force 2025-10-01 (law-firm summaries; open the CRC
text). EO 14365 (2025-12-11) on state AI laws + DOJ AI Litigation Task Force; xAI v. Colorado filed
2026-04-09 against SB24-205. Bloomberg 2024 GPT-3.5 test (1,000 runs, 8 groups, Black men top 7.6%
vs 12.5% parity; method published on GitHub). UMD 2025 preprint arXiv 2509.00462 (screeners
favor resumes written by the same model) - lead for ai-written-resumes.

## Claim table

76 citation markers in the article (82 id citations, 22 distinct ids); 110 rows below.

| # | Line | Claim | Source | What the source says | Verdict | Sev |
|---|---|---|---|---|---|---|
| 1 | 2 | Title: "Is AI resume screening biased? What the studies show" | - | Article delivers it; 52 chars | Supported | - |
| 2 | 3 | Description: models judge by name, gender, age, disability; direction changes; real data scarce | all | Fair summary; 150 chars | Supported | - |
| 3 | 13 | Identical resumes judged differently by name, gender, age or disability | wilson-caliskan-2024 | Name/race + gender only | Overstated: cited ids cover no age or disability (F10) | low |
| 4 | 13 | same | an-2025 | Name, race + gender only | as row 3 | low |
| 5 | 13 | same | rozado-2026 | Gender + order only | as row 3 | low |
| 6 | 14 | Who gets favored flips between models, versions, designs | gao-2026 | Flips by model vintage | Supported | - |
| 7 | 14 | same | chen-xiao-2026 | About test design, not who is favored | Supported for "test designs" only | low |
| 8 | 15 | One large real-hiring set; game tests; "some groups shut out more" | bommasani-2026 | Adverse impact in 10.62% of positions; systemic rejection is a separate, group-neutral finding | Conflates two findings (F6) | medium |
| 9 | 16 | No resume trick shown to beat a biased screener | (none) | Absence claim; `uncited:` lists no search | Needs "no study found" + searched list (F7) | medium |
| 10 | 20 | Yes, in lab tests; models pick, rank or score differently | - | Some designs show no gap (Rozado alone-ratings, Chen ties, Gao null models) | Needs caveat (F11) | low |
| 11 | 22 | 3 text-matching models, 500+ resumes, 120 names | wilson-caliskan-2024 | Matches | Supported | - |
| 12 | 22 | White names favored in 85.1% of tests | wilson-caliskan-2024 | 85.1% of 27 tests | Supported | - |
| 13 | 22 | Black names favored in 8.6% | wilson-caliskan-2024 | Matches | Supported | - |
| 14 | 22 | Black men disadvantaged up to 100% "of cases" in some comparisons | wilson-caliskan-2024 | 100% of tests vs white male names | Supported ("tests", not "cases") | low |
| 15 | 24 | Gender result corrected August 2026 | wilson-caliskan-2024 | Note dated 2026-08-29 | Supported | - |
| 16 | 24 | Another team tried to repeat it and found a coding error | wilson-caliskan-2024 | Salzburg team; bug in code | Supported | - |
| 17 | 24 | After the fix female 51.9%, male 11.1% | wilson-caliskan-2024 | Derived by inverting; body still prints the old numbers | Supported; say the numbers are swapped per the authors' note (F12) | low |
| 18 | 24 | Published 2024 paper says the reverse | wilson-caliskan-2024 | Yes | Supported | - |
| 19 | 24 | Many articles still repeat the old gender result | (none) | No source cited; true of pages found in review search | Unsupported as written (F13) | medium |
| 20 | 24 | Race results held up when repeated | wilson-caliskan-2024 | Race-only + intersectional replicated | Supported | - |
| 21 | 26 | ~361,000 made-up resumes, five models | an-2025 | Matches | Supported | - |
| 22 | 26 | 4 of 5 models scored women or Black applicants higher on average | an-2025 | "female OR black" vs white men, significant | Supported | - |
| 23 | 26 | Black men the exception: GPT-3.5 scored them 0.3 points lower | an-2025 | -0.303 GPT-3.5; lower "by most of the models" | Understated: most models, not just GPT-3.5 (F14) | low |
| 24 | 26 | Gaps small per resume | an-2025 | Authors: "economically significant" | Needs balance (F14) | low |
| 25 | 26 | Pass mark 80: Black men -1.4 pp | an-2025 | GPT-3.5 example | Supported; name GPT-3.5 | low |
| 26 | 26 | Black women +1.7, white women +1.4 | an-2025 | vs white men, GPT-3.5 | Supported | - |
| 27 | 28 | Tests show what models can do, not employers' systems | - | Matches labels | Supported | - |
| 28 | 32 | Direction changes with model, version, test | - | Gao, Rozado, Chen | Supported | - |
| 29 | 34 | 22 models, 70 jobs, swapped names | rozado-2026 | Matches | Supported | - |
| 30 | 34 | Every one of 22 picked female more often | rozado-2026 | Significant in all models | Supported | - |
| 31 | 34 | Female names won 56.9% | rozado-2026 | Matches | Supported | - |
| 32 | 36 | Stronger pull from order | rozado-2026 | h 0.55 vs 0.28 | Supported | - |
| 33 | 36 | First listed won 63.5% | rozado-2026 | Matches | Supported | - |
| 34 | 36 | Order mattered in 21 of 22 | rozado-2026 | Matches | Supported | - |
| 35 | 36 | Rated alone, gender gap almost vanished | rozado-2026 | 8.65 vs 8.61, negligible | Supported | - |
| 36 | 38 | 2026 preprint, 14 models 2023-2026 | gao-2026 | Matches | Supported | - |
| 37 | 38 | GPT-3.5 favored white names by 2.12 "points" | gao-2026 | Percentage points of callback | Unit unclear next to An's 0-100 points (F15) | low |
| 38 | 38 | Every 2024+ model no gap or favored Black names | gao-2026 | Matches | Supported | - |
| 39 | 38 | Not yet peer-reviewed | gao-2026 | arXiv v1 | Supported | - |
| 40 | 40 | GPT-3.5 favored men by 1.92 points | gao-2026 | pp | as row 37 | low |
| 41 | 40 | 10 of 12 later models favored women, 2 no gap | gao-2026 | Matches; one fails strict correction | Supported | - |
| 42 | 42 | 2026 preprint, 9 open models choose between two resumes | chen-xiao-2026 | Matches | Supported | - |
| 43 | 42 | Forced to choose, models looked biased | chen-xiao-2026 | Spurious 0.39 ratio | Supported | - |
| 44 | 42 | Allowed a tie, they did so in at least 94% of cases | chen-xiao-2026 | ">= 94%" for most models | Overstated: "most models" (F9) | low |
| 45 | 48 | Not reliably, in one preprint | chen-xiao-2026 | Preprint | Supported | - |
| 46 | 48 | Team removed names and personal details from 620 resumes | chen-xiao-2026 | Resumes built without names; cues ADDED to one section at 3 strengths | Misdescribed (F1) | high |
| 47 | 48 | Models guessed ethnicity 75.7% on average | chen-xiao-2026 | Average incl. explicit tier (100%); faint cues 8.6-69% | Overstated (F1) | high |
| 48 | 48 | Clues like a school, a language or a club gave it away | chen-xiao-2026 | Languages held identical; cues = community, activities, interests; no school | Misattributed (F2) | high |
| 49 | 50 | Score differences very small | chen-xiao-2026 | "only very small" | Supported | - |
| 50 | 50 | Models could tell, barely acted on it | chen-xiao-2026 | Authors: recoverability does not show hiring effect | Supported | - |
| 51 | 52 | Leaving details off may not hide them; lines may be real experience | - | Advice; test was Australian, 5 groups | Needs caveat (F1) | medium |
| 52 | 56 | 2026 conference paper, 10 open models base + trained | bone-2026 | COLM 2026 | Supported; "open AI models" reads as OpenAI (F16) | low |
| 53 | 56 | Age shown through graduation year | bone-2026 | Matches | Supported | - |
| 54 | 56 | Trained versions 3.6% less likely to call back older applicants | bone-2026 | vs their base versions; older = 45-58 | Supported; say "than the base version" + who "older" is | low |
| 55 | 56 | Held in 8 of 10 | bone-2026 | Matches | Supported | - |
| 56 | 58 | GPT-4, one resume vs same plus disability awards | glazko-2024 | Matches | Supported | - |
| 57 | 58 | Disability version first in 15 of 60 | glazko-2024 | Matches; enhanced CV is the stronger one | Supported; add that it should win | low |
| 58 | 58 | Autism version first in none of 10 | glazko-2024 | Matches | Supported | - |
| 59 | 58 | Version "told to avoid disability bias" 37 of 60 | glazko-2024 | Custom GPT trained on DEI + disability-justice principles | Supported; 10 trials each, say small (F17) | low |
| 60 | 60 | Anthropic 2023 preprint, Claude 2.0, incl. job offers | tamkin-2023 | 2 of 70 decision types | Supported; "preprint" said | - |
| 61 | 60 | Favored women and non-white people; less positive over 60 | tamkin-2023 | Matches; far smaller when inferred from names | Needs caveat (F17) | low |
| 62 | 60 | Telling it discrimination is illegal cut the gaps | tamkin-2023 | Several prompt interventions cut both | Supported | - |
| 63 | 62 | Age + disability count against you in some models | - | Lab | Supported | - |
| 64 | 66 | Largest real set not about resumes; 4.2M applications, game tests | bommasani-2026 | Matches | Supported; add years 2018-2022 (F6) | medium |
| 65 | 66 | 3.4M people, 1,746 jobs, 156 employers | bommasani-2026 | Matches | Supported | - |
| 66 | 68 | In 10.62% of jobs tests recommended Black applicants "at a clearly lower rate" | bommasani-2026 | Adverse impact under the US four-fifths standard | Supported; name the standard | low |
| 67 | 68 | 25.87% of Black applicants' applications went to those jobs | bommasani-2026 | Matches | Supported | - |
| 68 | 68 | 4% of 10-job applicants not recommended anywhere | bommasani-2026 | Matches | Supported | - |
| 69 | 68 | More than chance "because employers used the same tool" | bommasani-2026 | Same vendor; gameplay reused | Causal wording on real records; contradicts line 70 (F6) | medium |
| 70 | 70 | Real records: a link, not a cause | - | Label right | Supported | - |
| 71 | 72 | 528 people, simulated AI | wilson-2025 | Matches | Supported | - |
| 72 | 72 | No / neutral AI -> about equal | wilson-2025 | Matches | Supported | - |
| 73 | 72 | Followed its lean up to 90% | wilson-2025 | Matches | Supported | - |
| 74 | 72 | So "a person makes the final call" does not remove bias | wilson-2025 | Lab, simulated AI | Overstated: "may not" (F8) | medium |
| 75 | 74 | Applying through different routes spreads the risk | - | Inference from Bommasani | Needs "our reading" wording (F8) | low |
| 76 | 78 | "Two cases are often cited" | - | Three follow | Wrong count (F18) | low |
| 77 | 80 | Reuters 2018: Amazon dropped a resume-ranking tool | dastin-2018 | Team disbanded by early 2017 | Supported | - |
| 78 | 80 | Marked down "women's" | dastin-2018 | Matches | Supported | - |
| 79 | 80 | Learned from 10 years of resumes, mostly men | dastin-2018 | Matches | Supported | - |
| 80 | 80 | Recruiters never relied on it alone | dastin-2018 | Sources; Amazon: never used to evaluate | Supported; add Amazon's denial (F18) | low |
| 81 | 82 | iTutorGroup settled for $365,000 in 2023 | eeoc-itutorgroup-2023 | Matches | Supported | - |
| 82 | 82 | Alleged rejection of women 55+, men 60+ | eeoc-itutorgroup-2023 | Matches | Supported | - |
| 83 | 84 | Plaintiffs allege Workday's AI screened out older applicants, p. 3 | mobley-2025-order | Race, age, disability alleged; quote on pp. 1-2 | Incomplete + pin (F4) | medium |
| 84 | 84 | Workday denies; nothing proven as of October 2026 | lawyer-monthly-2026 | Matches; misses June 2026 ruling + class bid | Outdated (F4) | medium |
| 85 | 90 | NYC: yearly audit, public summary, notice; enforced July 2023 | nyc-ll144 | Within one year before use | Supported | - |
| 86 | 90 | 2024 check: 391 employers, 18 audits | wright-2024 | Matches | Supported | - |
| 87 | 90 | Comptroller called enforcement ineffective, Dec 2025 | nys-comptroller-2025 | Complaint process "ineffective"; 1 vs 17 | Supported | - |
| 88 | 91 | Illinois since Jan 2026: discriminatory-effect AI = violation; notice | il-hb3773 | Matches | Supported | - |
| 89 | 92 | Colorado from Jan 2027: notice, explanation, correction, human review | co-sb26-189 | Matches; AG rules pending; federal challenge | Needs caveat (F5) | medium |
| 90 | 93 | EU: filtering AI is high-risk | eu-ai-act | Annex III 4(a) | Supported | - |
| 91 | 93 | Rules start December 2027 | eu-omnibus-2026 | Matches | Supported | - |
| 92 | 94 | US federal anti-discrimination laws unchanged | (none) | Uncited | Needs citation (F5) | medium |
| 93 | 94 | 2025 order tells agencies to move away from disparate impact | eo-14281 | "deprioritize enforcement" | Supported | - |
| 94 | 88 | "a few places set rules" | - | California ADS rules (Oct 2025) missing | Incomplete (F5) | medium |
| 95 | 96 | In NYC, IL, soon CO "you can ask whether AI is used" | - | Laws put notice on the employer; no right to ask stated | Misstated right (F19) | medium |
| 96 | 100 | No study measures unattended AI screening across employers | - | Vendor surveys (self-report) exist | Needs "no study found" + searched list (F7) | medium |
| 97 | 101 | Almost all evidence uses made-up resumes | - | Matches | Supported | - |
| 98 | 102 | Results changed between versions within two years | gao-2026 | 2023 vs 2024 | Supported | - |
| 99 | 103 | How much test design drives the result | chen-xiao-2026 | Matches | Supported | - |
| 100 | 103 | same | rozado-2026 | Order + labels | Supported | - |
| 101 | 104 | No study compares AI vs human screeners in real hiring | - | Lead (unopened): Cowgill's resume-screening field study, algorithm vs human screeners at one firm | Likely wrong (F3) | high |
| 102 | 108 | Apply widely; one "no" can repeat | bommasani-2026 | Same vendor, games | Supported; inference | low |
| 103 | 109 | No resume trick shown to beat a biased screener | - | as row 9 | (F7) | medium |
| 104 | 110 | Notice NYC + IL, explanation CO | nyc-ll144 | Notice | Supported | - |
| 105 | 110 | same | il-hb3773 | Notice | Supported | - |
| 106 | 110 | same | co-sb26-189 | Explanation | Supported | - |
| 107 | 111 | Bias is the employer's problem | - | House framing | Supported | - |
| 108 | 117 | Tool ranks by posting + settings, never name, age, gender, background | - | `app/rank.py`: no personal fields; "age" there is posting age | Supported | - |
| 109 | 118 | Never invents or changes a fact | - | AGENTS.md Hold tier | Supported | - |
| 110 | 119 | "Lists every match from your search" | - | Not checked against job-find | Check wording (F20) | low |

## Findings

All fixed in plan-xsy.23 (see Revision).

- **F1 (high, status: fixed)** Line 48-52: Chen & Xiao did not take real-looking resumes and strip names. They
  built name-free resumes and added ethnic cues (community, activities, interests) at three
  strengths, one of them explicit. The 75.7% average includes the explicit tier (100%). Fix: "When
  a resume mentioned community or activities linked to a background, models often guessed it:
  every time when the clue was plain, 9-69% when faint." Add: Australian setting, five groups.
  Soften the "for you" line to match.
- **F2 (high, status: fixed)** Line 48: "a school, a language or a club" - the study held languages
  identical on purpose, and schools are not a cue. Fix: "community groups, activities and interests".
- **F3 (high, status: fixed)** Line 104: "no study compares them directly" - a bold absence claim. Lead,
  NOT opened in this review: Cowgill's working paper "Bias and Productivity in Humans and
  Algorithms" is widely described as a resume-screening field study comparing an algorithm with
  human screeners at one firm. Open it; if it holds, register it, and either cite it in a "Is AI worse than people?" paragraph or reword to "few
  studies, one employer". Also check Bloomberg 2024 (see F5b) and the An et al. comparison to
  field experiments (Gao compares to Kline et al.).
- **F4 (medium, status: fixed)** Line 84: Mobley is behind. June 22, 2026 order: Title VII race, ADA and ADEA
  disparate-impact claims proceed; May 2025 age collective certified preliminarily; September
  2026 bid for four subclasses, hearing March 9, 2027. Open the June order; say all three
  grounds; pin the quote to pp. 1-2.
- **F5 (medium, status: fixed)** Laws: (a) California's Civil Rights Council rules on automated-decision
  systems in hiring, in force October 1, 2025 - missing; open the official text. (b) Colorado:
  enforcement waits on Attorney General rules, and EO 14365 (December 2025) directs a federal
  task force to challenge state AI laws; xAI sued over Colorado's earlier law in April 2026 -
  say "as of October 2026, may change". (c) "US federal laws unchanged" needs a citation (the
  statute or EEOC page) or rewording. (d) Bloomberg 2024 (must-cover list) is absent: add as
  news test of GPT-3.5 with its published method, noting what was disputed.
- **F6 (medium, status: fixed)** Bommasani: short answer conflates adverse impact (some groups) with
  systemic rejection (some people); line 68 "because employers used the same tool" is causal on
  real records and contradicts line 70; data are 2018-2022, before chat AI - say so.
- **F7 (medium, status: fixed)** Absence claims (lines 16, 100, 109) need "no study found" wording and a
  searched list in `uncited:` per research.md; the current `uncited:` snippet lists nothing searched.
  Line 100 also skips vendor surveys that ask employers (self-report) - say they exist.
- **F8 (medium, status: fixed)** Line 72: from a lab test with a simulated AI, write "may not remove the
  bias", not "does not". Line 74 "different routes spreads that risk" = our reading; say so.
- **F9 (low, status: fixed)** Line 42: ties ">= 94%" is "for most models".
- **F10 (low, status: fixed)** Short answer line 13 cites only name/gender studies for age + disability;
  add bone-2026 + glazko-2024 or drop those words.
- **F11 (low, status: fixed)** Line 20 "Yes, in lab tests" - add that some tests show no gap.
- **F12 (low, status: fixed)** Line 24: say the 51.9/11.1 figures come from swapping the paper's numbers as
  the authors' note directs (the v3 body still prints the old ones).
- **F13 (medium, status: fixed)** Line 24 "Many articles still repeat the old gender result" - uncited
  claim; cite one example as news or cut.
- **F14 (low, status: fixed)** Line 26: most of An's models scored Black men lower, not GPT-3.5 alone; the
  authors call the gaps economically significant - say both.
- **F15 (low, status: fixed)** Lines 38, 40: "points" -> "percentage points of call-backs" (An uses points of 100).
- **F16 (low, status: fixed)** Line 56 "open AI models" reads as OpenAI - "openly released AI models".
- **F17 (low, status: fixed)** Glazko: 10 trials per disability, early-2024 GPT-4 web UI - "a small test".
  Tamkin: gaps far smaller when inferred from names.
- **F18 (low, status: fixed)** Line 78 says two cases, three follow. Line 80: add Amazon's statement that
  recruiters never used it to evaluate candidates.
- **F19 (medium, status: fixed)** Line 96 "you can ask whether AI is used" - the laws require employers to
  give notice; NYC lets applicants request an alternative process or accommodation. Reword to
  what each law actually gives.
- **F20 (low, status: fixed)** Line 119 "Lists every match" - check against job-find / Today behaviour.

Plain words: telegraphic short answer fine; body sentences short. Jargon to fix: "percentage
points" unexplained once, "base and a trained version", "disparate impact" (explained - keep).
No quote over 15 words; no owner data; tool box separate and after the evidence. Internal links:
ats-rejection-myth, methods, index (>= 2). Add ai-written-resumes once it exists.

## Revision (plan-xsy.23, 2026-10-03)

New sources, opened 2026-10-03, no text addressing an AI:
- `cowgill-2020`: working paper, March 2020 (Wayback copy of the IZA PDF; the live IZA link answered
  503). Field experiment, one firm, one software engineer opening, one location; algorithm (LASSO +
  SVM on four years of past resumes; names and demographics not in the model) randomly overrides human
  screeners. Marginal machine picks +14% to pass interview + get an offer vs candidates both select;
  more non-traditional hires "This includes women, racial minorities" (p. 3). Applicant count not
  found in the text read; registry `sample` says one opening at one company.
- `mobley-2026-order`: ECF 360, 2026-06-22, Judge Lin (Clearinghouse copy of the RECAP PDF). p. 1:
  race, age, disability alleged; p. 1-2: Title VII race, ADA, ADEA disparate-impact claims proceeding
  since earlier rulings; p. 11: Rowe's new race claim (Title VII or FEHA) dismissed, Hughes ADA claim
  stands, FEHA claims otherwise stand, own-hiring employer claim dismissed; no further leave to amend.
  The review's "Title VII race, ADA and ADEA claims proceed" came from a blog; the order says the
  same of the earlier posture (p. 1-2).
- `ca-crc-ads-2025`: Council release 2025-06-30 (approved 2025-06-27, in force 2025-10-01) and the
  adopted text (Attachment B, 2025-03-17): ADS use can violate FEHA; records incl. ADS data kept four
  years; evidence or lack of anti-bias testing relevant to a claim or defense.
- `bloomberg-2024`: Bloomberg graphics page (Bloomberg's own prod.cm host; www answers a bot wall) +
  GitHub README. 2024-03-07; GPT-3.5/GPT-4 0613; 8 resumes x 1,000 rankings x 4 jobs; 800 names, 8
  groups; Black women top for software engineer 11% (GPT-3.5); OpenAI: may not reflect customer use.
  The disputed part = OpenAI's response; the review's 7.6% figure was not seen on the page and is not used.
- `eo-14365`: govinfo HTML of FR 2025-23092 (federalregister.gov redirects to a bot check). Signed
  2025-12-11; Sec. 3 AI Litigation Task Force "to challenge State AI laws"; Sec. 1 names Colorado's law.
- `chen-xiao-2026` registry sample corrected (cues added at three strengths, 5 groups, Australia).

Searched for F7 (web search incl. arXiv + news, 2026-10-03): studies of a resume
change that protects against biased screening - none found; anonymisation studies (Chen & Xiao,
arXiv 2112.08910) show leakage, not protection. Hidden-text prompt-injection studies exist (arXiv
2605.28999, 2512.20164: injected text can raise a resume's rank) - not a protection against bias and
Hold-tier dishonest; the claim is worded "protects you from a biased screener" so it stays true.
Lead for ai-written-resumes. Cross-employer measures of unattended AI screening: none found.

- F1: rewritten - name-free resumes with background clues added, plain clue = every time, faint
  clue = 9-69%; five groups, Australian setting; reader line now "if other lines point to it".
- F2: "community groups, activities and interests"; school + language dropped.
- F3: Cowgill paragraph added under real applicants (field experiment, one firm, older algorithm,
  working paper); "What we don't know" says we found one field test, not none.
- F4: Mobley: race, age, disability (p. 1); May 2025 age collective; June 2026 order (p. 11); Sept
  2026 class bid + March 2027 hearing; Workday denies; nothing proven.
- F5: (a) California bullet added; (b) Colorado: AG enforces + writes rules; EO 14365 task force names
  Colorado; "some may change" in the lead; xAI suit left out (news only, SB24-205 replaced); (c)
  "federal laws unchanged" cut, replaced by private suits still using disparate impact (Mobley p. 2);
  (d) Bloomberg 2024 paragraph added with method, numbers and OpenAI's response.
- F6: Short answer now group finding only ("some jobs' tests passed fewer Black applicants");
  four-fifths benchmark named + explained; systemic rejection set apart as an individual finding,
  causal "because" replaced by the two facts (same vendor, reused results); dates 2018-2022 added.
- F7: "No study found ..." / "We found no study showing ..." on lines 16 + What helps; vendor
  surveys mentioned as self-report; searched line added; `uncited:` snippets added.
- F8: "may not remove the bias" + lab caveat; "our reading" + "may spread".
- F9: "most models".
- F10: bone-2026 + glazko-2024 added to the Short answer line.
- F11: "in many lab tests, though some tests find no gap"; "often pick".
- F12: "The authors' note says the gender numbers should be swapped. Swapped as the note directs ...".
- F13: "Many articles still repeat" cut.
- F14: "most of the models scored them lower"; GPT-3.5 named as the example; economically significant.
- F15: "percentage point higher call-back rate".
- F16: "openly released AI models" (Bone, Chen & Xiao); base/trained explained in plain words.
- F17: Glazko "small", stronger resume should win, 10 trials, early-2024 GPT-4, custom GPT described;
  Tamkin name-inferred gaps much smaller.
- F18: "Three cases"; Amazon's statement added.
- F19: reader line says what each law gives: notice (NYC, IL), explanation (CO 2027), NYC
  alternative process or accommodation.
- F20: tool line now "Checks for new jobs from your search every day" (daily check; `find` shows a
  ranked top 15, not every match).
- Claim table rows 3-110: low "Supported; ..." notes applied where they named a wording (row 14
  "tests", row 25 GPT-3.5, row 54 base version + who "older" is, row 57, row 66 standard).


## Re-review 2026-10-03: citations thinned (plan-xsy.48)

Citation placement only - no wording, number or source changed. A run of sentences citing the
same source now cites it once, at the run's end (build rule: 3 in a row = error). Checked: every
sentence the moved citation now covers comes from that source.
61 repeat citations dropped. Sentences newly under a citation, each checked against the claim
table above: "The authors' note says the gender numbers should be swapped" + "The published
2024 paper still prints the reverse" (wilson-caliskan-2024, arXiv v3 note; rows 17-18);
"Bloomberg published its method and code" (bloomberg-2024); "That extra training is how makers
turn a raw model into a chat assistant" + "Older meant over 45 in that test" (bone-2026);
"The version with awards was the stronger resume ..." (glazko-2024 design). All supported.

## Re-review 2026-10-04: voice pass (plan-xsy.53)

Voice only. Section endings lost their "For you," opener (5 lines, plus "For you, our reading" -> "Our reading"); Glazko "the GPT-4 of early 2024" -> "on a GPT-4 version from early 2024" (matches source table: early-2024 GPT-4 web UI); home-page line added after the tool box; `modified` 2026-10-04. Checked: each changed line keeps its meaning, scope, hedging and evidence label; section endings still say what the finding means for the reader; no new "this"/"it" across sentences; no app jargon; closing line "CEZ Job Finder is a free job-search app for Windows and Mac" matches docs/index.html title + og:title; link is our own home page. No finding.
