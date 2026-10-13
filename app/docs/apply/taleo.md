# Oracle Taleo application forms - measured facts

Taleo career sections = the hiring system behind many large employers' careers sites
(`<tenant>.taleo.net/careersection/<section>/jobapply.ftl?job=<id>`; posting page `jobdetail.ftl`).
`app/apply/systems/taleo.py` reads each step off the user's signed-in tab, types answers into its
boxes, attaches the resume and makes work history + education match the resume; shared steps
(`apply-form`) in `apply-systems.md`. Tenant named by letter, never employer; add yours as a new line.

How measured: tenant A, one application, 2026-10-12 - every step read through the Claude Chrome
extension (labels, ids, option lists, what each click did) while the user applied and clicked every
Save and Continue and Submit themselves. Not `apply-form measure`: the steps exist only signed in.
No page saved; the test pages (`app/tests/fixtures/taleo/`) are rebuilt from those reads.
Unmeasured below = not seen, built to the nearest measured fact - the first real use checks it.

## Links (2026-10-12)

| Seen | Shape | Count |
|---|---|---|
| freehire `source` taleo, newest 50 US | `<tenant>.taleo.net/careersection/<section>/jobdetail.ftl?job=<id>&lang=en` | 50 of 50, 17 tenants |
| Tenant A's own careers site (freehire `source` radancy) | posting on the employer's domain; its Apply = `jobapply.ftl?job=<id>` on section `10000`; a second Apply on section `10020` for employees (`btn-internal-apply`) - never taken | 18 of the newest 50 US radancy rows |

The careers-site posting is found from the job list's link by `apply/careers_page.py` (below).
`application_url` = `jobapply.ftl` on the same section (jobdetail's Apply: unmeasured, Taleo's own
route shape).

## Before the steps: the applicant's own

1. `jobapply.ftl` opens **Privacy Agreement** (page title), a language list + the employer's
   personal-information policy to accept. Accepting = agreeing: the user's (job-apply hard limits).
2. Sign-in / new account: the user's (never typed). Not seen - the user was signed in already.

`read` stops on both with the step to tell the user; `prepare` again after.

## Steps (tenant A)

One page per step, tracker "1 Attachments, 2 About You, 3 Education and Experience, 4 Job Profile
Questions, 5 eSignature, 6 Review and Submit". Page title = step name (used as each question's
`page`). Buttons on each: Save and Continue, Save as Draft, Quit - never clicked by the program.
"Applying for: <title> (Job Number: <id>)" heads each step; `read` prints it - the steps after the
first share one address for every job (`/careersection/careersection/candidateacquisition/flow.jsf`),
so a second Taleo application open on the same site is told apart only by that line.

Pre-filled from the account: the user's 2022 application came back on every step (contact, work
history, schools, conflict-of-interest answers, a 2022 resume ticked as Resume / CV). Old, not wrong
on purpose - the filler makes it match today's resume.

### 1 Attachments

