# freehire API - contract, measured behavior, rejected sources

Every fact here measured against live API; date on each. Re-measure w/ `uv run app/jobs.py probe`
before trusting count.

## Contract (2026-09-15)

- Base `https://freehire.me/api/v1`, keyless, `x-ratelimit-limit: 600`.
- `GET /jobs/search` -> `{"data":[...],"meta":{"total":N,"limit":L,"offset":O}}`.
- Pagination ceiling `offset+limit <= 10000` => pass wider than 10k rows truncates silently;
  narrow it w/ `posted_within_days`. Truncated pass closes nothing (`ingest/freehire.py`): rows
  past the ceiling were never fetched, so their absence proves nothing.
- `GET /jobs/facets?<same filters>` -> live counts per facet value. Lists EVERY valid value for
  every facet in one call => `uv run app/jobs.py probe --facets [<facet>]` instead of guessing
  slugs one probe at a time (unknown slug answers 0, never error, so a guess loop is silent
  and slow). 47 `category` values, 2026-09-20.
- `GET /jobs/<slug>` -> one posting, description whole (search rows carry ~1,000 chars); also
  serves closed postings (search never does). `GET /agent/jobs/search` = same filters, full
  description (5,343 chars vs 994, 2026-10-01) - unused: tailoring fetches one job.
- `GET /geo/cities?q=<text>` -> exact `cities=` values (`uv run app/jobs.py probe --city <text>`).
  `cities=` matches exact value only: `new york` misses `New York City`.
- Row fields: `public_slug` `title` `company` `company_slug` `url` `source` `location` `cities`
  `countries` `regions` `work_mode` `skills` `collections` `posted_at` `created_at`
  `last_seen_at` `closed_at` `description` `enrichment` `reality` `requires_clearance` (true or
  absent: 45,763 US rows, 2026-10-01).
