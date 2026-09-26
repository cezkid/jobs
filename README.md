# Job Finder

Finds new job postings that match what you're looking for, in any field, tells you about new
ones each morning, and makes a version of your resume tailored to any job you pick. You talk to
it in plain English in VS Code's AI panel; it does the rest.

**Easiest: open https://cezkid.github.io/jobs** - one button, one paste, done.

## What you need

- Windows 10/11 or a Mac
- Paid Claude (Pro or Max) - https://claude.ai - or ChatGPT (Plus or Pro)

## Install (once, about 5 minutes)

Copy the line for your computer, paste it where shown, press Enter, then type 1 (Claude) or 2
(ChatGPT) when asked. It installs uv, VS Code and your AI's panel (only what's missing, no admin
prompt), then opens VS Code. Click **Sign in** on the right-hand panel, then press Enter. Safe to
run again: it repairs the program and keeps your files.

**Windows** - click Start, type `PowerShell`, open Windows PowerShell, paste, Enter:

```
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/cezkid/jobs/main/app/install/install-windows.ps1 | iex"
```

**Mac** - click the magnifying glass top-right, type `Terminal`, open it, paste, Enter:

```sh
curl -fsSL https://raw.githubusercontent.com/cezkid/jobs/main/app/install/install-mac.sh | bash
```

## Everyday use

Double-click **Job Finder** on your Desktop, or click the morning "new jobs" notification. It
updates itself and opens VS Code with a **START HERE** page and the AI chat ready. Ask the AI
things like "any new jobs?" or "make my resume for job 3".

## What's private

Everything you see in VS Code's file list (My Jobs, My Resume, My Settings) is private and
stays on your computer. The Job Finder program is public, open source and hidden from that
list. START HERE explains exactly what leaves your computer and when.

## For developers

Thin client over freehire's keyless job API (`app/docs/jobs/freehire.md`): polls search profile,
dedupes, ranks, notifies daily of new rows (desktop notification, email optional), tailors
resume to one posting as PDF. Discovery + tailoring only - no application tracking, no
auto-apply. Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). All code under `app/`;
root holds user folders, tool config, `Guides/` (plain-words guides the user sees in the file
list) and `docs/` (install page, GitHub Pages from `main` `/docs`). Program docs - measured
facts and evidence per area - are indexed in [`app/docs/README.md`](app/docs/README.md). AI layer: `AGENTS.md` (single source; `CLAUDE.md` imports it), skill bodies
`app/skills/`, stubs `.claude/skills/` + `.agents/skills/`, pre-approved commands
`.claude/settings.json` + `.codex/`.

```sh
git clone https://github.com/cezkid/jobs && cd jobs && uv sync
mkdir -p "My Settings" && cp app/profiles/example.yml "My Settings/Search settings.yml"
uv run app/jobs.py probe category=finance work_mode=remote countries=us   # count before committing filter
uv run app/jobs.py find
```

Search settings merge over tracked `app/defaults.yml`; `JOBS_CONFIG=<path>` points elsewhere.
`app/profiles/example.yml` carries measured reasoning for its filters. Every command:
`uv run app/jobs.py <command>`; bare call lists them. Tests: `uv run pytest` (live gates hit
freehire API).