| What | On the page | Filler rule |
|---|---|---|
| File box | `input[type=file]` "Select the file to attach" + "Comments about the file" + an **Attach** button; the file goes up on Attach, the step reloads with it as a new row | after the user's yes: choose, click Attach (an upload, not a Save), wait up to 30 s for the new row |
| Files on the account | table: Relevant Files tick, Resume / CV tick, File Name, Date (`m/d/yy`: 11/10/22, 10/12/26), Delete. Tick ids `<block>:<n>:selectionid` (Relevant) and `<block>:<n>:resumeselectionid` (Resume / CV), `n` = row | new row ticked both; Resume / CV unticked on every other row; an older file **with the same name** (an earlier job's tailored resume - Job Finder names every one alike) unticked both. Other files still marked Relevant: named, never unticked for the user (a reference letter may be meant) |
| Limits | "Each file must not exceed 1024 kilobytes" above, "allocated limit of 2048 kilobytes" in the help - both on one page; "attach up to 5 documents" | the smaller size wins: over it -> FAIL before anything is sent. 5 on the account -> FAIL, the user deletes one (Delete is theirs) |

Ticks clicked by script took (Taleo read them at Save and Continue, review page showed the new file
alone). Whether Resume / CV ticks are one-of (radio-like): unmeasured - the filler unticks the rest itself.
A today-dated row with the same name = attached already: never twice.

### 2 About You

Labels by `label[for]`, each with Taleo's mark: ". Required" after the words (read as "First Name .
Required"). Selects' empty pick = "Select One..." / "Not Specified" (never an answer; a Yes / No
select is a yes/no question once it's left out).

| Box | Rule |
|---|---|
| Source Type (required select) | how you heard: saved answer; "Other" shows a required **Please Specify** text box (seen) - read again after, filled in the next `fill` |
| First / Middle / Last Name under "Please provide full legal name" | the words sit outside each label: read off the step, so these are `legal_first` / `legal_middle` / `legal_last` (`contact.legal_*`; none saved -> asked) |
| Primary Number (Home / Work / Cellular) + one box each, hint `xxx-xxx-xxxx` | plain text boxes: the resume phone goes in Cellular, typed in the hint's shape (Review showed it as digits) |
| Text-message opt-in, marketing-email opt-in (required selects) | consent: asked every time, never saved |
| Country, State/Province, Nearest Metropolitan Area/City (selects), Street (line 1), line 2, City, Zip | `home_address` in search settings (named to the user), else asked. Plain text boxes: known by their words (`CONTACT`) - no type or autocomplete on them |
| Email Address | resume |
| Employer's own questions (conflict of interest `[COI1A]` ... `[COI6B]`, `[LEGAL1-3]`) | Yes/No selects + "If this does not apply, type NA" boxes; codes in brackets stripped from the words. Asked |
| Work permit: "legally authorized to work in the country where the job is located without any restrictions", "now, or in the future, require sponsorship to work in the country where the job is located" | not the US question word for word ("country where the job is located") -> asked with choices, never filled from setup (job-apply hard limits) |
| A tick set ("Choose all applicable fields" - Deloitte / Baker Tilly / KPMG / None of the above) | no legend: its words are the smallest block around it (`TITLES`) |

### 3 Education and Experience

Entries in blocks, each box `label[for]`, order measured:
- school: Name of Educational Institution, Area of Study ("Limit answer to 50 characters"), Education
  Level (select: Bachelor's Degree, Associate's Degree/College Diploma ...), Education Level Completed?
- job: Current Job (tick), Employer, Job Title, Start Date Month + Year, End Date Month + Year
  (selects: Jan..Dec, years)
- licence: Licensure/Certification, Number/ID, Issuing Organization, Country, State/Province, Nearest
  Metropolitan Area/City, two Month + Year pairs - one empty block on the page

Add Education / Add Work Experience / Add Licensure/Certification + Remove ... per entry. **Add
reloads the step** (the script's own read was cut by the navigation); what was typed before stays;
the blank entry comes last. Seen: the account missing the current job and the two oldest, two end
dates off, a company spelled with a trailing "." for its "... LLC".

One question for the whole step (`taleo-history`, yes/no, said plainly: Taleo keeps it on the user's
account once they click Save and Continue). Yes ->
- jobs = `questions.form_roles` (same as the page, or all, as the user chose); each paired to an entry
  by company (legal endings and punctuation aside) + title, else the one left of that company, else a
  blank entry; employer, title, dates, Current Job set as the resume says them; missing ones added.
- an entry on the account that isn't on the resume: left as is, named (removing it is the user's).
- schools paired by name (bracketed short name aside: "Beta County College (BCC)"); Area of Study =
  the resume's field (over 50 characters -> asked, never cut), Education Level by `degree_option`,
  Completed = not still being earned. Name kept as the account spells it; new schools added - their
  other boxes, if a new entry has more than the measured four, named to check (unmeasured).
- licences on the resume: named for the user to add (fields unmeasured beyond their labels).
  The empty licence block: left; tenant A's Save and Continue took the step after it was removed by
  hand - whether it takes an empty one: unmeasured.

### 4 Job Profile Questions

Numbered questions "1. <words> (EDU05) . Required"; radios `...-q-<id>-<n>-qr`, a text answer
`...-<n>-qt` (textarea). No legend or label on the set: words from the block (`TITLES`), number and
code stripped. Seen: highest education, five "how many years" bands, sponsorship ("currently sponsored
or will you in the future require sponsorship ... visa status") - not the setup question word for word,
asked - and "desired minimum base salary and total compensation" (the user's: saved pay answer
offered, never filled). Whether the text box has a label of its own: unmeasured - read either way.

### 5 eSignature

Statement (drug test, at-will, application true and complete) + a **Full Name** box = the signature.
The user's: `read` names it, reads no question.

### 6 Review and Submit, then sent

Every step's answers, Edit per step; **Submit** = the user's. After: page "Process completed - Thank
you for your online job submission" (title "Careers at <employer>"), same flow address. `read` there
says it's sent: `status set <job> applied`.

## Careers-site postings (apply/careers_page.py)

freehire lists some employers under their own careers site (`source` radancy - Radancy's TalentBrew
sites). The posting's Apply anchors carry `data-selector-name="job-apply-link"` with the system's link
in `data-apply-url` and `href` (4 employers, 5 pages, 2026-10-12). `prepare` reads that page once
(a plain GET of the public posting - the employer's site sees a visit, nothing about the user) when
no system matches the link, and goes on with the system's link. Newest 50 US radancy rows, one page
per employer (12): Taleo 1, iCIMS 3, Workday 2 (its own route), 6 to systems not filled here. A gone
posting's page sent the visitor to the site's job search (`/search-jobs`, 1 of 1): said, nothing read.

## What leaves when

- Resume: to the employer when the program clicks Attach (after the user's yes) - before Submit; kept
  on their account there for later applications.
- Each step's boxes: on the user's Save and Continue - before Submit; kept on their account (tenant A's
  2022 answers came back).
- The careers-site posting page: a visit, when `prepare` looks up where its Apply leads.

## Not measured yet

Sign-in page, a jobdetail.ftl link's own Apply, a closed posting's Taleo page, other tenants' steps
(employers choose which steps and questions), a step's voluntary self-identification (tenant A asked
none), Remove buttons, a new school's other boxes.
