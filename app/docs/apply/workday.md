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
| Search-and-pick (Field of Study, Skills) | type + Enter -> `promptOption` popup; picks become `selectedItem` pills w/ `DELETE_charm` | exclude options inside the field's own pills; remove w/ `DELETE_charm` |
| Repeating sections (Work Experience, Education) | "Add" when empty, "Add Another" after | click last matching button in section, wait for new entry |
| Page in a hidden window | `setTimeout` throttled to ~once a minute; screenshots black | wait w/ `MessageChannel`, read state w/ `status()` not screenshots |
| Extension tool call | times out at 45s | fill runs in background; poll `window.__jf.status()` |
| cxs API URL (`/wday/cxs/.../jobapplication/...`) opened directly | `HTTP_400 "You are not authorized to this job application"` | not a page - ignore; real session expiry shows same text on Save -> sign out and in |

## Tenant lists

| Tenant | Field | Measured |
|---|---|---|
| tenant A | Degree | H.S., A. - Associate's degree, B. - Bachelor's degree, B.A., B.S., B.F.A., M., M.B.A., M.F.A., J.D., Ph.D., Professional Doctorate, Certificate, Non Degree Seeking. No "Associate of Arts" -> generic entry (`DEGREE_FAMILY`) |
| tenant A | Languages | no Languages section; "Languages & Skills" box takes `English - Conversational` / `English - Fluent` only. Native -> Fluent, never Conversational (first run picked Conversational: understated a native speaker) |
| tenant A | Field of Study | niche program name ("<X> Media Technology") absent; nearest a broad media field -> ASK, user confirms |
| tenant A | Skills | every resume skill name accepted as written (54/54) |

## Resume autofill ("Autofill with Resume")

Workday parses the uploaded PDF once, at start. Tenant A, before education fix (PR #18): school
= whole "Field | School" line, Degree blank, Skills blank; jobs got title, company, dates, but
location lost its comma ("City ST"), role description kept PDF line wraps + subline. Filler
overwrites all of it.
