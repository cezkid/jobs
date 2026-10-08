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
| match (0.35) | share of the posting's **required** asks the resume backs: years asked vs dated years (`knockout.dated_years`), degree asked vs held, a language asked vs their Languages line at working level (every non-English one it names; Conversational / Basic back none; English alone not counted - the resume is in it; 88 of 1,966 live required lines name one, 2026-10-08), named tool (Excel, SAP) on the resume, else half the ask's content words found. Traits ("detail-oriented") not counted. `experience_years_min` = one more ask when no line said years - never on an early-career title or an intern / junior row (`rank.early_career`): there the tag read 10 on "Software Engineer - New Grad", 20 on "Entry Level Sales Representative", 7 on "18+ years old" (2026-10-07) | Minimum qualifications are a real knock-out (Hidden Workers 2021, HBS/Accenture - survey; Enhancv 2025, n=25 recruiters - vendor survey; `resume/bullets.md`). Weighs most. Word overlap = an estimate for order, never a verdict; `job-tailor` judges each ask w/ the user |
| asks (0.15) | required asks + lead/own/manage asks counted twice; full at `asks_light` (8) or fewer, 0 at `asks_heavy` (16). Level 2+ rungs above their `career_level` halves it | Owner: "some ask a lot". Cut-offs measured 2026-10-04: 944 live US rows, 7 occupations, 449 list required asks, median 7, top tenth 12+, 14 at 16+. Convention, not a study |
| pay (0.2) | place among the listed pay of the jobs scored; under their pay floor halves it; not listed 0.25 | Their own floor (setup answer). Unknown pay sits below a listed middle, not favoured. Under the floor = hidden unless let back in a thin week (`pay-filter.md`) |
| where (0.15) | their own where-first order (search settings passes): first 1, last 0 | Their stated preference, nothing inferred |
| fresh (0.15) | 1 posted today, linear to 0 at `fresh_days` (21); posting date = freehire's first sighting, else when it reached their list | Owner: "newer jobs are better". Old postings are more often filled or ghost (`freehire.md` reality, stale). Convention |
| demerit (-0.15 each) | rank's own: likely ghost, level/hours mismatch (internships only: a title naming no internship, early-career level or student programme), no sponsor, clearance they can't hold, a student's "asks 3+ years" / graduation window missed (`rank.asks_beyond`) | Same signals rank already demotes by |

## Freshest first

Before the score: jobs posted in the last day (`fresh_windows[0]`) go first, best first among them.
Fewer than `fresh_enough` (5) there => the window widens - 2, 3, 5, 7, 14, 21 days - until it holds
that many; then the next group starts the same way. Older than the last window or age unknown = last.
Why: owner 2026-10-08, "start with 1 day and if not keep expanding" - top picks sat 5-7 days old while
19 open jobs had gone up in the last day; the `fresh` weight alone (0.15) let pay + match outvote a
week. Old postings are more often filled (`freehire.md` reality). Convention, not a study.

No resume yet, or a posting w/ no required asks listed => match + asks neutral 0.5; Today says once
"Add your resume for a better order".

## Why line

Plain words in the score's order: "Matches 8 of 10 asks · Asks a lot: 14 requirements · $160k
(meets your pay) · remote · posted 2 days ago", then any demerit reason. Never a number score.

## Rejected

- Keyword-density score vs the posting: rewards stuffing, which `resume/bullets.md` rejects.
- Hiding low scorers: order only; their search settings decide what's on the list.
