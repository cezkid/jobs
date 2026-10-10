# About me - notes beyond the resume, and what Job Finder knows

Code: `app/about.py` (`uv run app/jobs.py about show | list | read KIND | add KIND WORDS | forget KIND N`).
Store: `My Settings/About me.yml` (private, gitignored). Page: `.data/What Job Finder knows about you.md`.

## Why

What the user tells a chat about themselves - where they want to go, workplaces they'd avoid, how
they like to sound - was lost when the chat ended, or kept only in one AI's own memory: outside
this folder, not in the privacy table, unseen by the other two AIs, left behind when the folder
is deleted. Facts about the user were also spread over 4 files w/ no single view. One visible file
any of the 3 AIs can read, plus one page listing everything, fixes both.

## Kinds + what each is used for

| Kind | Holds | Read when | Never |
|---|---|---|---|
| `goals` | what they want next | tailoring: which of their true lines lead; interview practice | written into a letter (cover-letter.md: the "why" is their own sentence) |
| `workplace` | workplaces they like or avoid (size, industry, way of working) | they ask whether a job fits; a company or kind they name -> hidden w/ count first (job-find) | guessed onto a company |
| `voice` | how they like to sound | wording of a letter or follow-up they ask for | a reason, a motive or a fact |
| `never_mention` | things never to put on a page | before any resume, letter, form answer, email | - |
| `values` (sensitive) | beliefs + causes they want weighed: ethics, faith, politics | ONLY when they ask whether a job or company fits | on a resume, form, letter; sent to the job search; in the chat brief |
| `personal` (sensitive) | health, family, caregiving they want weighed | ONLY when they ask whether a job fits | same as values |

Commute, hours, pay, place, work permit stay in search settings (one source each); a note never
repeats them.

## Rules

