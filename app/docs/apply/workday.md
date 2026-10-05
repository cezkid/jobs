# Workday application forms - measured facts

Workday = careers site for thousands of employers (`<company>.wd<N>.myworkdayjobs.com`). Widgets
are Workday's, shared by every tenant; *lists* inside them (degrees, fields of study, skills,
language levels) are each employer's. `app/apply/workday.js` finds every field by visible label,
never id -> one filler, every tenant. Each fact names its tenant by letter, never the employer
(public repo; a name shows where the user applied). Add yours as a new line; never rewrite one.

## Widgets (all tenants)

| Widget | Behaviour | Filler rule |
|---|---|---|
| Text box, text area | value kept only once focus leaves; set w/o focus-out shows filled but **Save and Continue** reports "required" (tenant A, 2026-09) | `put` = focusin + value + input event; `out` = blur + focusout |
| Date (From / To) | two boxes, `dateSectionMonth-input` + `dateSectionYear-input`; month shows w/o leading zero | set each box, typed digits as fallback |
| Menu (Degree) | button opens `[role=listbox]` popup; options in tenant's wording ("B.A. - Bachelor of Arts") | match inside listbox options only - never stray `promptOption` pills |
| Search-and-pick (Field of Study, Skills) | type + Enter -> `promptOption` popup; picks become `selectedItem` pills w/ `DELETE_charm` | exclude options inside the field's own pills; remove w/ `DELETE_charm`. Enter must never move the form on (a Save nobody clicked): address, active step or the field itself changing after Enter stops the whole fill w/ a FAIL - safe on tenant A, unmeasured elsewhere |
| Repeating sections (Work Experience, Education) | "Add" when empty, "Add Another" after | click last matching button in section, wait for new entry |
| Page in a hidden window | `setTimeout` throttled to ~once a minute; screenshots black | wait w/ `MessageChannel`, read state w/ `status()` not screenshots |
| Extension tool call | times out at 45s | fill runs in background; poll `window.__jf.status()` |
| Re-render after a fill | can clear an answer that showed when filled (modelled in `test_apply_workday_js.py`; not yet seen live) | `verify()` at the end of the same background run: 2.5 s settle (MessageChannel sleep), every filled box read again - text, month/year, Degree shown text, "I currently work here". Dropped -> refilled once (`put` + `out`; checkbox and menu compare before clicking), still dropped -> FAIL "answer dropped". Skills + Field of Study pills never refilled (`pick` presses Enter - could move the step) -> ASK. Limit: `put` sets the value through the native setter, so a box can show a value Workday did not keep; verify catches values a re-render cleared, not every unkept one (2026-10-05) |
| cxs API URL (`/wday/cxs/.../jobapplication/...`) opened directly | `HTTP_400 "You are not authorized to this job application"` | not a page - ignore; real session expiry shows same text on Save -> sign out and in |

## Tenant lists

| Tenant | Field | Measured |
|---|---|---|
| tenant A | Degree | H.S., A. - Associate's degree, B. - Bachelor's degree, B.A., B.S., B.F.A., M., M.B.A., M.F.A., J.D., Ph.D., Professional Doctorate, Certificate, Non Degree Seeking. No "Associate of Arts" -> generic entry (`DEGREE_FAMILY`) |
| tenant A | Languages | no Languages section; "Languages & Skills" box takes `English - Conversational` / `English - Fluent` only. Native -> Fluent, never Conversational (first run picked Conversational: understated a native speaker) |
| tenant A | Field of Study | niche program name ("<X> Media Technology") absent; nearest a broad media field -> ASK, user confirms |
| tenant A | Skills | every resume skill name accepted as written (54/54) |

## Closed posting

Checked on the posting page, before Apply + sign-in: `window.__jf.closed()` (send `workday.js` + that
call in one tool call; awaits up to 10 s). Closed only when no Apply button (`adventureButton`) shows
AND the page says so (`CLOSED` in `workday.js`). Page is blank at load, drawn seconds later - read
before that, it is neither (`apply-form measure` read 0 words, 0 buttons on both kinds: it reads too
early for Workday). Measured 2026-10-05, posting link GET only, cookie notice left alone:

| Tenant | Job search said | Apply button | Page says | `closed()` on its saved page |
|---|---|---|---|---|
| tenant B | closed | none | "The page you are looking for doesn't exist." (`errorContainer` > `errorMessage`, Search for Jobs button) | true |
| tenant C | closed | none | same words; cookie notice above | true |
| tenant D | open | `adventureButton` "Apply" under the title | posting | false |
| tenant E | open | same; cookie notice above | posting | false |
| tenant F | open | none | same "doesn't exist" words | no saved page; the job search's open is not the page's |

Same words + hooks on every closed page seen; another wording -> false (not closed), the AI reads
the page. Wording from other systems (`form.CLOSED`) also in the pattern, unmeasured on Workday.
Saved pages (anonymised): `app/tests/fixtures/workday/posting-*.html`.

## Resume upload

Resume/CV box on My Experience: the extension's file upload puts the PDF in its file input, then
`window.__jf.uploaded("<file name>")` polls (MessageChannel sleep, up to 20 s) the box only = smallest
block holding a file input + a "Resume" / "CV" heading or label (Cover Letter box, errors on other
fields not read). Returns `ok` (file name shows in the box), the box's `errorMessage` text (an error
wins, also one appearing within 1 s after the name), `not confirmed` (neither), or `no Resume/CV box
on this page`. Modelled only (`fixtures/workday/upload.html`, 2026-10-05): live widget markup,
wording + whether Workday sends the file on choosing unmeasured (no account) - recorded on the
next real application (plan-nko.22); until then the privacy table has no Workday upload row.

## Fixtures

`window.__jf.snapshot()` (send `workday.js` + that call in one tool call): read-only picture of the
step shown - per shown field its label, kind (text, textarea, date, checkbox, checkboxes, radio,
select, menu, search-pick, file), `formField-*` hook + its controls' hooks, required mark (`*` or
required attribute), option list (radio, checkbox, select; a menu's options only while its listbox
is open); headings, buttons outside fields, active step. Never an answer: no value, checked state,
picked pill, menu's shown choice; search-popup options left out (they echo what was typed). Save
what it returns to a file, then `uv run app/jobs.py apply-form workday-fixture <file>`: drops the
page block (host, title, site name), names from it (site name, "at X" in the title, the host's
tenant part) -> `.data/measure/tenants.txt` + "Acme" everywhere in the fixture, an email or phone
number anywhere refuses the file, writes `app/tests/fixtures/workday/<step>.json`. Run the
anonymity grep before committing one. Modelled on `form.html` only (2026-10-05): kind detection on
live widgets (date, search-pick, radio groups) unmeasured - first real run: plan-nko.22.

## Resume autofill ("Autofill with Resume")

Workday parses the uploaded PDF once, at start. Tenant A, before education fix (PR #18): school
= whole "Field | School" line, Degree blank, Skills blank; jobs got title, company, dates, but
location lost its comma ("City ST"), role description kept PDF line wraps + subline. Filler
overwrites all of it.
