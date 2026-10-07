# Page format - what the hygiene gates check, and why

Screening tools, ATS and career-centre guides agree on presentation rules separate from wording:
text a machine reads back word for word, one colour, consistent rhythm down the page. Cheap to
meet, fail silently -> `render.py` checks every PDF (untailored + tailored), FAILs on a break.
Wording rules: `bullets.md`; page geometry (lines, fill, typeface): `typeface.md`.

## The gates

| Gate | Checks | Why | Basis |
|---|---|---|---|
| `text-color` | every text span black or near-black (each RGB channel <= 0x33), links aside | scanned-resume guidance = black throughout; coloured name, heading or job title the most common failure. Blue email / LinkedIn link accepted | convention, stated in screening-tool format checks + career-centre guides |
| `split-words` | no gap between two letters of one word wider than 0.04em of type size | PDF-to-HTML conversion (some screening tools read through it) guesses word breaks from glyph positions. Headings at +0.08em came back "EXP E R I ENC E"; body at +0.015em came back whole | measured 2026-09-24; PyMuPDF, pdfminer, pypdf read both whole -> gap measured, not an extractor's output |
| `heading-gap` | baseline distance heading -> first line under it agrees across sections within 1pt | even spacing after headings = standard format check. A job opened 10pt lower than a skills line -> EXPERIENCE 7.5pt looser than SKILLS | convention |
| `typeface` | every character on the page drawn by the resume's own typeface, or named first by lint `font-coverage` (then info) | Typst fills a character the family lacks from its own fonts (Libertinus, New Computer Modern) w/o a word: the line mixes typefaces and its width is off from `measure.py`. Fails only on a substitution nothing predicted | measured 2026-10-01: ✓ -> NewCMMath; ị Ạ Ơ μ ⁹ ★ Greek, Cyrillic -> LibertinusSerif |
| `headline (info)` | optional headline fits one row | read as one line; wrapped = paragraph | convention |

`test_colour_letterspacing_and_heading_gap_fail_their_gates` re-injects old styling, asserts
exactly these three fail.

Also measured on old template: pypdf merged LANGUAGES heading into the education line above.
Unspaced heading reads clean in all three extractors.

Parser study 2026-10 (`app/web/research/resume-parser-test-2026-10/`, article `resume-parser-test`):
headings at +0.25em -> single letters ("E X P E R I E N C E") in all 5 readings (PyMuPDF x2,
pdfminer, pypdf x2); plain one column 0 of 5 broke; sidebar + placed text boxes broke readers that
sort by position, text boxes also file-order readers; table split job dates from title in 2.

## The headline

Optional one-line `headline` in Resume details, bold under contact line, above summary: user's
real title + main skills ("Software Engineer | Python, SQL"). Career guidance: one in place of a
generic "Summary" label. Untailored copy: their words as written, never a level their title lacks
(`bullets.md` Tier 1).

Per job (2026-10-06, users asked): a tailored copy may swap the title part - words before `|` -
for the posting's title (`headline_title`); words after `|` print as written. No headline -> the
title alone becomes one. No `|`, or a part before it sharing no word w/ any of their job titles
("Python, SQL | Engineer"; filler words like "and" don't count) = their own sentence, never touched.

| For | Against / limit |
|---|---|
| Top line = target-role label, not an employment record: no employer, no dates, nothing a background check compares. Work-history titles stay locked (`title-changed`) | Read as what they are NOW, w/ nothing beside it showing the real title -> level judged on roles still running (else the newest) or their own headline title; an old Manager role never vouches for a Manager headline. Level list wider than "Senior": VP, Vice President, Architect, Leader, Charge ... (`tailor.SENIORITY`); a grade numeral counts only as the title's last word and only upward ("Engineer II" over III fine; "IV Infusion Nurse" = intravenous) |
| Recruiter search: 55.3% of 384 recruiters filter by job title (Jobscan 2025 recruiter survey, vendor survey); title = the posting's exact string, read first on the page (same mechanism as `bullets.md` Tier 3 terms) | Jobscan 2025 "10.6x interview rate" = a matching title ANYWHERE on the resume, its own users' tool activity, method one line, interview undefined; same table gives a bachelor's degree 6.1x - correlational, never cited as cause or as proof for the top line |
| Career coaches + resume companies advise a target title at the top, real titles kept below. NOT a career-office convention: Harvard + MIT resume guides say nothing on it (checked 2026-10-06); the SUNY Canton / Oregon State "career services" posts are a reposted coach newsletter (The Job Insiders) | A title they can't defend in interview (posting's quirky or wider title) -> whole words, capitals as the posting writes them (all-caps posting: any), AI picks the plain part ("Data Analyst" of "Data Analyst Rockstar - Remote"), user confirms |
| Confirmed on every job under "To confirm" - `resume.title_mirror: always` pre-approves brackets beside a role's title only, never the top line in place of theirs | Copies sent to one employer can carry different top lines - harmless (one resume per posting is normal), named here so nobody re-asks |

