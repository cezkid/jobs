# Application systems - how Job Finder fills them, and how to add one

Each hiring system lays its form out its own way; questions are much the same (contact, resume
upload, work permit, a few employer ones). Shared logic in one place, each system's quirks in a
small plug-in.

| System | Link looks like | Route | Facts |
|---|---|---|---|
| Workday | `<co>.wd<N>.myworkdayjobs.com` | `apply` script, run by the Claude Chrome extension (sign-in wall, multi-page) | `workday.md` |
| Ashby | `jobs.ashbyhq.com/<co>/<id>` | `apply-form`, Job Finder's own Chrome | `ashby.md` |

Not yet: Greenhouse (`boards.greenhouse.io`, `job-boards.greenhouse.io`), Lever (`jobs.lever.co`),
SmartRecruiters, iCIMS, Workable. `apply-form prepare` says so plainly -> user gets tailored PDF
+ answers to paste.

## The pieces (`app/apply/`)

| File | Job | Changes when a system is added? |
|---|---|---|
| `questions.py` | shared question shape (`KINDS`, `KEYS`), answers from resume + setup, answers file | only if the system asks something no kind covers |
| `browser.py` | Job Finder's Chrome (own profile in `.data/`, no automation flag), reused across applications | no |
| `form.py` | the `apply-form prepare / fill` steps, report, never Submit | no |
| `systems/__init__.py` | picks the system from the link | one line: add to `SYSTEMS` |
| `systems/<name>.py` | read the form's questions; type an answer into its widgets | new file |

## Add a system

1. **Measure first.** Live posting. Where questions come from: public job-board API (Ashby,
   Greenhouse, Lever have one), else read the page. Find the steady hook on each question box -
   never generated class names like `_active_1svni_57` (change each release).
2. **Write `systems/<name>.py`** per contract in `systems/__init__.py`: `NAME`, `READY`,
   `matches`, `application_url`, `questions`, `fill`, `ids_on_page`. Native types ->
   `questions.KINDS`, native system fields -> `questions.KEYS`. Unknown types -> `text`, native
   name kept in `native`.
3. **`fill` checks what took.** Read value / selected state back after typing; return `ok`,
   `ASK <why>` (nearest choice, or nothing matched) or `FAIL <why>`. Never click Submit, Next or
   Save.
4. **Register** in `SYSTEMS`. Contract test fails until you do.
5. **Tests:** saved (anonymised) form definition -> questions; link matching.
6. **`docs/<name>.md`:** widgets table + tenant notes, like `ashby.md`. Add a row to the table
   above, and to the `AGENTS.md` privacy table if the system sees something new.

## Browser (every system)

Chrome starts as a normal window on Job Finder's profile (`.data/apply-browser`), fixed debugging
port Job Finder picks + records (`job-finder-port` in the profile). Filler attaches, fills,
disconnects; window stays open. Measured 2026-09, Chrome 154, reading `navigator.webdriver` (what
an employer's spam check sees at Submit):

| Launch | webdriver |
|---|---|
| `--remote-debugging-port=<fixed>`, tab opened by Chrome (command line or `/json/new`) | `false` - used |
| `--remote-debugging-port=0` | `true` on every page, before any attach |
| tab opened by Playwright (`new_page`) | `true` |
| Playwright `launch()` (adds `--enable-automation`) | `true` + banner |

Second application reuses the open window: new tab via `/json/new`. Another Chrome on the same
profile would just hand the link to the first, no port to attach to.

## Shared rules (every system)

- Resume answers only what it states outright: name, email, phone, links. Location asked.
- Work-permit yes/no from setup, only for the same US question, named to the user.
- Everything else asked, clickable choices where the form gives options.
- Upload resume only after user said yes to that named file. Upload first -> no re-parse
  overwrites typed answers.
- Questions on page but not in answers file (voluntary disclosures): counted, left for user.
