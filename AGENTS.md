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

## Private vs shared - say it plainly

User must always know what stays on their computer and what leaves it. Explain w/ this table
when asked, at setup, and before any step sending something new off computer.

| What | Where | Who sees it |
|---|---|---|
| Resume, job folders, search settings | `My Resume/`, `My Jobs/`, `My Settings/` | Private - only this computer |
| Job list, logs, email password (email optional) | `.data/` (hidden) | Private - only this computer |
| Job Finder program | `app/` (hidden) | Public, open source - same for everyone |
| Search settings (not resume) | freehire.me job search | Sent each time jobs are checked |
| Resume + postings you work on | this AI chat (Claude or ChatGPT) | User's own AI account |
| Code fix only, after user says yes | maintainer | Everyone who uses Job Finder |

Everything user sees in VS Code file list is private; program is hidden. Private folders never
reach maintainer or other users - git ignores them, and `/report-defect` gates check it.

## Layout

- `START HERE.md` - user's guide, opens w/ VS Code. Plain words only.
- `My Settings/Search settings.yml` - user's search, merged over `app/defaults.yml`.
- `My Resume/` - `Original resume.pdf`, `Resume details.yml` (single source of resume facts,
  hand edits win), untailored `First_Last_Resume.pdf`.
- `My Jobs/<Company - Title>/` - one per tailored job: `First_Last_Resume.pdf`,
  `Job posting.md`, `Check before sending.md`, `.data/` (AI task + answer files).
- `.data/` - `jobs.db`, `daily.log`, `email.env`, AI task files for import + pasted postings.
- `app/` - all code: `jobs.py` single entry, `launch.py` (Desktop launcher), `update.py`
  (program-only update: zip, or `git pull` in developer checkout), `cfg.py`, `ingest/`,
  `rank.py`, `alert.py`, `notify.py`, `daily.py`, `autorun.py`, `resume/`, `profiles/`
  (example search), `skills/`, `install/`, `deploy/`, `docs/`, `tests/`.
- `docs/index.html` - install page, GitHub Pages (`https://cezkid.github.io/jobs`).

Every command: `uv run app/jobs.py <command>`; bare `uv run app/jobs.py` lists them.
Tests: `uv run pytest` (live gates hit freehire API).

## AI writing steps

Resume import, pasted posting and tailoring: command writes task file (rules, input, answer
format), you write answer JSON yourself at path it names, then run check command it prints.
Check fails -> read violations, fix JSON, rerun; after 2 failed retries tell user plainly and
stop. No other program writes resume content.

Tailored page rules (gates `pages` + `line-fill`, tailored copies only): at most 2 pages, a
2nd page 60%+ full; every bullet fills one line or fills two - land between and it wraps to a
2-3 word stub wasting a whole row. Gate detail names each stub + chars to cut or add. Code
measures, you rewrite the words.

## Skills

Bodies in `app/skills/<name>.md`; `.claude/skills/` + `.agents/skills/` hold stubs pointing
there. `job-setup` first run + search changes, `job-find` new jobs + cleanup, `job-tailor`
resume for one posting, `report-defect` send fix upstream.

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
