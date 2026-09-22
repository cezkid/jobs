# Bullets - what a line has to do, and what the evidence actually supports

Checked on 2026-09-22 against current hiring guidance: university career centres (Harvard, MIT,
Emory, Berkeley, Arizona, UConn), ATS vendor documentation (Greenhouse, Lever), background-
screening data (HireRight 2025) and recruiter surveys. Every rule names its basis, and where the
basis is thin the rule says so - the same way `typeface.md` prints its measurements instead of
only its conclusion.

Scope is the claim text `lint.py` sees: bullets and the summary. Page geometry is `typeface.md`.

Three things were checked and did not survive: see
[What did not survive](#what-did-not-survive) and
[Considered, not mechanised](#considered-not-mechanised). One of them was this document's own
leading candidate.

## The thing that decides it: precedence

**Accuracy > Substance > Relevance > Clarity.**

A lower tier never justifies breaking a higher one. This ordering, and the grading of evidence
in Tier 2, are what this document adds; most of the individual rules below were already enforced
in `lint.py` or stated in `tailor.py`'s prompt, and each one says which.

The ordering exists because of one observed failure mode: a lower rule quietly manufacturing a
breach of a higher one. A rule that demands a number the writer does not have will get a number
invented. So every rule below is marked **enforce** (code can decide it) or **report** (code may
name it, only the writer may fix it). No rule that pressures invention is ever enforced.

---

## Tier 1 - Accuracy

A failure here can cost the offer, not only the interview. These are the claims a third party
checks.

| Rule | Basis | |
|---|---|---|
| Employer, title and dates match what verification will find | HireRight's 2025 benchmark (1,000+ HR and talent professionals) reports over three-quarters of employers found candidate discrepancies in the prior year, employment verification the leading category, with discrepancy rates rising from 9.9% (FY21) to 14.3% (FY24). Shortening or lengthening a role is not a rounding error - it is the field most likely to be checked. | enforce: `title-changed`, `employer-changed`, `dates-changed` |
| Overlapping dates are not an error; **unlabelled** overlap is | The National Resume Writers' Association answers it directly: "List them all! Many people work multiple jobs at once; concurrent roles are not frowned upon." Same-employer overlap must read as stacked titles under one employer; different-employer overlap needs a marker (part-time, freelance, contract) or it reads as a date mistake. | enforce: `role-dates-overlap`, which carries the same-employer case |
| Every number is defensible in an interview | Any number on the page becomes a question. Insight Global's 2025 survey (Atomik Research, n=1,005 US hiring managers) found ~88% believe they can spot AI-written material and 54% care, with "impressive numbers with no context" a named tell. No controlled study measures the cost of an undefendable number: this is professional consensus plus adjacent fraud data. | enforce **in tailoring only** - see the note below |
| A year inside a bullet falls inside that role's dates | No external source states this. It is internal-consistency hygiene: one of the year and the date span is wrong, and both are verifiable. Adjacent guidance (Jobscan 2026) runs against it, advising dates stay on the role header and out of bullets. | **report only** - measured unfit for code, see [Considered, not mechanised](#considered-not-mechanised) |
| No grade the reader cannot check | Berkeley: "minimize the use of adjectives and adverbs." Arizona: "it's better to be clear than be complicated." *Advanced, best-in-class, world-class, industry-leading* carry no information; the fact or named recognition that earned the grade does. Most "ban these words" advice sits in resume-product blogs; the defensible core is substitution, not a list. | enforce: `unmeasurable-grade` (new) |

**Where numbers are actually born.** `unresolved-entity` FAILs any number in a tailored bullet
that appears in no master claim, so tailoring cannot invent one. Nothing checks the master file
itself - that is where a number enters the resume, and no code can tell a recalled figure from a
guessed one. `round-metric` catches a generated `10|15|20|25|30|40|50|100%` absent from master,
which is eight values, not all round numbers. Treat the master file as the place a human must
still vouch for every figure.

## Tier 2 - Substance

What earns the line its space.

| Rule | Basis | |
|---|---|---|
| A bullet carries **evidence**: an outcome metric where one exists, otherwise scope (how many, how large, how often) or a named qualitative result - approval won, process adopted, audit passed. Scope counts as evidence only when the writer can say where the number came from. A bullet with no evidence is reported, never filled. | The most contested point in the set, and the wording is deliberate. MIT's PAR framework ends every bullet in a result; Emory gives "Action Verb + task, resulting in quantitative outcome". But **Arizona states outright that not every bullet requires a numeric result** - results are "most often left out" and included "whenever possible". Emory's own framework splits quantification into *scale* questions (how many projects, how many people) and *results* questions (by what percentage, how much time): a bullet quantified on scope alone is quantified. | **report** - the nearest enforceable proxy is `specificity` |
| Achievements over duties | The most consistently stated rule found, with no dissent. Harvard lists "not demonstrating results" among its top resume mistakes; Emory's "do not include" list is headed by "daily job duties and tasks"; Berkeley: employers care about "the impact that your work had", not "just what work you did". | **report** - the difference is in the facts behind the sentence, not its shape |
| Scope numbers and change numbers do different jobs; a role whose bullets are all one kind is worth noticing | Emory separates "Scale Questions" from "Results Questions"; MIT treats scale ("over 100,000 data points", "size of your department, event, budget") as a mode distinct from percentage change. Both count as quantification. | **report only.** Enforcing it would demand a scope number for a role that has none - Tier 1 wins |
| No hedged opener | Arizona names the constructions to cut: "helped to", "worked on", "responsible for". Dissent worth recording: UConn lists "assisted" and "collaborated" among its *recommended* verbs, so the objection is to the hedged opening, not to every collaborative word. | enforce: `hedge` |
| Ownership claims match the actual role | Screening sources name this as its own red flag: claiming to have "led" work merely joined, or "managed" a team with no reports, or a team result as a personal one. Reference checks are where it surfaces. | **report only** - measured 100% false positives, see below |
| No two bullets built on one template | Better grounded than most word-level rules: Insight Global 2025 names "identical sentence structure across all bullet points" a primary AI tell, alongside "vague power verbs without proof". The 2025-26 finding is that rejection tracks generic, uncontextualised content, not AI use - ~80% of recruiters would not reject an application merely for AI help. | partial: `same-verb-opening` compares first words. **No shipped check measures syntax.** `uniform-bullet-length` measures word-count spread and is labelled unmeasured in the source |

## Tier 3 - Relevance

Getting in front of a person.

| Rule | Basis | |
|---|---|---|
| Use the posting's literal term for anything a recruiter would search - tool names, certifications, licences, titles, hard skills - **but only for something the candidate has.** The term replaces the writer's wording for the same thing; it never introduces a thing. A posting term with no claim behind it is a gap to report. | The advice survives; its usual justification does not. The mechanism is recruiter *search*: Greenhouse documents Boolean candidate search with AND/OR/NOT, quoted phrases and wildcards; Lever matches word variations but **not** acronyms; Jobscan reports 97.4% of the Fortune 500 on a detectable ATS and 76.4% of surveyed recruiters searching by skills drawn from the posting. A literal query is literal. | already in `tailor.py`; `unresolved-entity` + `inferences` enforce the possession half |
| Do not write for an auto-rejecter | The "75% of resumes are auto-rejected" figure traces to Preptel, a defunct vendor, with no disclosed method. Enhancv's 2025 study (n=25 US recruiters) found 92% said their systems do not auto-reject on formatting, keywords or match score; the 8% that do use knock-out criteria. Keyword density is not a score to maximise. **Knock-out filters are real but narrow** - work authorisation, licences, location, minimum qualifications, and per the HBS/Accenture 2021 *Hidden Workers* study cited at `schema.py:20`, a long employment gap. Reject the 75% folklore, not the existence of filters. | n/a |
| Lead each role with the bullet most relevant to **this** posting | Indeed: put the most important information at the top of the list, where skimming reaches it. Berkeley adds the ordering rule - bullets should follow "the order or priority that the employer has stated in their position description". | already in `tailor.py`; `lead-bullet-weak` warns when the opener carries no number and a later bullet does |
| Bullet counts taper with age | Emory gives a flat "3-5 bullet points below each role" with no taper. The taper appears in no career centre or recruiter survey found and no data backs the counts: convention, not evidence. The operative ladder is `tailor.py`'s - 3-5 for recent roles, 6 max, 2-3 for older, 0 for the oldest - which is what the generator reads. `bullet-taper` detects *inversion* (an older role carrying more than the newer one above it); it does not require a taper, and passes an even spread. | soft preference |
| 10-15 years of experience, older only where exceptionally relevant | Consistent across Indeed, Monster and Coursera on two grounds: relevance and age-discrimination exposure. Career-media consensus; no primary study fixes the cut-off. | **report** |
| Bullets let a reader place the work at the right level, on scope the candidate actually has - team size, budget, volume, project scale. Where that evidence is absent the level goes unsignalled; never adjust a verb or a number to reach a level. | Recruiter-side screening looks for whether work matches "the seniority and ownership the job needs". Practitioner sourcing, not survey data - a widely repeated heuristic, not a measured effect. | **report only** |

## Tier 4 - Clarity

Surviving one pass at scanning speed.

| Rule | Basis | |
|---|---|---|
| One idea, one sentence - **unless the page disagrees** | UConn: "one sentence, typically 1-2 lines in length". MIT: "bite-sized chunks, keeping each statement to 1-2 lines". Emory adds that a bullet should fill at least one full line, two being the maximum. **But `line-fill` and `pages` are FAIL gates and this is a style note:** splitting a filled one-line bullet at its semicolon was measured here to turn one 87%-full row into a 65% row and a 21% stub, against a 40% floor. Where they conflict, the page wins. | already in `tailor.py`; **never enforce a sentence count** |
| Assume about seven seconds on the first pass | One small study: The Ladders, 2018 - **30 recruiters**, eye-tracked over 10 weeks, 7.4 seconds on initial screen, up from 6 seconds in its 2012 predecessor. Not peer-reviewed, one commercial vendor, no replication, source now unreachable. Every "6-second scan" claim traces here. Cite it as one small study. Seven seconds buys headings, titles and each role's first bullet. | n/a |
| An acronym appears at least once with its expansion | Mechanical, not stylistic: Lever's search recognises word variations but not acronyms, so an unexpanded one does not surface. Gloss once per page. Employer-internal jargon the target reader would not recognise is replaced, not glossed. **The discriminator between this and Tier 3 is whether the reader's own field writes the string that way** - a specialist term keeps its exact spelling, internal shorthand does not. | already in `tailor.py`, which is the only place the posting is known |
| Every number names what it counts | Unit-naming is modelled in every Emory and MIT example ("over 100,000 data points", "4 team members") though never stated as a rule. A percentage is stronger with its baseline ("18 minutes to 7") and weaker without - but **report a missing baseline, never demand one:** the baseline is often a former employer's figure, not the candidate's to supply or publish. | **report** |
| Bullet punctuation is uniform across the page | No source; internal consistency. Worth stating because the two files shipped in this repo disagree - a real master ends every claim with a period, `master.example.yml` ends none - and a page assembled from both renders visibly mixed. | stated in `tailor.py`: follow master |

---

## What the page cannot fix

Three findings sit outside bullet wording and outrank it.

**Layout beats wording for machine readability.** The Ladders study found multi-column layouts,
clutter, missing section headers and missing job titles sank resumes - the same failure modes ATS
parsing guides flag (tables, text boxes, graphics, content in headers and footers). Jobscan
reports parser pass rates of 88% (Workday), 91% (Greenhouse), 93% (Lever). A well-written bullet
in an unparseable container does not exist. `render.py` emits a single-column, heading-led page
and the render gates check for tables, images and header/footer text for this reason.

**An unexplained gap is the problem, not the gap.** LiveCareer (2025) reports over half of job
seekers had at least a one-month gap that year and one in four a gap of 12 months or more; a 2025
MyPerfectResume survey reports 79% of hiring managers would still hire with a properly explained
gap. Under about three months needs no treatment. `schema.py` flags past six, citing HBS/Accenture
2021. Past eighteen months the sources give no wording guidance at all - a real hole, not a
settled question.

**Short tenure is not a bullet problem.** A 12-month role is computable from the dates, but the
remedy is never a rewritten bullet - it is a labelled contract or part-time marker, or nothing.
Indeed Hiring Lab (2025) puts median tenure near two years three months and reports job-hopping
slowing. The pattern draws scrutiny, not the instance.

## What the code checks

`lint.py` measures; the writer rewrites. Wording rules go through `hit()`, which WARNs on the
candidate's own words and FAILs on generated text - the candidate's register stays theirs.

| Check | Catches | Severity |
|---|---|---|
| `title-changed`, `employer-changed`, `dates-changed` | tailoring altered a verifiable identity field | FAIL |
| `unknown-entry`, `inference-source` | a page entry or added claim with no master source | FAIL |
| `unresolved-entity` | a number, tool or company in generated text that is in no master fact | FAIL |
| `ai-era` | AI wording, or a tool named before its release, inside a role that predates it | FAIL |
| `role-dates-overlap` | a role ending after the next one starts, same-employer case named | WARN |
| `company-legal-id` | an employer name missing Inc./LLC | WARN |
| `round-metric` | a generated `10|15|20|25|30|40|50|100%` absent from master | via `hit()` |
| `unmeasurable-grade` | a grade the reader cannot check, in a bullet or the summary | via `hit()` |
| `specificity` | a bullet naming no product, stack item, number or proper noun | via `hit()` |
| `style-word` | 19 words over-represented in generated prose | via `hit()` |
| `hedge` | helped, contributed to, assisted with, played a key role | WARN |
| `resume-verb` | leveraged, spearheaded, orchestrated, synergized, drove innovation | WARN |
| `rule-of-three`, `not-only-but-also` | two generated-prose sentence shapes | WARN |
| `same-verb-opening` | consecutive bullets opening on the same word | WARN |
| `uniform-bullet-length` | word-count spread below a craft floor (unmeasured) | WARN |
| `lead-bullet-weak` | opening bullet carries no number while a later one does | WARN |
| `bullet-taper` | an older role carrying more bullets than the newer one above it | WARN |
| `canonical-casing` | drifted tech spellings (15 names) | WARN |
| `em-dash`, `markdown`, `invisible-unicode` | characters that betray generated text | via `hit()` |
| `pages`, `line-fill`, `contact-line`, `no-prose-block` | page geometry (`render.py` gates) | FAIL |

## Considered, not mechanised

Measured against two corpora - a real 29-bullet resume and `master.example.yml` - and rejected. A
rule with no measured hits is unproven; a rule whose hits are all false positives is dead.

| Candidate | Measured | Why not |
|---|---|---|
| `date-outside-role` - a year in a bullet outside its role's span | **0 hits on either corpus.** The example that motivated it did not survive checking: in the source document the bullet and the role header agreed, and in the file where the dates differ the bullet carries no year. The error was real but it was a *date* error, and the shipped `role-dates-overlap` caught it - four times over. | Unproven, and the residual false positives are semantic, not lexical: *Windows 2000*, *port 2019*, *modernised a 2014 codebase* under a role starting later are all correct English. No regex separates them. Kept as prose in Tier 1 |
| `bullet-two-sentences` | 2 hits, **both false positives.** Both render as a single line at 87% and 88% fill; splitting them yields rows at 65/21% and 60/28%, two of them stubs under the 40% floor | Would make the page worse to satisfy a style note, against two FAIL gates |
| `acronym-without-expansion` | 16 distinct acronyms in one corpus, ~13 of them false positives (AWS, UI, REST, PHP, US, UK) | Zero false positives needs a hand-kept list of "acronyms everyone knows", which is a judgment wearing a regex and wrong the first time the user changes occupation. `tailor.py` handles the only knowable case |
| `ownership-verb-exceeding-title` | 1 hit per corpus, **both false positives** - "Led a 4-person team" under the title *Lead Developer*, and "Led design system migration", normal individual-contributor work | Needs the reporting line, which no file holds |
| `bare-percentage-without-baseline` | 3 hits, all true by the rule's definition, all good bullets | The fix requires a number the candidate does not hold. Report only |
| `stale-tech-in-skills` - a tool named as a current skill after its end of life | 1 true positive, 0 false positives | Declined on judgment, not measurement. It needs a hand-kept end-of-life table, which is occupation-specific - and this tool is meant to work for any occupation. The supporting evidence is the weakest in the set: staffing-firm advice with no measured penalty. Revisit if an occupation-neutral source appears |

## What did not survive

**"Avoid inflated verbs" (`resume-verb`, WARN) - shipped, and the stated reason is wrong.** No
recruiter survey, eye-tracking study or career-centre guidance was found saying recruiters react
badly to *spearheaded*, *orchestrated* or *leveraged*. The counter-evidence is direct: **Indeed's
own bullet-point guide uses "Spearheaded" in its worked examples**, and university action-verb
lists publish this register as the recommended alternative to hedging. What sources object to is
a different category - vague self-descriptive adjectives (*passionate*, *results-driven*, *team
player*), which occur in summaries rather than bullets - and separately a strong verb repeated
across every bullet or attached to nothing verifiable. The rule stays a WARN because verb
monotony is a real AI tell and the list is a cheap proxy for it. It is a proxy. The narrower,
better-evidenced check is `same-verb-opening`.

**"Add soft-skill keywords to close the match gap."** Rejected. It is contradicted by this
document's own Tier 3 evidence: recruiters search for skills drawn from the posting, systems do
not score-reject, and Insight Global names vague self-descriptors as an AI tell. Adding them is
the failure mode, not the fix.

**"Every bullet needs an outcome metric."** Contradicted by Arizona, in tension with Tier 1, and
observed in practice: enforcing it produced a request to invent a cost-savings figure the
candidate did not have. Report a role with no outcome anywhere; never demand one per bullet.

## Sources

HireRight 2025 Global Benchmark Report. Insight Global, *2025 AI in Hiring* (Atomik Research,
n=1,005, fielded Oct 2024). Enhancv ATS auto-rejection study, 2025 (n=25), via IT Brief. The
Ladders eye-tracking study, 2018 (n=30), via HR Dive. Jobscan ATS Usage Report 2026 and keyword
guidance 2026. Greenhouse Boolean search documentation. Career-centre guidance: Harvard FAS
Mignone Center, MIT CAPD, Emory CPD, UC Berkeley, University of Arizona, UConn. National Resume
Writers' Association. Indeed Career Guide; Indeed Hiring Lab 2025. HBS/Accenture, *Hidden
Workers: Untapped Talent*, 2021 (as cited by `schema.py`).
