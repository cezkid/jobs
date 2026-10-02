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
The job search's own count, ~100k forms: 67% ask nothing beyond a resume + contact details, 16% 1-4
questions, 16% 5-14, 1% 15+ (one source, tech-heavy).

## Drafted, then pasted (systems the program can't fill)

`apply-form prepare <job> <link>` on a system with no filler (Lever, Workable,
Recruitee) uses the read-ahead questions: contact boxes from the resume, the US work-permit
questions from setup, the rest blank for the AI to fill with the user. `apply-form paste <job>`
writes `Application answers.md` in the job folder - each question in order, its answer under it -
for the user to paste. Options weren't captured: the user picks the matching one on the page.

## Never drafted

Pay expected, where you live, voluntary questions about you (gender, race, veteran...), and the
sensitive kinds (date of birth, graduation date, criminal history, work break, disability or
health - `fair-screening.md`) are marked "ask the user" when prepared. An answer to one must come
from the user, marked `source: "you said"`; `fill` and `paste` refuse any other - a guess at a
salary is the user's number on the employer's file. Work permit + sponsorship come only from
setup's answers, the US question asked the same way (`questions.work_permit`).

## Saved answers (`app/apply/answers.py`)

After one yes (`saved_answers: true` in search settings, asked once at the first form), the user's
own answers - source "you said" - are kept in `My Settings/Saved answers.yml` (visible, private),
one per topic or question, newest wins. The next form:

| Recalled how | Questions | Why |
|---|---|---|
| Filled, named before Submit | 18 or older, notice period, how you heard, the same question word for word | true on any form; a wrong one is cheap |
| Offered first, never filled | pay expected (beside the posting's pay), moving for the job, start date, written answers | each depends on this job |
| Never kept | work permit + sponsorship, current pay, sensitive kinds, voluntary questions about them, where they live, two topics in one question | setup answers the US permit questions; the rest are the user's every time |

Basis: one form corpus, 647,795 forms (2026-09) - how you heard 61,762, 18+ 30,337, salary 24,762,
notice 7,841; 69% of 12,352 labels in a 4,000-form sample recall nothing. Saves typing on the
common few; most questions are still asked.

## On the page

`fill` reads the opened page first: one that says the job is closed ("no longer accepting
applications", "position has been filled") stops before typing anything. After filling it prints
"required answered X of Y" and names what's left for the user on the page.
