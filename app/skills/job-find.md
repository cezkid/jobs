# job-find

User not technical - `AGENTS.md` #User = not technical binds. `My Settings/Search settings.yml`
missing -> `job-setup` skill instead.

1. `uv run app/jobs.py find --limit 15` (checks for new jobs, then ranks). Row columns: `NEW` (not yet
   notified) or `-`, tier, `title | company`, `[why]` in plain words (place, pay, employer list,
   first seen, reposts, level/hours mismatch), slug (last). Repeat "why" to the user when asked.
2. Show as `AGENTS.md` numbered list, grouped by tier label (e.g. "Remote US", "Springfield area").
   Keep number -> slug mapping.
3. Ask which look good. Good -> offer tailored resume (`job-tailor` skill).
4. User says job is wrong ("that's staffing agency", "not my field") -> find cause, make
   smallest settings change, tell them in one plain sentence what you changed:
   - reposter / staffing agency -> `blocklist.companies`
   - wrong field -> `blocklist.categories` (enrichment.category, local only)
   - misleading title -> `blocklist.title_phrases` (whole words, case-insensitive); first
     `uv run app/jobs.py rank --would-hide "<phrase>"`, tell user the count it hides
   - whole search too wide -> tighten params, measured w/ `uv run app/jobs.py probe` first
5. `uv run app/jobs.py rank --suspects` lists companies posting across many unrelated fields
   (likely reposters) - offer to hide ones user agrees with.
6. After changes: `uv run app/jobs.py check-settings`, then `uv run app/jobs.py rank --limit 15`;
   say how many dropped.

Daily check questions: `uv run app/jobs.py autorun status` (on/off, last run, log tail); turn
on/off w/ `autorun on|off`; change time = `schedule.local_daily` in search settings + `autorun
on`. New jobs arrive as notification, or email when `.data/email.env` set (`job-setup` #5).

Privacy question ("who sees my stuff?") -> `AGENTS.md` #Private vs shared table, plain words.

Edits go to `My Settings/Search settings.yml` only. Noise caused by tracked code (ranking bug,
crash) -> `AGENTS.md` #Framework defects.
