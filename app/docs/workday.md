# Workday application forms - measured facts

Workday runs the careers site for thousands of employers (`<company>.wd<N>.myworkdayjobs.com`).
The form widgets are Workday's own and shared by every tenant; the *lists* inside them (degrees,
fields of study, skills, language levels) are each employer's. `app/apply/workday.js` finds every
field by its visible label, never by id, so one filler serves every tenant. Each fact below names
the tenant it was measured on (a letter, never the employer: the repo is public and a name would
show where the user applied); add yours as a new line, never rewrite an old one.

## Widgets (all tenants)

| Widget | Behaviour | Filler rule |
|---|---|---|
| Text box, text area | value is kept only once focus leaves the field; set without a focus-out shows filled but **Save and Continue** reports "required" (tenant A, 2026-09) | `put` = focusin + value + input event; `out` = blur + focusout |
| Date (From / To) | two boxes, `dateSectionMonth-input` + `dateSectionYear-input`; month shows without the leading zero | set each box, typed digits as fallback |
| Menu (Degree) | button opens a `[role=listbox]` popup; options carry the tenant's own wording ("B.A. - Bachelor of Arts") | match inside listbox options only - never stray `promptOption` pills |
| Search-and-pick (Field of Study, Skills) | type + Enter -> `promptOption` popup; picked items become `selectedItem` pills with a `DELETE_charm` | exclude options inside the field's own pills; remove with `DELETE_charm` |
| Repeating sections (Work Experience, Education) | "Add" when empty, "Add Another" after | click the last matching button in the section, wait for the new entry |
| Page in a hidden window | `setTimeout` throttled to about once a minute; screenshots come back black | wait with `MessageChannel`, read state with `status()` not screenshots |
| Extension tool call | times out at 45s | fill runs in background; poll `window.__jf.status()` |
| cxs API URL (`/wday/cxs/.../jobapplication/...`) opened directly | `HTTP_400 "You are not authorized to this job application"` | not a page - ignore; a real session expiry shows the same text on Save -> sign out and in |

## Tenant lists

| Tenant | Field | Measured |
|---|---|---|
| tenant A | Degree | H.S., A. - Associate's degree, B. - Bachelor's degree, B.A., B.S., B.F.A., M., M.B.A., M.F.A., J.D., Ph.D., Professional Doctorate, Certificate, Non Degree Seeking. No "Associate of Arts" -> generic entry (`DEGREE_FAMILY`) |
| tenant A | Languages | no Languages section; "Languages & Skills" box takes `English - Conversational` / `English - Fluent` only. Native -> Fluent, never Conversational (first run picked Conversational: understated a native speaker) |
| tenant A | Field of Study | a program named for a niche ("<X> Media Technology") absent; nearest was a broad media field -> reported ASK, user confirms |
| tenant A | Skills | every resume skill name was accepted as written (54/54) |

## Resume autofill ("Autofill with Resume")

Workday parses the uploaded PDF once, at the start. Measured on tenant A before the education
fix (PR #18): school = the whole "Field | School" line, Degree blank, Skills blank; jobs came
through with title, company, dates, but location lost its comma ("City ST") and the role
description kept the PDF's line wraps plus the subline. Our filler overwrites all of it.
