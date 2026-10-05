---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session, bead plan-xsy.65 (no drafting context; sources opened and the study rerun before the draft was read)
---
# Review: Are two-column resumes ATS friendly? We tested 7 layouts (`resume-parser-test.md`)

Verdict **revise**: 1 high, 7 medium, 9 low findings (all closed in plan-xsy.66: 16 fixed, 1 rebutted in part - see Resolution). Every study number in the draft
matches the committed results file, and the rerun is byte-identical. Each cited source says what
the draft says it says, with a few trims. The problems: a newer vendor test with the same free
readers (Enhancv, Aug 2026, 357 runs, 17 templates) is missing, and it found one-column templates
breaking too; the draft reads our data as backing "the failure isn't columns", when 4 of our 13
breaks were readers sorting text by position across two columns; the title promises an ATS test;
the icons result rests on drawn icons, not the icon fonts real templates use; the "copy it into a
text editor" check can't show what other readers do, which is the study's own main finding.

## Sources, read before the draft (all opened 2026-10-04, fresh downloads in `~/.cache/plan-xsy.65/`)

| id | What it actually supports | Limits |
|---|---|---|
| greenhouse-parse | Help page "Unsuccessful resume parse", last updated March 02, 2026. Parsing = Greenhouse "scans an imported resume and auto-fills" candidate fields; a failed parse leaves the resume "only been attached". Causes: file > 2.5MB; fake data ("First Last", town name skipped; "Company 1, Client 1, Any Company", "employee 1"); formatting: spaces between letters, graphics/photos/word art, image files, "tables, headers, and footers", name + contact in "header, footer, or text box", "columned layout", no clear sections, company names without Inc./LLC, abbreviated titles. Formatting issues "may result in a partial resume parse" | Written for recruiters adding candidates, not for job seekers; says what can fail, not how often. Page does not mention icons |
| mit-capd-ats | MIT CAPD guide: "boring is better"; avoid graphics, icons, images, tables, text boxes; artistic resumes kept for "direct-delivery methods" when the field values design; plain-text (.txt) self-test, where "text in the wrong order" points to text boxes or columns; Canva/LaTeX/builders may "confound the ATS"; opens with "about 99% of Fortune 500" (unsourced on the page) | Career-office guide (Convention); no test behind it |
| resumap-2026 | dev.to post, 2026-07-28, by Resumap staff (discloses the 36 templates are theirs). One synthetic engineer, 3 jobs, 15 bullets, 36 templates from one PDF renderer, into Zoho Recruit, Manatal ("AI match scoring rather than parsing"), Workable, Textkernel. Table: email + phone 36/36 on all three parsers shown; all 3 jobs segmented Zoho 34, Workable 36, Textkernel 31; location Textkernel 31; skills Zoho 27, Textkernel 36. Quote "The failure mode isn't columns. It's text-stream order." "Several" two-column layouts scored perfectly, "several" one-column didn't - no counts. Also: before testing, the text layer of every PDF was checked and "the words were present, in the right order, in the file". Advises `pdftotext -layout` to see what a parser sees | Vendor test, no per-template breakdown in the post, not peer-reviewed. Its own text-layer check says every file was in order, so its failures are not explained by stored order - the post's "emission order" explanation is not shown by its own numbers |
| textkernel-2023 | Textkernel blog, datePublished 2023-10-18. "at least 15% of CV documents use a column layout" - later in the same post "they only account for about 10-15% of documents". First step of extraction = convert to raw text; top-down left-to-right is enough for standard layouts, mixes column sections. Results: visual-gap decisions 82% -> 91% (600+ gaps), column gaps 60% -> 82%; "well-rendered CVs increased from 62% to 90%" on "about 700 CVs" judged side-by-side by its own annotators (subjective); contact fill rates +4-10 points on 12,000+ CVs | Maker's own test, method in outline; the 700 were judged by its staff; post says it inconsistently (15% vs 10-15%) |
| bast-2017 | Authors' PDF of JCDL 2017 paper. Abstract: PDF specifies "fonts and positions of the individual characters rather than the semantic units"; 14 tools, 12,098 arXiv articles. p. 9 (sec. 4.4): "In principle, all tools are able to identify the correct reading order of words. However, some tools have problems with two-column articles" (pdf2xml, pdf-extract named); PdfMiner merges hyphenated words | Scientific articles, not resumes; 2017 tool versions; the authors' copy carries a placeholder DOI (registry DOI is the IEEE one) |

