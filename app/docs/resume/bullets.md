# Bullets - what a line has to do, and what the evidence actually supports

Checked 2026-09-22 vs career centres (Harvard, MIT, Emory, Berkeley, Arizona, UConn), ATS vendor
docs (Greenhouse, Lever), screening data (HireRight 2025), recruiter surveys. Each rule names its
basis; thin basis says so. Scope: claim text `lint.py` sees (bullets + summary); page geometry ->
`typeface.md`.

Rejected: [What did not survive](#what-did-not-survive),
[Considered, not mechanised](#considered-not-mechanised); retired/softened 2026-09-24:
[Reviewed 2026-09-24](#reviewed-2026-09-24). Read before re-proposing a rule.

## The thing that decides it: precedence

**Accuracy > Substance > Relevance > Clarity.** Lower tier never justifies breaking a higher one.

Guards one failure: a lower rule manufacturing a higher breach (demand a number the writer lacks ->
number invented). So each rule = **enforce** (code decides) or **report** (code names, only the
writer fixes). No rule that pressures invention is enforced.

---

## Tier 1 - Accuracy

Can cost the offer, not just the interview. Claims a third party checks.

| Rule | Basis | |
|---|---|---|
| Employer, title, dates match verification | HireRight 2025 (1,000+ HR/talent pros): over 3/4 of employers found discrepancies in prior year, employment verification top category; rate 9.9% (FY21) -> 14.3% (FY24). Role length = field most likely checked. Mirrored posting title = suffix user confirms, never a level their title lacks: "Staff Nurse (Nurse Manager)" claims a promotion. | enforce: `title-changed`, `employer-changed`, `dates-changed`; `tailor.check_selection` fails a `title_mirror` not whole words of the posting title or adding a seniority word (Senior, Lead, Principal, Staff, Manager, Director, Head, Chief, Supervisor) |
| Overlap fine; **unlabelled** overlap isn't | National Resume Writers' Association: "concurrent roles are not frowned upon." Same employer -> stacked titles; different -> marker (part-time, freelance, contract), else reads as date mistake. | enforce: `role-dates-overlap`, incl. same-employer case |
| Every number defensible in interview | Insight Global 2025 (Atomik Research, n=1,005 US hiring managers): ~88% think they spot AI-written material, 54% care; "impressive numbers with no context" a named tell. No controlled study of an undefendable number's cost: consensus + adjacent fraud data. | enforce **in tailoring only** - note below |
| Year in a bullet inside the role's dates | No external source; internal consistency. Jobscan 2026 runs against it (dates on header, not bullets). | **report only** - see [Considered, not mechanised](#considered-not-mechanised) |
| No uncheckable grade | Berkeley: "minimize the use of adjectives and adverbs"; Arizona: "better to be clear than be complicated". *Advanced, best-in-class, world-class, industry-leading* carry nothing; the fact behind them does. Word-ban lists = resume-product blogs; defensible core is substitution. **Grade word inside a term isn't a grade** (*Advanced Cardiac Life Support*, *advanced practice nurse*). | enforce: `unmeasurable-grade`, skipped when facts or posting use the word |

**Where numbers are actually born.** `unresolved-entity` FAILs a tailored number in no master
claim. Nothing checks master itself - where numbers enter; no code tells recalled from guessed.
`round-metric` catches only generated `10|15|20|25|30|40|50|100%` absent from master (eight values).
A human still vouches for every master figure.

## Tier 2 - Substance

What earns the line its space.

| Rule | Basis | |
|---|---|---|
| Bullet carries **evidence**: outcome metric, else scope (how many / large / often, source known to writer) or named qualitative result (approval won, process adopted, audit passed). None -> reported, never filled. | Most contested point. MIT PAR ends in a result; Emory: "Action Verb + task, resulting in quantitative outcome". But **Arizona: not every bullet needs a numeric result** ("whenever possible"). Emory splits *scale* from *results* questions: scope alone = quantified. | **report** - proxy `specificity` |
| **Every clause adds something new.** Fails when true of any instance ("a component library, so new screens assemble from existing pieces"), restates the opening, or true of anyone in the role ("shipping features end to end"). | Mirror of Tier 1: true by definition -> conveys nothing, spent words at 7 s. AI-tell shape: Insight Global 2025 - rejection tracks "generic, uncontextualised content"; Arizona warns against bullets to "sound professional". Duty dressed as outcome - Harvard, Emory, Berkeley rank last. | **report**: `empty-clause` WARNs, purpose-clause form only (*names nothing specific*, not *adds nothing*); other forms report |
| Achievements over duties | Most consistent rule found, no dissent. Harvard: "not demonstrating results" a top mistake; Emory: "daily job duties and tasks" heads "do not include"; Berkeley: "the impact that your work had". | **report** - lives in facts, not shape |
| Scope vs change numbers differ; all-one-kind role worth noticing | Emory "Scale" vs "Results" questions; MIT scale ("over 100,000 data points", "size of your department, event, budget") vs % change. Both quantify. | **report only** - enforcing demands a scope number; Tier 1 wins |
| No hedged opener - **unless the hedge is the truth** | Arizona cuts "helped to", "worked on", "responsible for". Dissent: UConn *recommends* "assisted", "collaborated" - objection is the opening, not the word. Own "assisted with" -> "performed" = ownership claim (next row), Tier 1. | **report**: `hedge` WARNs, quiet when another fact uses it. Prompt keeps sourced hedge, bans upgrades (assisted -> performed, coordinated -> led, member -> lead) |
| Ownership matches actual role | Screening red flag: "led" work merely joined, "managed" w/ no reports, team result as personal. Surfaces at reference checks. | **report only** - measured 100% false positives (below). `tailor.py`: never upgrade the candidate's part |
| No two bullets on one template | Insight Global 2025: "identical sentence structure across all bullet points" a primary AI tell, w/ "vague power verbs without proof". Rejection tracks generic content, not AI use - ~80% of recruiters wouldn't reject merely for AI help. | partial: `same-verb-opening` compares first words. **No shipped check measures syntax.** `uniform-bullet-length` = word-count spread, unmeasured |

## Tier 3 - Relevance

Getting in front of a person.

| Rule | Basis | |
|---|---|---|
| Posting's literal term for anything searched (tools, certifications, licences, titles, hard skills) - **only for what the candidate has.** Replaces wording, never introduces a thing; unbacked term = gap to report. | Mechanism = recruiter *search*: Greenhouse Boolean (AND/OR/NOT, quotes, wildcards); Lever matches variations, **not** acronyms; Jobscan: 97.4% of Fortune 500 on detectable ATS, 76.4% of recruiters search posting skills. | already in `tailor.py`; `unresolved-entity` + `inferences` enforce possession |
| Don't write for an auto-rejecter | "75% auto-rejected" = Preptel, defunct vendor, no method. Enhancv 2025 (n=25 US recruiters): 92% no auto-reject on formatting, keywords, match score; the 8% use knock-outs. Density not a score. **Knock-outs real but narrow**: work authorisation, licences, location, minimum qualifications, long gap (HBS/Accenture 2021 *Hidden Workers*, `schema.py:20`). | n/a |
| Lead each role w/ bullet most relevant to **this** posting | Indeed: most important at top. Berkeley: follow "the order or priority that the employer has stated in their position description". | already in `tailor.py`; `lead-bullet-weak` warns: opener no number, later one has |
| Bullet counts follow relevance, recency breaking ties | Emory flat "3-5 bullet points below each role"; taper backed by no source or data: convention. `tailor.py` ladder (3-5 recent, 6 max, 2-3 older) ranks by relevance: role proving a *required* item keeps those bullets; oldest -> 0 only if it proves nothing required. Every proven required item on page, leading its entry (Berkeley). `bullet-taper` catches *inversion* only; even spread passes. | soft; `bullet-taper` WARN |
| 10-15 years, older only if exceptionally relevant | Indeed, Monster, Coursera: relevance + age-discrimination exposure. Consensus, no study fixes cut-off. Drop only from list end, ended 15+ years ago (`tailor.OLD_ROLE_YEARS`); mid-career drop = date hole (gap, below). | enforce: `check_selection` fails other drops |
| Level readable from scope the candidate has (team, budget, volume, scale). Absent -> unsignalled; never adjust verb or number to reach a level. | Screening checks "the seniority and ownership the job needs". Practitioner heuristic, not measured. | **report only** |

## Tier 4 - Clarity

Surviving one pass at scanning speed.

| Rule | Basis | |
|---|---|---|
| One idea, one sentence - **unless the page disagrees** | UConn: "one sentence, typically 1-2 lines"; MIT: "bite-sized chunks ... 1-2 lines"; Emory: at least one full line, two max. **`line-fill` + `pages` are FAIL gates; this is style:** splitting a filled line at its semicolon measured 87% -> 65% row + 21% stub (floor 40%). Page wins. | in `tailor.py`; **never enforce a sentence count** |
| Required certifications under the summary | Knock-out (Tier 3) must be found on first pass, not page two's foot. | enforce: `tailor.page_model` moves Certifications up when a requirement names a held one (full name or bracketed short form) |
| Assume ~7 s first pass | One small study: The Ladders 2018 - **30 recruiters**, eye-tracked 10 weeks, 7.4 s, up from 6 s (2012). Not peer-reviewed, one vendor, no replication, source unreachable. Every "6-second scan" traces here. Buys headings, titles, each role's first bullet. | n/a |
| Acronym expanded at least once | Lever search misses acronyms. Gloss once per page. Employer-internal jargon -> replaced, not glossed. **Vs Tier 3: does the reader's field write it that way** - specialist term keeps spelling, internal shorthand doesn't. | in `tailor.py` (only place posting is known) |
| Every number names what it counts | Modelled in every Emory + MIT example ("over 100,000 data points", "4 team members"), never stated. Baseline strengthens a % ("18 minutes to 7") - **report missing, never demand:** often a former employer's figure. | **report** |
| Uniform bullet punctuation | No source; consistency. Real master ends claims w/ period, `master.example.yml` none -> mixed page. | `tailor.py`: follow master |

---

## What the page cannot fix

Outside bullet wording; outranks it.

**Layout beats wording for machine readability.** Ladders: multi-column, clutter, missing headers
and job titles sank resumes - same as ATS guides flag (tables, text boxes, graphics,
header/footer). Jobscan parser pass rates: 88% Workday, 91% Greenhouse, 93% Lever. `render.py` ->
single-column, heading-led; render gates check tables, images, header/footer text.

Readable != filled in. Forms (Workday, iCIMS, Taleo, SuccessFactors) fill fields from *line shape*
(heading, then detail). Measured on Workday, 2026-09: `BA, Field | School` -> school "Field |
School", Degree empty ("BA" not on its list), "<Town> CC" unmatched. So `render.py` prints
institution on its own line, spelled-out degree + field under (`DEGREES`); `entry-lines` re-reads
each PDF for whole heading + detail lines; `abbreviated-school` warns. Workday Skills box often
empty regardless (own skill list only) - form, not file; convention, unmeasured.

Languages: own `Languages` heading, one per line, level in brackets (`Spanish (Fluent)`), never in
Skills. Parsers store language + level (Textkernel data model); Jobscan, Indeed: name-then-level,
standard scale (ILR US government, CEFR Europe). "English and Spanish - fluent in reading, writing
and speaking" pairs level w/ one or neither. Vendor docs + convention, unmeasured.
`language-level` warns; level asked, never guessed.

**Unexplained gap is the problem, not the gap.** LiveCareer 2025: over half of seekers had a 1+
month gap, 1 in 4 12+ months; MyPerfectResume 2025: 79% of hiring managers would hire w/ an
explained gap. Under ~3 months: nothing. `schema.py` flags past 6 (HBS/Accenture 2021). Past 18
months: no wording guidance in sources - real hole.

**Short tenure is not a bullet problem.** Remedy = contract/part-time marker, or nothing. Indeed
Hiring Lab 2025: median tenure ~2 years 3 months, job-hopping slowing. Pattern draws scrutiny, not
one instance.

## What the code checks

`lint.py` measures; writer rewrites. `hit()`: WARN on own words, FAIL on generated.

| Check | Catches | Severity |
|---|---|---|
| `title-changed`, `employer-changed`, `dates-changed` | identity field altered | FAIL |
| `unknown-entry`, `inference-source` | entry or added claim w/o master source | FAIL |
| `unresolved-entity` | generated number, tool, company in no master fact; "1,000" = "1000" | FAIL |
| `ai-era` | AI wording / tool before its release in an older role. `RAG` capitals only, never red-amber-green; bare *evals*, *embeddings*, *fine-tuning* excluded | FAIL generated, WARN own |
| `role-dates-overlap` | role ends after next starts; same-employer named | WARN |
| `company-legal-id` | employer missing Inc./LLC | WARN |
| `round-metric` | generated `10|15|20|25|30|40|50|100%` not in master (`N%`, `N percent`, `N per cent`) | via `hit()` |
| `unmeasurable-grade` | uncheckable grade, bullet or summary, unless posting/fact uses it | via `hit()` |
| `empty-clause` | purpose clause (so, allowing, enabling, ...) w/o number, proper noun, known tool | WARN |
| `specificity` | no product, stack item, number, proper noun | via `hit()` |
| `style-word` | 17 words over-represented in generated prose, unless posting/fact uses it | via `hit()` |
| `hedge` | helped, contributed to, assisted with, played a key role - unless a fact uses it | WARN |
| `resume-verb` | leveraged, spearheaded, orchestrated, synergized, drove innovation - unless posting/fact uses it | WARN |
| `rule-of-three`, `not-only-but-also` | two generated-prose shapes | WARN |
| `same-verb-opening` | consecutive bullets, same first word | WARN |
| `uniform-bullet-length` | word-count spread below craft floor (unmeasured) | WARN |
| `lead-bullet-weak` | opener no number, later one has | WARN |
| `bullet-taper` | older role more bullets than newer above | WARN |
| `canonical-casing` | drifted tech spellings (15 names) | WARN |
| `em-dash`, `markdown`, `invisible-unicode` | generated-text characters | via `hit()` |
| `street-address`, `personal-details`, `old-graduation-year`, `abbreviated-school` | own file only (`resume-lint`): house number, apartment, suite, ZIP in location; birth date, age, marital status, nationality; degree 15+ years ago w/o `hide_year`; shortened school (CC, Univ., U of); languages line not one language + bracketed level | WARN |
| `spelling` | British form (`US_FORMS`: theatre, colour, organise, modelling, licence...) or unknown word one letter from a known one, likely word named. Skips skills, stack, `WORK_WORDS` (workflow, dataset, telehealth...), names, tool tokens; generated may use any facts/posting word. Scorers fail the page on one error | via `hit()` |
| `compound-modifier` | one of 32 open two-word modifiers before noun (*live streaming channels*, *full stack engineer*); never after (*shipped end to end*) | WARN |
| `overused-opening` | one opener on 4+ bullets (convention, unmeasured) | WARN |
| `filler-word` | *successfully*, *actively*, first person (me, my, we, our; *I* only opening a sentence). *the, that, which, their*, *lazy* ("lazy loading") left out | WARN |
| `pages`, `line-fill`, `contact-line`, `no-prose-block` | page geometry (`render.py` gates) | FAIL |
| `split-words`, `text-color`, `heading-gap` | letters 0.04em+ apart; non-black text outside links; unequal heading space - [page-format.md](page-format.md) | FAIL |
| `budget` | words outside every window: one page 75-100% full, or two w/ second 60%+. Facts too few for lowest window -> info | FAIL / info |
| `no-abbreviated-title` | Sr./Jr. in role heading - never name ("Robert Hayes Jr.") or employer | FAIL |
| selection: mirror, skills, coverage, dropped role | `tailor.check_selection`: mirror claiming a level, skill not in master, coverage evidence off page, role dropped not from old end | FAIL |

## Why each rule - in words the user can take

Chat's answer when asked why a line was flagged; first line of "Check before sending.md".
Mirrored from `lint.WHY`; `test_lint` keeps them in step.

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
| `language-level` | Resume readers store each language with its own level, so write one per line with the level in brackets, like Spanish (Fluent). |
| `old-graduation-year` | A graduation year from 15+ years ago can invite age bias; you may leave the year off. |
| `spelling` | Resume scanners count a spelling mistake against the whole page, and US employers read British spellings as mistakes. |
| `compound-modifier` | Two words describing the next one take a hyphen - live-streaming channels, full-stack engineer. |
| `overused-opening` | One word starts many of your lines; a different true verb here and there reads less repetitive. |
| `filler-word` | Words like 'successfully' or 'my' take room and add nothing the line does not already say. |

## What the fill advice aims at

`line-fill` fails below `MIN_LINE_FILL` (40%); advice was once worked back from it: skills line at
39% -> **"cut 41 or add ~1"** - clears the gate, leaves 60% empty. Floor = "bad enough to stop the
page?", not "what fills the line?". Now separate numbers; only advice moved - **nothing that passed
fails now**. Floor at 90% measured + rejected: 3 lines on a real passing resume fail, 2 skills
lists, fixable only by padding w/ unused tools.

| Number | Where | Value | Why there |
|---|---|---|---|
| `MIN_LINE_FILL` | `render.py`, FAIL gate | 40% | Unchanged. Tails cluster 3-35% then stop -> threshold, not knob |
| `TARGET_LINE_FILL` | `render.py`, `add ~N` target | 90% | Filled-reading wrapped blocks land at 93% + 98%; 10% spare stops the last word spilling to its own row |
| `TWO_LINE_FILL` | `tailor.py`, low edge of two-line window | 60% | **Not** `TARGET_LINE_FILL`: aiming high empties the window. Caladea window chars: 49 at 40%, 28 at 60%, 14 at 75%, 4 at 85%, **empty at 90%.** 60% = fullest edge w/ ~4 words of choice |

At 40% the edge sold a 145-char bullet as "fills two" w/ second row 48% empty -> a real resume's
49%-full second row (ten words, half a line white). Edge now 166 chars; 145-165 = the no-write gap.

## The blind spot this document had

Rubric passed: *"Expanded the shared component library to every micro-frontend, so new screens
assemble from existing pieces and every app shares one consistent interface."* 14 of 22 words
define a component library - in the most-read line on the page (most recent role, first bullet).
Passed every tier: true, real scope number, right role + position, one sentence. Rubric banned what
the reader *can't* check, not what they *already know* - same failure, opposite ends. Hence
`empty-clause`. Any tier asking only "true?" + "evidence?" passes true, evidenced, empty.

**Measured before shipping.** Purpose-clause form only:

| corpus | bullets | hits | false positives |
|---|---|---|---|
| real resume | 29 | 1 | 0 |
| `master.example.yml` | 4 | 0 | 0 |
| same candidate's prior resume (out of sample) | 32 | 1 | 0 |
| constructed adversarial clauses | 8 | 4 | **1** |

False positive: *"Added Storybook so designers review components before merge"* - real workflow
change, no number or proper noun. Limit: detects *names nothing specific*, not *adds nothing* ->
WARN, on generated text too since 2026-09-24.

## Reviewed 2026-09-24

Adversarial review as a nurse, new graduate, finance analyst: rules pushing invention or failing a
true resume forever. Re-propose an old form only w/ new evidence.

| Was | Now | Why |
|---|---|---|
| Budget floor 500 words | One page = 75-100% of page capacity at this density; two pages unchanged; 860 ceiling kept | Full page ~378 words in Caladea -> window (500-378) empty, every one-page resume failed. Prompt prefers one page under ~5 years or when facts fit |
| Budget fails short page | Info when all facts can't reach lowest window | Gate truth can't pass = demand to invent |
| `no-abbreviated-title` on whole PDF | Role headings only | "Robert Hayes Jr.", "Martin Luther King Jr. Hospital" failed forever |
| Style + grade words banned | Pass when a fact or posting uses the word | *Advanced Cardiac Life Support (ACLS)*, *Consumer Insights*, *leveraged finance* = field terms; paraphrase loses search match (Tier 3) |
| `across`, `within` style words | Removed | Carry scope ("across 6 teams") = evidence (Tier 2) |
| Hedges banned in prompt | Sourced "assisted with" kept; upgrades banned | Ban pushed "assisted" -> "performed": ownership claim, Tier 1 |
| `ai-era` matched `rag`, `evals`, `embeddings`, `fine-tuning` any case; failed own wording | `RAG` capitals, not "RAG status"; bare words dropped; own wording WARNs | RAG status reports, nurse competency evals, maths embeddings read as backdated AI |
| `empty-clause` FAIL on generated | WARN always | Only measured false positive was a real change |
| "1,000" vs "1000" unresolved; `round-metric` missed "20 percent" | Separators stripped; written percent accepted | Both failed the candidate's own number |
| Coverage = on-page bullets only | + `certifications[i]`, `education[i]`, `skills:<item>` | Licence proven by Certifications read as gap, inviting a restating bullet |
| Certifications near end | Under summary when a requirement names a held one | Knock-out belongs on first pass |
| Never drop a role | Trailing roles ended 15+ years ago may go | 10-15 year convention (Tier 3); end only -> no date hole |
| Bullet counts by age | By relevance, recency breaks ties; required evidence on page, leading | Old role proving a required item cut to 0 |
| Skills lines filled by adding items | Trim/merge groups; never add; item not in master FAILs | Barely-used tool = padding ([What the fill advice aims at](#what-the-fill-advice-aims-at)) |
| Line fit by any cut | Never cut number or name; shorten other words | Number = evidence (Tier 2) |
| `title_mirror` substring match | Whole words; FAIL on added seniority word; listed for user | "Nurse Manager" onto "Staff Nurse" = promotion |
| Year-only dates -> "Jan 2019 - Dec 2021" on import | Year stays year; year-only end -> years only; compare at shared precision | Invented month may fail background check (Tier 1) |
| Import recovery skipped any all-caps line as heading | Named section headings only | "ACTIVE TS/SCI CLEARANCE", "BLS/ACLS CERTIFIED" could drop silently; every left-out line now shown |
| No volunteer/awards/clearances; projects needed dates | `other` sections verbatim; undated projects OK | Fact w/o field = lost on import |
| Education always after Experience | First when no jobs, or degree ended within 12 months over under 24 months of work | New graduate's strongest line was last |
| Nothing flagged street address, birth date, marital status | `street-address`, `personal-details` WARN (untailored); `old-graduation-year` suggests `hide_year` | US hiring doesn't ask; invites bias; year never hidden w/o user's say |
| Gap only ever a gap | `career_break` entries w/ jobs, no lines, counted as covered | Named break answers what a silent gap raises |
| Summary 1-2 lines (prompt, file notes) | Up to 4, last well filled; 57-word cap unchanged | Guidance: 3-6 lines. 57 words already ~5 lines (~12 words/line Caladea); cap 90 would allow 7 |
| No spelling check | `spelling` WARN own, FAIL generated; typo-shaped + British only | Scorers fail page on one error; US reads *theatre* as one. Plain dictionary flagged *workflow*, *dataset*, *telehealth* -> one-letter-off unknowns only |
| Dropped items unexplained; report in slugs + ids | `reasons` per dropped bullet, role, skill; "Check before sending.md" plain words, ids/rules in trailing parenthetical | User can challenge only decisions w/ visible reasons |

## Considered, not mechanised

Measured on real 29-bullet resume + `master.example.yml`; rejected. No hits = unproven; all false
positives = dead.

| Candidate | Measured | Why not |
|---|---|---|
| `date-outside-role` - bullet year outside role span | **0 hits either corpus.** Motivating example: bullet + header agreed in source; where dates differ, no year in bullet. Real error was a *date* error - `role-dates-overlap` caught it 4 times. | Unproven; false positives semantic: *Windows 2000*, *port 2019*, *modernised a 2014 codebase* are correct English, no regex separates. Prose in Tier 1 |
| `bullet-two-sentences` | 2 hits, **both false positives**: one line at 87% + 88%; split -> 65/21%, 60/28%, two stubs under 40% | Worse page for a style note, vs two FAIL gates |
| `acronym-without-expansion` | 16 acronyms, ~13 false positives (AWS, UI, REST, PHP, US, UK) | Needs hand-kept "known acronyms" list - judgment as regex, wrong on occupation change. `tailor.py` covers the knowable case |
| `ownership-verb-exceeding-title` | 1 hit per corpus, **both false positives**: "Led a 4-person team" under *Lead Developer*; "Led design system migration", normal IC work | Needs reporting line; no file has it |
| `bare-percentage-without-baseline` | 3 hits, all true, all good bullets | Fix needs a number candidate lacks. Report only |
| `stale-tech-in-skills` - tool as current skill past end of life | 1 true positive, 0 false positives | Judgment, not measurement: needs occupation-specific end-of-life table; tool is for any occupation. Weakest evidence: staffing-firm advice, no measured penalty. Revisit w/ an occupation-neutral source |

## What did not survive

**"Avoid inflated verbs" (`resume-verb`, WARN) - shipped, stated reason wrong.** No survey,
eye-tracking or career-centre source found against *spearheaded*, *orchestrated*, *leveraged*.
**Indeed's own bullet guide uses "Spearheaded"**; university verb lists recommend this register
over hedging. Sources object instead to vague self-descriptors (*passionate*, *results-driven*,
*team player* - summaries, not bullets) and one strong verb on every bullet or attached to nothing
verifiable. Kept as WARN: cheap proxy for verb monotony, a real AI tell. Better-evidenced check =
`same-verb-opening`.

**"Add soft-skill keywords to close the match gap."** Rejected by own Tier 3 evidence: recruiters
search posting skills, systems don't score-reject, Insight Global names vague self-descriptors an
AI tell.

**"Every bullet needs an outcome metric."** Contradicted by Arizona, vs Tier 1; enforcing it
produced a request to invent a cost-savings figure. Report a role w/ no outcome; never demand one
per bullet.

## Sources

HireRight 2025 Global Benchmark Report. Insight Global, *2025 AI in Hiring* (Atomik Research,
n=1,005, fielded Oct 2024). Enhancv ATS auto-rejection study, 2025 (n=25), via IT Brief. The
Ladders eye-tracking study, 2018 (n=30), via HR Dive. Jobscan ATS Usage Report 2026 + keyword
guidance 2026. Greenhouse Boolean search docs. Career centres: Harvard FAS Mignone Center, MIT
CAPD, Emory CPD, UC Berkeley, University of Arizona, UConn. National Resume Writers' Association.
Indeed Career Guide; Indeed Hiring Lab 2025. HBS/Accenture, *Hidden Workers: Untapped Talent*,
2021 (cited by `schema.py`). LiveCareer 2025; MyPerfectResume 2025; Textkernel.
