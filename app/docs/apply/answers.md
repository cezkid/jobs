# Application questions - read ahead, drafted, pasted

## Read ahead (`app/apply/readahead.py`)

Making a resume for a job on the list also asks the job search what that job's application asks:
`GET /jobs/<slug>/apply-form`, keyless, the listing id only (privacy table). Saved as
`<job folder>/.data/apply-form.json`, summed up in Check before sending.md under "What the
application asks": how many questions, how many written answers, what they're about (pay, permission
to work, sponsorship, where you live, start date, how you heard, sensitive kinds), a cover letter box.

Measured 2026-10-01: covers Greenhouse, Lever, Ashby, Workable, Recruitee - on one real tech list,
712 of 1,275 open jobs. Shape: `{provider, basics, questions: [{text, required, answer?}]}`, no
options, no ids. A 404 = no form captured: "Not known ahead", never "asks nothing". Lever marks
nothing required - said so. Captured once; the live form may have changed - the summary says so.
The job search's own count (freehire.me, published 2026-08), ~100k forms: 67% ask nothing beyond a resume + contact details, 16% 1-4
questions, 16% 5-14, 1% 15+ (one source, tech-heavy; its page not re-found 2026-10-03 - its repo's
measurements folder holds the 647,795-form count below, not this one).

## Drafted, then pasted (systems the program can't fill)

`apply-form prepare <job> <link>` on a system with no filler
(Recruitee) uses the read-ahead questions: contact boxes from the resume, the US work-permit
questions from setup, the rest blank for the AI to fill with the user. `apply-form paste <job>`
writes `Application answers.md` in the job folder - each question in order, its answer under it -
for the user to paste. Options weren't captured: the user picks the matching one on the page.

## Never drafted

Pay expected, where you live, voluntary questions about you (gender, race, veteran...), and the
sensitive kinds (date of birth, graduation date, criminal history, work break, disability or
health - `fair-screening.md`) are marked "ask the user" when prepared. An answer to one must come
from the user, marked `source: "you said"`; `fill` and `paste` refuse any other - a guess at a
salary is the user's number on the employer's file. Work permit + sponsorship come only from
setup's answers, the US question asked the same way (`questions.work_permit`) - and "authorized
... without restriction" is asked every time for a visa holder (`needs_sponsorship` or
`student_visa`: a CPT/OPT or H-1B permit has limits; CMU + UCI international offices say No on F-1),
even over a Yes an older setup saved.

## A student's boxes

`questions.student_answer`, from the school in progress on the resume, named at handover:
expected graduation date (box says expected / anticipated / "when do you expect to graduate", one
degree in progress - the date the page shows, "read it before Submit"; a bare "graduation date"
stays sensitive), GPA (the transcript's figure; a number box gets the part before "/"; a range list
the one range holding it; another scale is never converted - asked; major, high-school, weighted or
term GPA asked), "currently enrolled?" (Yes while a degree is in progress; full-time, half-time or
returning-after questions asked). A school's start boxes take its `start` (`schema.shown_start`:
never with `hide_year`). None of these is kept for the next form.
Agreeing, consenting, signing - terms and conditions / of use, privacy policy or notice, texts /
SMS / automated calls, e-signature or "type your name to sign", certify / attest / acknowledge
statements: never drafted, never filled, not even from "you said" - the applicant's own act, ticked
or typed by them on the page. `prepare` marks them "yours to do on the page", `missing` skips them,
`fill` / `paste` refuse one carrying an answer, `fill` names them under "still to do on the page".
A signature box is never a name box (no resume name typed into "Signature (type your full name)").
Measured 2026-10-03 (one tenant each): a start-page SMS consent Yes/No, a terms box + e-signature in
one system's apply flow, consent checkboxes on another. Near misses left alone: "informed consent"
(clinical), "signed off", a certification held, "digital signature" (crypto skills).
Saying whether AI helped - "I confirm that my application materials and interview responses ...
were not generated, edited, or supplemented by AI tools" (required, one Greenhouse tenant,
2026-10-05; `apply-form try` had filled it with a test Yes): a resume tailored here is AI help, so
a drafted Yes is a false statement. Same handling as signing, tagged `saying whether AI helped`;
`prepare` also prints "name it to the user" - the AI says their resume was tailored with AI help
and the answer is theirs, on the page. Caught: AI words + making words (generated, written,
edited, used...) + their own application (my / your / this ... application, resume, answers,
materials). Near misses left alone: "experience with AI tools", "used AI in your work", "used AI
to draft responses to customers".
Voluntary questions: one exception, the user's consent first - with `self_identification` saved,
`prepare` asks once whether to fill it on forms (`fill_on_forms`); yes -> filled when exactly one
option matches, named before Submit; no or unasked -> asked on each form as before (#Saved
voluntary answers).

