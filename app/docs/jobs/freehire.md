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
- `seniority` facet skewed (senior 168, junior 3, middle 6): junior levels live in title string,
  not facet.

## Title search

`q=<words>&q_fields=title` matches titles only. Measured 2026-10-01, `countries=us`:

| title | unquoted | quoted (exact phrase) |
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
