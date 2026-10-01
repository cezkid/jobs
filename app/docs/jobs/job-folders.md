# Job folders - where each one lives

One folder per tailored job, filed under where the job stands. Status (`applications` table,
`app/status.py`) is the truth; the folder follows it, never the other way round.

```
My Jobs/
  1 To apply/      saved, resume made
  2 Applied/         applied
  3 Heard back/   heard back, interview, offer
  4 Closed/       they said no, not sending, closed
    12 - Acme - Data Analyst/
      First_Last_Resume.pdf, Job posting.md, Check before sending.md, Application answers.md, Cover
      letter.md + First_Last_Cover_Letter.pdf, Follow-up email.md (when asked for), .data/ (jd.json, apply-form.json, task, answers)
```

Table: `status.STAGES`. Stage folders appear when a job first needs one; never removed after.

## Name

`Job <n> - <Company> - <Title>`; n = the job's number in the chat, Today page + email
(`store.number`). 80 chars max, number never cut (Windows path budget: deep home dir + stage +
`.data/<file>`). Unique per job => same job prepared in two chats shares one folder.

## Found by what's inside

Job folder = any folder under My Jobs, any depth, holding a readable `.data/jd.json`
(`tailor.job_dirs`). Never found by name or place: a folder moved or renamed by hand still works.
No job file (a stray note, a half-copied folder) => not a job: never counted, numbered or moved.

## When folders move

| Trigger | Moves |
|---|---|
| `status set N <state>` | that job's folder; prints `folder: <path>` |
| `tailor prepare` | new job -> `1 To apply`; a closed one reopens (saved) -> `1 To apply`; filed before any path is printed, so the task file's answer path stays good |
| launch (`launch.first_page`) | every folder not where its status says, before the Today page is built |
| `status sort` | same, on demand |

Never from the chat-start hook, the Today rebuild, the morning check or a reading command.
Never on a timer: a resume made weeks ago stays in To apply until the user says otherwise.

Rules (`status.sort_folders`):
- Rename only - never `shutil.move` (copy + delete fallback can leave a job in two places).
- Name taken -> both left as they are, said why. Rename fails (Windows: a file open in another
  program) -> folder stays whole, retried at next launch / `status sort`.
- Deepest first: a job folder dragged inside another is filed before the outer one moves.
- One chat at a time (`cfg.DATA/job-folders.lock`).
- One way: a folder dragged to another stage by hand goes back at next launch. The user tells the
  chat instead ("I sent job 12"); guessing a status from a drag can't tell a drag from a failed move.

After a move, paths printed earlier in a chat are stale: use the last `folder:` line
(`status show N` prints it). `apply-form fill` works the resume's path out at fill time for the
same reason - never a path saved earlier.

## Why this layout

Same pipeline job-search trackers use (to apply, applied, interviewing, closed) - convention, not
a measured rule. Numbered so every file list shows the stages in order: VS Code (sorted by name,
`.vscode/settings.json`), Finder, Explorer, a browser's upload box. Job number in the name = the
number the user already says.

Rejected:
- Folder-only Closed (`move-closed`, 2026-09): status kept saying applied, so a closed job stayed
  in Waiting on you / Follow up. Closed is a status now.
- Folders by date or company: neither answers "what's left to send?"
- Moving stale resumes on a timer: a resume made weeks ago can still be sent; only the user says.

Renamed stages (`1 To send` -> `1 To apply`, `2 Sent` -> `2 Applied`, 2026-10-01): sort files their
jobs into the new names, then removes the old folder once it holds nothing (`status.RETIRED_STAGES`).
A file of the user's own inside keeps it.