## Saved voluntary answers

`self_identification` in search settings, the user's own words, saved only when they ask to reuse
a disclosure (`job-apply`). Filled only with `fill_on_forms: true`, each one named before Submit
(source "your saved voluntary answer"); a key not saved, an option list where nothing or more than
one option matches, or a title asking about two kinds at once ("Veteran and disability status") ->
asked as before (`questions.voluntary_answer`).

| Key | Saved as | Questions it answers | Options it picks (Greenhouse, 2026-10-05) |
|---|---|---|---|
| `gender` | the user's word (`Male`) | title says "gender" (not "transgender") | same word, or Male/Man, Female/Woman |
| `hispanic_latino` | `true` only | race, ethnic, Hispanic | the one starting "Hispanic" ("Hispanic or Latino", "Hispanic, Latinx or of Spanish Origin") |
| `protected_veteran` | `true` / `false` | the EEOC list ("Veteran Status"): its options ("I am not a protected veteran", "classifications of protected veteran") decide, whatever the title names; else "veteran" without armed-forces words | "I am not a protected veteran"; true: "I identify as one or more of the classifications of ..." |
| `armed_forces` | `true` / `false` | armed forces, military, active duty / member ("Are you a veteran or active member of the United States Armed Forces?", "What is your military status?"), options not the EEOC list | "No, I am not a veteran or active member", "I have never served in the military", "No military service"; true: "Yes, I am a veteran or active member" / "I am a veteran or active member" |
| `sexual_orientation` | the user's word (`Queer`) | orientation | that word, alone or joined ("Straight/Heterosexual"); Heterosexual = Straight |
| `transgender` | `true` / `false` | transgender ("Do you identify as transgender?", "Are you a person of transgender experience?") | Yes / No |
| `disability` | `true` / `false` | disability, not accommodation nor "disabled veteran" ("Disability Status", "Do you have a disability or chronic condition ...", "Do you live with a disability (as outlined by the ADA)?") | Yes / No, bare or worded ("No, I do not have a disability and have not had one in the past") |

Protected veteran and armed forces stay apart, though both titles can say "veteran": a protected
veteran is one kind of veteran, so neither answer is read off the other. Disability stays a
sensitive kind: filled with source `sensitive: disability or health - read it before Submit`, its
wording read back. An "LGBTQ+ community" question is voluntary (never drafted) but not filled from
these keys - asked. Basis: Greenhouse's own survey on tenant G + one more board, EEOC lists and
four employer surveys (5 public job boards, read 2026-10-05).

## Saved answers (`app/apply/answers.py`)

After one yes (`saved_answers: true` in search settings, asked once at the first form), the user's
own answers - source "you said" - are kept in `My Settings/Saved answers.yml` (visible, private),
one per topic or question, newest wins. The next form:

| Recalled how | Questions | Why |
|---|---|---|
| Filled, named before Submit | 18 or older, notice period, how you heard, the same question word for word | true on any form; a wrong one is cheap |
| Offered first, never filled | pay expected (beside the posting's pay), moving for the job, start date, written answers | each depends on this job |
| Never kept | work permit + sponsorship, current pay, sensitive kinds, voluntary questions about them, where they live, agreeing / consenting / signing, two topics in one question; a student's status (enrolled, current student, graduation, GPA, OPT / CPT / F-1 / EAD, eligibility, immigration) - by question, and any answer naming a permit or a GPA | setup answers the US permit questions; a kept "I agree" would tick the next form's box; a student's status changes (a saved "Yes, enrolled" would fill the next form after graduation); the rest are the user's every time |

Basis: freehire.me's captured forms, 647,795 (Greenhouse, Lever, Ashby, Recruitee, Workable;
measured 2026-09-09, github.com/strelov1/freehire, docs/superpowers/plans/measurements/ 01 + 03) - how you heard 61,762, 18+ 30,337, salary 24,762,
notice 7,841; 69% of 12,352 labels in a 4,000-form sample recall nothing. Saves typing on the
common few; most questions are still asked.

## Answers kept across prepares

A second `prepare` keeps an earlier answer only when the question id AND its title (folded: case,
punctuation, "please tell us") both match; else drafted fresh. Generated page ids (`rc_select_4`,
`spl-form-element_10`, `:r3:`) can name another question on the next load - by id alone, a "you
said" answer could land on it.

## On the page

`fill` reads the opened page first: one that says the job is closed ("no longer accepting
applications", "position has been filled") stops before typing anything. After filling it prints
"required answered X of Y" and names what's left for the user on the page. Results are matched to
questions by id, not title: one form can ask "Phone" twice.
