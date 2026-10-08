# job-setup

`AGENTS.md` #User = not technical binds every step.
Read `app/docs/jobs/freehire.md` first: geography, null-facet and `q=` rules below come from it.

Open w/ short paragraph: you'll ask what they're looking for, check how many jobs match, read
their resume, then show first matches; ~10 minutes. Privacy in plain words (`AGENTS.md`
#Private vs shared): their file list (My Jobs, My Resume, My Settings) stays on this computer;
job searches send only their search settings to freehire.me (a resume made for a listed job, or
"still open?", sends that job's listing id - nothing about them); resume is read here in this AI
chat; nothing goes to CEZ Job Finder's maintainer without asking first. Same opening, one line:
free + provided as is - AI can get things wrong, so they read every resume + answer before sending;
it never clicks Submit; general information, not legal advice. Terms: `jobs.py open
"https://jobs.enrriquez.com/terms.html"` only if they ask.
On Copilot (`.data/ai`): in the same opening, one line - pick Claude Sonnet in the model list
under the chat box, the automatic model can't make tailored resumes (`AGENTS.md` #User = not
technical). Copilot's free tier can't either: say Copilot Pro ($10 a month) if they're on it.
Copilot Student (free for verified students) has had only the automatic model since 2026-06-24 -
untested here, same model Free failed 3 of 3 on: say Copilot Pro lets them pick a stronger AI and
keeps the rest of their Student Pack, and that Pro chats may train unless switched off.
Copilot, already set up: `.data/profile-migrated` reads `model: not copied` (window moved to its
own space, model pick stayed behind) => say that same line once, then add `told` to that file.

Then, BEFORE any interview question (their answers - work permit, pay - are typed into this
chat too), AI training, one question. Personal Claude (Free/Pro/Max), ChatGPT (Free/Go/Plus/
Pro) and GitHub Copilot (Free/Pro) plans may train on chats unless the user switches it off; work
plans (Claude Team/Enterprise, ChatGPT Business/Enterprise/Edu, Copilot Business/Enterprise),
Copilot Student and developer (API key) sign-ins don't by default. Copilot chats may be shared
with Microsoft. A school account (ChatGPT Edu, Claude for Education) is the school's: say what its
admins can see is up to the school, and it may end after graduation. Only the user
can change it - no setting here reaches their account. Ask: "What you tell me and your resume are
read in this chat. Want your chats kept out of AI training? One switch, 30 seconds." Options: Yes,
show me / Already off, or a work account / Leave it on. Yes -> open
`Guides/Keep your chats out of AI training.md`, then the settings page for THEIR AI (Claude:
`https://claude.ai/settings/data-privacy-controls`; ChatGPT: `https://chatgpt.com`, then
Settings, Data controls; GitHub Copilot: `https://github.com/settings/copilot`, then Privacy,
"Allow GitHub to use my data for AI model training" -> Disabled), walk them through the one switch, ask "Done?" before going on. Can't check it's
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
- full time / part time / internship or co-op / contract, `multiSelect` + "doesn't matter", each
  with its count in their field (`probe --facets employment_type <their params>`; internship also
  `--facets seniority`). Types they didn't pick -> `blocklist.employment_types` (hidden, by the job
  search's own tag; untagged jobs stay, and a title saying intern / co-op / part-time keeps a job
  whose tag says otherwise - 87 of 300 real internships are tagged full time) - say the count each
  hides before saving. Internship or co-op picked -> `rank.employment_types` gets `internship`, and
  the search gets internship passes (#2). Student or recent graduate (internship picked, or they
  say so) -> the student notes below apply.
- lowest yearly pay - 4 bands + "doesn't matter". Say in the question: jobs paying less are hidden
  unless few new jobs come in that week; jobs with no pay listed stay. Before saving, count it:
  `uv run app/jobs.py rank --pay-floor <band>` (once jobs are in; before that, `probe` counts of
  `salary_min`) and say "hides N, keeps M" (AGENTS.md, narrowing). Internship or part-time picked
  -> lowest hourly pay instead: 4 hourly bands (e.g. $15 / $18 / $22 / $28 an hour) + "doesn't
  matter"; count with `rank --pay-floor 18/hr`; save the yearly number it prints as
  `rank.salary_floor_usd` + `rank.salary_floor_unit: hour` - every list says it back per hour, and a
  part-time job listing only a yearly sum (hours unknown) is never hidden by it. Want no-pay-listed jobs hidden
  too -> push back once (unlisted pay isn't low pay; most fields outside tech list none; count
  with `--hide-unlisted`), then `rank.pay_filter.hide_unlisted: true` if they still want it.
  `app/docs/jobs/pay-filter.md`