No text in any source addressed an AI (all five scanned for instruction-like text).

Searched for newer or contrary work (2026-10-04): "two-column resume ATS parsing test study 2025 2026", "Workday resume parsing two column documentation", Lever help. Found and opened:

- **Enhancv, "Two-column resume ATS test"** (enhancv.com/blog/two-column-resume-ats-test/, Aug 24, 2026, updated Sept 30, 2026; read via a summarising fetch, re-open in full before citing). A resume builder that sells two-column templates. 357 extraction runs: 3 resumes x 17 of its templates x 7 extraction modes - pdftotext (layout, default, raw), PyMuPDF sorted + unsorted, pdfminer.six, pypdf. Word recovery within half a point between one and two columns; "section integrity" worst case 35% two-column vs 60% one-column, about 1 point apart with newer modes; an AI model reading the text cut the gap to about 3 points. Vendor survey; same readers as ours.
- **ATS Verification, "ATS parsing benchmark 2026"** (atsverification.com, June 30, 2026; summarising fetch). Founder of a resume-scanner business; one resume, 6 layouts, one pdf.js-based extractor + its own detectors (not an employer system). Two-column + sidebar the only layout with a reading-order flag; header contact read 3 times; skills grid and curly quotes fine. Vendor survey, very small.
- Lever help article 20087345054749 opened again: page returns only "CSS Error" to scripts; no Wayback copy (`archived_snapshots: {}`). No Workday or Lever maker's page on layout found. Several SEO blogs claim Workday reads "strictly left-to-right" - no primary source; not usable.

## Study rerun (step 1b)

- `uv run app/web/parser_test.py build --check` -> exit 0 (PDFs + truth byte-identical).
- `uv run app/web/parser_read.py > scratch/readings.json` -> `cmp` with committed `readings.json`: identical.
- `uv run app/web/parser_test.py score scratch/readings.json > scratch/results.csv` -> `cmp` with `results.csv`: identical; sha1 `1d4b7c35...` both; `resume-parser-test-2026-10.csv` = `results.csv` (cmp).
- Numbers in the draft vs the CSV: broke per layout one-column 0, header-footer 0, icons 0, sidebar 2 (pymupdf-sort, pypdf-layout), table 2 (pdfminer, pymupdf), text-boxes 4 (all but pdfminer), spaced-headings 5 -> total 13 of 35: match. lost_words 0 in all 35; email + phone true in all 35: match. split_words 4 in each spaced-headings row, raw text "S U M M A R Y", "E X P E R I E N C E", "E D U C A T I O N", "S K I L L S" in all 5: match. "PresentCity" only in sidebar/pymupdf-sort: match. table/pdfminer first line "SUMMARY": match. text-boxes pymupdf + pypdf: first line "EXPERIENCE", name + contact last two lines: match. header-footer: all 5 read the name first and email/phone/city last, after "Languages": match.

## Claim table

Counts: the article has 16 citation groups and 16 source-id citations (`grep -o '\[@[^]]*\]' | wc -l` = 16; per-id `grep -o '@[a-z0-9-]*'` = 16: greenhouse-parse 7, resumap-2026 4, bast-2017 2, mit-capd-ats 2, textkernel-2023 1). The table has 72 rows (cited and uncited fact sentences, incl. own-measurement claims).