Filter choice: facet w/ many null values (probe tally `-`) drops every null row, not only
mismatches - outside tech `seniority` null on most rows. Salary and top companies rank as
boosts, never filters (`app/docs/jobs/freehire.md` #Filters vs rank boosts).

### Resume steps - any AI

No model CLI. Command writes task file (rules, input, answer schema); chat AI writes answer
JSON; check command validates schema + gates. `My Resume/Resume details.yml` = single source of
resume facts - user's edits win on wording, employer/title/dates change only to fix a mistake
(`AGENTS.md` #Lead, explain, push back); shape `app/resume/master.example.yml`.

That file is the non-technical user's editing surface, so it holds their facts and nothing else:
bullets are plain sentences, and ids, `metrics`, `stack` and `ai_era` are derived at load
(`resume/schema.py` #expand) or read from `.data/resume-index.yml` (`resume/facts.py`), keyed by
the claim. Both shapes load - a file still carrying those fields keeps exactly what it says, and
a hand-written id is never renumbered. `app/resume/details.schema.json` is wired into
`.vscode/settings.json`, so a mistyped fact is underlined as the user types it.

```sh
uv run app/jobs.py resume-import prepare --pdf <path>   # -> .data/resume-task.md; AI writes .data/resume-mapped.json
uv run app/jobs.py resume-import finish                 # traceability gate -> Resume details.yml
uv run app/jobs.py resume-tidy                          # rewrite details as plain facts (notes -> .data)
uv run app/jobs.py resume-render                        # untailored PDF + parse gates
uv run app/jobs.py resume-lint                          # AI-tell + honesty lint
uv run app/jobs.py tailor prepare <slug>                # My Jobs/<Company - Title>/ + .data/task.md
uv run app/jobs.py tailor posting <text file> --url <link>   # pasted posting: extraction task first
uv run app/jobs.py tailor check <slug>                  # PDF, gates, Check before sending.md; rc 1 on fail
```

Job folder: `First_Last_Resume.pdf`, `Job posting.md`, `Check before sending.md` (coverage,
gaps, gates, every inference to confirm), `.data/` (jd, task, answer). Found by slug in
`.data/jd.json`, never by folder name.

Tailored copies are held to the page: `pages` gate = at most 2, a 2nd page 60%+ full;
`line-fill` gate = no wrapped paragraph ends in a stub line. Both measure the rendered PDF in
points - a line counts as wrapped only when the line above had no room for its first word, so a
deliberate break (an entry subline) is never mistaken for one. Bullets fill one line or fill
two, checked before rendering by `resume/measure.py` against real font advances, never character
counts: one glyph runs 3.2x the width of another. Untailored `resume-render` reports both as
info only. Stubs in the user's own facts (contact, dates, education) are reported, never failed.

Typeface is `resume.font` (default Caladea - Cambria's metrics under the OFL, in
`app/resume/fonts/Caladea/`). Which family renders decides what fits: on one real resume the
spread between families runs 85-101 characters a line, which is the difference between 2 pages
with no stub lines and 3 pages with nineteen. So nothing is hardcoded - `resume/typeface.py`
resolves the family and column widths, the word space, the writer's character guides and the
page word windows are all read off the file. The page trades three settings against each
other - family, side margin (`MARGIN_X_IN` 0.85in) and letterspacing (`TRACKING_EM` +0.015em,
which `measure.width` adds back per character). Measurements, why Caladea over Georgia even
with the margins eased, and how to add a family: `app/docs/resume/typeface.md`.

### Daily check

`uv run app/jobs.py autorun on|off|status` schedules `daily` (Windows Task Scheduler / launchd):
poll, then new rows -> email when `.data/email.env` set, else desktop notification
(`app/notify.py`: Windows toast, click -> `jobfinder:` protocol -> Desktop launcher; macOS
`osascript`). Either path marks rows seen only after send succeeds.

Optional email: `.data/email.env` (template `app/email.env.example`) holds SMTP credentials +
recipient. SMTP host, schedule: `app/defaults.yml`, overridable in search settings. Implicit TLS
(port 465) only.

### Install scripts

`docs/index.html` shows one line per computer w/ a copy button; the installer asks which AI
first (1 Claude, 2 ChatGPT), skipped when `JOBS_AI` is set or a re-run finds either AI panel
already in VS Code. Pasted line, never downloaded file: download hits SmartScreen / Gatekeeper.
Steps open PowerShell / Terminal by clicking, never Win+R: security software blocks
download-and-run lines typed into the Run box (the "ClickFix" malware pattern) with "Windows
cannot access the specified device, path or file". Windows line has no `$` so the outer shell
passes it through unexpanded (PowerShell or cmd), and `-ExecutionPolicy Bypass` (this process
only) because uv's installer refuses Windows' default `Restricted` policy; policy locked by Group
Policy -> uv via winget.
`app/install/install-windows.ps1` (`irm|iex`) and `install-mac.sh`
(`curl|bash`): per-user uv, VS Code (user installer / `~/Applications`), AI extension, repo zip
-> `~/jobs` (top-level entries replaced, My folders + `.data/` untouched), `uv sync`, Desktop launcher ->
`app/install/start-*` (`update`, `launch`). No git, gh or admin. `update`: `.git` present ->
`git pull --ff-only`, else zip swap of program files. `launch`: registers `jobfinder:`
protocol (Windows, HKCU), opens VS Code w/ `--disable-workspace-trust` (no trust dialog), then
Claude tab pre-filled via `vscode://anthropic.claude-code/open?prompt=` - "set me up" until
search settings exist, then "any new jobs?". Test w/o touching `~/jobs`:
`JOBS_DIR=<dir> JOBS_NO_LAUNCH=1 JOBS_AI=1`. `.vscode/settings.json` hides everything but START
HERE + My folders.

### Linux server

1 vCPU / 1GB / 10GB, Python 3.11+, uv at `/usr/local/bin/uv`, repo at `/opt/jobs` owned by `jobs`.

```sh
sudo uv run python app/deploy/render_units.py --out /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable --now jobs-poll.timer jobs-digest.timer
```

Poll every 30 min, digest daily; both calendars live in `schedule`, re-render after changing
them. First digest carries whole backlog, every row listed and marked seen.

### Contributing

Found bug in tracked code, profile example or doc? `.github/CONTRIBUTING.md`; AI does it via
`report-defect` skill (installs git + gh on demand, fork + PR).