Then narrowing what they picked:
- which exact roles inside the family they picked, `multiSelect`. Then count the role itself,
  every way its title is written (their words + the short form: "registered nurse" + RN,
  "certified public accountant" + CPA): `uv run app/jobs.py probe --title "registered nurse"
  --title RN countries=us`. A category count says nothing about one role (Healthcare ~32,000;
  "registered nurse" 50, RN ~19,800). Every form under 30 posted in the last 30 days -> one plain
  line: "The job search we use carries few <role> jobs - about N posted in the last month across
  the US." Offer: keep going anyway / widen to related roles - never pretend the count is bigger.
- which city - offer 4 real metros from THEIR timezone (`readlink /etc/localtime`), counts from
  the `cities` facet; "Other" covers the rest
- career level (entry - "student, new graduate or first job" / mid / senior / leader) -
  `rank.career_level`: titles clearly above or below it sort lower, never hidden; entry also sorts
  lower a job whose required line asks 3+ years (the posting's own words, not the job search's
  years tag - it read 10 on "Software Engineer - New Grad"). Never a `seniority` filter for
  everyone (facet null on 30-45% of rows, junior lives in title string) - internship passes only (#2)
- work permit, one question - nearly every US application asks both "legally authorized to work
  in the US without restriction?" and "will you now or in the future require sponsorship?", and
  employers that require it (government work, security products) ask "US citizen or permanent
  resident (green card)?" - so ask once here; each form still shows the answer before Save.
  Options -> `work_authorization` (`authorized_us`, `needs_sponsorship`,
  `citizen_or_permanent_resident`):
  - US citizen or green card holder -> true, false, true
  - Other status, never need sponsorship (refugee, asylee) -> true, false, false
  - International student (F-1): CPT/OPT now, will need a work visa later -> null, true, false, +
    `student_visa: true`
  - Allowed now with an employer-tied visa, will need sponsorship later (H-1B transfer) -> null,
    true, false
  - Need sponsorship to start -> false, true, false
  - "Ask me on each application" (typed under Other) -> leave all null
  Visa holders' `authorized_us` stays null: "authorized ... without restriction" is asked on every
  form (Carnegie Mellon + UC Irvine international offices say No on F-1; H-1B is one employer;
  `questions.work_permit` asks even over an old saved Yes). `check-settings` printing "ask once:
  work permit ..." = an old setup saved Yes there - ask this question again, once.
  F-1 + part-time picked -> one line, general information: "On F-1, off-campus jobs need CPT or OPT
  approval first; on-campus jobs up to 20 hours a week while classes are in session don't - your
  international student office has the final word." Point them to their school's own job board
  for campus jobs (paste a posting there to tailor a resume).
  Say in the question it's saved only on this computer (no job search sends it). Needs sponsorship ->
  count from `probe --facets visa_sponsorship` on their category: "freehire marks 36,846 US jobs
  'no visa sponsorship' - they'll sort lower, never hidden". Never guess it from name, school
  or where they studied. Never help shade it (`AGENTS.md` #Lead, explain, push back - Hold).
- security clearance, one question, only when it matters: `probe --facets requires_clearance
  <their pass params>` shows 1 in 20 or more of their matches need one (judgement, not a
  measured cut-off), and the work-permit answer didn't settle it (neither citizen nor green card
  -> can't hold one, no question). "About N of your matches need a US security clearance - only
  US citizens can hold one. Can you?" Yes, I have one or can get one / No / Not sure ->
  `work_authorization.can_hold_clearance` true / false / null. No -> they sort lower, never
  hidden; every such job says "needs a security clearance" either way. Can hold one but don't
  want government / defense work -> `blocklist.clearance: true` hides them (say the count).

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
- `q=` only as one exact title phrase w/ `q_fields: title` (`cfg` rejects any other use) - for a
  role its category is too wide for (RN inside healthcare). The job search has no OR: one form
  per pass, the one w/ most postings; say which other forms it leaves out.
- Internship or co-op picked: per location tier, two passes with the SAME `tier` - one with
  `seniority: [intern]`, one with `employment_type: [internship]` (2026-10-07, either tag: 199 of
  200 "internship" titles, 156 of 171 "summer analyst", 153 of 200 "co-op"; one tag alone misses
  up to a third). Co-ops wanted -> a third pass `q: "co-op"` + `q_fields: title`. Internship only
  -> these passes only; with full-time jobs too -> add their plain pass (a row in two passes keeps
  the last one's tier: put the plain pass first in the same tier, or say the order).
- Probe base pass, then once per added filter. Facet w/ many nulls (`-` in tally) drops those
  rows, not only mismatches => outside tech skip `seniority`, `employment_type` unless tally
  shows few nulls. Keep total under 10k (pagination ceiling).
- Tell user in plain numbers: "About 170 finance jobs match right now - 132 remote, 36 around
  Springfield. Sample: <3 titles>." Ask as clicks: looks right / too many, narrow it / too few,
  widen it - each option naming what you'd actually change. Adjust + re-probe.
- "Too many" + a named technology => search `skills=<tech>` alone, drop `category=`. Then read
  100 rows' `enrichment.category` and blocklist the non-role ones the tag leaks onto: measure it
  (`skills=react` 2026-09-20 leaked Sales Consultant, Payment Operations Analyst, Product
  Designer, Product Manager), never guess the list. Then the titles: a skill tag also lands on
  roles outside their kind of work (`skills=react` 2026-10-01, 1,275 rows: back-end 127, data /
  AI 108, managers 99, mobile 28, testing 13). Count each group w/ `rank --would-hide "<word>"`,
  read its titles (a full-stack or front-end title caught -> `title_keep`), then ONE clickable
  multiSelect w/ counts: "Which kinds should I hide? Tick all that fit, then Submit" ->
  `blocklist.title_phrases`.
- Rank has NO per-skill boost (`rank.py`: tier, likely-ghost/level/hours mismatch, pay,
  employer lists, age - `app/defaults.yml` #rank), and a row matching two passes keeps the LAST
  pass's tier. So "X first, everything else after" is NOT expressible w/ overlapping passes -
  narrow to X or leave it wide. Say which you did.

Write `My Settings/Search settings.yml`: `profile.name` (their words, e.g. "accounting jobs" -
heads notification + email), `passes`, `blocklist` (keep `jobgether` + their companies),
`rank.salary_floor_usd` (+ `rank.pay_filter` only if they changed it), `rank.career_level`, `rank.employment_types` (full/part time/contract
answer; [] for "doesn't matter"), `work_authorization`; decisive counts + date as comment beside each param. Then
`uv run app/jobs.py check-settings`.

## 3. Resume

- Ask for their resume - PDF or Word file (drag it onto My Resume in the file list; `AGENTS.md`
  #User), then `uv run app/jobs.py resume-import prepare --file "<path>"` (`--force` if
  re-importing). Never open the file yourself (`AGENTS.md` #Speed). Older Word, Pages, Google Docs
  -> it prints the one step to say (save a copy as .docx or PDF).
  Re-import: `finish` writes nothing yet when the new file lacks things in their resume details -
  it prints up to 3 groups (lines: their wording + added lines and skills; entries: jobs, schools,
  breaks, sections; details: legal name, hidden years, language levels, notes on a job) w/ counts
  + examples. ONE clickable multiSelect, each option naming its count ("23 lines you reworded or
  added"), "tick all that fit, then Submit"; then `finish --keep <ticked, comma-separated | none>`.
  It backs up the old file first - say so.
- Do printed task yourself (`AGENTS.md` #AI writing steps), then
  `uv run app/jobs.py resume-import finish`. Gate fails -> copy source text more exactly, rerun.
  Read every "left out" line it prints to user; real facts go back in (awards, volunteering,
  clearances -> `other`), never silently dropped.
- Read `My Resume/Resume details.yml`; confirm w/ user in plain words: jobs + dates, schools,
  contact details. A student's: degree in progress = `expected: true` + the expected `end` (page
  says "Expected May 2027" until they say they finished - lint `expected-date-passed` = ask
  "Did you finish your <degree>?" Finished -> remove `expected`; not yet -> the new date); `gpa` in
  quotes exactly as the transcript gives it (Hold: never rounded up, never converted from another
  scale - ask, keep theirs); `coursework` = a few courses as their school names them; clubs and
  groups = `projects` with `role` + `section` (the heading they gave, e.g. Leadership & Activities)
  - the group's name exactly as written, never shortened or generalised (their call how each shows:
  `resume-feedback` says it once, same words for everyone - never prompted by a group's name). Year-only dates stay years (never guess months). Header `# assumed` lines =
  dates import couldn't read, or jobs re-sorted newest first - check each w/ user.
  Corrections -> edit that file yourself (wording theirs; employer, title, dates only to fix a
  real mistake - `AGENTS.md` #Lead, explain, push back).
- Birth date, marital status or full street address came in -> push back once: US convention
  leaves them off (invites bias; city + state is enough) - convention, not a study. Offer to
  remove; their call. Photo asked for -> can't (`AGENTS.md` #Lead, explain, push back).
- `gap` line from `finish` (6+ months; their search running now is no break - say nothing) ->
  privacy line first: "A few words is enough - no diagnosis or case details. What you type here
  goes to your AI account." Then raise it kindly, never as a fault, in `gap_note`'s words (6+
  months: a line; 12+: a line + recent work, study or volunteering really done; never penalty
  numbers). Their call, said plainly: "a line saves the reader guessing - it helped for one
  health reason, made no difference for childcare in one trial; a layoff line was never tested
  against saying nothing". ONE clickable question: Family care /
  Health matter, now resolved or managed / Study or training / Something else - I'll say ("Leave
  it off" under Other). Answer -> `career_break` entry (dates + their reason; on the page, closes
  the gap); work, study or volunteering they really did -> its own entry. Studying at a school
  already in their Education (between summer internships, a degree in progress) is no break: ask
  when they started there -> `education[i].start` (a fact; the gap closes and, while it explains
  one, the page shows the school's dates) - never a "Study or training" career break for it. Never suggest paying for
  a course (no US study behind it). Layoff, when true -> one line under the last job instead:
  "Role cut in company-wide layoff, Jul 2025". Time in custody: the page needn't name it - real
  work, training or study done there under its real name; "personal leave" for it -> push back
  once (dates show on a background check). Facts: `app/docs/resume/fair-screening.md` #Work breaks.
- Lint warns `street-address`, `personal-details` -> the push back above. `old-graduation-year`
  / `old-certification-year` (15+ years) -> offer `hide_year`, their call; degree 20+ years
  (detail says so) -> recommend the one bundle - graduation + certificate years, jobs that ended
  15+ years ago, long year counts ("25 years") - and name its possible small cost (some hiring
  managers want the full history - vendor survey; not measured in the US). Words: "this year lets a reader guess age", never
  "because you're older". `abbreviated-school` -> ask the full name (forms say "Do not use
  abbreviations").
- Languages, every user, once (a fact in their file, same question for all): "Do you speak any
  other languages?" Yes -> each one's level w/ choices (Native / Fluent / Professional /
  Conversational / Basic) - their fact, never guessed - then one line each: `Spanish (Fluent)`.
  `language-level` warns -> the same level question.
- Names: no name question in setup. A legal-name split, initials or a name they go by come up at
  the first application (`job-apply` #Names) or when they ask.
- Fill the gaps: `uv run app/jobs.py resume-gaps prepare`, do the task yourself (lists lines
  with no number, lines saying "helped" or "we" - what was their own part? - and a leadership
  question per recent job), asking the user in chat ONE question at a time - clickable "I know it /
  skip" choices, the number as free text. Only what they say goes in; never guess or
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
Tail says notifications switched off -> their own Windows setting: walk them through Settings >
System > Notifications on, rerun `daily` (nothing marked seen while it failed).

Tell them: each morning computer checks for jobs, pops up a notification when new ones arrive;
clicking it opens CEZ Job Finder. First one covers every current match, later ones only new jobs.
Computer must be on; missed run happens when it next starts (Windows) or wakes (Mac).
- Different time -> `schedule.local_daily: "HH:MM"` in search settings, `autorun on` again.

Email too (only if they say yes):
- Gmail recommended (Yahoo works too; others only if they support SMTP over SSL port 465 -
  sender uses implicit TLS only).
- Gmail needs app password: 2-Step Verification on, then https://myaccount.google.com/apppasswords
  -> create "CEZ Job Finder" -> 16-letter code. Open that page for them; walk through it. Tell
  them: the code goes through this chat, so it reaches their AI account (Claude also keeps a copy
  on this computer 30 days); then it's kept in a hidden file here, used only to send their own
  email; they can cancel it any time on that same Google page.
- Write `.data/email.env` from `app/email.env.example`: `SMTP_USER`, `SMTP_PASSWORD` (spaces
  removed), `ALERT_TO` if different inbox. Yahoo: also `alert.smtp_host: smtp.mail.yahoo.com`
  in search settings.
- Email replaces notification. `email --dry-run` (order above) exits nonzero on bad
  credentials; next scheduled run emails (log tail "emailed").

## 6. Wrap up

Tell them: open "CEZ Job Finder" on Desktop any time and say things like "any new jobs?",
"make my resume for job 3", "stop showing jobs from <company>", "change my search" - and ask
"why?" about anything it does. Same line for everyone: "Worried about bias - your name, age or
a break? Ask any time." And: "Anything that matters to you in a workplace, or how you like to
sound - tell me and I can save it as a note. Ask 'what do you know about me?' to see it all." Next launch opens the Today page (what's waiting, newest jobs)
instead of START HERE; `Guides/What you can ask.md` + `Guides/Who sees what.md` repeat this and
show what's private.

Defect in tracked code hit during setup -> `AGENTS.md` #Framework defects.