| # | Line | Claim (short) | Source | What the source says | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|---|
| 1 | 2 | Title: "Are two-column resumes ATS friendly? We tested 7 layouts" | own | No ATS tested; free PDF readers only | overstated | medium | See F3 |
| 2 | 3 | Description: plain never broke; spaced always; columns, tables sometimes | CSV | Matches | supported | - | Add "free PDF readers" stays; see F3 |
| 3 | SA1 | 1 resume, 7 layouts, 3 readers, 35 readings | CSV | 7 x 5 = 35 rows | supported | - | - |
| 4 | SA2 | Per-layout counts 0/5/4/2/2 | CSV | Match | supported | - | - |
| 5 | SA3 | Email + phone exact in all 35; no lost words | CSV | Match | supported | - | - |
| 6 | SA4 | Greenhouse warns against the same layouts | greenhouse-parse | Spaces, tables, header/footer, text box, columns: yes; icons not named | supported | low | "most of the same layouts" |
| 7 | 34 | Two-column = gamble; sidebar 2 of 5; plain 0 of 5 | CSV | Match; but Enhancv found one-column templates failing too | needs caveat | high | See F1 |
| 8 | 36 | Made-up resume, 3 jobs, degree, two skill lines | facts.yml | Match | supported | - | - |
| 9 | 36 | Read 5 ways with 3 readers | METHOD.md | Match | supported | - | - |
| 10 | 38 | ATS = software employers use to collect applications | - | Definition | supported (convention) | - | - |
| 11 | 38 | Greenhouse scans an uploaded resume and fills applicant fields | greenhouse-parse | "scans an imported resume and auto-fills" | supported | - | - |
| 12 | 38 | Reading the text is the first step | (uncited) | Textkernel: "The first step ... is to convert documents into raw text" | unsupported as placed | low | Cite textkernel-2023 |
| 13 | 38 | Scrambled text -> every later step scrambled | textkernel-2023 (implied) | Textkernel: "any mistake will impact the performance of subsequent steps" | supported if cited | low | Same cite as row 12 |
| 14 | 40 | 13 of 35 broke | CSV | Match | supported | - | - |
| 15 | 40 | Definition of "broken" | METHOD.md | Omits lost words + email/phone not exact | incomplete | low | See F12 |
| 16 | 42-52 | Bars: 7 layouts, counts | CSV | Match | supported | - | - |
| 17 | 54 | Safest layout was the plainest | CSV | Within our 7 | supported | - | - |
| 18 | 58 | Summary from committed results file | CSV | Yes | supported | - | - |
| 19 | 63 | Header/footer: every reader put the contact line last | readings.json | Yes, 5/5 | supported | - | - |
| 20 | 64 | Icons: nothing broke | CSV | Icons were drawn shapes, not characters (METHOD.md) | needs caveat | medium | See F4 |
| 21 | 65 | Sidebar: read across both columns line by line | readings.json | pymupdf-sort, pypdf-layout | supported | - | - |
| 22 | 66 | Table: dates split from title | CSV | 0/3 job headers, 2 readers | supported | - | - |
| 23 | 67 | Text boxes: name last, or columns mixed | readings.json | Yes | supported | - | - |
| 24 | 68 | Spaced headings: every heading split | readings.json | Yes, all 4 in all 5 | supported | - | - |
| 25 | 70 | All four headings into single letters, e.g. "E X P E R I E N C E" | readings.json | Exact | supported | - | - |
| 26 | 70 | A search for "Experience" would not find that heading | logic | Inference from text; true for a word search | supported (inference) | low | "A word search" is fine; keep as our reasoning |
| 27 | 70 | Only layout that broke every reading | CSV | Yes | supported | - | - |
| 28 | 72 | Designer templates often place boxes in one order and save them in another | none | No source; our layout was built that way on purpose | unsupported | medium | See F5 |
| 29 | 72 | Two readings kept saved order, name + contact last | readings.json | pymupdf, pypdf | supported | - | - |
| 30 | 72 | Two others mixed education/skills into job bullets | readings.json | pymupdf-sort, pypdf-layout | supported | - | - |
| 31 | 74 | Sidebar: two readings across both columns; "PresentCity" in one | readings.json | Yes | supported | - | - |
| 32 | 74 | Other three read sidebar + main column as separate blocks, in order | CSV | broke=false for 3 | supported | - | - |
| 33 | 76 | Table: two readings dates on another line | CSV | Yes | supported | - | - |
| 34 | 76 | One read left column first, "Summary" before the name | readings.json | pdfminer first line SUMMARY | supported | - | - |
| 35 | 78 | Header/footer: no break by our rules; all 5 read contact last after Skills | readings.json | Yes | supported | - | - |
| 36 | 78 | A system expecting contact near the top could miss them | logic | Greenhouse lists contact in header/footer as a parse risk | supported if cited | low | Cite greenhouse-parse here |
| 37 | 80 | Damage = order + word shape; no lost word; email/phone exact in 35 | CSV | Yes | supported | - | - |
| 38 | 84 | Greenhouse lists spaces between letters, tables, headers/footers, columns; name/contact in header, footer, text box | greenhouse-parse | Yes, word for word | supported | - | - |
| 39 | 84 | Those are the layouts that broke readings or moved the contact line | CSV + greenhouse-parse | Yes for spaced, table, columns, text boxes, header/footer | supported | - | - |
| 40 | 86 | Greenhouse skips names it takes for fake data ("First Last", "Company 1") | greenhouse-parse | Yes | supported | - | - |
| 41 | 86 | A commercial parser might skip "Your Name"/"Company A" | greenhouse-parse | Reasonable; Greenhouse's examples include "Any Company" | supported (hedged) | - | - |
| 42 | 88 | MIT: "boring is better"; avoid tables, text boxes, icons | mit-capd-ats | Yes | supported | - | Also cite MIT's "columns -> text in the wrong order" line (F9) |
| 43 | 88 | That is a guide, not a study | mit-capd-ats | Yes (Convention) | supported | - | - |
| 44 | 90 | No public Workday or Lever help page on layout; Lever page didn't load for our scripts | uncited | A Lever article exists but could not be read; reader-facing "for our scripts" is process detail | needs caveat | medium | See F6 |
| 45 | 94 | Textkernel sells a reader used inside other hiring systems | textkernel-2023 | "trusted by 2,500+ HR software vendors" | supported | - | - |
| 46 | 94 | 2023: at least 15% of resumes use columns | textkernel-2023 | Same post also says "about 10-15%" | cherry-picked | low | See F10 |
| 47 | 94 | Well-rendered test resumes 62% -> 90% | textkernel-2023 | About 700 CVs, judged side by side by its own annotators | needs caveat | low | See F10 |
| 48 | 96 | "Strongest outside test we found" says columns not the problem | resumap-2026 | Vendor test; Enhancv (Aug 2026) is larger and closer to ours and is missing | outdated / overstated | high | See F1 |
| 49 | 96 | Resumap: 1 resume, 36 of its templates, Zoho, Manatal, Workable, Textkernel | resumap-2026 | Yes; Manatal round is match scoring, not parsing | supported | low | "three resume readers plus Manatal's match scoring" |
| 50 | 98 | Email + phone 36/36 everywhere; Workable 36, Textkernel 31 for all 3 jobs | resumap-2026 | Table: yes | supported | - | - |
| 51 | 98 | Quote "the failure mode isn't columns. It's text-stream order." | resumap-2026 | Exact, 8 words | supported | - | - |
| 52 | 98 | Two-column did as well as one-column when the file stored text in reading order | resumap-2026 | Post: "Several" did; no counts; and its own check says every file was already in order | overstated | medium | See F2 |
| 53 | 98 | Run by a template seller, not peer-reviewed | resumap-2026 | Yes | supported | - | - |
| 54 | 100 | Our results fit that finding | CSV | Partly: 4 of 13 breaks were position-sorting readers on two-column pages | overstated | medium | See F2 |
| 55 | 100 | Two text-box readings broke from stored order | CSV + readings | Yes | supported | - | - |
| 56 | 100 | Sidebar broke only for position-sorting readings | CSV | Yes (pymupdf-sort, pypdf-layout) | supported | - | - |
| 57 | 102 | Bast + Korzen: 14 readers, 12,098 articles; some had trouble with two columns | bast-2017 p. 1, 9 | Yes; same paragraph: "In principle, all tools ... correct reading order" | needs caveat | low | See F11 |
| 58 | 102 | PDF stores position of each letter, not words or paragraphs | bast-2017 | Abstract: yes | supported | - | - |
| 59 | 104 | Column risky because you can't see stored order | own | Our sidebar's stored order was fine; position-sorting readers broke it | wrong reason | medium | See F2 |
| 60 | 108 | No study tests big hiring systems side by side with a published method | uncited | Resumap (4 systems, not Workday/Greenhouse/Lever) partly does; search list missing | needs caveat | low | See F13 |
| 61 | 109 | No study links parse errors to callbacks | uncited | None found by me either | supported | low | List searches in `uncited:` (F13) |
| 62 | 110 | Our files from Typst; each tool stores text in its own order | METHOD.md | Yes | supported | - | - |
| 63 | 111 | Greenhouse keeps the file attached when parse fails | greenhouse-parse | "only been attached" | supported | - | - |
| 64 | 112 | Greenhouse skips names that look fake | greenhouse-parse | Yes | supported | - | - |
| 65 | 116 | One column: 0 of 5 | CSV | Yes | supported | - | - |
| 66 | 117 | Spaced headings 5 of 5 | CSV | Yes | supported | - | - |
| 67 | 118 | Keep title, employer, dates on one line outside a table | CSV | Table broke 2 readers' job headers | supported | - | - |
| 68 | 119 | Name/email/phone in body; Greenhouse lists both places | greenhouse-parse | Yes | supported | - | - |
| 69 | 120 | Skip text boxes + designer templates online; keep for direct hand-over, as MIT suggests | mit-capd-ats | MIT: artistic resumes for design-valuing fields, by direct delivery | supported, slightly broadened | low | "If your field values design, MIT suggests ..." |
| 70 | 121 | Copy into a plain text editor; Resumap gives the same advice | resumap-2026 | Resumap: `pdftotext -layout`, not copy-paste; MIT gives the .txt test | misattributed + needs caveat | medium | See F7 |
| 71 | 121 | If it reads top to bottom, the order is right | own | Our sidebar read fine in 3 readers and broke 2 | overstated | medium | See F7 |
| 72 | 127-129 | App: one column, plain headings, black text; checks no tables, images, header/footer text, spaced letters; reads back in order | app/resume/render.py | Gates `no-table`, `no-images`, `no-header-footer`, `split-words`, `text-color`, `round-trip`, `single-column` (sorted vs stream) exist | supported | low | "Reads back with one reader (PyMuPDF), both orders" - see F14 |

