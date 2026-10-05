# Job Finder docs

**Users**, plain words, in the file list:

- [START HERE](../../START%20HERE.md) - first-run steps; Today page opens instead once set up, START HERE leaves the file list.
- [What you can ask](../../Guides/What%20you%20can%20ask.md) - what to say, where jobs come from, how the resume is made.
- [Who sees what](../../Guides/Who%20sees%20what.md) - what stays on the computer, what leaves and when.
- [What makes a good resume](../../Guides/What%20makes%20a%20good%20resume.md) - every rule
  in one line, w/ strength of its evidence.
- [Unfair hiring - what's known, what helps](../../Guides/Unfair%20hiring%20-%20what's%20known,%20what%20helps.md) -
  name, age, breaks, records, AI screening: what helps, w/ strength of its evidence.
- [Keep your chats out of AI training](../../Guides/Keep%20your%20chats%20out%20of%20AI%20training.md) -
  the switch on each AI account, what it doesn't cover.

**AI assistant + contributors** - measured facts + evidence behind the code. Read the area's doc
before changing it: each records what was measured and rejected, so a retired rule stays retired.

| Area | Doc | What it holds |
|---|---|---|
| Resume | [resume/bullets.md](resume/bullets.md) | What a line has to do: accuracy > substance > relevance > clarity, every wording rule w/ basis, lint enforces vs reports, advice that did not survive |
| Resume | [resume/page-format.md](resume/page-format.md) | Page hygiene gates (black text, whole words, even heading spacing), headline, summary length, format advice declined |
| Resume | [resume/cover-letter.md](resume/cover-letter.md) | Cover letter: when it's offered, the user's own sentence, what the check holds a draft to, basis graded |
| Resume | [resume/typeface.md](resume/typeface.md) | Why Caladea, how widths are measured, adding a font + its cost |
| Resume | [resume/fair-screening.md](resume/fair-screening.md) | Name, age, work-break, record + AI-screening bias: evidence graded by strength, laws as of 2026-09, what the program carries, advice we don't follow, unverified list |
| Install | [desktop-icon.md](desktop-icon.md) | Desktop icon: brand files + how they're made, Mac applet edits, why the Dock still shows VS Code |
| Jobs | [jobs/freehire.md](jobs/freehire.md) | Job API: filters, facets, measured pitfalls - read before touching search or ingest |
| Jobs | [jobs/job-folders.md](jobs/job-folders.md) | My Jobs layout: stage folders by status, `N - Company - Title` names, when folders move, rename-only rules |
| Jobs | [jobs/best-next.md](jobs/best-next.md) | "Best to apply next" order: Today, chat brief, email - each factor, weight, basis |
| Jobs | [jobs/pay-filter.md](jobs/pay-filter.md) | Jobs under their lowest pay hidden on every list; closest back in a thin week |
| Applying | [apply/apply-systems.md](apply/apply-systems.md) | How application filling works, systems supported, adding one |
| Applying | [apply/workday.md](apply/workday.md) | Workday forms, filled through the Chrome extension |
| Applying | [apply/ashby.md](apply/ashby.md) | Ashby forms, filled in Job Finder's own Chrome |
| Applying | [apply/greenhouse.md](apply/greenhouse.md) | Greenhouse forms, filled in Job Finder's own Chrome; resume goes out as soon as chosen |
| Applying | [apply/vscode-browser.md](apply/vscode-browser.md) | Filling a form inside the Job Finder window's own tab - two routes measured (local form + one Greenhouse posting), costs, recommendation |
| Applying | [apply/ukg.md](apply/ukg.md) | UKG Pro Recruiting forms: sign-in first, resume sections saved as added |
| Applying | [apply/lever.md](apply/lever.md) | Lever forms, filled in Job Finder's own Chrome; resume goes out as soon as chosen (Lever reads it to fill the form) |
| Applying | [apply/workable.md](apply/workable.md) | Workable forms, filled in Job Finder's own Chrome; resume goes out as soon as chosen |
| Applying | [apply/smartrecruiters.md](apply/smartrecruiters.md) | SmartRecruiters forms - being measured (plan-6oq), nothing filled yet |
| Applying | [apply/jazzhr.md](apply/jazzhr.md) | JazzHR forms (`<co>.applytojob.com`): form read off the posting page, widgets, what leaves when |
| Applying | [apply/bamboohr.md](apply/bamboohr.md) | BambooHR forms (`<co>.bamboohr.com/careers/<id>`): form definition over HTTP, widgets, what leaves when (resume on choosing it) |
| Applying | [apply/paylocity.md](apply/paylocity.md) | Paylocity forms - being measured (plan-6oq), nothing filled yet |
| Applying | [apply/dayforce.md](apply/dayforce.md) | Dayforce forms - being measured (plan-6oq), nothing filled yet |
| Applying | [apply/paycom.md](apply/paycom.md) | Paycom forms - being measured (plan-6oq), nothing filled yet |
| Applying | [apply/adp.md](apply/adp.md) | ADP Workforce Now forms - being measured (plan-6oq), nothing filled yet |
| Applying | [apply/oracle.md](apply/oracle.md) | Oracle Recruiting Cloud forms - start box measured + filled, pages after it unmeasured |
| Applying | [apply/icims.md](apply/icims.md) | iCIMS forms - start box measured + filled, pages after it unmeasured |
| Applying | [apply/sent.md](apply/sent.md) | Was it sent? Sent page + applied list per system, browser-history check, what it can't see |
| Applying | [apply/answers.md](apply/answers.md) | What an application asks, read ahead when a resume is made; answers drafted + pasted for systems w/o a filler; questions never drafted |
| Applying | [apply/interview.md](apply/interview.md) | Interview practice + debrief: what each rule rests on, how a stated fact reaches the resume, declined |
| Applying | [apply/follow-up.md](apply/follow-up.md) | When a quiet job is suggested for a follow-up (days per stage + basis), one nudge per silence, what the draft says and never says |
| App window | [app-window.md](app-window.md) | VS Code window the Desktop icon opens: phase 1 look, pages, Today links + chips, quiet settings; phase 2 own profile + extension (`app/vscode`: start page, Today dashboard, buttons that fill the chat, never send) - what + why, measured, owner checks open, rejected |
| Site | [site.md](site.md) | Install site in `docs/`: generated files + `app/web/assets.py`, look, rules (no third-party requests, scam-safe install line, robots, JSON-LD, share image), measured hosting facts |
| Site | [research.md](research.md) | Research articles: sourcing order, evidence labels (plain scale -> registry), citations, 3-step review + publication gate, style, search rules, laws, privacy, re-check + corrections |

Testing the window: tests can't reach the real VS Code, Claude settings or Desktop icon (guard in
`app/tests/conftest.py`). Live look = `uv run python app/tests/demo.py` (placeholder jobs in this
checkout) + `JOBS_VSCODE_DIR=<scratch dir> uv run app/jobs.py launch` - a separate VS Code w/ its own
data + extensions there, Claude trust + Desktop icon too (`launch.vscode_paths()`). Quit it after.

Assistant instructions: [AGENTS.md](../../AGENTS.md) + skills in [../skills/](../skills/).
Contributing: [.github/CONTRIBUTING.md](../../.github/CONTRIBUTING.md).
