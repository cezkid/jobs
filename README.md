# CEZ Job Finder

Finds jobs in any field, tells you each morning about new ones, makes your resume for any job
you pick. You chat in plain English in VS Code's AI panel; it does the rest.

**Easiest: https://jobs.enrriquez.com** - one button, one paste.

## Need

- Windows 10/11 or Mac
- Paid Claude (Pro/Max), ChatGPT (Plus/Pro) or GitHub Copilot Pro ($10/month; pick a strong model such as Claude Sonnet - the free tier can't make tailored resumes)

## Install (once, ~5 min)

Paste the line for your computer, press Enter, type 1 (Claude), 2 (ChatGPT) or 3 (GitHub Copilot)
when asked. Installs only what's missing, no admin prompt, opens VS Code. Safe to rerun - keeps
your files.

**Windows** - Start, type `PowerShell`, open it, paste, Enter:

```
irm https://jobs.enrriquez.com/win | iex
```

**Mac** - magnifying glass top-right, type `Terminal`, open it, paste, Enter:

```sh
curl -fsSL https://jobs.enrriquez.com/mac | bash
```

Read the script first: [Windows](app/install/install-windows.ps1) · [Mac](app/install/install-mac.sh) - the exact file the line runs.

## Everyday

Double-click **CEZ Job Finder** on your Desktop, or click the morning notification. Opens VS
Code with the **Today** page (START HERE on first run) and the chat. Ask "any new jobs?", "make my resume for job 3".

## Private

File list (My Jobs, My Resume, My Settings) stays on your computer. Program = public, open
source, hidden. `Guides/Who sees what.md` lists what leaves and when. Resume is read in user's own AI chat;
setup offers to switch off AI training on their account (`Guides/Keep your chats out of AI training.md`).

## For developers

Thin client over freehire's keyless job API: polls search settings, dedupes, ranks, notifies
daily of new rows, tailors resume to one posting as PDF. Finds jobs, tailors resumes, tracks where each application stands, fills forms but never
submits. How it works, in plain words: [research](https://jobs.enrriquez.com/research/) and
[privacy](https://jobs.enrriquez.com/privacy.html). Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/cezkid/jobs && cd jobs && uv sync
mkdir -p "My Settings" && cp app/profiles/example.yml "My Settings/Search settings.yml"
uv run app/jobs.py probe category=finance work_mode=remote countries=us   # count before committing filter
uv run app/jobs.py find
```

Every command: `uv run app/jobs.py <command>`; bare call lists them.
Tests: `uv run pytest` (live gates hit freehire API).
Search settings merge over `app/defaults.yml`; `JOBS_CONFIG=<path>` points elsewhere.
All code under `app/`; root = user folders, `Guides/`, `docs/` (install page, GitHub Pages).

### Where things are

- `AGENTS.md` - single source of AI instructions, layout, rules (`CLAUDE.md` imports it)
- [`app/docs/README.md`](app/docs/README.md) - program docs index, measured facts per area
- `app/docs/jobs/freehire.md` - API facts, filter pitfalls, filters vs rank boosts
- `app/docs/resume/bullets.md` / `typeface.md` / `page-format.md` - bullet rules, font + page gates
- `app/skills/` - skill bodies; stubs in `.claude/skills/` + `.agents/skills/`
- `.github/CONTRIBUTING.md` - bug fixes + PRs (AI: `report-defect` skill)
- `docs/` - install site (GitHub Pages); generated files from `uv run app/web/assets.py` + `pages.py`, rules in
  [`app/docs/site.md`](app/docs/site.md); left out of the app download (`.gitattributes`)
- Install scripts: `app/install/` - pasted line, not downloaded file -> avoids SmartScreen /
  Gatekeeper. Test w/o touching `~/jobs`: `JOBS_DIR=<dir> JOBS_NO_LAUNCH=1 JOBS_AI=claude`
  (`chatgpt` / `copilot`, or 1 / 2 / 3; saved to `.data/ai`, `uv run app/jobs.py ai` shows or changes it)
- Linux server: 1 vCPU / 1GB / 10GB, uv at `/usr/local/bin/uv`, repo at `/opt/jobs` owned by
  `jobs`; calendars in `schedule` (`app/defaults.yml`), re-render after changing them

```sh
sudo uv run python app/deploy/render_units.py --out /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable --now jobs-poll.timer jobs-digest.timer
```
