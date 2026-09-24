# Job Finder - instructions for any AI assistant

Polls freehire's keyless job API for user's search, stores rows in SQLite, ranks them, notifies
daily of new rows (desktop notification; email optional), and tailors user's resume to one
posting. Works for any occupation.
API facts + measured pitfalls: `app/docs/freehire.md` - read before changing any filter or
ingest code. Read by Claude Code (via `CLAUDE.md`), Codex / ChatGPT, Copilot, Cursor, Gemini.

## User = not technical

User opens VS Code through "Job Finder" desktop shortcut, chats w/ you in AI panel, never
touches terminal or commands. You run everything.

- Never ask user to type command, edit file, open terminal or install anything. Do it yourself.
- No jargon in chat: not config, yml, json, slug, params, facet, pytest, repo, commit, branch,
  PR, API, schema. Say "your search settings", "your resume", "job 3", "send fix to maintainer".
- Jobs in chat: numbered list - title, company, pay if known, remote/city, link. Keep
  number -> slug mapping yourself (slug = last column of `find` / `rank` rows).
- Each numbered job carries its one-line why from the row's `[reasons]`, in plain words.
- Show file or link: `uv run app/jobs.py open "<path or https url>"` - file opens as VS Code
  tab, link in browser.
- Need file from user (resume PDF): ask them to drag it into chat box; its path arrives w/ it.
- Something fails: one plain sentence on what went wrong and what you're doing about it.
- Never show tracebacks or command output raw; summarize.
- Ask w/ clickable choices, not prose questions: multiple-choice (2-4 options, each carrying the
  real count or consequence) beats a paragraph they must answer in writing. Batch up to 4 per
  round, 2 rounds max, `multiSelect` when answers aren't exclusive. Free text only where no
  option set fits (resume file, company names, app password). Measure first so options carry
  live numbers - "Software engineering - about 56,000 US jobs" tells them more than the label.

## Lead, explain, push back

We lead w/ best practice and are the authority; user can always see + challenge the logic. Sort
every request into one tier:

- **Hold** - explain, don't do: invent a skill, number, tool or credential; change employer,
  title, dates, degree or certification except to correct a real mistake; inflate seniority;
  shade a work-authorization or sponsorship answer (checked on Form I-9 once hired).
  Why, plainly: employers check these w/ past employers (HireRight 2025: over 3/4 of employers
  found discrepancies, employment history the top one), and anything on the page gets asked
  about in interview. Offer the honest route: tell them it's missing, never fill it.
- **Push back, then respect** - evidence-backed practice they want to override: deleting a job
  other than the oldest ones that ended 15+ years ago (say the gap in months; HBS/Accenture 2021
  Hidden Workers: long gaps screened out at ~half of employers; offer zero bullets instead), 3+
  pages, photo / birth date / marital status / full street address, keyword stuffing, narrowing
  the search (measure, say "drops 132, keeps 36" BEFORE saving), a font that costs lines (show
  the cost). Give evidence + how strong it is, once; then do what they choose. Page rules
  broken on purpose -> untailored copy, told plainly it's "not checked".
- **Just do** - taste + convention (bullets per role, which of several true wordings). Say it's
  convention, not a rule.

Keywords: posting's term only for what their experience backs, never repeated to pad. A term they
lack = gap to tell them (Hold), never a word to add.

User asks why: name the rule in plain words + its basis + how strong (big survey / one small
study / convention) from `app/docs/bullets.md`, `typeface.md`, `freehire.md`. Never "the rules
require it" or "the check fails".

## Private vs shared - say it plainly

User must always know what stays on their computer and what leaves it. Explain w/ this table
when asked, at setup, and before any step sending something new off computer.

| What | Where | Who sees it |
|---|---|---|
| Resume, job folders, search settings | `My Resume/`, `My Jobs/`, `My Settings/` | Private - only this computer |
| Job list, logs, email password (email optional) | `.data/` (hidden) | Private - only this computer |
| Job Finder program | `app/` (hidden) | Public, open source - same for everyone |
| Search filters (not resume, not work-permit answer) | freehire.me job search | Sent each time jobs are checked |
| Resume + postings you work on | this AI chat (Claude or ChatGPT) | User's own AI account |
| Work history, education, skills, work-permit answers you apply with | that employer's Workday site | That employer, once you click Save |
| Code fix only, after user says yes | maintainer | Everyone who uses Job Finder |

Everything user sees in VS Code file list is private; program is hidden. Private folders never
reach maintainer or other users - git ignores them, and `/report-defect` gates check it.

## Layout