## Findings (status: fixed or rebutted, plan-xsy.66)

High

- **F1 - Closest prior test is missing, and it complicates "plain one column never broke" (fixed; ATS Verification part rebutted).** Enhancv's "Two-column resume ATS test" (Aug 24, 2026, updated Sept 30, 2026) ran 357 extractions: 3 resumes x 17 templates x 7 modes, with the same readers we used (PyMuPDF sorted + unsorted, pdfminer.six, pypdf) plus pdftotext. Its worst-case "section integrity" was 35% for two columns and 60% for one column; newer modes closed the gap to about a point, and an AI model reading the text to about 3 points. It is a builder that sells two-column templates - label Vendor survey. It is the counter-evidence the brief asked for, it is larger than ours, and its one-column templates broke too. Fix: open the full page (not a summary), add it to `sources.yml` (vendor survey), report it in "Do modern resume readers handle columns fine?", replace "the strongest outside test we found" (line 96), and add to the description/SA that our clean control is one page we built, not every one-column template. Also add ATS Verification's 2026 benchmark (6 layouts, one pdf.js extractor; two-column the only reading-order flag) only if it adds something - it is small and a vendor.

Medium

- **F2 - Draft reads our data as backing "it's not columns", but our data show both causes (fixed).** Of 13 breaks: 5 spaced letters, 2 table rows, 2 text boxes from stored order, and 4 from readers that sort by position (sidebar x2, text boxes x2) - our sidebar file's stored order was right (file-order readers passed). So for position-sorting readers, columns themselves broke the reading. Line 100 "Our results fit that finding" and line 104 "risky because you can't see the order your file stores the text in" give one cause. Resumap's own pre-check also says every file was stored in order, so its "emission order" explanation is not shown by its numbers (line 98 "did as well ... when the file stored the text in reading order" is overstated; the post gives "several", no counts). Fix: "Columns broke readers that sort text by where it sits; stored order broke readers that keep the file's order. You can't control which kind an employer uses." Line 98: "Resumap says column count did not predict which layouts failed; it gives no counts."
- **F3 - Title promises an ATS test (fixed).** "Are two-column resumes ATS friendly? We tested 7 layouts" reads as 7 layouts in ATS. Searched wording is kept by e.g. "Are two-column resumes ATS friendly? A 7-layout PDF test" (52) or "Two-column resumes and ATS: we tested 7 layouts in 3 readers" (59). H1 question stays for search.
- **F4 - Icons result doesn't cover icon fonts (fixed).** METHOD.md: icons were "vector drawings, not characters". Many templates use icon fonts, whose glyphs come out as odd characters in the text. "Icons: 0 of 5, nothing" must say "drawn icons"; add to What we don't know: icon fonts untested. Same for SA2 if icons are named there.
- **F5 - Unsourced claim about designer templates (fixed).** Line 72 "Designer templates often place boxes on the page in one order and save them in another" - no source; our layout was built to do that. Fix: "Our text-box page saves its boxes in a different order than they appear, as placed-box designs can." or find a source.
- **F6 - Lever/Workday absence line (fixed).** Line 90: a Lever help article exists (20087345054749) but returns only "CSS Error" to scripts and has no archive copy; "We found no public help page from ... Lever" is not true, and "did not load for our scripts" is process talk for a reader. Fix: "We found no Workday page on this. Lever has a help page we could not open in October 2026." Put the search in `uncited:`; add a browser-check line to the ship bead for the Lever page.
- **F7 - Self-check advice misattributed and overstated (fixed).** Line 121: Resumap advises `pdftotext -layout`, not copying into a text editor; MIT is the source of the plain-text test (save as .txt; "text in the wrong order" -> text boxes or columns). And "If the text reads like your resume ... the order is right" is contradicted by our own sidebar: 3 readers in order, 2 scrambled - one viewer's copy shows only one reader. Fix: cite mit-capd-ats; add "This shows one reader's view. Others may read columns across, so a single column is still the safer choice."
- **F8 - Missing "what we don't know": AI-model readers (fixed).** Enhancv reports that an AI model reading the extracted text recovers most structure; many hiring systems now add AI steps. Our test stops at text extraction. Add one line.

