# Application systems - how Job Finder fills them, and how to add one

Employers take applications through a handful of hiring systems. Each one lays its form out its
own way, but the questions are much the same: contact details, resume upload, work permit,
a few of the employer's own. Job Finder keeps what is shared in one place and puts each system's
quirks in a small plug-in of its own.

| System | Link looks like | Route | Facts |
|---|---|---|---|
| Workday | `<co>.wd<N>.myworkdayjobs.com` | `apply` script, run by the Claude Chrome extension (sign-in wall, multi-page) | `workday.md` |
| Ashby | `jobs.ashbyhq.com/<co>/<id>` | `apply-form`, Job Finder's own Chrome | `ashby.md` |

Not yet: Greenhouse (`boards.greenhouse.io`, `job-boards.greenhouse.io`), Lever (`jobs.lever.co`),
SmartRecruiters, iCIMS, Workable. `apply-form prepare` on one of these says so plainly. The user
then gets the tailored PDF plus answers to paste.

## The pieces (`app/apply/`)

| File | Job | Changes when a system is added? |
|---|---|---|
| `questions.py` | shared question shape (`KINDS`, `KEYS`), answers from resume + setup, answers file | only if the system asks something no kind covers |
| `browser.py` | Job Finder's Chrome (own profile in `.data/`, no automation flag), reused across applications | no |
| `form.py` | the `apply-form prepare / fill` steps, report, never Submit | no |
| `systems/__init__.py` | picks the system from the link | one line: add to `SYSTEMS` |
| `systems/<name>.py` | read the form's questions; type an answer into its widgets | new file |

## Add a system

1. **Measure first.** Open a live posting. Find where the form's questions come from: a public
   job-board API (Ashby, Greenhouse and Lever have one), or else reading the page. Find the steady
   hook on each question box. Never rely on generated class names like `_active_1svni_57`: they
   change with each release.
2. **Write `systems/<name>.py`** with the contract in `systems/__init__.py`:
   `NAME`, `READY`, `matches`, `application_url`, `questions`, `fill`, `ids_on_page`. Map every
   native type to one of `questions.KINDS`, and native system fields to `questions.KEYS`. Unknown
   types become `text`, keeping the native name in `native`.
3. **`fill` checks what took.** Read the value or selected state back after typing, and return
   `ok`, `ASK <why>` (nearest choice, or nothing matched) or `FAIL <why>`. Never click Submit,
   Next or Save.
4. **Register** it in `SYSTEMS`. The contract test fails until you do.
5. **Tests:** turn a saved (anonymised) form definition into questions; link matching.
6. **`docs/<name>.md`:** widgets table + tenant notes, as `ashby.md` does. Add a row to the
   table above, and to the `AGENTS.md` privacy table if the system sees something new.

## Browser (every system)

Chrome starts as a normal window on Job Finder's own profile (`.data/apply-browser`), with a
fixed debugging port Job Finder picks and records (`job-finder-port` in the profile). The filler
attaches, fills, and disconnects; the window stays open. Measured 2026-09, Chrome 154, reading
`navigator.webdriver` (what an employer's spam check sees at Submit):

| Launch | webdriver |
|---|---|
| `--remote-debugging-port=<fixed>`, tab opened by Chrome (command line or `/json/new`) | `false` - used |
| `--remote-debugging-port=0` | `true` on every page, before any attach |
| tab opened by Playwright (`new_page`) | `true` |
| Playwright `launch()` (adds `--enable-automation`) | `true` + banner |

A second application reuses the open window: new tab via `/json/new`. Starting another Chrome on
the same profile would only hand the link to the first one, with no port to attach to.

## Shared rules (every system)

- Resume answers only what it states outright: name, email, phone, links. Location is asked.
- Work-permit yes/no comes from setup, only for the same US question, and is named to the user.
- Everything else is asked, with clickable choices where the form gives options.
- Upload the resume only after the user said yes to that named file. Upload it first, so no
  re-parse can overwrite typed answers.
- Questions on the page but not in the answers file (voluntary disclosures) are counted and
  left for the user.
