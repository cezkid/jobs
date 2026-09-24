# job-find

User not technical - `AGENTS.md` #User = not technical binds. `My Settings/Search settings.yml`
missing -> `job-setup` skill instead.

1. `uv run app/jobs.py find --limit 15` (checks for new jobs, then ranks). Row columns: `NEW` (not yet
   notified) or `-`, tier, `title | company`, `[why]` in plain words (place, pay, employer list,
   first seen, reposts, level/hours mismatch), slug (last). Repeat "why" to the user when asked.
2. Show as `AGENTS.md` numbered list, grouped by tier label (e.g. "Remote US", "Springfield area").
   Keep number -> slug mapping. Add one plain sentence on how the list is ordered, read off
   `rank.py` #rank + their search settings, never recited from memory.
3. Ask which look good. Good -> offer tailored resume (`job-tailor` skill).
4. User says job is wrong ("that's staffing agency", "not my field") -> find cause, make
   smallest settings change, tell them in one plain sentence what you changed:
   - reposter / staffing agency -> `blocklist.companies`
   - wrong field -> `blocklist.categories` (enrichment.category, local only)
   - misleading title -> `blocklist.title_phrases` (whole words, case-insensitive); first
     `uv run app/jobs.py rank --would-hide "<phrase>"`, tell user the count it hides
   - whole search too wide -> tighten params, measured w/ `uv run app/jobs.py probe` first
   - any narrowing (filter, city, blocked field) -> measure first, state the cost BEFORE saving:
     "Only near Springfield drops 132 remote jobs and keeps 36 - still want it?" Then do what
     they pick (`AGENTS.md` #Lead, explain, push back).
5. "Why is job 3 here?" -> its row's `[reasons]` in plain words: what it matched, what put it
   at that spot. Reason is wrong -> step 4. "may be closed" -> say so before tailoring for it.
6. `uv run app/jobs.py rank --suspects` lists companies posting across many unrelated fields
   (likely reposters) - offer to hide ones user agrees with.
7. After changes: `uv run app/jobs.py check-settings`, then `uv run app/jobs.py rank --limit 15`;
   say how many dropped.

Daily check questions: `uv run app/jobs.py autorun status` (on/off, last run, log tail); turn
on/off w/ `autorun on|off`; change time = `schedule.local_daily` in search settings + `autorun
on`. New jobs arrive as notification, or email when `.data/email.env` set (`job-setup` #5).

Privacy question ("who sees my stuff?") -> `AGENTS.md` #Private vs shared table, plain words.

Edits go to `My Settings/Search settings.yml` only. Noise caused by tracked code (ranking bug,
crash) -> `AGENTS.md` #Framework defects.
