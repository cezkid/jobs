# Job Finder

Job Finder looks for new job postings that match what you want, tells you each morning when
new ones arrive, and makes a version of your resume tailored to any job you pick.

## How to use it

Open the AI chat panel and type what you want in plain English. Using ChatGPT? Click the
ChatGPT icon on the left side of this window, then type: **set me up**. For example:

- "Set me up" (the first time)
- "Any new jobs?"
- "Make my resume for job 3"
- "Stop showing jobs from Acme Staffing"
- "Only show jobs near my city"
- "Check for jobs at 7 every morning"
- "Email me the new jobs too"
- "Who can see my information?"

The AI does all the work. You never need to type commands or edit files.

## Changing your resume details yourself

Everything Job Finder knows about your career sits in one file: **Resume details.yml**, inside
My Resume. Click it and you'll see your jobs, newest first, with one line for each thing you
did there, in your own words. Change a line, add a line, delete a job you'd rather leave off -
then ask the chat for a fresh resume and it uses what you wrote. Your edits always win.

Two things to keep an eye on:

- Leave the spacing at the start of each line alone. The lines are lined up on purpose.
- Write dates as the year, a dash, then the month: **2023-02** means February 2023. The job
  you're in now ends with the word **present**.

If you type something the file can't use, it gets a red underline right away and hovering over
it says what's wrong. Nothing is broken until you fix it - you can also just say "I mistyped
something in my resume details" and the chat will sort it out.

You never have to touch this file. "Change my phone number" or "take the Drupal line
off my resume" in the chat does the same thing.

## How your tailored resume is laid out

When Job Finder makes a resume for a job, it holds it to two rules so it reads like someone
laid it out by hand:

- **Never more than two pages.** One page is fine. If it runs onto a second page, that page
  has to be at least well over half full, so you never get a stray line or two on its own.
- **No lines with a few words dangling.** Every line of a bullet point is filled out. If a
  sentence would spill two or three words onto a line of their own, the AI rewrites it -
  either shortening it to fit, or saying a little more so the line fills.

Those stray part-lines are worth more than they look: on a resume they can waste most of a
page, which is what pushes a two-page resume onto a third. If the AI can't make something
fit, it tells you in plain words rather than handing you a resume that breaks the rules.

Your resume is set in a serif typeface called Caladea. It is the same shape and size as
Cambria, the font on every copy of Microsoft Word, so it looks familiar to whoever opens it -
and it is a free version, so nobody has to install anything. It was picked because it fits
more words on a line than the alternatives, which is what keeps those dangling part-lines off
your page - and the spare room goes back into the page as slightly wider letter spacing, so it
reads open rather than crammed. If you would rather have a different one, just ask - say which font you want and it
gets set up for you, and everything about how the page fits is worked out again for it.

## What's private and what's shared

**Everything in the file list on the left is yours and private.** It stays on this computer
and is never sent to the Job Finder maintainer or to anyone else who uses Job Finder.

| Folder | What's in it | Private? |
|---|---|---|
| My Jobs | One folder per job: your tailored resume, the job posting, a checklist to read before you apply | Private - only on this computer |
| My Resume | Your original resume and the details Job Finder uses to build new versions | Private - only on this computer |
| My Settings | What jobs you're looking for | Private - only on this computer |

**My Resume and My Jobs start out empty.** My Resume fills up when you show Job Finder your
resume, and My Jobs gets a folder each time you pick a job to apply for. Nothing is missing.

Some things are hidden from the list so they don't get in your way:

- **Your job list, and your email password if you turn on email** - private, stay on this
  computer.
- **The Job Finder program itself** - public and open source. It's the same for everyone who
  uses Job Finder, and it updates itself each time you open it.

What leaves this computer, and only when you use it:

- **Checking for jobs** sends your search settings (like "accounting jobs near my city") to
  freehire.me, the job site Job Finder searches. Your resume is never sent there.
- **The AI chat** (Claude or ChatGPT) reads your resume and job postings while it helps you,
  under your own account with that company.
- **Daily email**, only if you turn it on, goes from your own email account to you. The
  morning pop-up notification never leaves this computer.
- **Bug fixes**: if the AI finds a problem in Job Finder itself, it asks you first before
  sending the fix to the maintainer. Only the program fix is sent - never your files.

## Opening Job Finder

Double-click **Job Finder** on your Desktop, or click the morning notification. It checks for
updates, then opens this window with the AI chat ready.
