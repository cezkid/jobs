# Dover application forms - measured facts

Filled by `app/apply/systems/dover.py`: questions from the posting's form definition (plain HTTP),
answers typed into its page in Job Finder's own Chrome, read back off the page.

Dover = recruiting system for small companies; every employer's form on one host:
`app.dover.com/apply/<employer>/<job uuid>`, posting text and form on the same page. React page
(MUI boxes, react-final-form, react-dropzone), Cloudflare Turnstile, PostHog + Google Analytics.
Tenant named by letter, never employer.

Measured 2026-10-26: the form definition of every Dover link freehire lists (`source=dover`, 150
links -> 120 forms, 43 employers; plain GET 2 s apart, 0 429, 1 read timed out); 1 posting through
`apply-form measure` (2 loads, canary ok: 0 received, 9 blocked); `apply-form try` on 3 postings, 3
tenants (A: radios + long boxes, B: 18 questions incl. a tick-box list, C: phone hidden, resume
optional), + 3 blocked probes (resume block markup; what PostHog's posts carry); the page's own
script read (source maps are public). Page loads on the host: 15, at most 5 per employer. Raw notes
+ saved definitions: `.data/measure/` (private, not shipped).

## Links

| Link | Answer |
|---|---|
| `/apply/<employer>/<uuid>` (freehire adds `?utm_source=freehire.me`, Adzuna `?utm_source=adzuna&utm_medium=adzuna`) | the page: posting, then the form (150 of 150 freehire links this shape) |
| employer part | any case (capitals seen on 1 tenant); the page reads the job by uuid only |
| `/<employer>/careers/<client uuid>` | the employer's job list - no form, not matched |
| unknown uuid | definition 404 `{"detail": "Not found."}`; page: "Hmm... we couldn't find the job posting you're looking for. It may have been filled or deactivated." (page script) |

A real closed posting: unmeasured - freehire's search never lists one. `closed()`: 404 -> "may have
been filled or deactivated"; `active: false` -> no longer active (0 of 120 seen); other -> can't tell.

## Form definition

`GET https://app.dover.com/api/v1/inbound/application-portal-job/<uuid>` - JSON, public, no key (120
of 120; the page itself fetches it). Top: `client_name`, `title`, `require_linkedin_profile_url` (0 of
120 true), `allow_docx_resumes_in_applications` (15 of 120), `is_notifiable_source` (0), `active`
(120), `application_questions: [{id, question, input_type, question_type, required, hidden,
multiple_choice_options, max_selections, order_index}]` (3-17 per form, 527 in all).

| question_type / input_type | Seen (120 forms) | Filler rule |
|---|---|---|
| LINKEDIN_URL / SHORT_ANSWER | 120: 49 required, 1 hidden | url, key linkedin, box `linkedinUrl`; required also when `require_linkedin_profile_url` |
| PHONE_NUMBER / SHORT_ANSWER | 120: 55 required, 3 hidden | phone, box `phoneNumber` |
| RESUME / FILE_UPLOAD | 120: 89 required, 31 optional, 0 hidden | file, key resume, title "Resume" |
| CUSTOM / MULTIPLE_CHOICE | 53 (52 required): 38 Yes / No, 3 Yes / No / Willing to Learn, the rest lists (notice, level, US states, how you heard) | choice; Yes + No only -> yesno; radios |
| CUSTOM / SHORT_ANSWER | 69 (46 required) | text (link / name titles keyed) |
| CUSTOM / LONG_ANSWER | 44 (35 required) | longtext |
| CUSTOM / MULTIPLE_SELECT | 1 (required), `max_selections` none | multichoice; tick boxes |
| hidden | 4, Dover's own questions only | never asked - the page draws no box (tenant C's phone: no box, measured) |
| `order_index` | null on the resume question (120 of 120) | page order: First, Last, Email, then by order_index, Resume at the foot |

Fixed boxes on every form, not in the definition: First Name *, Last Name *, Email * (page script, 3
of 3). A list with no options draws nothing (page script) - left out.

## Widgets (3 tenants, 2026-10-26)