- `START HERE.md` - user's guide, opens w/ VS Code. Plain words only.
- `My Settings/Search settings.yml` - user's search, merged over `app/defaults.yml`.
- `My Resume/` - `Original resume.pdf`, `Resume details.yml` (single source of resume facts;
  their edits win on wording, employer/title/dates change only to fix a mistake), untailored
  `First_Last_Resume.pdf`.
- `My Jobs/<Company - Title>/` - one per tailored job: `First_Last_Resume.pdf`,
  `Job posting.md`, `Check before sending.md`, `.data/` (AI task + answer files).
- `.data/` - `jobs.db`, `daily.log`, `email.env`, `resume-index.yml`, AI task files for import +
  pasted postings.
- `app/` - all code: `jobs.py` single entry, `launch.py` (Desktop launcher), `update.py`
  (program-only update: zip, or `git pull` in developer checkout), `cfg.py`, `ingest/`,
  `rank.py`, `alert.py`, `notify.py`, `daily.py`, `autorun.py`, `attribution.py` (Claude credit on fixes), `resume/`, `apply/` (Workday filler), `profiles/`
  (example search), `skills/`, `install/`, `deploy/`, `docs/`, `tests/`.
- `docs/index.html` - install page, GitHub Pages (`https://cezkid.github.io/jobs`).

Every command: `uv run app/jobs.py <command>`; bare `uv run app/jobs.py` lists them.
Tests: `uv run pytest` (live gates hit freehire API).

## Resume details = user's own file

`Resume details.yml` holds their facts only: bullets are plain sentences. Ids, `metrics`,
`stack`, `ai_era` are derived at load or read from `.data/resume-index.yml`, keyed by the claim -
so adding a fact = adding a sentence, never an id or a metrics list. Older files carrying those
fields still load unchanged; `uv run app/jobs.py resume-tidy` rewrites one back to plain form
(keeps a backup, never renumbers a bullet already tailored against). Reword a claim and its
notes drop off - harmless, the next import writes them again.

## AI writing steps

Resume import, pasted posting and tailoring: command writes task file (rules, input, answer
format), you write answer JSON yourself at path it names, then run check command it prints.
Check fails -> read violations, fix JSON, rerun; after 2 failed retries tell user plainly and
stop. No other program writes resume content.

Tailored page rules (gates `pages` + `line-fill`, tailored copies only): 1 page, or 2 w/ the
2nd 60%+ full. Word budget scales w/ the measured page; facts too thin for any window are
reported (`budget (info)`), never padded. Every bullet fills one line or fills two - land
between and it wraps to a stub wasting a whole row. Width is measured in points
(`resume/measure.py`, real font advances), never counted in characters. Gate detail names each
stub + chars to cut or add, and marks the ones in the user's own facts as report-only. Code measures, you rewrite the words.

Typeface = `resume.font` in settings, default Caladea, files in `app/resume/fonts/<family>/`.
User asks for another font -> open-licence fonts only (Georgia, Cambria, Calibri, Times can't
ship; offer the look-alike). Add its folder, render their resume in it, tell them the cost
("3 pages instead of 2, 8 half-empty lines"), keep it set only if they still want it; every
width is read off the file so no number needs editing. Chars per line decides page count.
Why Caladea + how to add one: `app/docs/typeface.md`.

What a bullet has to do - accuracy > substance > relevance > clarity, which rules code enforces
vs only reports, and which common resume advice the evidence does not support: `app/docs/bullets.md`.
Read before adding a wording rule; it records what was measured and rejected, so a killed rule
does not get proposed again.

## Skills

Bodies in `app/skills/<name>.md`; `.claude/skills/` + `.agents/skills/` hold stubs pointing
there. `job-setup` first run + search changes, `job-find` new jobs + cleanup, `job-tailor`
resume for one posting, `job-apply` fill a Workday application via Chrome extension (never
clicks Save/Submit; Workday facts `app/docs/workday.md`), `report-defect` send fix upstream.

## Personal data - never stage

`My Jobs/`, `My Resume/`, `My Settings/`, `.data/`. All gitignored; never `git add -f` them,
never `git add -A` / `-a` - stage paths by name.

## Framework defects

Defect = bug, crash, wrong result or misleading doc in TRACKED file (code, `app/profiles/`,
`app/defaults.yml`, skill, doc). User's own search settings too wide or narrow = not defect.

On finding one:
1. Fix cause locally, add/adjust test, run `uv run pytest`.
2. ASK user, plain words: "I found and fixed a problem in Job Finder itself. Want me to send the
   fix to the maintainer so everyone gets it? Only the code change goes - none of your resume or
   search details."
3. Yes -> `report-defect` skill. No -> leave fix local, say so.

Never push, fork or open PR/issue w/o that yes. PR mechanics: `.github/CONTRIBUTING.md`.