Low

- **F9 - MIT also says columns put text in the wrong order (fixed).** Cite at line 88 next to text boxes; it is a second source for the columns point.
- **F10 - Textkernel numbers (fixed).** "at least 15%" - same post later says "about 10-15%": use "10-15%". The 62% -> 90% was about 700 CVs judged side by side by Textkernel's own staff - say so.
- **F11 - Bast context (fixed).** Same paragraph says "In principle, all tools are able to identify the correct reading order"; problems were with two-column articles in some tools (2017 versions). Add "in 2017" and "most readers handled order".
- **F12 - "Broken" definition incomplete (fixed).** Line 40 omits lost words and wrong email/phone (none happened, but the rule should be complete); line 40 also runs 27 words - split.
- **F13 - Search list missing (fixed).** `uncited:` has "No study found" but no list of what was searched (research.md rule). Add the searches (callback link, side-by-side ATS test, Workday/Lever docs). Line 108: Resumap did test 4 commercial systems side by side - narrow to "Workday, Greenhouse, Lever or iCIMS".
- **F14 - Tool box precision (fixed).** Line 129 "Reads each page back" - the gate reads with PyMuPDF only, in sorted and file order (`render.py` `round-trip`, `single-column`). Accurate but say "with one reader, two ways" so it doesn't promise more than our own study says one reader shows.
- **F15 - Line 36/38 cite (fixed).** "Reading the file's text is the first step" + "every later step works from scrambled text" are uncited; Textkernel says both. Cite textkernel-2023.
- **F16 - Resumap Manatal (fixed).** Manatal round was "AI match scoring rather than parsing" (post). Line 96 lists it among systems files were loaded into for parsing - add "(match scoring)" or drop.
- **F17 - SEO for "do ATS read tables" + "can ATS read PDF" (fixed).** No heading answers them. Add short H2s ("Do ATS read tables?" from the table result; "Can ATS read a PDF?" - yes when its text is real text, Greenhouse parses .pdf; image files fail).

