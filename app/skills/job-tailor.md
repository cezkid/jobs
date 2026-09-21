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
   - Stubs in the user's own facts (contact, dates, education) are reported, never failed - only
     they can shorten a link or blurb in `Resume details.yml`. Mention it, let them choose.
   - Want a different typeface -> `app/docs/typeface.md` #Changing it. Chars per line move with
     it, so redo the task file (`tailor prepare`) after, never reuse the old answer.
3. Read `Check before sending.md` in job folder: coverage, gaps, gate results, then every
   inference = claim not in their original resume. Ask each in plain words: "New version says
   you 'led team of 5'; your resume says 'coordinated 5 nurses'. Is 'led' accurate?" No -> fix
   `tailored.json` or `My Resume/Resume details.yml`, rerun check; never leave unconfirmed claim.
4. Gaps they can truthfully fill ("Do you have IV certification?") -> add fact to
   `Resume details.yml`, redo task, rerun check.
5. Open PDF for them; say it's in `My Jobs/<Company - Title>/`, private to this computer, ready
   to upload.

Never invent experience to close gap. Tailor/render/lint crash or wrong output from tracked code
-> `AGENTS.md` #Framework defects.