- Filter facets: `category` `skills` `work_mode` `countries` `regions` `cities`
  `employment_type` `seniority` `collections` `company_size` `salary_min` + `salary_currency`
  `visa_sponsorship` `experience_years_min` `posted_within_days` `sort` `order`, + (2026-10-01)
  `q` w/ `q_fields=title` ([Title search](#title-search)), `requires_clearance`,
  `open_within_days` (first-seen date; posted<=7d 76,484 vs open<=7d 67,666 US - not used yet),
  `<facet>_exclude` (null-safe: `category_exclude=marketing` = 798,143 - 27,237 exactly).

## Category slugs (2026-09-19, `countries=us`)

`healthcare` 29,971 - `sales` 85,154 - `finance` 16,233 - `legal` 10,673 - `education` 3,463.
`nursing` and `customer_support` answer 0 - real slugs `healthcare`, `support`. Unknown slug
returns 0, never error => never guess: `probe --facets category countries=us` lists all 47 w/
counts in one call.

## `reality` + pay fields (2026-09-24, 500 newest US rows)

- `reality` = `{class, age_days, repost_count, mass_posting_count, fake_freshness}`, on every
  row. `class` facet: `fresh` 181k, `stale` 587k, `likely-evergreen` 7.7k. `age_days` median 70
  on `stale`. `fake_freshness` true on 133/500: `posted_at` restamped while `age_days` stays old
  => age shown + sorted from `age_days`, `posted_at` only fallback.
- `repost_count` = postings sharing the role's fingerprint, any status; `mass_posting_count` =
  the open ones; both count the job itself. Relisted = `repost_count - mass_posting_count`
  (earlier copies that closed) - freehire's own classifier subtracts the same way. Raw
  `repost_count` (2026-09-30) called copies open at once "reposted": 75 of 111 demoted rows on a
  real 1,275-row list (38 at 3/3, class fresh); live 500 newest US rows, 30 of 35 with
  `repost_count >= 3`. `likely-evergreen` = 2 of: 90+ days old, relisted 3+, 5+ copies open, "always
  hiring" text.
- Rank demotes (never hides) relisted `>= rank.repost_demote`, `age_days >= rank.old_days`,
  `likely-evergreen` - one doubt however many fire, each named in reasons.
- Separate `ghost` object `{level: possible|likely, criteria}` exists in freehire's code, computed
  on read; absent on 100/100 likely-evergreen US rows + the detail row checked (2026-10-01).
  Dormant - re-probe before using it.
- `salary_period` null on 315/500, incl. rows w/ pay; `hour` 17k rows US-wide. Period missing
  => value < 1000 hourly, < 10000 monthly (`rank.pay`). One `month` row read 70000-100000 -
  label wrong at source, left as is.

## Visa sponsorship (2026-09-24, `countries=us`)

`enrichment.visa_sponsorship`: `false` 36,846, `true` 13,775 of 775,975 rows - null on 93.5%, so
a `visa_sponsorship=` filter drops nearly every job. Weak label: of 12 full postings (one per
company) marked `false`, 4 say so in the text ("visa sponsorship is not available"), 8 say
nothing; of 12 marked `true`, none mentions sponsorship. Search rows carry only the first
~1000 chars of `description`, so the full posting is read via `GET /jobs/<slug>`. => user who
needs a sponsor (`work_authorization.needs_sponsorship`): `false` rows demoted w/ reason, never
hidden; `true` never boosted. Tailoring reads the full posting and quotes the line.

## Closing + stale rows

Passes sharing a tier close together (`freehire.run`): only rows none of them returned, inside the
shortest window they fetched. Closed per pass (2026-10-07 to -08), an internship search's second tag
pass closed every row only the first found - 40 of 214 open on one fresh check.

`close_missing` closes only rows posted inside a pass's `posted_within_days` window: older rows
are never re-fetched, so never closed. Window = the one the pass actually fetched at: each pass starts at
`window.days` (7) or its own `posted_within_days`, widens through `window.widen_to` while it
returns fewer than `window.min_jobs` (30) rows (`app/defaults.yml`, counts measured 2026-09-26). `rank` sorts open rows no fetch returned in more than
`rank.stale_days` (default 14) days, read off `jobs.fetched_at`, to the bottom of their tier w/
reason "may be closed - not seen in Nd"; digest never announces them. Demoted, not hidden:
hiding a still-open job costs a chance, showing a closed one costs a click.

Jobs in progress (`status open`, `status.still_open`) read the same signals: `closed_at` set ->
"may be closed - gone from your job search since D"; unseen more than `rank.stale_days` ->
"may be closed - not seen in N days", counted from the last check, not today, so a morning
check that stopped running reads "can't tell - no job check in N days", never closed. Pasted
postings + jobs applied outside have no row => "can't tell - check the link". No re-fetch of
the employer's page: it would send a new thing off the computer.

`status open` first asks the job search itself, `GET /jobs/<slug>` per listed job in progress
(listing id only; privacy table row). Search never returns a closed row, the detail endpoint
does. Measured 2026-10-01 on 6 rows our list had closed: 3 answered 200 w/ `closed_at`, 3
answered 404 (gone from the catalogue); an open row: `closed_at` null, `last_seen_at` = last
crawl that found it. => closed_at -> "may be closed - the job search marked it closed on D"
(its own rules include closing by age, so never "closed"); 404 -> "may be closed - the job
search no longer lists it"; `last_seen_at` older than `rank.stale_days` -> "may be closed";
else open. Request fails -> the list's own signals above.

## Defects handled in code

- **`q=` alone matches prose** (2026-09-15). `q=react` returned "Lifecycle Marketing Manager".
  Same for any occupation keyword. `cfg.q_problem` rejects `q` w/o `q_fields: title` - see
  [Title search](#title-search).
- **Facets ignore `q_fields`** (2026-10-09). `/jobs/facets?q=...&q_fields=title` answers with
  `meta.ignored_params: [{"param": "q_fields"}]`; without q_fields its counts read the words anywhere
  in a posting - "compliance" (3,562 US jobs titled it) summed to 61,000+ across categories,
  management alone 13,666. `probe --facets` with `q` tallies the newest 500 rows itself
  (`probe.title_facets`); `-` = untagged.
- **Unknown filter = every job** (2026-09-30). A misspelled param is ignored, not refused:
  `bogus_param=1` -> 798,143 US rows, flagged only in `meta.ignored_params` (`[{"param": ...}]`,
  search + facets). `freehire.understood` stops the pass before anything is stored.
- **Every link tagged** (2026-09-30). `url` carries `utm_source=freehire.me` (1431 of 1431 stored
  rows); a link copied from the employer's page doesn't. `store.link_key` drops `utm_*` before
  comparing; links stay as served.
- **Geography facets OR together** (2026-09-19). `regions` `countries` `cities` in one pass widen,
  never narrow: `countries=us` + `cities=new york,...` returned all-US hybrid/onsite (461 rows vs
  93 real). `cfg.load` rejects two in one pass; city tier uses `cities` alone.
- **City names carry no state** (2026-10-08). `cities=` matches the name in any state or country, and
  the row's `cities` list is loose (a Milford CT row under `Newark`; chain postings list 60 cities).
  100 newest: `Newark` CA 40, NJ 11; `Wayne` PA 32, MI 16, NJ 11; `Washington` pulls Washington state.
  A DC-area search (8 cities, internship passes): 29 of 78 rows named only other states (Seattle,
  Redmond, Arlington TX, Alexandria NSW). `regions` holds continents, no state filter. => a city pass
  carries `states:` (local only, `cfg` checks the codes); `rank.far` drops a row whose `location`
  names only other states or `countries` lacks us. No state written / remote => kept (can't tell):
  0 wrong drops on 151 rows read by hand.
- **Reposter pollution** (2026-09-15). `jobgether` re-lists other employers' postings, held 4 of
  top 12 rows. Every profile blocklists it; `uv run app/jobs.py rank --suspects` lists companies spanning
  `rank.suspect_min_categories` enrichment categories.
- **Test postings live in results** (2026-09-19). `builtin-integration-sandbox` ("Senior
  Financial Analyst - Job 89 9/19/2026 ...") held 5 of 100 finance remote rows, also in
  `software_engineering`; no `enrichment.requirements` => cannot be tailored. Example profile
  blocklists it.
- **`posted_at` no novelty signal** (2026-09-15). Stamped at crawl time in batches:
  `posted_within_days=1` 25 rows vs `=7` 47. Novelty = `seen` table keyed on `public_slug`;
  `posted_within_days` only bounds fetch.
- **Enrichment tags leak across categories** (2026-09-15). freehire tags `react` onto marketing
  roles => `skills=` search needs `blocklist.categories: [marketing, sales]` locally.

## Internships + early career (2026-10-07, `countries=us`)

- Facets: `employment_type` internship 17,726 of 813,575 rows (~52% untagged); `seniority` intern
  15,622 (~75% untagged). Titles open: "intern" 7,979, "entry level" 2,728, "summer intern" 2,094,
  "junior" 1,974, "internship" 1,895, "co-op" 952, "new grad" 539, "early career" 303.
- 300 newest intern-titled rows: tagged internship 196, full_time 87, part_time 17 => the title
  decides the type (`rank.title_type`; one way - it keeps a job, never hides one); `seniority`
  intern on 297. Either tag (`seniority=intern` or `employment_type=internship`, two passes, one
  tier) covers 199 of 200 "internship", 156 of 171 "summer analyst", 70 of 90 "summer associate",
  153 of 200 "co-op" titles; "student assistant" / "student worker" (campus jobs) 9 + 18 of 344.
  Each tag alone misses up to a third. 300 newest `seniority=intern`: 200 intern/co-op titles, the
  rest trainee, new grad and a few mislabels (AI Engineer II, a Director) - `career_level: entry`
  sorts those lower.
- `enrichment.experience_years_min`: on 990 of 1,600 rows (8 categories), 749 >= 3; but 407 of
  990 have no years line in the required asks, and on early-career titles it reads wild ("Software
  Engineer - New Grad" 10, "Entry Level Sales Representative" 20, "18+ years old" 7). => a
  student's years demerit reads the required lines (`knockout.years_asked`: 1,149 reads on 10,360
  lines, 1 changed by the school-study rule, a true fix), never the tag.
- Graduation windows on required lines: 92 of 616 unique student required lines (2,268 intern /
  new grad / entry level / co-op / early career rows); 0 on 11,719 required lines of ordinary
  postings except 2 real summer-analyst programmes (`knockout.graduation_window`, hand-checked:
  1 misread - a line the source cut mid-date, now read open-ended). 144 of 308 intern rows state an
  enrolment or graduation requirement; 133 titles carry the year ("Summer 2027") - the
  internship's year, not a graduation window, never read as one.
- Pay on 74 of 308 intern rows (62 hourly, median top $49/hr on this tech-heavy source - never
  typical); 1 says "unpaid" in its first 1,000 characters.

## Project + program management (2026-10-09, `countries=us`)

Titled jobs, open / posted in the last 30 days: project manager 26,319 / 8,749, program manager 12,203 /
5,379, technical program manager 2,105 / 1,150 (212 remote), delivery manager 1,288, technical project
manager 844 / 354 (115 remote), program management 746, IT project manager 727 (84 remote), program
director 311, PMO 300, IT program manager 170. "program manager" holds every TPM title; "technical
project manager" + "IT project manager" are not in it. New York City: TPM 152, program manager 556;
Charlotte: program manager 101, TPM 3.
- Categories: `project_management` 40,139, its 1,000 newest: project manager titles 556, program
  manager 213, coordinators + assistants 105, TPM 66, technical project manager 21; about a fifth
  construction / facilities / field by title word. 1,000 newest TPM titles: project_management 902,
  hardware 33, management 17; "program manager": project_management 878, management 56.
- Business analysts are a separate job: `business_analysis` 6,859, 490 of its 500 newest titled
  analyst. 1,000 newest "business analyst" titles: business_analysis 747, data_analytics 95,
  operations 34, finance 21, project_management 13. A PM title pass brings none (0 analyst titles
  in 1,000 TPM, 2 "Program Analyst" in 1,000 program manager) => a PM who gets analyst jobs has a
  `business_analysis` (or data_analytics / finance) pass: never add one for a PM.
- Kinds by title word (1,000 newest, rough): TPM - software / IT / data / cloud / security ~790,
  hardware / manufacturing / defense / space ~115; "project manager" - construction / facilities /
  field ~260, software / IT ~150, plain ~490; "program manager" - 254 software / IT, the rest
  operations, defense, supply chain, social services (youth, day programs), HR, marketing. Need a
  clearance: TPM 112 of 1,000, program manager 168, project manager 36. "Portfolio manager" (1,370)
  in finance = investment management, not a PMO.
- Industry has no filter. `category=finance` = finance jobs (analysts, accountants), not jobs at
  banks. `domains` (fintech 15,513 US) is null on 47-56% of PM rows; of 57 TPM rows at banks, card
  networks, insurers by name, 42 untagged (every JPMorgan Chase row) => never a `domains` filter.
  Their industry counts through resume match (`best.py`).
- Engineering background asks, rejected as a rank rule: 225 of 702 TPM postings w/ requirements
  name CS / engineering in a required line, nearly all a degree "or equivalent" or a "TPM or
  software engineering" menu; a hard "N years as a software engineer" w/o alternative 20 of 1,249
  PM postings. PMP / PgMP / SAFe / ITIL asks are read (`knockout.credentials_asked`).
- What the interviews test (2,858 postings' full descriptions, TPM / finance split): delivery,
  stakeholders, risk 86-94%; system design 46% of TPM; SOX / Basel / CCAR ~0 =>
  `app/docs/apply/interview.md` #Program managers.
Shape: `app/profiles/program-manager.yml`.

## Work with no category: compliance + risk (2026-10-09, `countries=us`)

No `compliance` (or risk, audit, privacy) category among the 47. Titled jobs, open / posted in the
last 30 days: compliance 3,562 / 1,408 (manager 1,494, analyst 815, officer 396, specialist 177,
associate 77), regulatory affairs 965, GRC 376, privacy 300, risk analyst 286, internal audit 218,
regulatory compliance 187, trade compliance 162, AML 124, BSA 61, KYC 37, financial crimes 57,
sanctions 29, healthcare compliance 30, chief compliance officer 68. 500 newest "compliance": legal
248, management 73, security 43, project_management 34, finance 15, rest across 20+;
`work_mode` null 308, remote 94; `requires_clearance` 30. 1,000 newest by title word: security / GRC /
cyber 112, environmental / safety / fleet 77, trade / import / export 70, housing / grants /
government 66, engineer 45, tax / payroll 37, quality / validation 35, attorney / counsel 24,
healthcare 26, broker-dealer / investment 19, AML / BSA / KYC / fraud 15, product manager 13;
515 general (Compliance Analyst / Manager / Officer). => title passes, one phrase each, one tier
(`app/profiles/compliance.yml`); a category pass would drop half and add lawyers.
Risk, open / last 30 days: risk 2,283 / 826 (259 remote), risk manager 1,223, risk & compliance 316,
risk and compliance 136, risk analyst 286, credit risk 133, technology risk 89, enterprise risk 85,
IT risk 71, SOX 60, insurance risk 59, operational / fraud risk 47 each, model risk 46, market risk 43,
third-party risk 42, clinical risk 39, risk adjustment 27 (medical coding), ERM 25. 1,000 newest
"risk": management 422, security 153, project_management 44, legal 42, sales 37; 135 say compliance
too; remote 120, clearance 36. By word: security / cyber / IT 193, data / analytics 96, engineer 75
(insurance risk engineers = loss control), insurance / clinical / patient 70, operational /
enterprise 65, software / product 57, credit / lending 52, market / treasury / quant 44, third-party
/ vendor 37, sales 35, fraud / AML 27, model 22, risk adjustment 17; 338 general (Risk Manager).
Hospital Risk Manager posts often ask an active RN licence.
Required lines asking to hold a licence or certification (`knockout.credentials_asked`): 38 of
6,990 compliance, 41 of 5,003 risk (risk, risk management, SOX, internal controls, ERM): Series 7 /
24 / 57 / 63, CAMS, CPA, CIA, CISA, CRISC, CISSP, CPHRM, CTPRP, CBCP, RN. FRM, PRM, CFA, ARM, CPCU
show up as wishes ("preferred", "a plus") - never read as asked.

## Video work: editing, shooting, motion (2026-10-09, `countries=us`)

Titled jobs, open / posted in the last 30 days (remote open): video 817 / 334 (143), editor 556 / 223
(138), content creator 459 / 158, video editor 263 / 111, videographer 221 / 61 (14), multimedia 198,
video producer 149 / 77, motion designer 135 / 61 (32), animator 84, video content 61, media producer
41, videographer/editor 35, VFX 33, motion graphics 32, creative producer 31, post-production 18,
assistant editor 6, colorist 4, film editor 1. A slash joins words ("videographer/editor" 35, not in
"videographer"). City: New York City video 122, editor 68; Los Angeles proper video 20 (its studios
sit in Burbank, Santa Monica, Culver City).
`category=creative` 1,270 US, its 500 newest: video producer 22, video editor 19, photographers 50+,
game artists + animators; 500 newest "video" titles: creative 223, marketing 58, management 43, design
32, software_engineering 22, project_management 17, sales 14, 25+ others => title passes
(`app/profiles/video.yml`), never the category alone. Noise in the "video" pass (500 newest): engineer
/ developer 67 (streaming, Prime Video), sales 15, software / product manager 13, network / AV 11,
scientist 7; in "editor": technical writer 64, photo editor 48, social media editor 19, news 15, copy 8.
1,023 video / editor / motion rows: `employment_type` null 486, full_time 214, contract 182, part_time
104; `work_mode` null 584, remote 191; `salary_period` set on 161 (year 120, hour 37, month 4), no day rates seen.
Required asks (4,253 lines on 551 rows): portfolio / reel on 204 rows (`knockout.portfolio_asked`; hand
check below), Premiere 231 lines, After Effects 193, social formats 315, camera / shooting 287,
storytelling 173, broadcast / news 172, years 297, degree 125, AI tools 105, DaVinci 56, Final Cut 54,
color grading 38, edit test 37, drone / Part 107 12, union / guild 4.
Portfolio reader, hand-checked on 6 fields' required lines (video 3,828, creative 2,490, marketing
1,985, software 2,272, finance 1,759, healthcare 763): hits 209 / 121 / 23 / 2 / 1 / 0. Cut before:
"managing portfolios", "cash portfolios", "a portfolio of strategic investments", "enterprise
portfolio", "the NBCUniversal portfolio", Instagram "Reels", slot-machine "reel spins".
Freelance / temporary titles, 3,000 newest rows over 6 fields: 63; tagged contract 38, part_time 15,
full_time 5, internship 4 => `rank.TITLE_TYPES` reads them contract.
Resume side (import, numbers, credits, reel link, letters): `docs/resume/bullets.md` #Video resumes.

## Software engineering kinds

2026-10-09, `countries=us`. Software engineering = many jobs under one name. Categories split it
by title: newest 1,000 each, `frontend` 1,000 titled front-end, `fullstack` 881 full-stack + 119
front-end, `backend` 982 back-end, `mobile` 919 mobile, `embedded` 949 systems.
`software_engineering` (42,421) holds the
rest: 582 of 1,000 titled plainly ("Senior Software Engineer"), 163 systems, 132 back-end, 49
infra, 41 data / AI, 16 front-end. A plain title's kind shows only in `skills`: of 582, front-end
tags (react, typescript, css ...) on 201, back-end / systems tags w/o any front-end one on 225,
neither 152. Titles filed elsewhere (500 newest each): "ui developer" design 375, frontend 65;
"ui engineer" design 174, frontend 45; "web developer" software_engineering 308, fullstack 98,
frontend 43 - real developer jobs (react / javascript / css tags), so a `category=frontend` search
misses most UI and web developers.
`skills=` values OR together (react 15,528, typescript 26,504, both 33,981).

Front-end search, remote US: `category=frontend,fullstack` 1,279; `software_engineering` +
`skills=react,typescript,javascript,angular,vue,nextjs` 1,896, none overlapping, 1,323 plain
titles; title passes new to both: ui developer 19 of 29, ui engineer 20 of 26, ux engineer 19 of
22, web developer 24 of 112. `design` + front-end skills: 151, half product designers => title
passes instead. Shape: `app/profiles/frontend.yml`.

`rank.software_kinds` (`app/software.py`): a title's role words decide (front-end, back-end,
embedded, mobile, platform, data ...), its language words only when it has none - "Senior Backend
Engineer (TypeScript)" is back-end (19 of 1,000 `backend` rows read front-end on the language
alone); plain titles are read off skill tags, sorted lower only on another kind's stack w/ none of
theirs. As front-end + full-stack: `frontend` + `fullstack` 2,000 of 2,000 kept; `backend` 992 of
1,000 flagged, `mobile` 993, `embedded` 997 - every one kept names front-end work too ("Front-End/
Back-End Engineer", "Embedded UI Engineer"). The remote skills pass above: 1,418 kept, 478 lower.
Plain titles lowered by tags: 18 of 250 mention front-end words anywhere, read by hand mostly
in passing ("integrate backend services with frontend applications"). Sorted lower, never hidden;
`blocklist.software_kinds` hides by title only, after the user sees the count.

## Null facets outside tech (2026-09-19)

Healthcare sample: `seniority` null ~95% of rows, `work_mode` ~85%, `employment_type` ~30%.
Filtering on facet drops every null row, not only mismatches. => filter only on facets whose
probe tally shows few `-` (null); `work_mode=remote` safe (remote rows carry it). TUI lists null
seniority as `unspecified`.

## Filters vs rank boosts (2026-09-15, `skills=react` remote US slice)

Hard filter drops rows w/ NO data, not rows that fail:
- `salary_min=<floor>` cut 177 -> 40; only 91 of 247 carried salary. => `rank.salary_floor_usd`
  compared to TOP of posted range ($55k-$90k meets $60k), applied locally, never as a search
  param; rows then ordered by midpoint. Under it = hidden by `rank.pay_filter`, no pay listed kept
  unless they choose (`pay-filter.md`).
- `collections` cut 177 -> 21. => `rank.boost_collections` boost, below pay: `bigtech`
  `unicorn` `yc` mean nothing outside tech, so only order rows w/o pay. Default `fortune500`.
- `employment_type` / level: same null problem => `rank.employment_types` + `rank.career_level`
  demote clear mismatches (title words, stated type); null never demoted.
- `category=frontend,fullstack` cut 247 -> 103, dropped React roles filed under
  `software_engineering`. => tech search by one skill uses `skills=` alone, no `category=`.
  Kind of software work (front-end, not back-end): [Software engineering kinds](#software-engineering-kinds).
- `seniority` facet skewed (senior 168, junior 3, middle 6): junior levels live in title string,
  not facet.

## Title search

`q=<words>&q_fields=title` matches titles only. Measured 2026-10-01, `countries=us`:

| title | unquoted | quoted (every word) |
|---|---|---|
| nurse | 269 | 111 |
| registered nurse | 240 | 50 |
| RN | 19,851 | 19,827 |
| teacher | 85 | 69 |
| accountant | 52 | 18 |
| medical assistant | 3,759 | 275 |
| data analyst | 23,232 | 3,462 |
| software engineer | 37,068 | 30,043 |

Unquoted, one word also matches longer words ("nurse" -> "Nursery ...", 35 of the first 100) and
several words match any of them ("staff accountant" 12,818, mostly Staff ... Engineer) =>
`freehire.phrase` always quotes. No OR: `"registered nurse" OR "rn"` -> 24 (titles holding both)
=> one phrase per pass (`cfg.q_problem` rejects a list). `probe --title A --title B` counts each
form, open + posted in the last 30 days.
Quoted is every word, any order, word stems - not the phrase as written (2026-10-09): titles not
holding it literally, "technical project manager" 149 of 844, "IT project manager" 210 of 727,
"technical program manager" 53 of 1,000, "program manager" 85 of 1,000. Mostly the same job
("Project Manager - Technical", "Technical Project/Program Manager", "Technical Program
Management"); a few the opposite ("Non-Technical Project/Program Manager", "Project Manager (Non
IT)") or another job ("Program Security Manager") - `blocklist.title_phrases` once counted.

## Companies (2026-10-03)

Job rows carry `company` + `company_slug`, no website. `GET /companies/<company_slug>` ->
`data.company.company_info.website` (Notion https://notion.so, Figma https://figma.com);
`company_info` empty for some (Muse Group); 404 = no record. 17 of 30 companies of the newest 30
US postings had a website. No about-us URL anywhere => main website only, never a guessed path or a
URL built from the slug. Python urllib w/o a User-Agent gets 403; httpx fine.
`app/companies.py`: asked at the job check (50 per check, one after another), cached in
`companies` 30 d, failure = asked again next check; Today links it, else plain name (no web search, owner 2026-10-03).

## What the job source leaves out

freehire is an IT job board and prunes the rest by design (their catalog-pruning design,
2026-07-25; dictionary `internal/dict/classify/nontech.go`): titles on a hands-on/non-tech list
are deleted at every company, and non-tech roles at companies w/ no tech evidence. The list holds
whole words - nurse, registered nurse, lpn, cna, teacher, accountant, pharmacist, therapist,
driver, cashier, warehouse... - so the short form can survive: Healthcare 31,964 US jobs, 17,849
titled RN, 50 "registered nurse"; teacher 69, accountant 18 open (0 posted in 30 days)
(2026-10-01). => a category count says nothing about one role: setup counts every form of the
user's title (`probe --title`) and says plainly when the source carries few. Counts move as
pruning waves run - re-measure, never quote these.

## Rejected sources (2026-09-15)

- **Himalayas** - every filter returns identical `totalCount=104918`; bulk dump, not search API.
- **`wallentx/jobscout`** - human commits stop 2026-06-24; new source needs Go code. Layout
  reference only.
- **Remotive** - 16 jobs total, filters ignored.
