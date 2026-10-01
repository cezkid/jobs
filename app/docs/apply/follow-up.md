# Follow-up - when the Today page suggests one, and what the draft says

A job sent and quiet too long shows under **Follow up** on the Today page. The user can ask for a
short note (`follow-up JOB` -> `Follow-up email.md` in the job folder), send it from their own
email, and say so (`status followed-up JOB`). Nothing is sent for them; nothing reads their inbox.

## When (settings `follow_up`, `app/defaults.yml`)

| Stage | Days quiet | Basis | Strength |
|---|---|---|---|
| Applied | 21 | recruiter advice: 1-3 weeks; one job-search tracker's own data, 92 applications - 21 days flagged 16% of them as quiet | convention + one small measurement |
| Heard back | 15 | between applied and interview; no measurement | judgement |
| Interview | 12 | one tracker, 6 interviews: 7 days flagged 5 of 6 too early, so raised | very weak |
| Floor | 5 | shortest wait that always holds two working days (a weekend can take 3) | arithmetic |

Offer and no-reply-yet states are not followed up: an offer is the user's to answer, a resume not
yet sent has nothing to chase.

## One nudge per silence

A logged follow-up never changes where the job stands (`application_log` event, not a status). The
job leaves the list for one more stretch of its stage's days; still quiet after that, the page
suggests closing it ("You followed up 22 days ago, still no reply"), never a second chase. Many
employers never write back - the page says so, so silence reads as theirs, not the user's.

## What the draft says (`app/followup.py`, no AI step)

- Subject "Following up: <Role> application".
- Opening names the role, the company and how long ago - weeks up to 45 days, then months.
  Applied: "I applied for ... and have not had a reply yet." Later: "We last spoke about ...".
- One direct question. Applied: "Is the role still open, and what is the timeline for the next
  step?" Later: "Where does my application stand, and what are the next steps?"
- At most one line on what they bring: a line of the resume they sent that proves a must-have,
  word for word their own fact - else none. Never a claim the user hasn't confirmed.
- Thanks, their name. Under 120 words. No apology, no "just checking in", no urgency ("another
  offer") unless they say it's true. Convention (career guides: short, specific, polite); tests pin it.

## Declined

- **Sending for the user, or reading their mailbox to time it.** Their email, their send; nothing
  new leaves the computer.
- **A second, third chase.** One nudge per silence, then closing is suggested.
