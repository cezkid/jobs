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
leading candidate. An adversarial review on 2026-09-24 retired or softened more rules that were
hurting real users: see [Reviewed 2026-09-24](#reviewed-2026-09-24) before re-proposing one.

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
| Employer, title and dates match what verification will find | HireRight's 2025 benchmark (1,000+ HR and talent professionals) reports over three-quarters of employers found candidate discrepancies in the prior year, employment verification the leading category, with discrepancy rates rising from 9.9% (FY21) to 14.3% (FY24). Shortening or lengthening a role is not a rounding error - it is the field most likely to be checked. A mirrored posting title is a suffix the user confirms, never a level their own title lacks: "Staff Nurse (Nurse Manager)" claims a promotion. | enforce: `title-changed`, `employer-changed`, `dates-changed`; `tailor.check_selection` fails a `title_mirror` that is not whole words of the posting title or adds a seniority word (Senior, Lead, Principal, Staff, Manager, Director, Head, Chief, Supervisor) |
| Overlapping dates are not an error; **unlabelled** overlap is | The National Resume Writers' Association answers it directly: "List them all! Many people work multiple jobs at once; concurrent roles are not frowned upon." Same-employer overlap must read as stacked titles under one employer; different-employer overlap needs a marker (part-time, freelance, contract) or it reads as a date mistake. | enforce: `role-dates-overlap`, which carries the same-employer case |
| Every number is defensible in an interview | Any number on the page becomes a question. Insight Global's 2025 survey (Atomik Research, n=1,005 US hiring managers) found ~88% believe they can spot AI-written material and 54% care, with "impressive numbers with no context" a named tell. No controlled study measures the cost of an undefendable number: this is professional consensus plus adjacent fraud data. | enforce **in tailoring only** - see the note below |
| A year inside a bullet falls inside that role's dates | No external source states this. It is internal-consistency hygiene: one of the year and the date span is wrong, and both are verifiable. Adjacent guidance (Jobscan 2026) runs against it, advising dates stay on the role header and out of bullets. | **report only** - measured unfit for code, see [Considered, not mechanised](#considered-not-mechanised) |
| No grade the reader cannot check | Berkeley: "minimize the use of adjectives and adverbs." Arizona: "it's better to be clear than be complicated." *Advanced, best-in-class, world-class, industry-leading* carry no information; the fact or named recognition that earned the grade does. Most "ban these words" advice sits in resume-product blogs; the defensible core is substitution, not a list. **A grade word inside a term is not a grade:** *Advanced Cardiac Life Support*, *advanced practice nurse*. So the word passes when another of the candidate's facts or the posting itself uses it. | enforce: `unmeasurable-grade`, skipped when the facts or posting use the word |

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
| **Every clause adds something the reader did not already have.** Three ways a clause fails: it is true of any instance of the thing named ("a component library, so new screens assemble from existing pieces"); it restates the bullet's own opening; or it would be true of anyone holding the role ("shipping features end to end"). | Tier 1 bans a claim the reader *cannot* check. This is its mirror - a clause the reader does not *need* checked, because it is true by definition - and it costs the same: nothing conveyed. At a 7-second first pass, words that carry nothing are not neutral, they are spent. It is also the shape the sources describe as the AI tell: Insight Global 2025 finds rejection tracks "generic, uncontextualised content", and Arizona warns against bullets written to "sound professional". A definitional clause is a duty statement wearing an outcome's clothes, which Harvard, Emory and Berkeley all rank last. | **report**: `empty-clause` WARNs, generated or not, for the purpose-clause form only (it detects *names nothing specific*, which is not *adds nothing*); the redundant and generic forms are report too |
| Achievements over duties | The most consistently stated rule found, with no dissent. Harvard lists "not demonstrating results" among its top resume mistakes; Emory's "do not include" list is headed by "daily job duties and tasks"; Berkeley: employers care about "the impact that your work had", not "just what work you did". | **report** - the difference is in the facts behind the sentence, not its shape |
| Scope numbers and change numbers do different jobs; a role whose bullets are all one kind is worth noticing | Emory separates "Scale Questions" from "Results Questions"; MIT treats scale ("over 100,000 data points", "size of your department, event, budget") as a mode distinct from percentage change. Both count as quantification. | **report only.** Enforcing it would demand a scope number for a role that has none - Tier 1 wins |
| No hedged opener - **unless the hedge is the truth** | Arizona names the constructions to cut: "helped to", "worked on", "responsible for". Dissent worth recording: UConn lists "assisted" and "collaborated" among its *recommended* verbs, so the objection is to the hedged opening, not to every collaborative word. Where the candidate's own claim says "assisted with", that is their account of their part; replacing it with "performed" is an ownership claim (the next row), which Tier 1 outranks. | **report**: `hedge` WARNs, and stays quiet when another fact already uses the word. The prompt keeps a sourced hedge and forbids upgrading a part (assisted -> performed, coordinated -> led, member -> lead) |
| Ownership claims match the actual role | Screening sources name this as its own red flag: claiming to have "led" work merely joined, or "managed" a team with no reports, or a team result as a personal one. Reference checks are where it surfaces. | **report only** in code - measured 100% false positives, see below. Stated in `tailor.py`: never upgrade the candidate's part |
| No two bullets built on one template | Better grounded than most word-level rules: Insight Global 2025 names "identical sentence structure across all bullet points" a primary AI tell, alongside "vague power verbs without proof". The 2025-26 finding is that rejection tracks generic, uncontextualised content, not AI use - ~80% of recruiters would not reject an application merely for AI help. | partial: `same-verb-opening` compares first words. **No shipped check measures syntax.** `uniform-bullet-length` measures word-count spread and is labelled unmeasured in the source |

## Tier 3 - Relevance

Getting in front of a person.

| Rule | Basis | |
|---|---|---|
| Use the posting's literal term for anything a recruiter would search - tool names, certifications, licences, titles, hard skills - **but only for something the candidate has.** The term replaces the writer's wording for the same thing; it never introduces a thing. A posting term with no claim behind it is a gap to report. | The advice survives; its usual justification does not. The mechanism is recruiter *search*: Greenhouse documents Boolean candidate search with AND/OR/NOT, quoted phrases and wildcards; Lever matches word variations but **not** acronyms; Jobscan reports 97.4% of the Fortune 500 on a detectable ATS and 76.4% of surveyed recruiters searching by skills drawn from the posting. A literal query is literal. | already in `tailor.py`; `unresolved-entity` + `inferences` enforce the possession half |
| Do not write for an auto-rejecter | The "75% of resumes are auto-rejected" figure traces to Preptel, a defunct vendor, with no disclosed method. Enhancv's 2025 study (n=25 US recruiters) found 92% said their systems do not auto-reject on formatting, keywords or match score; the 8% that do use knock-out criteria. Keyword density is not a score to maximise. **Knock-out filters are real but narrow** - work authorisation, licences, location, minimum qualifications, and per the HBS/Accenture 2021 *Hidden Workers* study cited at `schema.py:20`, a long employment gap. Reject the 75% folklore, not the existence of filters. | n/a |
| Lead each role with the bullet most relevant to **this** posting | Indeed: put the most important information at the top of the list, where skimming reaches it. Berkeley adds the ordering rule - bullets should follow "the order or priority that the employer has stated in their position description". | already in `tailor.py`; `lead-bullet-weak` warns when the opener carries no number and a later bullet does |
| Bullet counts follow relevance, recency breaking ties | Emory gives a flat "3-5 bullet points below each role" with no taper. The taper appears in no career centre or recruiter survey found and no data backs the counts: convention, not evidence. So the ladder in `tailor.py` - 3-5 for recent roles, 6 max, 2-3 for older - ranks by relevance to the posting first: an old role that proves a *required* item keeps the bullets that prove it, and the oldest goes to 0 only when it proves nothing required. Every required item the facts prove is on the page and leads its entry (Berkeley's posting-order rule, two rows up). `bullet-taper` detects *inversion* (an older role carrying more than the newer one above it); it does not require a taper, and passes an even spread. | soft preference; `bullet-taper` WARN |
| 10-15 years of experience, older only where exceptionally relevant | Consistent across Indeed, Monster and Coursera on two grounds: relevance and age-discrimination exposure. Career-media consensus; no primary study fixes the cut-off. A role may leave the page only from the end of the list and only once it ended 15+ years ago (`tailor.OLD_ROLE_YEARS`): dropping one mid-career opens a date hole, which is the gap problem below. | enforce: `check_selection` fails any other dropped role |
| Bullets let a reader place the work at the right level, on scope the candidate actually has - team size, budget, volume, project scale. Where that evidence is absent the level goes unsignalled; never adjust a verb or a number to reach a level. | Recruiter-side screening looks for whether work matches "the seniority and ownership the job needs". Practitioner sourcing, not survey data - a widely repeated heuristic, not a measured effect. | **report only** |

## Tier 4 - Clarity

Surviving one pass at scanning speed.

| Rule | Basis | |
|---|---|---|
| One idea, one sentence - **unless the page disagrees** | UConn: "one sentence, typically 1-2 lines in length". MIT: "bite-sized chunks, keeping each statement to 1-2 lines". Emory adds that a bullet should fill at least one full line, two being the maximum. **But `line-fill` and `pages` are FAIL gates and this is a style note:** splitting a filled one-line bullet at its semicolon was measured here to turn one 87%-full row into a 65% row and a 21% stub, against a 40% floor. Where they conflict, the page wins. | already in `tailor.py`; **never enforce a sentence count** |
| Certifications a posting requires sit under the summary | Where a licence or certificate is a knock-out (Tier 3: "knock-out filters are real but narrow"), it has to be found in the first pass, not at the foot of page two. | enforce: `tailor.page_model` moves Certifications up when a requirement names a held one, by full name or bracketed short form |
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

Readable is not the same as filled in. An application form (Workday, iCIMS, Taleo, SuccessFactors)
fills its fields from *line shape*: a heading line, then the detail line under it. Measured on a
Workday form, 2026-09: the one-line education format `BA, Field | School` came back as the school
name "Field | School", the Degree box empty ("BA" is not on its spelled-out list) and a school
written as "<Town> CC" unmatched. So `render.py` prints a school the way it prints a job - institution on its own line,
spelled-out degree and field under it (`DEGREES`) - the `entry-lines` gate re-reads every PDF to
confirm each heading and its detail line come back whole, and `abbreviated-school` warns on a
shortened school name. Skills are a different matter: Workday often leaves its Skills box empty
whatever the page does, because it adds only terms on its own skill list. That is the form, not
the file - convention, not measured, and nothing on the page fixes it.

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
| `unresolved-entity` | a number, tool or company in generated text that is in no master fact; "1,000" and "1000" are one number | FAIL |
| `ai-era` | AI wording, or a tool named before its release, inside a role that predates it. `RAG` matches in capitals only and never as a red-amber-green status; bare *evals*, *embeddings*, *fine-tuning* are not AI terms | FAIL on generated text, WARN on the candidate's own |
| `role-dates-overlap` | a role ending after the next one starts, same-employer case named | WARN |
| `company-legal-id` | an employer name missing Inc./LLC | WARN |
| `round-metric` | a generated `10|15|20|25|30|40|50|100%` absent from master (written as `N%`, `N percent` or `N per cent`) | via `hit()` |
| `unmeasurable-grade` | a grade the reader cannot check, in a bullet or the summary, unless the posting or another fact uses the word | via `hit()` |
| `empty-clause` | a purpose clause (so, allowing, enabling, ...) naming no number, proper noun or known tool | WARN |
| `specificity` | a bullet naming no product, stack item, number or proper noun | via `hit()` |
| `style-word` | 17 words over-represented in generated prose, unless the posting or another fact uses the word | via `hit()` |
| `hedge` | helped, contributed to, assisted with, played a key role - unless another fact uses it | WARN |
| `resume-verb` | leveraged, spearheaded, orchestrated, synergized, drove innovation - unless the posting or another fact uses it | WARN |
| `rule-of-three`, `not-only-but-also` | two generated-prose sentence shapes | WARN |
| `same-verb-opening` | consecutive bullets opening on the same word | WARN |
| `uniform-bullet-length` | word-count spread below a craft floor (unmeasured) | WARN |
| `lead-bullet-weak` | opening bullet carries no number while a later one does | WARN |
| `bullet-taper` | an older role carrying more bullets than the newer one above it | WARN |
| `canonical-casing` | drifted tech spellings (15 names) | WARN |
| `em-dash`, `markdown`, `invisible-unicode` | characters that betray generated text | via `hit()` |
| `street-address`, `personal-details`, `old-graduation-year`, `abbreviated-school` | on the user's own file (`resume-lint` only): a house number, apartment, suite or ZIP in the location; a birth date, age, marital status or nationality anywhere; a degree ended 15+ years ago without `hide_year`; a school name shortened (CC, Univ., U of) | WARN |
| `pages`, `line-fill`, `contact-line`, `no-prose-block` | page geometry (`render.py` gates) | FAIL |
| `budget` | page words outside every window at this page's density: one page 75-100% full, or two with the second 60%+. Facts too few for even the lowest window report, never fail | FAIL / info |
| `no-abbreviated-title` | Sr./Jr. in a role heading - never in a name ("Robert Hayes Jr.") or employer | FAIL |
| selection: mirror, skills, coverage, dropped role | `tailor.check_selection`: a mirror claiming a level, a skills item not in master, coverage evidence not on the page, a role dropped other than from the old end | FAIL |

## Why each rule - in words the user can take

The sentence the chat says when a user asks why a line was flagged, and the one "Check before
sending.md" prints first. Mirrored from `lint.WHY`; `test_lint` keeps the two in step.

| Rule | Plain words |
|---|---|
| `title-changed` | Your job title must match what your employer's records say. |
| `employer-changed` | The employer's name must match what their records say. |
| `dates-changed` | Job dates must match what your employer's records say. |
| `unknown-entry` | Every job on the page has to come from your resume. |
| `inference-source` | New wording has to point back to something your resume already says. |
| `unresolved-entity` | A number, tool or name appears that your resume never mentions. |
| `ai-era` | AI wording on a job that ended before those tools existed reads as backdated. |
| `role-dates-overlap` | Two jobs overlap in dates - fine if both were real, but a checker will ask. |
| `company-legal-id` | Employer names are often written with Inc. or LLC in official records. |
| `round-metric` | A round percentage your resume never states looks made up. |
| `unmeasurable-grade` | Words like 'world-class' can't be checked; the fact behind them says more. |
| `empty-clause` | Part of this line may explain something the reader already knows. |
| `specificity` | This line names nothing a reader can picture: no number, tool or name. |
| `style-word` | This word shows up far more in AI-written text than in people's writing. |
| `hedge` | 'Helped' or 'assisted' is fine when it is true; just check it describes your part. |
| `resume-verb` | Words like 'spearheaded' read as filler when every line uses one. |
| `rule-of-three` | Lists of three in a row are a pattern readers link with AI writing. |
| `not-only-but-also` | 'Not only ... but also' is a pattern readers link with AI writing. |
| `same-verb-opening` | Two lines in a row start with the same word. |
| `uniform-bullet-length` | Every line is about the same length, which reads as templated. |
| `lead-bullet-weak` | The first line under this job has no number, but a later one does. |
| `bullet-taper` | An older job has more lines than a newer one. |
| `canonical-casing` | A tool name is spelled differently from its official spelling. |
| `em-dash` | Long dashes are a common sign of AI-written text. |
| `markdown` | Formatting symbols would show up as stray characters. |
| `invisible-unicode` | An invisible character could trip up job-site software. |
| `street-address` | City and state is enough; a street address adds nothing and exposes you. |
| `personal-details` | US employers don't expect these; they invite bias. |
| `abbreviated-school` | Application forms match your school against a list of full names, so a short form like "CC" matches nothing. |
| `old-graduation-year` | A graduation year from 15+ years ago can invite age bias; you may leave the year off. |

## What the fill advice aims at

`line-fill` fails below `MIN_LINE_FILL` (40%), and for a while the advice printed beside it was
worked back from that same number. On a skills line rendering 39% full that came out as **"cut
41 or add ~1"**: adding one character does clear the gate, and leaves 60% of the row empty. The
floor answers "is this bad enough to stop the page"; it was never an answer to "how much would
fill this line".

So the two are now separate numbers, and only the advice moved - **no resume that passed before
fails now**. Raising the floor to 90% instead was measured and rejected: three lines on a real
resume that passes today would fail, two of them skills lists, and the fix for those is padding
a tool list with tools the candidate does not use.

| Number | Where | Value | Why there |
|---|---|---|---|
| `MIN_LINE_FILL` | `render.py`, the FAIL gate | 40% | Unchanged. Tails cluster at 3-35% and then stop; nothing lands between there and a filled line, so it is a threshold, not a knob |
| `TARGET_LINE_FILL` | `render.py`, what `add ~N` aims at | 90% | The wrapped blocks on the corpus that read as filled land at 93% and 98%. The 10% left over is what stops the last word the advice asks for from spilling into a row of its own |
| `TWO_LINE_FILL` | `tailor.py`, low edge of the writer's two-line window | 60% | **Not** `TARGET_LINE_FILL`: a bullet's second line is capped by what two lines hold, so aiming the window that high empties it. Window width in Caladea, in characters: 49 at 40%, 28 at 60%, 14 at 75%, 4 at 85%, **empty at 90%.** 60% is the fullest edge still leaving about four words of choice |

The window edge is the one that changes what gets written. At 40% it advertised a 145-character
bullet as one that "fills two" while its second row came out 48% empty - which is where a real
resume's 49%-full second row, carrying ten words and half a line of white space, came from. The
edge is now 166 characters, and 145-165 joins the gap the writer is told never to write into.

## The blind spot this document had

`empty-clause` was added after the rubric had already passed a bullet no hiring manager should
have to read: *"Expanded the shared component library to every micro-frontend, so new
screens assemble from existing pieces and every app shares one consistent interface."* Fourteen
of its twenty-two words explain what a component library is, and they sat in the first line of
the most recent role - the single most-read line on the page.

It passed every tier. Accuracy: nothing false. Substance: a real scope number. Relevance: right
role, leading position. Clarity: one sentence, the number names what it counts. The rubric had a
rule against saying something the reader cannot check and no rule against saying something the
reader already knows, and those are the same failure measured from opposite ends.

The general form is worth keeping in mind when adding any rule here: a tier that asks only "is
this true?" and "is there evidence?" will pass a sentence that is true, evidenced and empty.

**Measured before shipping.** Purpose-clause form only:

| corpus | bullets | hits | false positives |
|---|---|---|---|
| real resume | 29 | 1 | 0 |
| `master.example.yml` | 4 | 0 | 0 |
| same candidate's prior resume (out of sample) | 32 | 1 | 0 |
| constructed adversarial clauses | 8 | 4 | **1** |

The one constructed false positive - *"Added Storybook so designers review components before
merge"* - names a real workflow change in plain words with no number or proper noun in the
clause. That is the rule's known limit: it detects *names nothing specific*, which correlates
with *adds nothing* without being the same thing. It is a WARN for that reason - on generated
text too since 2026-09-24, so it is only ever reported.

## Reviewed 2026-09-24

An adversarial review read the rules as a nurse, a new graduate and a finance analyst would meet
them, and found rules that pushed toward invention or failed a true resume forever. Each change
below replaced a rule argued or measured wrong - re-propose the old form only with new evidence.

| Was | Now | Why |
|---|---|---|
| Budget floor fixed at 500 words | One page = 75-100% of what a page holds at this density; two pages as before; 860 ceiling kept | A full page holds ~378 words in Caladea, so the one-page window (500-378) was empty and every one-page resume failed. The prompt now prefers one page for under ~5 years or whenever the facts fit |
| Budget fails a page short of the window | Reports as info when every fact together cannot reach the lowest window | A gate the truth cannot pass is a demand to invent |
| `no-abbreviated-title` over the whole PDF text | Role headings only | "Robert Hayes Jr." and "Martin Luther King Jr. Hospital" failed forever, with nothing the tailorer could change |
| Style and grade words banned outright | Pass when another fact or the posting uses the word | *Advanced Cardiac Life Support (ACLS)*, *Consumer Insights*, *leveraged finance* are the field's own terms; paraphrasing them loses the search match (Tier 3) |
| `across`, `within` style words | Removed | They carry scope ("across 6 teams"), and scope is evidence (Tier 2) |
| Hedges banned in the prompt | A sourced "assisted with" is kept; upgrading a part is banned instead | The ban pushed "assisted" to "performed" - an ownership claim, Tier 1 |
| `ai-era` matched `rag`, `evals`, `embeddings`, `fine-tuning` in any case, and failed own wording | `RAG` in capitals, never "RAG status"; the bare words dropped; own wording WARNs | A project manager's RAG status report, a nurse's competency evals and a maths bullet on embeddings read as backdated AI claims |
| `empty-clause` FAIL on generated text | WARN always | Its one measured false positive was a real workflow change; a detector of "names nothing specific" cannot decide "adds nothing" |
| "1,000" vs "1000" unresolved; `round-metric` blind to "20 percent" | Separators stripped; written-out percent accepted | Both failed a number the candidate wrote |
| Coverage evidence = on-page bullets only | Also `certifications[i]`, `education[i]`, `skills:<item>` | A required licence proven by the Certifications line read as a gap, inviting a bullet that restates it |
| Certifications always near the end | Move under the summary when a requirement names a held one | A knock-out requirement belongs where the first pass reads |
| Never drop a role | The trailing run of roles ended 15+ years ago may go | The 10-15 year convention (Tier 3); only from the end, so no date hole opens |
| Bullet counts by age | By relevance, recency breaking ties; required evidence always on the page, leading its entry | An old role proving a required item was cut to zero bullets |
| Skills lines filled by adding items | Trim or merge groups; never add a low-value item; a skills item not in master FAILs | Filling a line with a tool the candidate barely used is padding (see [What the fill advice aims at](#what-the-fill-advice-aims-at)) |
| Line fit by any cut | Never cut a number or name to fit; shorten other words | The number is the evidence (Tier 2) |
| `title_mirror` substring match | Whole words; FAIL when it adds a seniority word the candidate's title lacks; listed for the user to confirm | "Nurse Manager" mirrored onto "Staff Nurse" claims a promotion |
| Year-only dates stretched to January-December on import, printed as "Jan 2019 - Dec 2021" | A year stays a year; a span with a year-only end prints years only; comparisons run at the precision both dates carry | An invented month is a date a background check may not match (Tier 1) |
| Any all-caps PDF line skipped by import recovery as a heading | Only named section headings skipped | "ACTIVE TS/SCI CLEARANCE" or "BLS/ACLS CERTIFIED" could be dropped without tripping the gate; every left-out line is now printed for the user |
| No place for volunteer work, awards, clearances; projects needed dates | `other` sections printed verbatim; projects may be undated | A fact with no field was a fact lost on import |
| Education always after Experience | First when there are no jobs, or a degree ended within 12 months over under 24 months of work | A new graduate's strongest line was at the bottom |
| Nothing said a street address, birth date or marital status was on the page | `street-address`, `personal-details` WARN on the untailored resume; `old-graduation-year` WARN suggests `hide_year` | US hiring does not ask for these and they invite bias; the year is never hidden without the user's say |
| A gap was only ever a gap | `career_break` entries shown with the jobs, no lines under them, and counted as covered time | A named break answers the question a silent gap raises |
| Dropped items unexplained; report in rule slugs and ids | `reasons` per dropped bullet, role and skill; "Check before sending.md" in plain words, ids and rule names only in a trailing parenthetical | The user can challenge every decision only if each one carries a visible reason |

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
