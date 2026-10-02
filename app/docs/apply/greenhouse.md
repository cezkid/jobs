# Greenhouse application forms - measured facts

Greenhouse = careers site for many tech employers (`job-boards.greenhouse.io/<company>/jobs/<id>`).
`app/apply/systems/greenhouse.py` reads questions from Greenhouse's public job board, types answers
into its widgets; shared steps (`apply-form`) in `apply-systems.md`. Tenant named by letter, never
employer; add yours as a new line.

## Form definition

`GET https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>?questions=true`, no key (EU:
`boards-api.eu.`). Only the listing id goes out - same as opening the posting.

| Part | Holds | Filler rule |
|---|---|---|
| `questions[]` | `label`, `required`, `fields[]` (`name`, `type`, `values[]`) - contact boxes, Resume/CV, Cover Letter, employer questions (`question_<n>`) | one question per entry, first non-hidden field; Resume/CV + Cover Letter list an upload and a paste box - the upload is the question |
| `location_questions[]` | Latitude, Longitude (hidden), Location | one Location (City) question, page id `candidate-location` |
| `demographic_questions.questions[]` | employer's own optional survey: `id`, `type`, `answer_options[]` | page id = the numeric id; `free_form` options (self-describe) are a separate box, left off |
| `compliance[]` (`eeoc`) | government self-ID: Gender, Race, Veteran Status (sometimes Disability) | choice questions, never required; Hispanic/Latino shows on the page but not here - added before Race |
| not listed | Country (phone dialing code) - required on the page | added after Phone |

Types: `input_text` -> text (email/phone by name), `textarea` -> longtext, `input_file` -> file,
`multi_value_single_select` -> choice (Yes/No only -> yesno), `multi_value_multi_select` ->
multichoice, `input_hidden` skipped.

## Widgets (tenant A, 2026-10-02)

| Box | On the page | Filler rule |
|---|---|---|
| every question | input whose `id` = field name (`first_name`, `question_<n>`, `1234501`) | find by id via `[id="..."]` - ids can start with a digit, `#1234...` is not a valid selector |
| text | `input.input__single-line` | focus, wait 400 ms, `fill`, read back, once more on mismatch. Signed in to MyGreenhouse in that Chrome, first focus on First/Last Name drops the saved name in a moment later: typed at once, the two ran together ("JaneAda") |
| choice / yesno / multichoice / Country | react-select: `input[role=combobox]`, list `.select__menu [role=option]` | type, click option w/ exact text - never the first offered; nothing matches -> clear + ASK. Read back from `single-value` / `multi-value__label`. Always scope to `.select__menu`: the phone box's own hidden country list is also `[role=option]` |
| Country | options read "United States +1"; chosen it shows flag + "+1" only | match w/o the code, read back the code |
| Location (City) | combobox `candidate-location`, places after typing (e.g. "Springfield, Illinois, United States") | type city only, pick option starting w/ the full answer |
| Resume/CV, Cover Letter | hidden `input[type=file]#resume` / `#cover_letter`; after upload `[aria-labelledby=upload-label-<id>] .file-upload__filename` shows the file name | upload first, confirm by name |
| Race | shown only after Hispanic/Latino = No | not shown -> skipped |
| Education (School, Degree ...) | `school--0` ...; optional; not in the job board's list | left alone; MyGreenhouse may fill it |

`navigator.webdriver` false in Job Finder's Chrome (2026-10-02). Submit button `button[type=submit]` -
never clicked. After Submit the address ends `/confirmation`.

## Tenant notes

| Tenant | Measured |
|---|---|
| tenant A | EEOC + own demographic survey both on one form - two separate sets of voluntary questions |
