# Typeface - why Caladea, and what changing it moves

Every number here was measured on 2026-09-21, at the size the template sets (11pt), against a
real full-length resume. Re-measure before changing the default.

The page is three settings, and they trade against each other: the family (`resume.font`), the
side margin (`render.MARGIN_X_IN`, 0.85in) and the letterspacing (`render.TRACKING_EM`,
+0.015em). Widening the margin buys characters per line; tracking spends them. The font is
chosen first because it decides how many there are to spend.

## The thing that decides it: characters per line

A resume is a stack of one-sentence bullets. Each one either fits its line or spills two or
three words onto a line of their own - a widow, which wastes the whole row. Enough of those
and the resume gains a page.

How many fit is a property of the font, and the spread between families is large enough to
flip most bullets at once. On the same resume, with the same words, at the margin this started
from (1.05in, no tracking):

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

Seven characters a line is the difference between two pages with no widows and three pages
with nineteen. Nothing else on the page moved.

This is why Georgia, which every guide names as the serif to use, is the wrong one here.
Georgia was drawn wide on purpose, for screen reading at large sizes; in a resume column it
costs a page. Its open twin Gelasio inherits the metrics and the result.

**Easing the margin does not rescue the others.** The field was re-run at the page this now
ships - 0.85in margins, +0.015em tracking - and again at 0.75in, the widest a US-letter resume
is usually set:

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

Past 0.85in the margin stops paying: once every bullet already fits one line, the page is
bound vertically, and 0.75in moved neither the page count nor the widow count for Caladea.

## The rest of the requirements

1. **Read easily at 11pt.** Apparent size is x-height, not point size. Caladea's 5.14pt is
   mid-field; the three fonts that fit the page are within 6% of each other on it, so this
   does not separate them. What it does decide is tracking: Caladea is fitted tight for
   economy, which at 11pt reads cramped, so the page adds +0.015em to every glyph. That costs
   about 1.5% of the line - three characters - which the eased margin pays for.
2. **Hold its weights.** `resume/templates/resume.typ` sets body 400, headings and entry
   titles 600, the name 700. Caladea has no 600, so Typst uses its bold - checked on the
   rendered page, and size plus the accent colour is what separates a heading there.
   `typeface.REQUIRED` is 400 and 700 for that reason; 600 is used when a family has it.
3. **Line up digits.** Every family above has uniform digit widths, so dates and metrics sit
   straight. It ruled nothing out, but a family that failed it would be disqualified.
4. **Survive a parser.** Embedded with a ToUnicode map, no ligature codepoints in the text
   layer. `resume/render.py`'s `fonts`, `ligatures` and `round-trip` gates check this on
   every render; Caladea passes all sixteen.

Between Caladea and Tinos, the two that fit: Tinos carries Times New Roman's metrics, a face
drawn in 1932 for narrow newspaper columns and the one every resume guide names as the default
to avoid. Caladea carries Cambria's, drawn in 2004 for legibility at small sizes on screen and
in print, which is the job. Both are open fonts that look like the ones on every Office
install, so the page reads as familiar without anyone downloading anything - the file is
embedded in the PDF.

Serif or sans is not in the table on purpose. Reading-speed studies find no reliable difference
between them at text sizes; what moves is x-height and fit, which are measured above. The
review on PR #6 asked for a serif, and a serif that fits the page was available.

## What a font change moves

Nothing is written down twice. `resume/typeface.py` resolves the family, and these follow from
the file:

- `measure.bullet()` - the hanging indent is 0.7em plus the marker glyph, 12.6pt of the
  489.6pt column in Caladea, so the width a bullet gets moves with the font.
- `render.runts()` - the word space a wrap had to fail to fit into (2.42pt here, 2.82pt in
  Lato, 2.20pt in Source Sans 3).
- `tailor.char_guides()` - the character counts quoted in the writer's prompt, found by
  wrapping real prose in the configured font: 91 or fewer for one line, 145-194 to fill two.
- `render.MAX_WORDS` - the outer clamp on page words, set clear of a font change: 860 keeps
  a two-page window open on any page up to 537 words. Caladea measures 378. The floors are
  shares of the page (`render.ONE_PAGE_FILL`, `MIN_LAST_PAGE_FILL`), so they move with it.
- `render.TRACKING_EM` is not a free knob. Typst adds it after every glyph, spaces included,
  so `measure.width()` adds `TRACKING_EM * SIZE` per character - calibrated against a rendered
  page, exact to four decimals. Leave it out and every width is short by 1.5%. The one place
  it does not apply is the list marker: Typst lays the body indent out from the glyph without
  the tracking that follows it, which is why `measure.bullet()` uses the raw advance.

`render.MIN_LINE_FILL` does not move. Tails cluster low and then stop - 3-30% full in Source
Sans 3, 24-35% in Caladea, nothing between there and a filled line either way; 0.40 sits in
that empty gap in both.

`resume/measure.py` predicts rendered width to a median 0.4%, worst 1.4%, over the 41 bullet,
summary and skills lines of a real resume - the text the page rules act on.

## Changing it

`My Settings/Search settings.yml`:

```yml
resume:
  font: Caladea
```

The name must match the folder in `app/resume/fonts/` and the name the font gives itself. To
add a family, put its `.ttf` files there in a folder of that name - regular and bold at
minimum, semibold used when present. `typeface.check()` runs before the first compile and says
what a folder is missing. Typst is handed that one folder and no system fonts, so a family can
never half-substitute another.

Measure before adopting one: render a full resume in it and count widows, as the table above
does. A font that reads beautifully and fits 90 characters a line is the wrong font here.

Only redistributable fonts. Caladea ships under the SIL Open Font License
(`app/resume/fonts/Caladea/OFL.txt`), which allows bundling and embedding in a PDF. Georgia,
Cambria, Calibri and Times New Roman are Microsoft-licensed and cannot be shipped, which is
what the metric-compatible open faces are for.
