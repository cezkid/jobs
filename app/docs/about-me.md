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

## Claude's own memory: off

`.claude/settings.json` `autoMemoryEnabled: false` (Claude Code docs, memory.md, 2026-10-06): one
store every AI can read; nothing about the user kept outside the folder by one AI. Memory files
written before the switch are not deleted by it. Claude Code also keeps each chat as a transcript
on this computer, `~/.claude/projects/<folder>/`, 30 days by default (`cleanupPeriodDays`,
sessions.md) - in the privacy table and the removal steps. Developers who want memory in their
checkout: `autoMemoryEnabled: true` in `.claude/settings.local.json` (not shipped, kept on update).
Copilot + ChatGPT memory settings: not checked yet (bead).

## Declined

- **Values filter on the job list.** freehire carries no politics, religion or ethics data on a
  company (company record = website only, `jobs/freehire.md` #Companies). A filter would rest on
  AI guesses. Words in postings ("faith-based", "defense") as a reason line: measure first (bead).
- **A settings section for values.** Search settings reach the job search; values must not.
- **Loading notes into every chat.** See the brief rule above.