| Rule | Basis |
|---|---|
| Saved only after one clickable "Save this to your notes?" (Save / Don't save), in their exact words; privacy line first for values + personal: "Saved only on this computer. Your AI reads it when you ask if a job fits - like anything you type here." | AGENTS.md: never infer protected traits ("church on Sundays" is no faith note unless they ask to save one) |
| Never asked for. Values + personal are recorded only when the user brings them up AND says save | same; religion + disability are protected traits under US federal law (EEOC) - the user's own choice to weigh them, never ours to prompt |
| AI reads one kind at a time (`about read KIND`), the kind its task uses; never the whole file, never the page | sensitive kinds reach the AI account only when the user asked a question they bear on |
| Not in `today --brief` | the brief loads into every Claude chat; notes there would steer answers unasked |
| Notes never auto-insert. A resume item on faith, politics or identity keeps the existing Their-call flow (AGENTS.md #Lead) | a note is a preference, not a fact on the page |
| `forget` by number; says the old chat still holds it | the chat is in their AI account; only they can delete it |
| `show` prints the page's path only; the AI opens it as a tab (`jobs.py open`) | the page lists work permit, address, values - the user reads it, the chat doesn't. GitHub Copilot may attach an open file to the next message (its implicit context): say so to Copilot users before opening it |
| Page rebuilt on every `about` command | never shows a forgotten note |

## Company fit

User asks "does Acme fit my values?":
- Posting text (local, data) + their notes. Say what the posting says, plainly, and what it doesn't.
- Never a company's politics, religion or ethics from the AI's own memory: unverifiable, may be
  stale or wrong about a real company. Say plainly it can't check that.
- Their company website: open it for them (`jobs.py open <website>`, the Today page's company link)
  - their visit, as any click. The AI never fetches it (`AGENTS.md` #Where each job stands:
  employer pages need a privacy row + a yes).
- They decide -> hide the company (job-find: `blocklist.companies`), counted first.

## Each AI's own memory

`.claude/settings.json` `autoMemoryEnabled: false` (Claude Code docs, memory.md, 2026-10-06): one
store every AI can read; nothing about the user kept outside the folder by one AI. Memory files
written before the switch are not deleted by it. Claude Code also keeps each chat as a transcript
on this computer, `~/.claude/projects/<folder>/`, 30 days by default (`cleanupPeriodDays`,
sessions.md) - in the privacy table and the removal steps. Developers who want memory in their
checkout: `autoMemoryEnabled: true` in `.claude/settings.local.json` (not shipped, kept on update).

Other two AIs (vendor docs, read 2026-10-06):

| AI | Its own memory | Off from this folder? | Chats kept |
|---|---|---|---|
| GitHub Copilot (VS Code) | memory tool: notes as local files, user scope `/memories/` across every workspace; default + off switch not documented (agents/memory). Copilot Memory: GitHub account, on by default for personal plans, used by cloud agent, code review, CLI - VS Code chat not listed (copilot-memory) | no setting id exists; the AGENTS.md rule (facts -> About me, never your own memory) is the guard. Copilot Memory: user only, github.com > Copilot settings > Features | local SQLite; `chat.sessionSync.enabled` (default true) syncs sessions to the GitHub account - set false in the window's own settings (`app/workspace.py`), so this window's chats stay local |
| OpenAI Codex (ChatGPT sign-in) | local Codex memories `~/.codex/memories/`, off by default; ChatGPT web memory is separate (learn.chatgpt.com customization/memories) | project `.codex/config.toml` loads only for a trusted project, memory keys at project level undocumented - default off already, nothing added | `~/.codex/sessions`, `history.jsonl` (local); server side: the privacy row's AI account |

Sources: code.visualstudio.com/docs/copilot/agents/memory, .../agents/sessions/session-sync,
docs.github.com/en/copilot/concepts/agents/copilot-memory, learn.chatgpt.com/docs/customization/memories,
learn.chatgpt.com/docs/config-file/config-reference. OpenAI help center unreachable (403).

## Declined

- **Values filter on the job list.** freehire carries no politics, religion or ethics data on a
  company (company record = website only, `jobs/freehire.md` #Companies). A filter would rest on
  AI guesses. What the posting itself says is named instead (below).
- **Politics in postings.** Measured below: the words match patient advocacy and legal aid, never
  a party stance. Nothing named.

## What the posting says (`rank.posting_says`)

Opt-in, per kind: `faith` -> "posting says: religious employer", `defense` -> "posting says: defense
or military work", `nonprofit` -> "posting says: nonprofit employer" (or "listed as a nonprofit
employer" when only the job search's company record says it), on the job's reason line (list, Today,
email). Nonprofit is also offered at setup when their resume shows nonprofit work - a sector, not a
value (`job-setup` #2 HR + people leadership). Set only when the user asks to
see it after a note ("tell me when a job is with a religious employer" / "... defense work"), their
yes first. Never hides, never sorts lower - they decide per job, or hide a company (`job-find`).
The employer's own words in its posting; nothing looked up.

Measured 2026-10-06: 1,091 US postings w/ text, 609 employers, 100 newest of each of 11
categories, 30 days (`rank.POSTING_SAYS` words, every match read):

| Kind | Rows | Employers | False | Notes |
|---|---|---|---|---|
| faith | 7 (0.6%) | 7 | 0 | religious schools, 2 dioceses, a church university - all in education |
| defense | 41 (3.8%) | 8 | 0 | "national security" left out: it matched an energy association's goals; costs 2 missed defense employers that said only that |
| politics ("advocacy", "progressive", party names) | 21 | 12 | ~all | patient advocacy, legal aid, "progressive approaches" - declined |
| tobacco / vape, fossil fuels | 0 | 0 | - | the job search carries few such employers (IT board, `jobs/freehire.md` #What the job source leaves out) |
| gambling, alcohol / cannabis | 1, 3 | - | 2 of 3 cannabis false (drug screen, behavioral health) | too few to name |

| nonprofit (2026-10-09, HR-titled, full text) | 107 of 4,790 | 92 | 0 of 40 read; an ask ("nonprofit experience preferred") or a client ("our clients run ... a large nonprofit") isn't it | company record adds 3x the employers, 2 of 20 recruiting firms misfiled (`jobs/freehire.md` #HR + people leadership) |

Small sample, one day: re-measure before adding a kind.
- **A settings section for values.** Search settings reach the job search; values must not.
- **Loading notes into every chat.** See the brief rule above.
- **Per-company research notes** (2026-10-06). A fit answer reads the posting (already in the job
  folder, `Job posting.md`) + the user's notes; the AI never looks a company up, so there is no
  research to keep. The company's website is cached already (`companies`, 30 d). A saved
  "about Acme" note would go stale unseen and invite stance claims - declined until a fit
  question measurably repeats work.
