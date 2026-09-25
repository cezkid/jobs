# Page format - what the hygiene gates check, and why

Resume screening tools, applicant tracking systems and career-centre format guidance agree on a
short list of presentation rules that have nothing to do with wording: text a machine can read
back word for word, one colour, and a consistent rhythm down the page. They are cheap to meet
and fail silently when missed, so `render.py` checks them on every PDF - untailored and tailored
alike - and FAILs when one breaks. Wording rules are `bullets.md`; page geometry (lines, fill,
typeface) is `typeface.md`.

## The gates

| Gate | Checks | Why | Basis |
|---|---|---|---|
| `text-color` | every text span is black or near-black (each RGB channel <= 0x33), links aside | Format guidance for scanned resumes is black text throughout; a coloured name, heading or job title is the most common failure. A blue email or LinkedIn link is accepted | convention, stated in screening-tool format checks and career-centre guides |
| `split-words` | no gap between two letters of one word wider than 0.04em of the type size | PDF-to-HTML conversion, which some screening tools read resumes through, guesses word breaks from glyph positions. Headings letterspaced at +0.08em came back as "EXP E R I ENC E"; body text at +0.015em came back whole | measured 2026-09-24; PyMuPDF, pdfminer and pypdf read both whole, so the gap is measured, not an extractor's output |
| `heading-gap` | the baseline distance from each section heading to the first line under it agrees across sections within 1pt | Consistent spacing after section headings is a standard format check. A job used to open 10pt lower than a skills line, so EXPERIENCE sat 7.5pt looser than SKILLS | convention |
| `headline (info)` | the optional headline fits one row | A headline is read as one line; wrapped, it reads as a paragraph | convention |

`test_colour_letterspacing_and_heading_gap_fail_their_gates` re-injects the old styling and
asserts exactly these three gates fail.

Measured on the old template, also: pypdf merged the LANGUAGES heading into the education line
above it. The unspaced heading reads cleanly in all three extractors.

## The headline

An optional one-line `headline` in Resume details prints bold under the contact line, above the
summary: the user's real title and main skills ("Software Engineer | Python, SQL"). Career
guidance recommends one in place of a generic "Summary" label. It is the user's own words, so
it is never generated, and it never adds a level their title lacks (`bullets.md` Tier 1).

## Summary length

Up to four lines at the summary's width (`MAX_SUMMARY_LINES`), the last well filled, under the
57-word cap. Career guidance puts a summary at 3-6 lines; four keeps it inside the two-page
budget. The tailoring prompt used to hold it to two.

## Wording hygiene on the same pass

Four lint rules sit beside the page gates because the same scorers check them. They are listed
with their plain-words reasons in `bullets.md` #What the code checks:

- `spelling`: British forms (a US reader takes *theatre* for a typo) and unknown words one
  letter from a known one. One spelling error is treated as a failure for the whole page.
- `compound-modifier`: *live-streaming channels*, *full-stack engineer*.
- `overused-opening`: one opening verb on 4+ bullets.
- `filler-word`: *successfully*, *actively*, first person.

## Advice declined

| Common advice | We do | Why |
|---|---|---|
| Add a number to every bullet, from a template ("for {{count}} screens") | `resume-gaps` asks the user for the real number; a skipped question changes nothing | a number the user did not give is invented, and any number gets asked about in interview (`bullets.md` Tier 1) |
| Add competency keywords with sample bullets | never | they are keyword-list matches, not the user's facts (`bullets.md` #What did not survive) |
| Cut skills to 6-12 | the user's full list | the skills block is where a recruiter's search terms land (`bullets.md` Tier 3) |
| Flag "the", "that", "which", "their", passive voice | not flagged | ordinary English; flagging them pushes toward stilted text |
| "City, ST Zip" | city and state | a ZIP adds nothing a US employer needs; `street-address` warns on one |
