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
user. The copy kept is `My Resume/Original resume.pdf` or `.docx`; `.data/resume-source` names the
one `prepare` read so `finish` checks against that same text. A second format never replaces or
deletes the first.

## Token cost - why the AI never opens the file

| 4 Word resume templates, 2026-10-06 | Characters |
|---|---|
| Text the program extracts | 4,762 - 6,198 |
| `word/document.xml` | 11.0x - 22.4x the text |
| Every XML part in the package | 29x - 63x the text |

Measured by unzipping each file and counting characters, not tokens; XML usually costs more
tokens per character than prose, so the token gap is likely wider (not measured). Claude Code's
Read tool has no Word reader (docs list images, PDF, notebooks), so an AI opening a .docx itself
unzips it and reads that XML. A PDF opened by the AI comes back as page text + images - also more
than the extracted text, and it skips the gates. Rule (`AGENTS.md` #Speed): the AI reads the task
file the program writes, never the resume file.

Copilot gets a file dropped in its chat as data with no path: the program can't read that copy,
so the user drags it onto My Resume (`AGENTS.md` #User).

## Out: PDF only

Every made resume is a PDF set in Caladea, page rules measured on the rendered page (`pages`,
`line-fill`, hygiene gates, [page-format.md](page-format.md)). A .docx reflows in each reader's
Word with whatever fonts it has - the page count and line fill the gates checked would not hold.
Greenhouse names both .pdf and .docx as files it reads; none of 35 PDF readings in our parser test
lost a word ([research: resume parser test](../../web/research/resume-parser-test.md)).

Declined for now: a Word copy of the tailored resume. Some recruiters ask for Word (said in
career guides; how often not measured); the copy would be unchecked by every page gate. Bead filed; if built, it
goes out marked "not checked", the PDF stays the default.
