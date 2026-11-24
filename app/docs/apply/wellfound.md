# Wellfound - what was measured

Job board (freehire `source` wellfound, `wellfound.com/jobs/<7 digits>-<slug>`: Teamtailor's link shape, never
Teamtailor). Its Apply is Wellfound's own, tied to a Wellfound account. No filler: `prepare` looks for the
employer's own posting (`apply/listing_copy.py`), and with none says the steps below (`listing_copy.own_form`).

Measured 2026-11-24, one posting, one account, by hand through the Claude Chrome extension in the owner's Chrome
(owner: "apply for me. if new system. figure it out"). One posting = thin: every line below is that one's.

| What | Seen |
|---|---|
| Plain read of the posting page | 403 (`httpx`) |
| `?autoOpenApplication=true` on the posting link | opens the application box at once, signed in or out |
| Signed out: the box | a new-account form: Full Name, Email, Set a Password, Confirm Password, Set Your Location, "I'm open to work remotely", Years of experience (list), Desired Salary (USD), US work authorization (authorized Yes / No, sponsorship Yes / No), Cover letter, resume upload (.pdf .doc .docx .txt), "Submit application" - "By continuing you accept our standard terms" |
| Signed out: an email that already has an account | "email belongs to an existing user, please log in!" as the box is left => the email reaches Wellfound before anything is clicked |
| Sign-in | `/login?after_sign_in=<posting path>`: Google, or email + password; lands back on the application box |
| Signed in: the box | "Is your profile up to date?", one text box "Cover Letter" (placeholder "Write a note to <company>.", no required mark), Cancel, "Send application". No resume box, no other question |
| Which resume goes | the one on the Wellfound profile. `/profile/edit/resume`: "Your resume is over 5 years old" + View / Upload new file / Remove; a PDF put in its file box showed "Your resume has been updated!" within 4 s, no Save button |
| Profile | a banner "Your profile can't be found by recruiters because it's missing key information" (work experience) - the employer sees the profile beside the resume |
| Posting age | "Reposted: 5 years ago" under the title, on a row the job search first listed the day before |

## Why no filler

- Lab (`apply-form measure`, 2 runs, 4 page loads, 2026-11-24): not measurable while blocked. The page reads
  through POSTs to `wellfound.com/graphql` and runs a Cloudflare check that POSTs
  (`/cdn-cgi/challenge-platform/...`) - all blocked, 10 of 10; controls read: 1. A cookie notice (Manage Choices /
  Agree & Proceed / Reject All) covers Apply Now in a fresh profile; `--click "Reject All"` timed out (not found as
  plain text - likely in a frame, unmeasured).
- The form worth filling shows only to a signed-in account - nothing synthetic can reach it.
- Signed in there is one optional box. The step that matters is which resume the profile holds, and changing it
  changes what every recruiter on Wellfound sees: the user's yes, each time.

Unmeasured: a second posting or account; a posting with the employer's own questions; whether Job Finder's
Chrome passes the Cloudflare check; the page after Send application; an application already sent.
