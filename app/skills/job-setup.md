# job-setup

`AGENTS.md` #User = not technical binds every step.
Read `app/docs/jobs/freehire.md` first: geography, null-facet and `q=` rules below come from it.

Open w/ short paragraph: you'll ask what they're looking for, check how many jobs match, read
their resume, then show first matches; ~10 minutes. Privacy in plain words (`AGENTS.md`
#Private vs shared): their file list (My Jobs, My Resume, My Settings) stays on this computer;
job searches send only their search settings to freehire.me; resume is read here in this AI
chat; nothing goes to CEZ Job Finder's maintainer without asking first.

Then, BEFORE any interview question (their answers - work permit, pay - are typed into this
chat too), AI training, one question. Personal Claude (Free/Pro/Max) and ChatGPT (Free/Go/Plus/
Pro) plans may train on chats unless the user switches it off; work plans (Claude Team/Enterprise,
ChatGPT Business/Enterprise/Edu) and developer (API key) sign-ins don't by default. Only the user
can change it - no setting here reaches their account. Ask: "What you tell me and your resume are
read in this chat. Want your chats kept out of AI training? One switch, 30 seconds." Options: Yes,
show me / Already off, or a work account / Leave it on. Yes -> open
`Guides/Keep your chats out of AI training.md`, then the settings page for THEIR AI (Claude:
`https://claude.ai/settings/data-privacy-controls`; ChatGPT: `https://chatgpt.com`, then
Settings, Data controls), walk them through the one switch, ask "Done?" before going on. Can't check it's
off - take their word. One ask, never nudge either way. Never ask them to rate or thumbs a chat:
feedback lets the AI company train on that whole chat even w/ the switch off. Codex's separate
"Include environments" setting covers cloud code copies only (private folders never in them) -
not a second switch to add. Menu names differ from the guide -> fix the guide
(`AGENTS.md` #Framework defects).

`My Settings/Search settings.yml` exists -> summarize current search in plain words, ask: change
it or start over?

## 1. Interview

Measure BEFORE asking so every option carries a live count: `uv run app/jobs.py probe --facets
countries=us` gives all 47 categories + every other facet in one call. Then ask ONE question at
a time, in this order (never batched - shows as tabs).

First, broad:
- what kind of work - 4 grouped families of `category` values, `multiSelect`
- where: remote only / remote first / local first / local only
- full time / part time / contract, `multiSelect` + "doesn't matter"
- lowest yearly pay - 4 bands (ranks higher-paying first, never hides jobs; say so in the question)

Then narrowing what they picked:
- which exact roles inside the family they picked, `multiSelect`
- which city - offer 4 real metros from THEIR timezone (`readlink /etc/localtime`), counts from
  the `cities` facet; "Other" covers the rest
- career level (entry / mid / senior / leader) - `rank.career_level`: titles clearly above or
  below it sort lower, never hidden; never a `seniority` filter (facet null on 30-45% of rows,
  junior lives in title string)
- work permit, one question - nearly every US application asks both "legally authorized to work
  in the US without restriction?" and "will you now or in the future require sponsorship?", so
  ask once here; each form still shows the answer before Save. Options ->
  `work_authorization` (`authorized_us`, `needs_sponsorship`):
  - Yes, never need sponsorship (US citizen, green card, refugee/asylee) -> true, false
  - Allowed now, will need it later (OPT, STEM OPT, H-1B transfer) -> true, true
  - Need sponsorship to start -> false, true
  - Ask me on each application -> leave both null
  Say in the question it's saved only on this computer (no job search sends it). Needs sponsorship ->
  count from `probe --facets visa_sponsorship` on their category: "freehire marks 36,846 US jobs
  'no visa sponsorship' - they'll sort lower, never hidden". Never guess it from name, school
  or where they studied. Never help shade it (`AGENTS.md` #Lead, explain, push back - Hold).

Companies they never want to see: don't ask up front - nothing to name yet. Blocklist
`jobgether` + `builtin-integration-sandbox` w/o asking, but say why in one sentence when you
first show matches: "I've hidden Jobgether - it re-posts other companies' jobs, and in a test
it took 4 of the top 12 spots - plus some fake test postings." At wrap-up: they can say "stop
showing jobs from <company>" any time.

## 2. Build search (internal - don't narrate commands)

- Start from `app/profiles/example.yml`.
- Field -> `category=` (tech: `skills=` often tighter). NEVER guess slugs:
  `uv run app/jobs.py probe --facets category countries=us` lists every valid value w/ live count
  (unknown slug answers 0, not error - a guess loop is silent and slow).
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
  employer lists, age - `app/defaults.yml` #rank), and a row matching two passes keeps the LAST
  pass's tier. So "X first, everything else after" is NOT expressible w/ overlapping passes -
  narrow to X or leave it wide. Say which you did.

Write `My Settings/Search settings.yml`: `profile.name` (their words, e.g. "accounting jobs" -
heads notification + email), `passes`, `blocklist` (keep `jobgether` + their companies),
`rank.salary_floor_usd`, `rank.career_level`, `rank.employment_types` (full/part time/contract
answer; [] for "doesn't matter"), `work_authorization`; decisive counts + date as comment beside each param. Then
`uv run app/jobs.py check-settings`.

## 3. Resume

- Ask for resume PDF (drag into chat), then
  `uv run app/jobs.py resume-import prepare --pdf "<path>"` (`--force` if re-importing).
- Do printed task yourself (`AGENTS.md` #AI writing steps), then
  `uv run app/jobs.py resume-import finish`. Gate fails -> copy source text more exactly, rerun.
  Read every "left out" line it prints to user; real facts go back in (awards, volunteering,
  clearances -> `other`), never silently dropped.
- Read `My Resume/Resume details.yml`; confirm w/ user in plain words: jobs + dates, schools,
  contact details. Year-only dates stay years (never guess months). Header `# assumed` lines =
  dates import couldn't read, or jobs re-sorted newest first - check each w/ user.
  Corrections -> edit that file yourself (wording theirs; employer, title, dates only to fix a
  real mistake - `AGENTS.md` #Lead, explain, push back).
- Photo, birth date, marital status or full street address came in -> push back once: US
  convention leaves them off (invites bias; city + state is enough) - convention, not a study.
  Offer to remove; their call.
- `gap` line from `finish` (6+ months) -> raise kindly, never as a fault: "There's a 9-month
  break between X and Y. Long breaks with no explanation get screened out at about half of
  employers; a one-line reason fixes most of that (caring for family, study, relocation). Want
  one?" Yes -> `career_break` entry (dates + reason in their words; shows on the page, closes
  the gap) or study / freelance / volunteering they really did as its own entry. No -> leave it.
- Lint warns `street-address`, `personal-details` -> the push back above. `old-graduation-year`
  (15+ years) -> offer `hide_year` (age bias; convention), their call. `abbreviated-school` ->
  ask the full name (forms say "Do not use abbreviations"). `language-level` -> ask each
  language's level w/ choices (Native / Fluent / Professional / Conversational / Basic) - their
  fact, never guessed - then one line each: `Spanish (Fluent)`.
- Fill the gaps: `uv run app/jobs.py resume-gaps prepare`, do the task yourself (lists lines
  with no number + a leadership question per recent job), asking the user in chat - clickable
  "I know it / skip" choices, the number as free text. Only what they say goes in; never guess or
  round; skipping is fine. Then `uv run app/jobs.py resume-gaps finish` (FAIL = a number or
  name not in their answer; fix the answer file). Tell them it kept a backup of the old file.
- `uv run app/jobs.py resume-render` + `uv run app/jobs.py resume-lint`; fix failures w/ user.
  Lint warn `company-legal-id` = ignore (hospitals, schools, agencies carry no Inc./LLC).
  Open rendered PDF in `My Resume/` for them to look at.
- `uv run app/jobs.py resume-feedback` -> `My Resume/Resume feedback.md`; open it and walk them
  through "At a glance" in plain words. `Worth a look` on numbers or leadership -> offer
  fill-the-gaps above; wording notes -> show each fix, their call. Page layout never in it
  (render gates enforce it).

## 4. First matches

`uv run app/jobs.py find --limit 10`. Show as `AGENTS.md` list. Offer: "Want resume tailored
for any of these? Say number."

## 5. Daily check (on by default)

`uv run app/jobs.py autorun on` w/o asking (08:00 from `app/defaults.yml`). Ask time, then email
(time: keep 08:00 / 3 other times; email: popup only / email too).

Ask BEFORE the first `uv run app/jobs.py daily`: that run marks every current match seen, so a
later `email --dry-run` prints "0 new" and the user never sees their own digest. Order = ask ->
write `.data/email.env` if they said yes -> `email --dry-run` (real preview + sign-in) -> `daily`
-> `uv run app/jobs.py autorun status`; log tail must show "notified"/"emailed" or "0 new".

Tell them: each morning computer checks for jobs, pops up a notification when new ones arrive;
clicking it opens CEZ Job Finder. First one covers every current match, later ones only new jobs.
Computer must be on; missed run happens when it next starts (Windows) or wakes (Mac).
- Different time -> `schedule.local_daily: "HH:MM"` in search settings, `autorun on` again.

Email too (only if they say yes):
- Gmail recommended (Yahoo works too; others only if they support SMTP over SSL port 465 -
  sender uses implicit TLS only).
- Gmail needs app password: 2-Step Verification on, then https://myaccount.google.com/apppasswords
  -> create "CEZ Job Finder" -> 16-letter code. Open that page for them; walk through it. Tell
  them: code stays in hidden file on this computer, used only to send their own email.
- Write `.data/email.env` from `app/email.env.example`: `SMTP_USER`, `SMTP_PASSWORD` (spaces
  removed), `ALERT_TO` if different inbox. Yahoo: also `alert.smtp_host: smtp.mail.yahoo.com`
  in search settings.
- Email replaces notification. `email --dry-run` (order above) exits nonzero on bad
  credentials; next scheduled run emails (log tail "emailed").

## 6. Wrap up

Tell them: open "CEZ Job Finder" on Desktop any time and say things like "any new jobs?",
"make my resume for job 3", "stop showing jobs from <company>", "change my search" - and ask
"why?" about anything it does. `START HERE.md` (open on left) repeats this and shows what's private.

Defect in tracked code hit during setup -> `AGENTS.md` #Framework defects.