## Checks

- Sources read first: all 5 cited ids opened and noted above before the article was read; the cited-id list was extracted with `grep -o` without reading the text.
- Every cited id appears in this review: `for id in $(grep -o '@[a-z0-9-]*' app/web/research/resume-parser-test.md | sort -u | tr -d @); do grep -q "$id" app/web/research/reviews/resume-parser-test.md || echo MISSING $id; done` -> no output.
- Own numbers: all reproduced from the rerun (section above); `uncited:` snippets cover them.
- Quotes: "boring is better" (3 words), Resumap quote (8 words) - both <= 15, attributed.
- Labels: greenhouse-parse + textkernel-2023 Maker's docs, resumap-2026 Vendor survey, mit-capd-ats Convention, bast-2017 Lab study - all match research.md; the body says "Maker's docs", "template seller", "guide, not a study", "peer-reviewed benchmark".
- Privacy: placeholders only ("Your Name", "Company A-C", example.com, 555-01xx); no owner data; Greenhouse, Workday, Lever, Textkernel named as products, not employers.
- "For you," used twice (lines 54, 104) - at the cap.
- Jargon: "parse" (lines 84, 119) unexplained - "read into its fields"; "well-rendered" (94) - "read in the right order"; "text-stream order" only inside the quote - explain after it.
- Links: `what-makes-a-good-resume.md#does-layout-matter` exists (H2 line 135); data page, ats-rejection-myth, methods exist. 4 links out; revise bead adds >= 2 links in from siblings (Wave 1 lessons).
- Title 56 chars, description 148 chars; body 1,584 words; `uv run app/web/pages.py --check` exit 0.

