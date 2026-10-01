# Was it sent? - telling from what the browser saw

Users forget to say they applied, or apply to several and lose track. Status then stays "resume
made" and the job keeps asking. Code: `app/sent.py`, run as `uv run app/jobs.py status sent`.

## Two moments to catch it

1. **Right after Submit** (`job-apply` last step): read the tab yourself before asking "Did you
   send it?". Sent page or applied list shows it -> `status set N applied`, one line saying so,
   no question. Nothing shows -> ask as before.
2. **Later**, user unsure or a job sat in Waiting on you: `status sent`. Each job not marked
   sent -> `sent` / `likely not sent` / `can't tell` / `no visits`, w/ why. Never records
   anything itself.

## What each system shows (measured 2026-09-30, real histories, 10 jobs)

| System | Sent page | Account list of what was sent |
|---|---|---|
| Greenhouse | `.../jobs/<id>/confirmation`, title "Thank you for applying" - seen on 2 sent jobs | `my.greenhouse.io` -> Applications tab: lists only applications sent while signed in there (a job sent signed out was missing) |
| Workday | `.../jobTasks/completed/application` (Candidate Home), loads right after Submit; names no job - counts for the job whose `/apply` page was open just before (within 2 h) | Candidate Home on that employer's site |
| Ashby | none: same address before + after Submit | none - no candidate account; confirmation email only |
| UKG Pro Recruiting | none seen | My Presence (`.../Candidate/ViewPresence`) -> Applications: rows Job / Status / Date applied; "You have not yet applied to any opportunities" when empty. Signed in only. Detail page keeps "Apply now" either way |
| Rippling | none seen | none |

Greenhouse + Workday: form opened, no sent page -> `likely not sent`. Systems w/o one ->
`can't tell`: say where to look (account list, confirmation email), never guess. Not settled by
history -> one clickable question, as `AGENTS.md` #Where each job stands.

## Matching a visit to a job

- Same id as the job's link: posting uuid, Greenhouse job id (`/jobs/<id>`, `gh_jid=`), UKG
  `opportunityId` (never the board uuid - every job of that employer shares it).
- Else company's first word in the address + job title inside the page title (Workday and
  Rippling pages carry no id from the listed link).

## Browsers + privacy

Reads Chrome, Brave, Edge, Arc, Vivaldi, Chromium (every profile), Firefox, Safari, and Job
Finder's own window - each history copied first (an open browser locks it). Nothing fetched,
nothing sent; only lines about jobs in progress are printed. macOS: Safari needs Full Disk
Access - reported as "could not read", never asked for. Phone, other computer, a browser not
listed: not seen - say so when it matters.

## Not measured yet

Lever (`jobs.lever.co/.../thanks` expected), SmartRecruiters, iCIMS, Workable. Add a row to
`SYSTEMS` only after seeing the sent page in a real history.
