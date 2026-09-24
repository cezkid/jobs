# job-setup

User not technical - `AGENTS.md` #User = not technical binds every step. You run all commands.
Read `app/docs/freehire.md` first: geography, null-facet and `q=` rules below come from it.

Open w/ short paragraph: you'll ask what they're looking for, check how many jobs match, read
their resume, then show first matches; takes ~10 minutes. Add privacy in plain words:
everything in their file list (My Jobs, My Resume, My Settings) stays on this computer; job
searches send only their search settings to freehire.me; their resume is read here in this AI
chat; nothing goes to Job Finder's maintainer without asking them first.

`My Settings/Search settings.yml` exists -> summarize current search in plain words, ask: change
it or start over?

## 1. Interview

Clickable choices, not prose questions (`AGENTS.md` #User = not technical). Measure BEFORE asking
so every option carries a live count: `uv run app/jobs.py probe --facets countries=us` gives all
47 categories + every other facet in one call.

Round 1, one batch of 4:
- what kind of work - 4 grouped families of `category` values, `multiSelect`, counts per option
- where: remote only / remote first / local first / local only
- full time / part time / contract, `multiSelect` + "doesn't matter"
- lowest yearly pay - 4 bands (ranks higher-paying first, never hides jobs; say so in the question)

Round 2, narrows round 1 (batch of 3):
- which exact roles inside the family they picked, `multiSelect`, counts per option
- which city - offer 4 real metros from THEIR timezone (`readlink /etc/localtime`), counts from
  the `cities` facet, so they click instead of typing; "Other" covers the rest
- career level (entry / mid / senior / leader) - `rank.career_level`: titles clearly above or
  below it sort lower, never hidden; never a `seniority` filter (facet null on 30-45% of rows,
  junior lives in title string)

Companies they never want to see: don't ask up front - nothing to name yet. Blocklist
`jobgether` + `builtin-integration-sandbox` w/o asking, but say why in one sentence when you
first show matches: "I've hidden Jobgether - it re-posts other companies' jobs, and in a test
it took 4 of the top 12 spots - plus some fake test postings." At wrap-up: they can say "stop
showing jobs from <company>" any time.

## 2. Build search (internal - don't narrate commands)

- Start from `app/profiles/example.yml`.
- Field -> `category=` (tech: `skills=` often tighter). NEVER guess slugs one probe at a time:
  `uv run app/jobs.py probe --facets category countries=us` lists every valid value w/ live count
  in one call (unknown slug answers 0, not error, so a guess loop is silent and slow).
- One tier per location group, preferred first: remote tier `work_mode=remote` +
  `countries=us`; city tier `cities=` ALONE (geography facets OR together, `cfg` rejects mix).
  Exact city values: `uv run app/jobs.py probe --city <text>`.
- Never `q=` (`cfg` rejects it).
- Probe base pass, then once per added filter. Facet w/ many nulls (`-` in tally) drops those
  rows, not only mismatches => outside tech skip `seniority`, `employment_type` unless tally
  shows few nulls. Keep total under 10k (pagination ceiling).
- Tell user in plain numbers: "About 170 finance jobs match right now - 132 remote, 36 around
  Springfield. Sample: <3 titles>." Ask as clicks: looks right / too many, narrow it / too few,
  widen it - each option naming what you'd actually change. Adjust + re-probe.
- "Too many" + a named technology => search `skills=<tech>` alone, drop `category=`. Then read
  100 rows' `enrichment.category` and blocklist the non-role ones the tag leaks onto: measure it
  (`skills=react` 2026-09-20 leaked Sales Consultant, Payment Operations Analyst, Product
  Designer, Product Manager), never guess the list.
- Rank has NO per-skill boost (`rank.py`: tier, likely-ghost/level/hours mismatch, pay,
  employer lists, age - `app/defaults.yml` #rank), and a row matching two
  passes keeps the LAST pass's tier. So "X first, everything else after" is NOT expressible w/
  overlapping passes - either narrow the search to X, or leave it wide. Say which you did.

Write `My Settings/Search settings.yml`: `profile.name` (their words, e.g. "accounting jobs" -
heads notification + email), `passes`, `blocklist` (keep `jobgether` + their companies),
`rank.salary_floor_usd`, `rank.career_level`, `rank.employment_types` (full/part time/contract
answer; [] for "doesn't matter"); decisive counts + date as comment beside each param. Then
`uv run app/jobs.py check-settings`.

## 3. Resume

- Ask them to drag resume PDF into chat box. Then
  `uv run app/jobs.py resume-import prepare --pdf "<path>"` (`--force` if re-importing).
- Do printed task yourself (`AGENTS.md` #AI writing steps), then
  `uv run app/jobs.py resume-import finish`. Gate fails -> copy source text more exactly, rerun.
  Read every "left out" line it prints to user; real facts go back in (awards, volunteering,
  clearances -> `other`), never silently dropped.
- Read `My Resume/Resume details.yml`; confirm w/ user in plain words: jobs + dates, schools,
  contact details. Year-only dates stay years (never guess months). Header `# assumed` lines =
  dates import couldn't read, or jobs re-sorted newest first - check each w/ user.
  Their corrections -> edit that file yourself (wording is theirs; employer, title, dates change
  only to fix a real mistake - `AGENTS.md` #Lead, explain, push back).
- Photo, birth date, marital status or full street address came in -> push back once: US
  convention is to leave them off (invites bias; city + state is enough) - convention, not a
  study. Offer to remove; their call.
- `gap` line from `finish` (6+ months) -> raise kindly, never as a fault: "There's a 9-month
  break between X and Y. Long breaks with no explanation get screened out at about half of
  employers; a one-line reason fixes most of that (caring for family, study, relocation). Want
  one?" Yes -> `career_break` entry (dates + reason in their words; shows on the page, closes
  the gap) or study / freelance / volunteering they really did as its own entry. No -> leave it.
- Lint warns `street-address`, `personal-details` -> the push back above. `old-graduation-year`
  (15+ years) -> offer `hide_year` (age bias; convention), their call.
- `uv run app/jobs.py resume-render` + `uv run app/jobs.py resume-lint`; fix failures w/ user.
  Lint warn `company-legal-id` = ignore (hospitals, schools, agencies carry no Inc./LLC).
  Open rendered PDF in `My Resume/` for them to look at.

## 4. First matches

`uv run app/jobs.py find --limit 10`. Show as `AGENTS.md` list. Offer: "Want resume tailored
for any of these? Say number."

## 5. Daily check (on by default)

`uv run app/jobs.py autorun on` w/o asking (08:00 from `app/defaults.yml`). Ask time + email as
two clickable questions (time: keep 08:00 / 3 other times; email: popup only / email too).

Ask BEFORE the first `uv run app/jobs.py daily`: that run marks every current match seen, so a
later `email --dry-run` prints "0 new" and the user never sees their own digest. Order = ask ->
write `.data/email.env` if they said yes -> `email --dry-run` (real preview + sign-in) -> `daily`
-> `uv run app/jobs.py autorun status`; log tail must show "notified"/"emailed" or "0 new".

Tell them: each morning computer checks for jobs and pops up a notification when new ones arrive;
clicking it opens Job Finder. First one covers every current match, later ones only new jobs.
Computer must be on; missed run happens when it next starts (Windows) or wakes (Mac).
- Different time -> `schedule.local_daily: "HH:MM"` in search settings, `autorun on` again.

Email too (only if they say yes):
- Gmail recommended (Yahoo works too; others only if they support SMTP over SSL port 465 -
  sender uses implicit TLS only).
- Gmail needs app password: 2-Step Verification on, then https://myaccount.google.com/apppasswords
  -> create "Job Finder" -> 16-letter code. Open that page for them; walk through it. Tell
  them: code stays in hidden file on this computer, used only to send them their own email.
- Write `.data/email.env` from `app/email.env.example`: `SMTP_USER`, `SMTP_PASSWORD` (spaces
  removed), `ALERT_TO` if different inbox. Yahoo: also `alert.smtp_host: smtp.mail.yahoo.com`
  in search settings.
- Email replaces notification. Test: `uv run app/jobs.py email --dry-run` shows what goes and
  signs in to prove the app password (exits nonzero on bad credentials); next scheduled run
  emails (log tail "emailed").

## 6. Wrap up

Tell them: open "Job Finder" on Desktop any time and say things like "any new jobs?",
"make my resume for job 3", "stop showing jobs from <company>", "change my search" - and ask
"why?" about anything it does. `START HERE.md` (open on left) repeats this and shows what's private.

Defect in tracked code hit during setup -> `AGENTS.md` #Framework defects.
