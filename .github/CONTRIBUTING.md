# Contributing

A pull request is licensed under the repo's [MIT License](../LICENSE), like the rest of the code -
send only code you wrote or may share that way.

Defect = bug, crash, wrong result or misleading doc in TRACKED code, profile example, skill or
doc. Your own search settings being too wide or narrow is tuning, not defect.

## Never commit personal data

Gitignored, and must stay out of every commit and diff: `My Jobs/`, `My Resume/`,
`My Settings/`, `.data/`, `Today.md`. Before commit: `git status --short` lists only files you meant
to change, and `git diff --cached` carries no name, email, phone or address of yours.

## Defect PR

1. Reproduce; fix cause, not symptom (config, schema, upstream call - not the call site).
2. Add or adjust test in `app/tests/` covering it.
3. While fixing, `uv run pytest --changed` runs only the tests your change can reach. Before the
   PR, `uv run pytest --touched` green: the whole suite for the parts your branch changed - program
   (`--app`), website (`--site`, `docs/` + `app/web/`) or both (~5 min both, 6 workers in parallel;
   live gates hit freehire API; note in PR if API was down). One test or a debugger: add `-n 0`.
4. Branch + commit, staging paths explicitly (never `git add -A`):

   ```sh
   git switch -c fix/<short-slug>
   git add <paths>
   git commit -m "<area>: <what was wrong> -> <fix>"
   ```

5. Push to your fork: `gh repo fork --remote` once (fork becomes `origin`, `cezkid/jobs`
   `upstream`), then `git push -u origin fix/<short-slug>`.
6. `gh pr create --repo cezkid/jobs --fill` then fill template sections (repro, cause, fix,
   test run).

Claude credit follows your Claude Code `attribution` setting: `uv run app/jobs.py attribution`
shows it, `attribution hook` strips "Co-Authored-By: Claude" from commits while it is off, and
`attribution strip --pr <file>` does the same for PR text.

No fix possible (upstream API, unclear cause): `gh issue create --repo cezkid/jobs` w/ repro
command, expected vs actual output, date.

## freehire findings

New measured API behavior -> `app/docs/jobs/freehire.md`, dated, w/ counts that settled it.
