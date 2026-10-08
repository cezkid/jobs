# Students - internships, new grad, part-time, F-1

What the program does for a college student, what each choice rests on, what was reviewed and
declined. Plan + adversarial review (student personas, engineering, evidence / law / privacy):
plan-0cw, 2026-10-07. User guide: `Guides/For students.md`.

## Who

A sophomore after a first internship (no jobs, class projects, one club role); a senior after 2
internships + a campus job, looking for a new-grad job; a student after a part-time job near
campus; an international student on F-1 (CPT for internships, OPT after); a master's student or an
adult finishing a degree after years of work; a community college student working 30 hours a week.

## Search + ranking

| Choice | Where | Basis |
|---|---|---|
| Internship or co-op is a type the setup offers, with live counts | `job-setup` #1 | Setup offered full time / part time / contract only |
| The title decides the type, one way | `rank.title_type`, `blocked`, `mismatches` | 87 of 300 real internships tagged full time, 17 part time (measured, `freehire.md` #Internships) - a blocked full_time hid them. Never hides by title ("Intern Program Manager") |
| Internship passes: `seniority=intern` + `employment_type=internship`, same tier | `job-setup` #2, `cfg.tier_order` (a tier once) | Either tag covers 199/200 "internship", 156/171 "summer analyst", 153/200 "co-op" titles; one alone misses up to a third (measured). Never a seniority filter for other searches |
| Internships only: an ordinary job the job search tags intern sorts lower ("title doesn't say internship") | `rank.mismatches`, `STUDENT_PROGRAM` | 117 of 442 intern-tagged business rows were ordinary jobs (Account Executive, Financial Analyst, a VP); 8 of a student's top 15 on Today; of the 117 only 2 SkillBridge postings (service members) called themselves internships. 16 student programmes titled w/o an intern word kept (Summer Analyst Program, Rotational Program, Fellowship, University New Hire) (2026-10-08). Never hidden |
| School town + hometown: two city tiers, school first; a hometown beside a big city offers it too | `job-setup` #1 | School in DC, home North Jersey: setup and the form asked one town. Home tier 2026-10-08: 49 of 54 internships NYC, 3 North Jersey |
| Entry level: a required line asking 3+ years sorts lower | `rank.asks_beyond`, `ENTRY_MAX_YEARS` | 749 of 990 rows stating years ask 3+ (measured); the threshold is convention (entry postings commonly ask 0-2) - shown, never hidden |
| Years read from the posting's lines, never the job search's tag | `knockout.years_asked`; `best.match` skips the tag on early-career titles | Tag read 10 on "Software Engineer - New Grad", 7 on "18+ years old" (measured) |
| School years aren't work years; "up to 2 years" asks no minimum | `knockout.STUDY`, `UP_TO` | "2 years of undergraduate study" read as experience; 0 other changed reads on 10,360 live lines |
| Graduation window vs theirs | `knockout.graduation_window`, `rank.student_graduation` | 92 of 616 student required lines carry one; 0 false on 11,719 others (measured, hand-checked). Read wide (a season spans its months) so only a clear miss is said. Their date only while studying or within 24 months, never `hide_year` (`fair-screening.md` #What the program does) |
| Hourly pay floor | `rank.parse_floor`, `salary_floor_unit` | Interns + part-time are paid by the hour (62 of 74 intern rows listing pay); NACE 2026: bachelor's interns averaged $23.35/hr (employer survey, 284 orgs) |
| Before tailoring: a window missed, a degree level not being studied for | `knockout.shortfalls` | Same report-only rule as years + degree: quoted, their call |

International business (and other majors that cut across fields) - measured 2026-10-08, US, posted in the
last 30 days: business internship passes (`business_analysis operations logistics finance sales marketing`,
either intern tag) catch 99 of 100 "marketing intern", 98 "sales intern", 74 of 78 "finance intern", 64 of 65
"procurement intern", 20 of 30 "supply chain intern" - but 0 of 157 "trade compliance" / "global trade" /
"import" / "export" titles (legal + management, no intern tag: entry jobs, not internships) and 17 of 87
rotational / leadership development programmes. A new-grad search adds a title pass for the one role they
want most (`job-setup` #2). Languages count toward match (`best.backed`).

## Resume

| Choice | Where | Basis |
|---|---|---|
| Degree in progress prints "Expected May 2027"; `expected: true` keeps it so past the date until they say | `render.graduation_label`, `schema.in_progress`, lint `expected-date-passed` | Hold: an unfinished degree never reads as held (degrees are checked - National Student Clearinghouse). A year alone = this year may be done, so only a later year is in progress |
| Education first while studying | `render.education_first` | Career centres + NACE (convention): a student leads with the degree. Counts only work before the degree began (a returning adult's 18 years still lead); `education_first` in their file wins |
| GPA as the transcript writes it, any scale, quoted | `schema.GPA`, `FOUR_POINT` | Hold: never higher than the transcript - cutoffs compare numbers and transcripts get checked; whether to round is a split convention (UIC Law allows normal rounding, others say never round up), so never. Never converted (9.2/10, %): asked |
| GPA note once to every student, same words | `feedback.GPA_NOTE` | NACE Job Outlook 2026: 42% of 183 employers screen by GPA (73% in 2019) - employer survey. A note aimed only at low GPAs would talk them out of their own choice |
| Relevant coursework on its own row, never a bullet, never evidence | `render.education_entry` note, `schema.MAX_COURSES` | A bullet counts as rewritable and would fail line-fill; a course title is no proof of a skill ask (review) |
| Clubs = projects with `role` + `section` | `render.page_model`, `schema.section_of` | Cheaper than a new section across ~17 files; same ids, tailoring, lint, resume-gaps |
| A group's name never changed on a tailored page | lint `employer-changed` on projects with a role; import + tailor task rules | Affinity items: their call (Kang 2016, field experiment - `fair-screening.md`); the program never decides it |
| Time in school is no work break | `schema.employment_gaps`, `closes_gap` | Two summer internships read as 9- and 13-month breaks. Only a start on file counts (never guessed); while it closes a gap the page shows the school's dates, or the reader sees a hole the program no longer flags |
| Summary leads with the degree being earned | tailor prompt | A campus or retail job title heading a marketing-internship resume (review) |
| Leadership asked about clubs when few jobs | `gaps.ACTIVITY_ASK` | Zero jobs = zero leadership questions before |
| Import: Expected / Class of / ranges, GPA, coursework, clubs whole | `import_pdf` | "Expected May 2027", "Class of 2027", "Aug 2023 - May 2027" all came back unparseable; GPA + coursework had no field; Leadership & Activities had no heading. Re-import doesn't report clubs or GPA lost (`carry.moved_to_projects`, `in_school_fields`) |

## Applying

| Choice | Where | Basis |
|---|---|---|
| "Authorized without restriction" asked every time for a visa holder | `questions.work_permit` | CMU + UCI international offices: No on F-1; H-1B is one employer. Setup's old OPT option saved Yes there - `check-settings` says ask once |
| F-1 setup answer `student_visa` | `defaults.yml`, `about.permit_lines`, rank sponsorship wording | CPT + OPT need no employer sponsorship (NCSU handout, CU Boulder): "no visa sponsorship" jobs say read the posting. Never sent to the job search (test) |
| Expected graduation, GPA, enrolled from the resume | `questions.student_answer` | The date is on the page; filled only when the box says expected and one degree is in progress. A bare "graduation date" stays sensitive (`fair-screening.md` #Age cues) |
| A student's status never kept | `answers.NEVER`, `NEVER_IN_ANSWER` | It changes: a kept "Yes, enrolled" would fill the next form after graduation |
| Ashby "Still Student?" not ticked by the filler | `job-apply` | Unmeasured: ticking may clear End date and fail the read-back - named at handover instead |

## Interviews

Practice for a student: `job-interview` #Formats, #Never during the real thing, #Students; basis +
sources `app/docs/apply/interview.md` (plan-ueh, 2026-10-08). `interview` prints `student:` when a
degree is in progress, so the student rounds apply. A Handshake or career-fair interview needs no
tailored resume: the pasted posting alone, or the resume + the role they name.

## AI plans

- Copilot Student: model picker removed 2026-03-13 (changelog), Auto only since 2026-06-24
  (changelog); upgrade to Copilot Pro keeps the rest of the Student Pack (GitHub staff, community
  discussion 189268). Untested here - Free's Auto failed 3 of 3 tailored resumes. Pro is trained on
  by default since 2026-04-24; Student isn't (GitHub FAQ).
- School accounts: Claude for Education - the school's Primary Owner manages the account and its
  data (Anthropic privacy article 11732894, 2026-03-16); ChatGPT Edu - workspace owners have admin
  + compliance tools (help pages 403 on 2026-10-07; not cited as more). Said plainly: the school
  decides what admins see, the account may end after graduation, and it runs Job Finder only if
  the school turned on Claude Code or Codex.

## Declined / later

- A separate "are you a student?" setup question: one more click for everyone, an exclusive option
  in a multi-select - folded into the type question + career level (persona review).
- A new `activities` key: same behaviour as projects with a role, ~17 files more (engineering
  review: kept as an option if the two ever need to differ).
- Coursework as evidence for a requirement; coursework picked per job (follow-up, plan-0cw.8).
- A first-tier "new grad" title pass: tier order follows pass order and a row in two passes keeps
  the last one's tier (follow-up).
- Deadlines: freehire rows carry none. Handshake: needs the school's sign-in - paste the posting.
- The title's year ("Summer 2027 Intern"): the internship's year, not a graduation window.
- Site sentence + claim for students: waits for the site redesign in flight (follow-up).

## Sources

NACE Job Outlook 2026 press release (2026-01-23); NACE 2026 Internship & Co-op Survey (intern
wages, conversion 63.1%); CU Boulder ISSS (2021-07-21), UCI, Brown, CMU OIE work-authorization
guides; SEVIS Help Hub CPT page; USCIS OPT page (2024-11-25); 8 CFR 214.2(f)(9)-(10); DOL WHD
Fact Sheet 71 (2018-01); FTC "Job Scams" (2023-03); GitHub changelog 2026-03-13 + 2026-06-24;
GitHub community discussions 189268, 188488; Anthropic privacy article 11732894. All checked
2026-10-07.
