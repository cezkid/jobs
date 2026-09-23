# job-tailor

User not technical - `AGENTS.md` #User = not technical binds. Needs
`My Resume/Resume details.yml` (missing -> `job-setup` skill step 3).

1. Source:
   - job from list: `uv run app/jobs.py tailor prepare <slug>`
   - pasted text: write it to `.data/posting.txt`, then
     `uv run app/jobs.py tailor posting .data/posting.txt --url "<link if given>"`; do printed
     task yourself, then run command it prints (`tailor prepare --posting ...`)
   - link only: fetch page text, write to `.data/posting.txt`, same as pasted
2. `prepare` makes `My Jobs/<Company - Title>/` + task file. Do task yourself (`AGENTS.md`
   #AI writing steps), then `uv run app/jobs.py tailor check <slug>`. FAIL lines -> fix
   `tailored.json`, rerun check; never hand over PDF while check fails.
   - `gate pages` -> 3+ pages, or a 2nd page under 60% full. Cut or add bullets, never retype
     the layout.
   - `gate line-fill` -> named paragraphs end in a stub line, wasting a whole row. Detail gives
     each one's text, how full it is, and chars to cut (pull it onto one line) or add (fill the
     second). Rewrite those bullets only; keep every claim sourced.
   - `bullet N: wraps to a line only N% full` from the selection check catches the same thing
     before any render, measuring the real font: a bullet fills one line or fills two.
   - `uv run app/jobs.py resume-fit "<wording>" ...` asks the same question about wordings not
     written into any file yet - several at once, or `-` to read them a line at a time. It
     prints the two target sizes first, so aim at an edge instead of writing then measuring.
     `thin` = clears the gate and still wastes most of a row; bare `resume-fit` checks every
     bullet already in `Resume details.yml` without rendering.
   - Stubs in the user's own facts (contact, dates, education) are reported, never failed - only
     they can shorten a link or blurb in `Resume details.yml`. Mention it, let them choose.
   - Want a different typeface -> `app/docs/typeface.md` #Changing it. Chars per line move with
     it, so redo the task file (`tailor prepare`) after, never reuse the old answer.
   - Rewriting a bullet -> `app/docs/bullets.md`: accuracy outranks fit, so never add a number,
     term or grade to fill a line or match a requirement. A bullet with no evidence behind it is
     a question for the user, never a line to fill in.
3. Read `Check before sending.md` in job folder: coverage, gaps, gate results, then every
   inference = claim not in their original resume. Ask each in plain words: "New version says
   you 'led team of 5'; your resume says 'coordinated 5 nurses'. Is 'led' accurate?" No -> fix
   `tailored.json` or `My Resume/Resume details.yml`, rerun check; never leave unconfirmed claim.
4. Gaps they can truthfully fill ("Do you have IV certification?") -> add fact to
   `Resume details.yml` as one plain sentence under `bullets:` (never an id or metrics list -
   `AGENTS.md` #Resume details), redo task, rerun check.
5. Open PDF for them; say it's in `My Jobs/<Company - Title>/`, private to this computer, ready
   to upload.

Wording the user asks about:
- Industry term: keep it spelled exactly as the field writes it - screeners match the string, and
  dropping it loses the keyword. Put its plain meaning in the same sentence instead ("WCAG 2.1 AA
  accessibility"), once per page, not in every bullet. `skills` items stay bare - that block is the
  keyword list, explaining there only bloats it.
- Bullet order inside one role: strongest first (the opening bullet is the one always read),
  relevance over chronology, a bullet w/ a number outranks one w/o, weakest last. `resume-lint`
  warns `lead-bullet-weak` when a role opens w/o a number while a later bullet carries one.

Identity = employer, title, dates. Verified w/ HR, so never reword one to fit a posting - `lint`
FAILs `title-changed`, `employer-changed`, `dates-changed`. A posting's title goes in
`title_mirror` (suffix only: "Software Engineer (Full Stack Engineer)"), never in place of
theirs. A self-added narrowing suffix ("Software Engineer (Frontend)") is the user's to drop:
it carries no verification risk, but it labels them narrower than their bullets and leaves the
mirror stacking two parentheticals. Ask whose wording it is before touching it.

`resume-lint` also WARNs on the shape of the master resume, all judgement calls, none fatal:
`role-dates-overlap` (one role ends after the next begins - same employer means a promotion
recorded wrong, different employers usually means real concurrent work), `bullet-taper` (an
older role given more bullets than a newer one), `canonical-casing` (NginX, JQuery - one
correct spelling per name, URLs exempt), `lead-bullet-weak`.

Keywords the user is missing: measure, never guess. Their own matched rows carry a `skills`
list - count it across `jobs.db`, subtract what they list, and show the top gaps w/ real
percentages. Offer only the ones their bullets already evidence (AWS when EC2 is on the page,
LLM when they built AI tooling) and let them confirm each; a keyword they cannot defend in an
interview is worse than a missing one.

Positioning = the user's own words, not a verified fact (unlike employer, title, dates), so it is
theirs to choose - but measure before advising, never opine:

- Specialization in `summary` ("full stack" vs "front-end"): count both words across their matched
  titles and the pay behind each (`jobs.db`), then check the label survives their bullets. A full
  stack claim carrying one back-end bullet in thirteen gets probed in the first interview. A
  qualifier keeps a broad claim honest: "Full stack software engineer, front-end focused".
- Years: lead with them, counted from the first role that genuinely does the work, and say which
  role you counted from so they can correct it.
- Location: count how their target rows name theirs (`location` in `jobs.db`). A town of 30k
  matches nothing a screener searches; the metro name matches every row. Say plainly what dropping
  the state costs - remote rows that restrict hiring by state need it. Longer location = longer
  contact line: `contact-line (info)` reports the wrap, and on a full page that wrap costs a whole
  page, so re-render before promising the wording.

Never invent experience to close gap. Tailor/render/lint crash or wrong output from tracked code
-> `AGENTS.md` #Framework defects.
