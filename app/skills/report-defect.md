# report-defect

Mechanics: `.github/CONTRIBUTING.md` #Defect PR - follow it step by step. This skill adds gates
+ setup for installed copy. User not technical: run everything yourself, report outcome in
plain words.

## Setup - installed copy has no git

Install downloads zip => no `.git`, no git, no gh. `.git` present -> developer checkout, skip
to gates.

1. Tools, missing only: Windows `winget install --id Git.Git -e --silent
   --accept-package-agreements --accept-source-agreements`, same for `GitHub.cli`. Mac: `git
   --version` (Apple dialog -> tell user click **Install**, wait); gh = latest
   `gh_<ver>_macOS_<arm64|amd64>.zip` from `github.com/cli/cli/releases`, `bin/gh` ->
   `~/.local/bin/`.
2. `gh auth status` fails -> `gh auth login --hostname github.com --git-protocol https --web`,
   `gh auth setup-git`; tell user: paste code shown into browser page, free GitHub account ok.
3. `gh repo fork cezkid/jobs --clone=false`, then `gh repo clone <their login>/jobs
   .data/upstream` (exists -> `git -C .data/upstream pull upstream main`).
4. Copy each file you fixed from install into same path under `.data/upstream`. Run
   CONTRIBUTING steps + every gate below INSIDE `.data/upstream`; diff there = only your fix
   (install older than upstream would revert others' work - fix that first).

## Gate 0 - consent

User said yes to sending fix to maintainer in THIS conversation, for THIS fix. Otherwise ask
(`AGENTS.md` #Framework defects wording); no -> stop.

## Gate 1 - scope

- `git status --short`: only files belonging to fix; stage by path, never `-A` / `-a`.
- `git check-ignore <staged paths>` prints nothing.
- Nothing under `My Jobs/`, `My Resume/`, `My Settings/`, `.data/` staged.

## Gate 2 - personal data

Read `contact` from `My Resume/Resume details.yml` (name, email, phone, address pieces). Grep
staged diff for each value, case-insensitive:

```sh
git diff --cached | grep -i -F -e "<name>" -e "<email>" -e "<phone>"
```

Any hit -> stop, remove it. Also scan diff for employer names, cities, pay from user's search
settings baked into tests or docs; replace w/ neutral values.

## Gate 3 - green

`uv run pytest` green on branch. Tail goes into PR template `Test run`.

## Ship

Tell user in one or two plain sentences what gets sent ("fix to how Job Finder reads job
locations, plus test - none of your files"), then run CONTRIBUTING steps. `gh` login failed ->
run `gh auth login --web`, tell them to paste code shown into browser page. No fix possible ->
`gh issue create --repo cezkid/jobs` w/ repro. Give them link. Developer checkout: switch back
to `main` after (`git switch main`) so launcher's update keeps working.
