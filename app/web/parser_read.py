# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf==1.28.2", "pdfminer.six==20260107", "pypdf==6.19.0"]
# ///
"""Resume parser test: run each open-source PDF reader on the corpus, print what it reads as JSON.

  uv run app/web/parser_read.py > readings.json                # every PDF in the study's pdf/ folder
  uv run app/web/parser_read.py some/folder > readings.json    # every PDF in another folder (tests)

Own pinned deps (inline above), so the project's packages stay untouched. Readers + calls are fixed in
app/web/research/resume-parser-test-2026-10/METHOD.md "Readers"; each call is one reader in the output:
{"versions": {...}, "readers": {reader: {layout: text}}}. Score with app/web/parser_test.py score.
"""

import json
import sys
from importlib.metadata import version
from pathlib import Path

import pymupdf
import pypdf
from pdfminer.high_level import extract_text

PDF = Path(__file__).resolve().parent / "research" / "resume-parser-test-2026-10" / "pdf"


def pymupdf_text(path: Path, sort: bool) -> str:
    with pymupdf.open(path) as doc:
        return "".join(page.get_text("text", sort=sort) for page in doc)


def pypdf_text(path: Path, mode: str) -> str:
    return "\n".join(page.extract_text(extraction_mode=mode) for page in pypdf.PdfReader(path).pages)


READERS = {
    "pymupdf": lambda p: pymupdf_text(p, sort=False),
    "pymupdf-sort": lambda p: pymupdf_text(p, sort=True),
    "pdfminer": lambda p: extract_text(p),
    "pypdf": lambda p: pypdf_text(p, "plain"),
    "pypdf-layout": lambda p: pypdf_text(p, "layout"),
}


def read(folder: Path) -> dict:
    pdfs = sorted(folder.glob("*.pdf"))
    return {
        "versions": {pkg: version(pkg) for pkg in ("pymupdf", "pdfminer.six", "pypdf")},
        "readers": {name: {p.stem: fn(p) for p in pdfs} for name, fn in READERS.items()},
    }


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    sys.stdout.write(json.dumps(read(folder), ensure_ascii=False, indent=1, sort_keys=True) + "\n")