Enforced: `tailor.check_headline_title` - whole words of the posting title (case kept), no `|`,
not a repeat, no level word the current title / own headline title lacks, no abbreviation (Sr,
Snr, Mgr ...), never wraps a headline that fit one row (measured in the 600 weight). Its words
count as generated words in the page budget (prompt says so). Lint's `unresolved-entity` skips
the headline (the check above owns its title part).

## Summary length

Up to 4 lines at summary width (`MAX_SUMMARY_LINES`), last well filled, under 57-word cap.
Career guidance: 3-6 lines; 4 fits the two-page budget. Tailoring prompt used to hold it to 2.

## Wording hygiene on the same pass

Four lint rules sit beside the page gates - same scorers check them. Plain-words reasons in
`bullets.md` #What the code checks:

- `spelling`: British forms (US reader takes *theatre* for a typo) + unknown words one letter
  from a known one. One error = failure for the whole page.
- `compound-modifier`: *live-streaming channels*, *full-stack engineer*.
- `overused-opening`: one opening verb on 4+ bullets.
- `filler-word`: *successfully*, *actively*, first person.

## Advice declined

| Common advice | We do | Why |
|---|---|---|
| Add a number to every bullet, from a template ("for {{count}} screens") | `resume-gaps` asks user for the real number; skipped question changes nothing | number user didn't give = invented; any number gets asked about in interview (`bullets.md` Tier 1) |
| Add competency keywords w/ sample bullets | never | keyword-list matches, not user's facts (`bullets.md` #What did not survive) |
| Cut skills to 6-12 | user's full list | skills block = where recruiter search terms land (`bullets.md` Tier 3) |
| Flag "the", "that", "which", "their", passive voice | not flagged | ordinary English; flagging pushes toward stilted text |
| "City, ST Zip" | city + state | ZIP adds nothing a US employer needs; `street-address` warns on one |
| 0.5in margins, a type-size knob (8.5-12pt), A4 | US Letter, 0.85in, 11pt | past 0.85in nothing moves - the page is bound vertically (`typeface.md`); `measure.py` is calibrated at 11pt; fit = rewriting words, never shrinking type; A4 narrows the column 3.4% |
| Justified text, hyphenation on | left-aligned, no hyphenation | a hyphen splits a keyword recruiters search ("LLM-backed"); `resume.typ` sets both off |
| Letterspaced headings or name | normal spacing | `split-words`: +0.08em read back "EXP E R I ENC E" |
| Grey dates or contact line, coloured headings | black throughout | `text-color` |
| Dates pushed right on the heading line | dates on the line under it | pdftotext read a right column after the bullets (`resume.typ:36`) |
| Two-column, sidebar or photo templates | one column, no images | `single-column` + `no-images` gates; multi-column did poorly in one vendor's eye-tracking study (Ladders 2018) |
| Education on one line: "BSc, Field \| School" | school on its own line, degree spelled out under | Workday read 2026-09: school "Field \| School", Degree empty |
| A "Stack:" line under each job | tools in the lines that used them | a row per job, repeating tools (keywords never repeated to pad) |
| Certification "Name - Issuer (Year)" w/ a long dash | Name \| Issuer \| Year | `em-dash` |
| Tracking links in the PDF (to see if it was opened) | links printed as written | link text that doesn't match its target is the pattern mail filters flag as phishing; needs a server; tracks the recruiter unasked |
