# Pay filter - jobs under their lowest pay hidden

`rank.pay_filter` in `app/defaults.yml`; code `rank.pay_filter` (one function - every list goes
through `rank.rank`: Today page + window dashboard, chat brief, morning email + pop-up, `rank`
/ `find`). Owner 2026-10-04: "we shouldn't be saving/showing jobs if below desired pay. only if
job count is low should lower paying jobs be allowed."

## What hides

- `salary_floor_usd` 0 => nothing (no floor, no filter).
- `hide_below_floor` (default on): top of the posted range under the floor ($55k-$90k meets $60k,
  same test as the old boost - `freehire.md` #Filters vs rank boosts).
- `hide_unlisted` (default off): no USD pay listed. Off because unlisted pay != low pay - most
  postings outside tech list none, and pay-transparency laws differ by state. Owner's list
  2026-10-04 (floor $130k): open 1,589 = 665 meet / 58 below / 866 none listed; last 7 days
  194 / 23 / 316. Owner turned it on for themselves after the push-back above (their call).
- Hourly floor (an internship or part-time search): `salary_floor_unit: hour`. The floor stays
  yearly (hourly x 2080, `rank.parse_floor`: `rank --pay-floor 18/hr`) so every comparison is one
  sum; lists, the probe count and What Job Finder knows say it back per hour ("$18/hr"). A
  part-time job (title or tag) listing only a yearly or monthly sum is never hidden by it - the
  hours behind the sum are unknown ($25,000 for 20 hours a week is $24/hr) - and its pay line names
  no verdict. 2026-10-07, 308 intern-titled US rows: pay listed on 74 - 62 hourly, 9 yearly, 2 monthly.
- Hidden = left off every list; row stays in `jobs.db` (dedupe, relax, a later settings change
  shows it again, never announced as new before it is shown).

## Pay read from the posting

Pay-transparency laws put the range in the posting's text; the job search's own pay field often
misses it outside tech, and is stale when it differs. `paytext.stated` (at the job check,
`freehire.pay`) reads the posting's own range; it wins over the field when both are there.
Measured 2026-10-09 on 4,790 US HR-titled + chief rows, full descriptions:
- field set on 190; text range read on 1,915 more. Of 190 w/ the field: same range 138, different
  38, text read none 14 (an amount only in the title, "$15/hr"). Different, read by hand: a range per
  city / level read as one span (the field took one band), or the field a stale or other band on every
  one checked ($22k-32k on a posting saying "$80,000-$82,000"; $125k-170k vs "$195,000 to $251,000").
- Hand check, 50 random text reads: 49 right, 1 a base + OTE pair read as one span (base $140k-152k,
  OTE to $178k). 40 single amounts: right, incl. GS step + bi-weekly county pay (said per year).
- Never read as pay: budgets, revenue, funding raised, bonuses, sign-on, stipends, tuition,
  reimbursements, a benefit's cost ("Medical starts at $8/week"), millions, $0 placeholders, day rates.
  One amount counts only next to a pay word or a period; a range also w/ "USD" after it.
- Stored description is now the whole posting (`freehire.SEARCH`): 3.3x the bytes per row.

## Thin week - closest come back

Live (not stale) jobs that pass and reached their list (`first_fetched_at`) in the last 7 days
< `relax_under_new_per_week` (25) => hidden ones from that same week fill up to it:

1. below the floor, top of range nearest it first - pay known, the gap is small and theirs to weigh;
2. then no pay listed, newest first - unknown, could be either side.

Older hidden ones never come back (would not be new). Each one back says why in its line:
"below your pay: $98k (few new jobs this week)" / "pay not listed (few new jobs this week)".
Basis: owner's rule; 25 a week = their number, not a study.

## Before saving a floor

`uv run app/jobs.py rank --pay-floor 130000 [--hide-unlisted]` prints what it would hide, all open
and last 7 days - say the counts before saving (AGENTS.md, narrowing the search).