## Re-review (2026-10-04, fresh session)

Fresh subagent, no editing context. Read `git diff HEAD` of the article, `sources.yml`, the three sibling pages and `page-format.md`, then the full current article, and checked every new or changed sentence against the cached primary text (`~/.cache/plan-xsy.65/`: `gh.txt` l. 27-64, `mit.txt` l. 100-127, `tk.txt` l. 63-66, 96, 115, `resumap.txt` l. 43-50, 99-100, 115, `bast.txt` l. 1881-1882; `~/.cache/plan-xsy.66/enhancv.txt` full text + `enhancv.html` dates/byline) and our own `results.csv`, `readings.json`, `METHOD.md` and `app/resume/render.py` (`round-trip`, `single-column`, PyMuPDF sort on/off). Confirmed: Enhancv 3 resumes x 17 templates x 7 modes = 357, words within half a point, email/phone (plus location, link) right in all 357, worst-method section integrity 35% vs 60%, about one point under another method, AI step to about three points, employer names 100% -> 83%, 10 customer resumes / 4 models, "No data here shows that any resume layout costs or wins an interview", Pub 8/24/2026, Upd 9/30/2026, author Doroteya Vasileva; Textkernel "about 10-15%" and 62% -> 90% on about 700 CVs judged side by side by its annotators; MIT .txt test + "Text in the wrong order ... text boxes ... columns" + design-field note; Greenhouse .pdf/.docx, image upload, header/footer/text box, columned layout; Bast "In principle, all tools ..." p. 9; own split 13 = 5 spaced + 2 table (file-order readers) + 4 position-sorting (sidebar, text boxes) + 2 stored-order (text boxes). Mechanics: quotes exact and <= 15 words ("boring is better" 3, Resumap 8, case-lowered first word only); every cited id in the registry; Enhancv label `vendor survey` matches Resumap's and the page says "Vendor survey"; "For you," 2; Short answer 4 bullets; title 56 chars, description 142; no body sentence over 21 words (the bold-led spaced-headings sentence is 21 after its label); 2 inbound links from published siblings (`ats-rejection-myth`, `what-makes-a-good-resume`) plus the data page, 4 out. `pages.py --check` fails only on this file's `verdict: revise`. Nothing in any source addressed an AI (Enhancv's expert quotes and AI-test text are data).

- F1 addressed (Enhancv in registry + body + SA3; "Our plain page" in description + SA; ATS Verification left out, rebuttal stands).
- F2 addressed (both causes with counts; Resumap "gives no counts"; "can't control which kind of reader").
- F3 addressed ("A 7-layout PDF test"; SA1 + description say no employer system).
- F4 addressed (bars, table, Icons paragraph, What we don't know).
- F5 addressed ("Our text-box page saves its boxes ... as placed-box designs can").
- F6 addressed on the page (Workday absence in `uncited:`; Lever "could not open ... so we do not cite it"); browser-check line for the ship bead not visible here.
- F7 addressed (MIT cited; one-reader caveat added).
- F8 addressed. F9 addressed. F10 addressed. F11 addressed. F12 addressed (lost words + email/phone added; split into 4 sentences).
- F13 addressed (side-by-side line narrowed; searches named in body, "We searched" in `uncited:`).
- F14 addressed. F15 addressed. F16 addressed. F17 addressed (two H2s, cited).

New findings:

- **R1 - Spaced-headings result clashes with the sibling sentence next to the new inbound link (fixed).** `what-makes-a-good-resume.md` l. 139: a spaced heading came back split from one converter, "Three other PDF text readers read it whole" (September, +0.08em, `page-format.md`); the next sentence links here, where "Every reader split all four headings" and the layout "broke every reading" (+0.25em). The article never says how wide its spacing was, so a reader sees PyMuPDF, pdfminer and pypdf both reading and not reading spaced headings. Fix: article - "Our headings had a quarter of a letter's width between letters" (or similar) in the Spaced-out headings paragraph; sibling - "In our October test, wider spacing split the headings in every reader: [Are two-column resumes ATS friendly?](resume-parser-test.md)".
- **R2 - "parser" / "parse" still unexplained in body text (fixed, low).** F-review Checks flagged "parse"; SA + Greenhouse section now say "read into its fields", but l. 90 "stop its parser reading", l. 100 "Its parser skips names", "A commercial parser might", l. 133 "read the parsed text ... when its parse fails", l. 134 "its parser skips" remain. Fix: "its resume reader" / "a commercial resume reader"; l. 133 "How often recruiters read the text the system pulled out instead of the file. Greenhouse keeps the file attached even when it can't read it into fields".

## Resolution (plan-xsy.66, 2026-10-04)

All F and R findings are closed. Notes where the fix is partial or a finding is rebutted:

- F1: Enhancv page opened in full (`~/.cache/plan-xsy.66/enhancv.txt`), registry `enhancv-2026` (vendor survey). ATS Verification benchmark left out (rebutted): only read through a summary, one resume, one pdf.js extractor plus the seller's own detectors - adds nothing Enhancv's larger test with our readers does not. Enhancv's footer link "LLMs come read here" addresses AIs - data, ignored.
- F6: Workday absence is our search (`uncited:`); Lever article named as unopened. Browser check of Lever article 20087345054749 added to ship bead plan-xsy.80.
- F17: two H2s added ("Do ATS read tables?", "Can ATS read a PDF?"), each from our data + greenhouse-parse.
- R1: article now gives the spacing (a quarter of a letter's width); sibling `what-makes-a-good-resume.md` says wider spacing split the headings in every reader. `app/docs/resume/page-format.md` records the study line (+0.25em -> split in all 5 readings).
- R2: "parser" / "parse" in body replaced by "resume reader" / "fill in the fields"; `greenhouse-parse` stays as a source id only.
- Links in: `what-makes-a-good-resume.md`, `ats-rejection-myth.md`, data page `resume-parser-test-2026-10.md`. Out: what-makes-a-good-resume, ats-rejection-myth, data page, methods.
