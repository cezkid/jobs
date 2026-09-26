# Typeface - why Caladea, and what changing it moves

All numbers measured 2026-09-21, 11pt (template size), on a real full-length resume. Re-measure
before changing the default.

Three settings trade against each other: family (`resume.font`), side margin
(`render.MARGIN_X_IN`, 0.85in), letterspacing (`render.TRACKING_EM`, +0.015em). Wider margin buys
chars/line; tracking spends them. Font chosen first - it decides how many there are.

## The thing that decides it: characters per line

Resume = stack of one-sentence bullets. Each fits its line or spills 2-3 words onto a row of
their own (widow) -> whole row wasted. Enough widows -> extra page.

Chars/line is a font property; spread between families flips most bullets at once. Same resume,
same words, starting margin (1.05in, no tracking):

| family | x-height | chars/line | pages | widows | real 600 |
|---|---|---|---|---|---|
| **Caladea** (Cambria metrics) | **5.14pt** | **98** | **2** | **0** | **no** |
| Tinos (Times New Roman metrics) | 5.05pt | 101 | 2 | 0 | no |
| Source Sans 3 | 5.35pt | 96 | 2 | 0 | yes |
| Gelasio (Georgia metrics) | 5.30pt | 91 | 3 | 19 | yes |
| Charis SIL (Charter) | 5.30pt | 91 | 3 | 19 | no |
| Lato | 5.57pt | 91 | 3 | 13 | yes |
| PT Serif | 5.50pt | 90 | 3 | 16 | no |
| Source Serif 4 | 5.22pt | 90 | 3 | 16 | yes |
| Spectral | 4.95pt | 90 | 3 | 17 | yes |
| IBM Plex Serif | 5.68pt | 85 | 3 | 25 | yes |

7 chars/line = 2 pages, 0 widows vs 3 pages, 19. Nothing else moved.

-> Georgia, every guide's serif pick, is wrong here: drawn wide on purpose for large-size screen
reading; costs a page in a resume column. Open twin Gelasio inherits metrics + result.

**Easing the margin does not rescue the others.** Re-run at shipped page (0.85in, +0.015em) and
at 0.75in (widest usual US-letter resume):

| family | 0.85in +track | 0.75in +track |
|---|---|---|
| **Caladea** | **100 chars, 2 pages, 0 widows** | 103 chars, 2 pages, 0 widows |
| Tinos | 103, 2 pages, 0 | 106, 2 pages, 0 |
| Gelasio (Georgia) | 93, 3 pages, 8 | 96, 3 pages, 4 |
| Spectral | 93, 3 pages, 8 | 96, 2 pages, 3 |
| Charis SIL | 93, 3 pages, 10 | 96, 3 pages, 5 |
| PT Serif | 92, 3 pages, 7 | 95, 3 pages, 2 |
| Source Serif 4 | 92, 3 pages, 7 | 95, 2 pages, 2 |
| IBM Plex Serif | 87, 3 pages, 20 | 90, 3 pages, 16 |

Past 0.85in margin stops paying: every bullet already fits one line -> page bound vertically;
0.75in moved neither page nor widow count for Caladea.

## The rest of the requirements

1. **Read easily at 11pt.** Apparent size = x-height, not point size. Caladea 5.14pt, mid-field;
   the 3 fonts that fit are within 6% -> doesn't separate them. Decides tracking instead:
   Caladea fitted tight, reads cramped at 11pt -> +0.015em per glyph. Costs ~1.5% of line (3
   chars), paid for by eased margin.
2. **Hold its weights.** `resume/templates/resume.typ`: body 400, headings + entry titles 600,
   name 700. Caladea has no 600 -> Typst uses bold (checked on rendered page; size + accent
   colour separate a heading). Hence `typeface.REQUIRED` = 400 + 700; 600 used when present.
3. **Line up digits.** Every family above has uniform digit widths -> dates + metrics sit
   straight. Ruled nothing out; a family failing it would be disqualified.
4. **Survive a parser.** Embedded w/ ToUnicode map, no ligature codepoints in text layer.
   `resume/render.py` gates `fonts`, `ligatures`, `round-trip` check every render; Caladea
   passes all sixteen.

Caladea vs Tinos (the two that fit): Tinos = Times New Roman metrics, drawn 1932 for narrow
newspaper columns, the default every resume guide says to avoid. Caladea = Cambria metrics,
drawn 2004 for small-size legibility on screen + print - the job. Both open, both look like
Office fonts -> familiar, nothing to download (embedded in PDF).

Serif vs sans left out on purpose: reading-speed studies find no reliable difference at text
sizes; x-height + fit move, measured above. PR #6 review asked for a serif; one that fits was
available.

## What a font change moves

Nothing written twice. `resume/typeface.py` resolves the family; these follow from the file:

- `measure.bullet()` - hanging indent = 0.7em + marker glyph, 12.6pt of 489.6pt column in
  Caladea -> bullet width moves w/ font.
- `render.runts()` - word space a wrap had to fail to fit (2.42pt here, 2.82pt Lato, 2.20pt
  Source Sans 3).
- `tailor.char_guides()` - char counts in writer's prompt, from wrapping real prose in the
  configured font: <= 91 for one line, 145-194 to fill two.
- `render.MAX_WORDS` - outer clamp on page words, clear of a font change: 860 keeps a two-page
  window open on any page up to 537 words. Caladea measures 378. Floors are page shares
  (`render.ONE_PAGE_FILL`, `MIN_LAST_PAGE_FILL`) -> move w/ it.
- `render.TRACKING_EM` not a free knob. Typst adds it after every glyph, spaces included ->
  `measure.width()` adds `TRACKING_EM * SIZE` per char, calibrated vs rendered page, exact to
  4 decimals. Omit -> every width 1.5% short. Exception: list marker - Typst lays body indent
  from the glyph w/o trailing tracking -> `measure.bullet()` uses raw advance.

`render.MIN_LINE_FILL` does not move. Tails cluster low then stop - 3-30% full Source Sans 3,
24-35% Caladea, nothing between there and a filled line; 0.40 sits in that gap in both.

`resume/measure.py` predicts rendered width to median 0.4%, worst 1.4%, over 41 bullet, summary
+ skills lines of a real resume - the text the page rules act on.

## Changing it

`My Settings/Search settings.yml`:

```yml
resume:
  font: Caladea
```

Name must match folder in `app/resume/fonts/` + the font's own name. Add a family: its `.ttf`
files in a folder of that name - regular + bold minimum, semibold used when present.
`typeface.check()` runs before first compile, names what a folder lacks. Typst gets that one
folder, no system fonts -> no half-substitution.

Measure before adopting: render a full resume, count widows, as above. Reads beautifully at 90
chars/line = wrong font here.

Redistributable fonts only. Caladea: SIL Open Font License (`app/resume/fonts/Caladea/OFL.txt`),
allows bundling + PDF embedding. Georgia, Cambria, Calibri, Times New Roman = Microsoft-licensed,
can't ship -> metric-compatible open faces.