| Box | On the page | Filler rule |
|---|---|---|
| contact | `input[name=firstName / lastName / email / linkedinUrl / phoneNumber]`, ids `:r2:` ... made by React | find by `name`, never id |
| employer question | `name` = the question's id (text box or textarea; MUI adds an unnamed hidden copy of each textarea) | find by `name` |
| labels | a plain `div` above each box ("First Name *"), never tied to it | titles from the definition |
| multiple choice | MUI radios, `name` = question id, `value` = the option's words | tick by value |
| multiple select | MUI tick boxes, no name, each in a `label` with the option's words, under the question's words ("... *") | found under the question's words; tick + untick to match |
| resume | hidden `input[type=file]` (accept `.pdf`, or `.pdf,.docx`), no name, in a "Drag and drop file or browse computer" block, "(PDF, 5 MB maximum)" | the file box NOT in the autofill block |
| resume chosen | the block turns into "Resume: <name>" (names over 35 letters cut + "...pdf") + a Remove button (`aria-label="Remove"`); the upload box is gone until Remove | read back by the words; a different file there -> Remove, then choose |
| Autofill from resume | a second hidden file box above the form, "Drag & drop or upload to autofill your application" | **never touched**: it sends the resume's text to Dover to be read (below) |
| Cloudflare check | Turnstile widget above Apply, closed shadow root; its hidden `cf-turnstile-response` box | the applicant's own; never read as a question |
| notify me | "Notify me by email when my application is viewed" tick, `notifyOnView` (0 of 120 forms) | the applicant's own choice |
| Apply | the form's submit button - Dover's Submit | never clicked |

0 ids changed between loads (measure, 2 loads). Page checks before it sends (page script): first,
last, email required; email shape; LinkedIn must be a LinkedIn profile link; phone matches
`^[+]*[(]{0,1}[0-9]{1,3}[)]{0,1}[-\s./0-9]*$` - so "+1 (555) 010-0100" fails it. Filler types such a
phone as its digit groups ("+1 555 010 0100", same digits); one with letters or an extension -> ASK.

## What leaves the computer, when

On load (blocked logs, every load): Google Analytics `g/collect`, PostHog (`us.i.posthog.com`
flags, events, `/s/` session recording), Cloudflare Turnstile challenge posts.

While filling:

| What | Where | When |
|---|---|---|
| every box as typed (name, email, phone, answers) + the page's words, the resume's file name among them | PostHog, Dover's analytics company - session recording `/s/` | on its own timer, as you type, before Apply. Measured: synthetic first name, email and file name found in the blocked `/s/` posts (gzip, 1 tenant); Dover's PostHog settings (`config.js`, public): `maskAllInputs: false`, `sampleRate: null` - every visit, nothing masked |
| choosing the resume in the Resume box | nowhere | 0 requests on choosing (3 of 3 tenants): the page keeps the file until Apply |
| everything: contact, answers (as JSON), the resume file, the Turnstile token | that employer's Dover site | at Apply: one POST (page script `createApplicationPortalInboundApplication`; never clicked) |
| Autofill from resume (never used here) | Dover | on choosing a file there: the PDF's text read in the browser + sent to Dover's parser with a Turnstile token (a DOCX or scanned PDF: the file itself) - page script |

`RECORDED_BY` in the module: prepare tells the AI to say the PostHog part before fill. Privacy table
rows: "that employer's Dover site" (at Apply) and "PostHog, Dover's analytics company" (as typed).

Apply needs the Turnstile token (page: "Please complete the CAPTCHA verification."); blocked, the
check never passes - Submit is unmeasurable here by design.

## Read back

`dover.holds` (form.recheck) - what shows, never the answer given:

| Kind | Read back |
|---|---|
| box (contact, employer text) | its value; phone by digits |
| radios | the one ticked, by value = the answer |
| tick boxes | under the question's words, ticked exactly the answers |
| resume | "Resume: <something>" in the form |

Upload: page idle (15 s cap), file chosen, "Resume: <name>" -> ok; the page's own note ("Invalid file
type. Accepted file types: .pdf." - `.png` measured, tenant C) -> FAIL with Dover's words; neither in
5 s -> ASK. An empty PDF is taken (measured) - the resume is never empty.

## Try (2026-10-26)

`apply-form try`, synthetic answers, canary ok each (0 of 9 test writes through): tenant A 10 of 10
`ok` (required 10 of 10), tenant B 18 of 18 (incl. Yes / No radio + tick-box list), tenant C 6 of 6
(phone hidden: no box, none asked). 0 writes sent; blocked = analytics + Turnstile only. Tenant C
`--upload-errors`: `.png` -> FAIL in Dover's words; empty PDF -> ok; the resume after it (box gone,
"Resume: <empty file>" showing) -> Remove, then chosen -> ok.

## Outage seen

2026-10-26 12:10-12:23: Dover's `api/v1/users/auth_context` hung (no answer in 10 s, plain GET too)
and the page stayed blank - no form at all. `fill` then times out on READY; try again later. Other
endpoints (the definition) answered throughout.

## Not measured

Submit (never clicked; Turnstile blocked); a real closed posting; a hidden employer question (0 of
167); `max_selections` set (0); `is_notifiable_source` (0); the window route (`--in-window`) - Chrome
only.
