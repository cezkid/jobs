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
- Hidden = left off every list; row stays in `jobs.db` (dedupe, relax, a later settings change
  shows it again, never announced as new before it is shown).

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
