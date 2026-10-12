# Best to apply next

Today page section, chat brief (`today --brief`), morning email + pop-up and `rank --best` share one
order: `app/best.py`. Replaced "New since last check" (owner 2026-10-04): a job from last week that
fits beats today's that doesn't. "N new since last check" stays as a header figure.

## Which jobs

Open rows on their list (rank's hides + blocks applied) w/ no job folder, not applied, not closed,
not stale (likely filled, `freehire.md` reality). Email: unseen rows only, same score.

## Score

Each factor 0-1, weighted mean (`rank.best_next` in `app/defaults.yml`), less `demerit` per rank
demerit. Ties: listing id order => same list reads the same every time.

| Factor | How | Why + basis |
|---|---|---|
| match (0.35) | share of the posting's **required** asks the resume backs: years asked vs dated years (`knockout.dated_years`), degree asked vs held, a language asked vs their Languages line at working level (every non-English one it names; Conversational / Basic back none; English alone not counted - the resume is in it; 88 of 1,966 live required lines name one, 2026-10-08), a licence or certification asked vs its short form anywhere in their resume details or a certification's initials ("Certified Internal Auditor" = CIA; one from an either/or list answers it; any other certificate never does; an exam part or candidacy - "FRM Part I", "CFA Level II Candidate" - holds nothing yet; before 2026-10-09 "Active CAMS certification" counted as backed by any certificate and Series 63 backed Series 24), a portfolio or reel asked vs a link to their work in their contact links (not LinkedIn; 204 of 551 video postings ask one - before 2026-10-09 it counted against everyone, link or not), named tool (Excel, SAP) on the resume - a maker or edition alone names none ("Adobe", "Pro": a resume w/ Photoshop + Final Cut Pro backed 60+ asks for Premiere Pro or After Effects before 2026-10-09; "the Adobe Creative Suite" / "Microsoft Office" by name is backed by any of that maker's tools), several-word names read as one (After Effects, Final Cut, Media Composer, Power BI, United States), else half the ask's content words found - each word also w/o its plural or -ed / -ing (edit / edits / edited / editing met no other form at 6 letters before 2026-10-09; old vs new on 13,000 required lines of 6 fields w/ a matching resume each: video + creative +290 backed (portfolio asks most), finance / software / healthcare +6 to +8, marketing +12; every change outside video read by hand, video by sample + the word each turned on). Traits ("detail-oriented") not counted. Age minimum, work permit, physical-ability asks not counted - answered on the form ("Must be at least 18 years of age", "Authorized to work in the US without sponsorship", "able to lift 50 pounds"; age 18+ on 12 of 143 forms read, a work permit on 70, `app/web/research/knockout-questions-2026-10.csv`; before 2026-10-10 each counted against everyone, as citizenship did); nor age-coded asks ("recent college graduate", "digital native", "young" - never "young children") (`best.NOT_ON_RESUME`; a real ask on the same line - years, a degree - is read first; a driver's licence or CDL is a credential, read as one). `experience_years_min` = one more ask when no line said years - never on an early-career title or an intern / junior row (`rank.early_career`): there the tag read 10 on "Software Engineer - New Grad", 20 on "Entry Level Sales Representative", 7 on "18+ years old" (2026-10-07) | Minimum qualifications are a real knock-out (Hidden Workers 2021, HBS/Accenture - survey; Enhancv 2025, n=25 recruiters - vendor survey; `resume/bullets.md`). Weighs most. Word overlap = an estimate for order, never a verdict; `job-tailor` judges each ask w/ the user |
| title (0.5) | share of the posting title's kind-of-work words found in their own past titles + headline (half) and anywhere in their resume details (half) - level, schedule and place words left out ("Senior", "Manager", "II", "Remote"), the bracketed part too; "front-end" / "frontend" / "front end" one word (also back end, full stack). No resume, or a title of level words only => 0.5. Why line says "title unlike your past work" only when no word meets | 2026-10-11: an HR director's top 10 held "Tableau Developer", a brokerage analyst's "Payroll Tax Analyst"; match reads asks only, and 4 in 10 postings list none. 1,050 live titles (finance, HR leader, front-end; a fixture resume each) judged same field / adjacent / other by `claude -p` (Sonnet), one run per batch: top-10 quality (nDCG, the judged labels) 0.55 / 0.97 / 0.82 at weight 0 => 0.79 / 0.97 / 1.00 at 0.25. Raised to 0.5 on 2026-10-12 (below, "Measured as a whole"). Own titles weigh half: "analyst" met "variance analysis" (6-letter stems), so "Financial Analyst" read as a senior accountant's own title. Word overlap, an estimate |
| asks (0.15) | required asks + lead/own/manage asks counted twice; full at `asks_light` (8) or fewer, 0 at `asks_heavy` (16). Level 2+ rungs above their `career_level` halves it | Owner: "some ask a lot". Cut-offs measured 2026-10-04: 944 live US rows, 7 occupations, 449 list required asks, median 7, top tenth 12+, 14 at 16+. Convention, not a study |
| pay (0.2) | place among the listed pay of the jobs scored; under their pay floor halves it; not listed 0.25 | Their own floor (setup answer). Unknown pay sits below a listed middle, not favoured. Under the floor = hidden unless let back in a thin week (`pay-filter.md`) |
| where (0.15) | their own where-first order (search settings passes): first 1, last 0 | Their stated preference, nothing inferred |
| fresh (0.15) | 1 posted today, linear to 0 at `fresh_days` (21); posting date = freehire's first sighting, else when it reached their list | Owner: "newer jobs are better". Old postings are more often filled or ghost (`freehire.md` reality, stale). Convention |
| demerit (-0.15 each) | rank's own: likely ghost, level/hours mismatch (internships only: a title naming no internship, early-career level or student programme), no sponsor, clearance they can't hold, a student's "asks 3+ years" / graduation window missed, a required licence or certification their resume details never name - "asks Series 24" (`rank.asks_beyond`, `knockout.credentials_asked`; counted once per credential however many lines ask it - "Series 7" folds into "Series 7 and Series 63", `rank.credential_asks`), an active clearance above the one their resume shows (`knockout.clearance_short`) | Same signals rank already demotes by |

Match is read with `match_prior` (2) asks added at half-backed: (backed + 1) / (counted + 2). 1 of 1
= 0.67, 3 of 3 = 0.8, 8 of 8 = 0.9, 0 of 1 = 0.33. Why: 2026-10-11, 1,200 live rows (finance, HR
leader, front-end, video; a fixture resume each): 4 in 10 list no requirements, so their only ask
was the years tag - "Matches 1 of 1" read as a perfect match and held 2-6 of the top 10 above
"5 of 6" and "8 of 8". A share off one ask is weak evidence; the same shrink-to-the-middle as a
Laplace / Bayesian average (convention, not a study).

## Employers spread, copies sink

After the score, inside each freshness group: each job less `repeat` (0.1) per job from the same
employer placed above it, and less `twin` (0.5) when a copy of the same posting sits above -
same title + the same description opening (markup left out), or the same title + the same 3+
required asks word for word. Order only: `best` stays as scored, nothing hidden.
Why: 2026-10-11, same 1,200 rows: one employer held 2 of the top 10 (UnitedHealth Group), and
35 postings sat twice under two company names - an aggregator's copy (jobgether, himalayas) or
a brand + its parent (PlayStation Global / Sony Interactive Entertainment, Safelite / Belron);
every one read by hand was the same job. Ten picks across ten employers spread the bet; one
employer's system sees every application to it. Convention (recommender re-ranking, MMR), not
a study. Copies kept apart by `rank.collapse` (one row per company + title + place) - a
different company name means a different row there.

## Freshest first

Before the score: jobs posted in the last day (`fresh_windows[0]`) go first, best first among them.
Fewer than `fresh_enough` (5) there => the window widens - 2, 3, 5, 7, 14, 21 days - until it holds
that many; then the next group starts the same way. Older than the last window or age unknown = last.
Why: owner 2026-10-08, "start with 1 day and if not keep expanding" - top picks sat 5-7 days old while
19 open jobs had gone up in the last day; the `fresh` weight alone (0.15) let pay + match outvote a
week. Old postings are more often filled (`freehire.md` reality). Convention, not a study.

Only the first `fresh_first` (5) picks come from that window; after them every other job by score,
any age (`fresh` still weighs). Why: 2026-10-12, on a 375-job security list the last-day window
held about 60 jobs, mostly senior or off-field, and the whole top 10 came from it - a 5-day-old
"Security Analyst" against a security analyst's resume sat at #152. Top-10 nDCG (AI fit ratings,
below): 0.695 => 0.713 on the 4 tuning fields, 0.452 => 0.554 on the 5 held out; HR leader alone lost
(0.92 => 0.84 - its last-day jobs were strong). The owner's 2026-10-08 case (top picks 5-7 days old
while 19 went up in the last day) still holds: the lead 5 are the freshest. `fresh_first: null` =
every job in window order, as before.

No resume yet, or a posting w/ no required asks listed => match + asks neutral 0.5; Today says once
"Add your resume for a better order".

## Why line

Plain words in the score's order: "Matches 8 of 10 asks · (title unlike your past work) · Asks a lot: 14 requirements · $160k
(meets your pay) · remote · posted 2 days ago", then any demerit reason. Never a number score.

When the one ask counted is the job search's years tag (no requirement lines, or none readable): "Asks 5+
years, you have them" / "Asks 8+ years, you have 6" (`best.years_only`). Before 2026-10-12 it said "Matches
1 of 1 asks" - read as a perfect match on the 4 in 10 postings that list no requirements.

## What counts as an ask

The job search tags each requirement line required or preferred; the tag is often wrong, so:
- **Wishes cut out** (`best.asked`): a line that is all wish ("Bachelor's in Accounting or related
  preferred", "MBA or CPA a plus") asks nothing; a wish inside a required line is cut ("6+ years
  (healthcare a plus)" asks the years). A part that also says required / must stays. 2026-10-12,
  7,249 required lines on 1,007 live rows: 217 all wish, 187 cut. Never "5 plus years",
  "competitive advantage".
- **Not on a resume** (`best.NOT_ON_RESUME`, counted neither way): also time zone + working hours,
  on-site / commute / relocation, "based in the US", travel ("travel up to 10%" - never "travel and
  expense reports", "travel arrangements"), hours a week, an employer's equal-opportunity statement.
  69 such lines read by hand, all right.
- **Years of what** (`backed`): a years ask is met only when the years are there AND half the words
  of what they are years of ("3+ years hands-on experience managing OneTrust" - before, any 3 years
  of work met it). "5+ years of experience" alone still needs the years only. 270 years lines where
  the years were enough, an AI asked whether the resume shows that kind of work: years alone agreed
  49% of the time, years + subject 75%; reading any one option of an "A, B or C" list 70-71%.
- **"IT" in capitals** = information technology (also "information technology" spelled out), never
  the filler "it": "Sr. IT Compliance Analyst" was a perfect title for an AML analyst.
- **A name of several words** (capitalised in a row, "of" / "for" / "the" between) is one tool, met
  when half its words are: before, "Uniform System of Accounts for the Lodging Industry (USALI)" was
  met by "Accounts" on any accounting resume. "/" splits names ("Excel/Google Sheets" = two);
  "-based" / "-driven" endings left out. 27 of 5,900 lines changed, read by hand.
- **A name of two words needs both** ("NIST SP 800-53" was met by NIST CSF, "Full Stack Developer" by
  any developer); a kind-of-thing word in a name is left out like "-based" ("HR Expertise", "NIST
  Framework", "Security Processes" - the name is the rest). "React.js" / "Node JS" = React / Node
  ("Node.js" was met by "Next.js", the "js" they share). "US" / "USA" / "United States" are no skill
  ("US payroll regulatory requirements" was met by "US GAAP"). Measured 2026-10-12: 540 required lines
  read by word overlap (60 per field, half met by the old rule, half not), each labelled by `claude -p`
  (Opus, high effort) "does this resume show it": agreement 0.741 => 0.765. Then 43 lines it changes
  that were never tuned on, labelled the same way: new rule right on 37, old on 6. Top-10 nDCG held
  out +0.001 / +0.002 (Sonnet / Opus labels), tuning unchanged.

## Measured as a whole (2026-10-11)

Same 1,050 live rows, fixture resume per field. `claude -p` (Sonnet), one run per field, rated each
job in the top 30 of 4 settings (108 jobs) 0-3 from the resume + the title + its required asks
(right work and meets most asks = 3; pay, place, age ignored). Top-10 quality (nDCG on those ratings):

| | finance | HR leader | front-end |
|---|---|---|---|
| before 2026-10-11 (no prior, title, spread) | 0.06 | 0.68 | 0.46 |
| + `match_prior` 2 | 0.27 | 0.73 | 0.45 |
| + `title` 0.25, spread (now) | 0.72 | 0.81 | 0.75 |

Title 0.4, match 0.5, prior 4 or pay 0.1 moved no field more than a few points either way: kept.
An AI's ratings on one resume per field - a check on direction, not a study. Not tried: a demerit
for meeting a third or less of 4+ asks - word overlap reads 150 of 498 front-end rows that low.

### Again, every job rated (2026-10-12)

1,007 live rows, 4 fields, every candidate job rated 0-3 by `claude -p` (Sonnet; 19 runs of 60 jobs,
each closed when done) against one fixture resume per field: senior accountant (finance search), HR
director (HR leader), front-end engineer, video editor. Top-10 nDCG, average of 4 fields:

| | avg | finance | HR | front-end | video |
|---|---|---|---|---|---|
| start of 2026-10-11 | 0.466 | 0.16 | 0.69 | 0.45 | 0.56 |
| + prior, spread | 0.507 | 0.26 | 0.79 | 0.43 | 0.56 |
| + title 0.25 | 0.636 | 0.41 | 0.85 | 0.68 | 0.61 |
| + names, wishes, not-on-resume lines | 0.644 | 0.44 | 0.85 | 0.68 | 0.61 |
| + own titles half | 0.654 | 0.48 | 0.85 | 0.68 | 0.61 |
| + title 0.5 (now) | 0.685 | 0.51 | 0.92 | 0.71 | 0.61 |

Each factor alone, how often it puts a job rated 3 above one rated 0-1 (0.5 = a coin): title 0.86,
match 0.78, fresh 0.61, asks 0.50, pay 0.41 (better-paid jobs sit above their level more often - pay
stays, it is their own preference; the ratings leave it out on purpose).

Tried, not kept (no gain): each word weighed by how rare it is among the list's asks (0.642); level
read from the posting's + their own titles when the tags are missing (0.653 vs 0.654); without
freshness groups 0.625 (they stay - and the ratings ignore age, which favours dropping them).

### Held out (2026-10-12)

The weights above were set on those 4 resumes; 5 more were never tuned on: security analyst
(security search), program manager, AML compliance analyst, junior front-end (front-end search),
FP&A analyst (finance search), each with the career level its resume shows. 1,451 jobs rated the same
way. Top-10 nDCG: start of 2026-10-11 0.351, before `fresh_first` 0.452, now 0.554 (security 0.16 =>
0.40, compliance 0.22 => 0.45, FP&A 0.29 => 0.68). Own titles at half was slightly worse held out
(0.348 => 0.323 at title 0.25) - kept, title 0.5 more than covers it, watch it.

Tried, not kept: a degree's subject vs the subject asked (77% vs 76% agreement with the AI on 184
lines - it calls Finance close enough to Business, words can't); title read by its best part or its
first part (split at "," / " - "; worse on all fields); a freshness window counting only good-looking
jobs toward `fresh_enough` (one field gained, nothing held out).

### Judged again by a stronger AI (2026-10-12)

Every label above came from Sonnet at default effort, so the gains might partly fit its quirks. The same
46 prompts (2,454 jobs, 9 resumes) were run again by `claude -p --model opus --effort high`. Agreement
with Sonnet: same rating 70%, within one 99%, weighted kappa 0.84 (0.73 security - 0.90 video). Opus
rates a little higher (+0.08 to +0.33 a job), mostly 0s Sonnet gave that Opus calls 1.

Top-10 nDCG, start of 2026-10-11 => now (`fresh_first` off in brackets). "Tuning + level" = the 4 tuning
resumes with the career level their resume shows (setup always asks it; the tuning set had none):

| labels | tuning | tuning + level | held out |
|---|---|---|---|
| Sonnet | 0.466 => 0.713 (0.695) | 0.448 => 0.739 (0.688) | 0.351 => 0.555 (0.452) |
| Opus | 0.551 => 0.772 (0.778) | 0.533 => 0.803 (0.784) | 0.409 => 0.689 (0.553) |

What holds: every gain since 2026-10-11, on both judges. `fresh_first` 5: held out +0.10 / +0.14, tuning
+ level +0.05 / +0.02; on the tuning set without levels Opus has it 0.006 behind. HR leader loses under
both judges (0.92 => 0.84 Sonnet, 0.95 => 0.82 Opus) - its lead 5 rate 3, 3, 3, 2, 3, the loss is a VP
role and a clearance job further down; finance without a level loses too (Opus 0.70 => 0.62). Kept: the
held-out gain is the larger one, and the ratings ignore age, which favours dropping it. Tried 3 / 7 / 10:
3 ties 5 held out and loses HR leader more (0.70 / 0.75), 7 loses held out (0.51 / 0.63). Title 0.5: best
held out under both (0.25 / 0.35 / 0.5 / 0.7 / 0.9 = 0.488 / 0.504 / 0.554 / 0.531 / 0.526 Sonnet; 0.607 /
0.635 / 0.687 / 0.666 / 0.655 Opus); Opus tuning prefers 0.35 (0.785 vs 0.772) - kept at 0.5.

Tried, not kept (held out no better, both judges):
- A capped bonus for preferred asks the resume backs (weight 0.03-0.1, cap 2-5): every setting lost,
  0.01-0.06 held out. Caveat: the rating prompt shows required asks only, so it can't reward this.
- A demerit for a level 2+ rungs above theirs, on top of halving `asks`: where it fires the jobs rate
  lower (frontend-jr 0.36 vs 1.11, Opus), but held out +0.001 / -0.004 at 0.05-0.25 - few reach the top 10.
- A degree "or equivalent experience" met by the degree at that level: the line reading agrees with the
  AI (35 of 38 such lines met; 94 of 108 changed lines right) but held out loses 0.008 / 0.010, security
  0.40 => 0.36 - every security posting carries the line, so match tells them apart less; read as "can't
  tell" loses too. The subject words in them help the order even when the line itself is met.
- An "A, B and C" list of tools met only by half of them (0.741 => 0.724 on the 540 lines); a share of
  2/3 or 0.6 of an ask's words (0.724 / 0.731); the 25 commonest ask words left out (no change); RESTful
  read as REST (4 right, 5 wrong of 9 changed lines).
- Title: generic words ("Group", "Corporate", "Expert") left out - the unmet title words on well-rated
  jobs are field words ("partner" for HR, "producer" for video), not generic ones.

## Shown

Today page + side panel: 10 (owner 2026-10-11, was 5); when Next up is a best job it is the
first of the 10. Chat brief: 3. Morning email: up to `alert.DIGEST_CAP`. The rest: "show me more
jobs to apply to".

## Rejected

- Keyword-density score vs the posting: rewards stuffing, which `resume/bullets.md` rejects.
- Hiding low scorers: order only; their search settings decide what's on the list.
- GitHub job tools reviewed 2026-10-11 (JobSpy, JobFunnel, Resume-Matcher, AIHawk forks,
  career-ops, InternPilot): most only collect jobs or ask an AI for a 1-10 score per job - no
  formula to copy. Taken: employer spread + copy detection (JobFunnel removes copies by
  description similarity), title fit (career-ops' title filter, here graded against the resume). Tried,
  not kept: a capped bonus for preferred asks backed (2026-10-12, below). Not yet: a score-band vs
  interview-rate report from their own statuses (career-ops `calibrate`, advisory, needs applications first).
