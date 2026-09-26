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
| `headline (info)` | optional headline fits one row | read as one line; wrapped = paragraph | convention |

`test_colour_letterspacing_and_heading_gap_fail_their_gates` re-injects old styling, asserts
exactly these three fail.

Also measured on old template: pypdf merged LANGUAGES heading into the education line above.
Unspaced heading reads clean in all three extractors.

## The headline

Optional one-line `headline` in Resume details, bold under contact line, above summary: user's
real title + main skills ("Software Engineer | Python, SQL"). Career guidance: one in place of a
generic "Summary" label. User's own words -> never generated, never adds a level their title
lacks (`bullets.md` Tier 1).

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
