# Loxo application forms - measured facts

Loxo = recruiting firms' own applicant system (`app.loxo.co/job/<base64 id>`, also
`<firm>.app.loxo.co/job/<id>`). The site shows the recruiting firm; the posting text may name the
hiring company (tenant B: the posting named its client, Loxo showed the firm). Measured 2026-10-26:
6 postings, 5 firms (tenants A-E), each form page by one plain GET; `apply-form measure` on tenant
A (2 loads, canary ok, 9 of 9 blocked); `apply-form try` on 3 postings, 3 tenants (A, B, C). Tenant named by
letter, never firm. Saved forms: `app/tests/fixtures/loxo/tenant-<a-d>.html` (the `<form>` only,
firm -> Acme Recruiting, phone numbers -> 555, ids + tokens made up).

## Links

freehire `source` loxo: 50 of 50 newest US links `https://app.loxo.co/job/<id>?utm_source=freehire.me`,
11 firms (2026-10-26); one older link on `<firm>.app.loxo.co`. Id = base64 of `<agency number>-<16
letters + digits>` (`10994-...` -> `MTA5OTQt...`): 28 or 32 characters, `=` padding or none, never
`/` or `+` (6-bit groups of those characters can't reach 62 or 63). The posting page has two "Apply for
this job" links to `/job/<id>/form?source_type=app` - `application_url` opens that page directly.

Unknown id: 404, "Page not found" (posting + form page both, 2026-10-26). A posting Loxo took down:
unmeasured (none found on the list) - `questions` / `closed(url)` read 404 / 410 or a page with no
form as "may have closed", another status or no answer as "can't tell".

## Form definition

No JSON (measure: 0 JSON responses). Server-rendered in the form page: `<form
action="/job/<id>/finish?source_type=app" method="POST" enctype="multipart/form-data">`. Plain HTTP
GET, no browser - only the posting id goes out, same as opening the posting. One page, no Next
(6 of 6).

| Field (name) | Seen | Shared kind / key |
|---|---|---|
| `name` ("Your Full Name", placeholder only) | 6 of 6 | text `name` - one box, never split |
| `email`, `phone` (type text, placeholder only) | 6 of 6 | email, phone |
| `better-file-input name="resume_uploaded_file[]" required` | 6 of 6 | file `resume` (title from its hidden button "Upload Resume/CV") |
| `custom_question_<n>` - the firm's own questions inside `div.custom-questions` | 3 of 6, 1-8 per form | radio -> choice (Yes / No only -> yesno), checkboxes `custom_question_<n>[]` -> multichoice (Yes / No pair -> yesno), text -> text (LinkedIn -> `linkedin`), number -> number, textarea -> longtext |
| `contact_consent` checkbox, never required | 6 of 6 | yesno, `loxo:consent` - see Opt-in |
| hidden: `utf8`, `authenticity_token`, `source_type_id`, `resume_source_type_id`, `form_template_id` | 6 of 6 | skipped |

No required mark on name / email / phone (6 of 6) - read as not required, as the page shows; what
Loxo does at Submit without them: unmeasured. A firm question is required when a red asterisk
(`<span style="color:#F05854">*</span>`) sits beside its label or inside it, or its controls carry
`required`. Tenant C's checkboxes have the asterisk but no `required`: the page lets Submit go
without them (browser check only on `required`).

Questions seen: LinkedIn, work authorization, sponsorship (Yes / No and "Yes - Visa Transfer
Needed" options), based in a city, on site 4-5 days, years with a skill (number), a link + role
(textarea), why this role (textarea, optional), how you heard (8 checkboxes, optional), a text-message
consent question (tenant C: "have your consent to communicate with you via SMS text message", No /
Yes checkboxes, asterisk).

## Widgets (2026-10-26)

| Box | On the page | Filler rule |
|---|---|---|
| name / email / phone / text / number | plain `input`, found by `name` | `fill`, change event, read back (phone by digits) |
| textarea | `textarea[name]` | same |
| radio / checkbox question | inputs sharing `name` (`[]` on checkboxes), value = a number; the option's words are the text after each input up to its `<br>` | tick by those words, any case; untick the rest; read each tick back |
| Resume | `better-file-input` (custom element, `better_file_input.js`): OPEN shadow root with its own hidden `input[type=file]`, a chip per file (name + `button.fa-times-circle`), the "Upload File *" drop box. Its light-DOM children - `input.btn-file-upload` button, `input[type=file][name="resume_uploaded_file[]"].hidden`, hidden source id - are NOT slotted: nothing of them shows | see Resume box |
| Opt-in | `#contact-consent-box`, label "Yes, <firm> can contact me about job opportunities." + fine print: phone / TEXT messages, "texting STOP", privacy policy, Terms of Service | applicant's own tick, never ours (`questions.signs` on label + fine print); with `text_messages: false` left unticked silently (`texts_off`) |
| Submit | `input[type=submit]` "Apply" | never clicked |

### Resume box

The bug a user caught (2026-10-26): the file set on the light-DOM `input[type=file]` (CDP
`setFileInputFiles`, the Chrome extension's upload) - the box still said "Upload File", so it looked
unattached. Measured in a blocked throwaway Chrome (canary ok), tenant B:

| Step | Chips shown | Files a `new FormData(form)` holds under the box's name |
|---|---|---|
| page loaded | none | 0 |
| file set on the light-DOM input | none ("Upload File*") | 1 - it would go at Submit, unseen |
| light input emptied, file set on the shadow input (`put_file`) | 1, the file's name | 1 |
| `put_file` again | 1 (kept, not added twice) | 1 |

Why (script read 2026-10-26): the component is form-associated; on the form's `formdata` event it
appends the files of its own list (its React state, filled from the shadow input's `change`, which
then clears that input). The light input is a plain form control, so its file goes too. Both set =
the file sent twice (read, not sent live).

Filler: page idle (15 s cap), then the file set on `shadowRoot.querySelector('input[type=file]')`
(Playwright fires `input` + `change`), wait up to 5 s for the chip. Ok = chips are exactly [file
name] AND the FormData holds exactly [file name] (building a FormData sends nothing). Already that
-> ok, nothing added. Other chips -> ASK the user to remove them with their x. Chip shown but the
form would send more (a file in the hidden light input) -> ASK to reload the page and fill again.
No shadow root yet -> ASK to choose it in the Upload File box.

## What leaves the computer, when

Every write blocked + logged: `measure` (load, tenant A) and `try` (load, resume chosen, every box
typed / ticked) on tenants A, B, C.

| Step | Writes | Requests of any kind | Tenants |
|---|---|---|---|
| page load | 0 | page + its scripts (cloudfront) | 3 |
| resume chosen | 0 | 0 | 3 |
| typing, ticks | 0 | 0 | 3 |
| Submit | native multipart form POST to `/job/<id>/finish` - contact, answers, resume - once; never clicked, unmeasured live | - | - |

Earliest point anything the applicant typed or chose leaves: Submit, to the recruiting firm's Loxo
site. Privacy table row: "that employer's Loxo site".

## Sent page

After Submit: `/job/<id>/finish?source_type=app`, "Application submitted" (1 sent job, 2026-10-26).
`sent.py`: Loxo row; a visit is matched to the job by its base64 id - the address names no company.

## Read back

`holds(page, q)`: text / number / textarea by value (phone by digits); radios + checkboxes by each
input's own tick against the option words; the resume by one chip = the one file the form would send.

Covered by `app/tests/fixtures/dom/loxo-form.html` in real headless Chrome (a stand-in for
`better_file_input.js` with the same shadow root, chip, list + formdata behaviour): every widget,
the shadow-root upload, a file already in the hidden input, a second file, fill twice.

## Try (2026-10-26)

`apply-form try`, synthetic answers, canary ok each run, 0 writes, 0 requests while filling:
tenant A 12 of 12 ok (required 8 of 8), tenant B 8 of 8 ok (required 4 of 4), tenant C 4 of 4 ok
(required 1 of 2: its text-message consent question left for the applicant). Left on the page each
time: the opt-in box. Not measured: Submit, the server's own checks (missing contact, file type /
size), a taken-down posting, the Job Finder window (`--in-window` not offered).

## Tenant notes

| Tenant | Measured 2026-10-26 |
|---|---|
| tenant A | firm label host (`<firm>.app.loxo.co`); 8 questions: radios with 3 options, number in its label, 2 textareas |
| tenant B | 2 postings: one with no questions, one with LinkedIn + 2 Yes/No radios + how you heard (8 checkboxes) |
| tenant C | text-message consent as a required No / Yes checkbox pair (`class=hierarchy-box`) |
| tenant D, tenant E | contact + resume + opt-in only |
