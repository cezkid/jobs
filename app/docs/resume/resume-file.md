# Resume file in, PDF out - formats + token cost

What file a user's resume arrives as, how the program reads it, why the AI never opens it, and why
every resume Job Finder makes stays a PDF. Code: `app/resume/word.py` (Word), `import_pdf.extract`
(both), `resume-import prepare --file`.

## In: PDF or Word (.docx)

| File | How it's read | Measured |
|---|---|---|
| PDF w/ a text layer | PyMuPDF, content-stream order (`import_pdf.extract`) | Word-exported PDFs: bullet glyphs, MM/YY dates, combined headings fixed (plan-8yi, `test_word_resume_imports_whole_and_dated`) |
| Word .docx | stdlib zip + XML (`word.extract`): header, body, footer; hidden text, tracked deletions, field codes, the old-Word copy of a text box left out | 4 Word resume templates (2026-10-06): name + contact line first in all 4; 2 of 4 hold it in the page header, so the header is read first |
| .doc, .docm, .dotx, .rtf, .odt, .pages, .txt, Google Docs | refused w/ one step: "save a copy as Word Document (.docx) or PDF" (`word.refusal`) | - |
| Scanned PDF (no text layer) | refused (no text) | - |

A .docx carries its text as text: no glyph-id fonts, no column interleaving, list bullets kept as
numbering rather than characters - fewer of the PDF failure modes. Not measured head-to-head on
the same resume (no Word on the build machine to export a PDF twin).

Both formats go through the same gates: every string the AI maps must be in the extracted text
(`untraced`), 98% of its words must land somewhere (`recovery`), every left-out line read to the
user. The copy kept is `My Resume/Original resume.pdf` or `.docx`; `.data/resume-source.json` holds
the file `prepare` read + the exact text it handed out, and `finish` checks against that text. A second format never replaces or
deletes the first.

## Word-made test files

`app/tests/fixtures/word/` (plan-xku.2, 2026-10-06): a fake-data resume built by python-docx (page
header w/ name + contact, 2-column tables per job, bullets at 2 levels, a text box w/ the
certifications), opened + re-saved by Microsoft Word for Mac 16.113 over AppleScript, + Word's PDF
of it. Remake: [word-fixture/](word-fixture/). Author fields set to "CEZ Job Finder test" (Word
stamps the computer's account name).

| Finding | Measured |
|---|---|
| Word's own save | `docProps/app.xml` "Microsoft Office Word", rsid marks on every paragraph, header part kept |
| Text box | Word 16 wrote the DrawingML box only - no VML `mc:Fallback` copy (older Word's duplicate) |
| Same words both ways | .docx 163 words = its PDF 163, no word on one side only; both pass `untraced` + `recovery` w/ one mapping |
| Text a box clips | box too short for its 3rd line: the line stays in the .docx, the PDF loses it without a trace (`word-resume-clipped`). The Word reader keeps it - the user's own line, and recovery reads left-out lines to them anyway |
| Word for Mac's PDF | scripted "save as PDF" = macOS print path (producer "Quartz PDFContext"): bullets come out as U+2022, not Windows Word's private-use U+F0B7 / U+F0A7. The Windows exporter's glyphs stay covered by the made-up PDF in `test_word_resume_imports_whole_and_dated` |

Not covered: Windows Word's PDF exporter, and Word for Mac's "Best for electronic distribution"
PDF (made by a Microsoft online service - the file leaves the computer).

## Token cost - why the AI never opens the file

Real Claude tokens (Opus 5.5, the model Claude Code ran here), 2026-10-06. 4 Word resume templates
(resume-site samples, not committed) + 1 one-page resume PDF rendered from `master.example.yml`:

| What reaches the chat | Tokens | Chars per token | vs the extracted text |
|---|---|---|---|
| Text the program extracts (4 templates) | 1,756 - 2,273 | 2.3 - 3.0 | 1x |
| `word/document.xml` alone | 42,698 - 92,672 | 1.5 - 1.6 | **19x - 45x** |
| 1-page PDF opened w/ Claude Code's Read | 2,069 | - | 5.1x (its text: 402) |

Method, no API key: one headless `claude -p` session per file - the model runs one tool on it,
then answers; Claude Code's own transcript (`~/.claude/projects/*/<session>.jsonl`) records each
API call's input (`input_tokens` + cache creation + cache read). File tokens = call 2 minus call 1,
minus a 13-character control file's (174 via Bash `cat`, 151 via Read). XML sent in 20,000-char
pieces: one `cat` of a whole document.xml came back cut to a preview (Claude Code caps command
output), so an AI opening a .docx this way needs several reads; Read also cuts a file past its
token limit to a "PARTIAL view" (limit not in the docs). Character ratios (11x - 22x document.xml, 29x - 63x every XML part)
understated it: Word's XML packs 1.5 characters per token, the resume text 2.3 - 3.0. Other models'
tokenizers differ (Claude 4.7+ counts ~30% more than older Claude, platform docs) - the ratio is the
part that carries over. Claude Code's Read has no Word reader (docs list images, PDF, notebooks).
A PDF opened by the AI also skips the import's gates. Rule (`AGENTS.md` #Speed): the AI reads the
task file the program writes, never the resume file.

Dropped in Copilot's chat (VS Code's Local harness, source read 2026-10-06): a PDF goes whole to
Claude / GPT-5+ models only, without its path; a .docx arrives as a hex dump of its first ~128
bytes - no text, no path ([app-window.md](../app-window.md#copilots-chat---pinned-settings--what-a-dropped-file-becomes)).
Either way the program can't read that copy, so the user drags it onto My Resume (`AGENTS.md` #User).

## Out: PDF only

Every made resume is a PDF set in Caladea, page rules measured on the rendered page (`pages`,
`line-fill`, hygiene gates, [page-format.md](page-format.md)). A .docx reflows in each reader's
Word with whatever fonts it has - the page count and line fill the gates checked would not hold.
Greenhouse names both .pdf and .docx as files it reads; none of 35 PDF readings in our parser test
lost a word ([research: resume parser test](../../web/research/resume-parser-test.md)).

Declined (2026-10-06): a Word copy of the tailored resume. Some recruiters ask for Word (said in
career guides; how often not measured); the copy would be unchecked by every page gate. No
measured form refuses a PDF: Ashby's resume box takes pdf, doc, docx ([ashby.md](../apply/ashby.md));
Paylocity's `.doc,.docx,.pdf` ([paylocity.md](../apply/paylocity.md)); Greenhouse names .pdf.
Reopen on a user's report of a form or recruiter that won't take PDF. Bead filed; if built, it
goes out marked "not checked", the PDF stays the default.
