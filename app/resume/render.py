import argparse
import difflib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pymupdf
import typst

import cfg
from resume import schema

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "templates" / "resume.typ"
FONTS = HERE / "fonts"
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SEP = " | "
WORD = re.compile(r"\w+")
LIGATURE = re.compile("[\ufb00-\ufb06]")
# XMP fields naming engine or build time; title, language, pdfuaid stay for PDF/UA-1
XMP_LEAK = re.compile(r"<(xmp:CreatorTool|xmp:CreateDate|xmp:ModifyDate|xmp:MetadataDate|pdf:Producer)>[^<]*</\1>")
INFO_LEAK_KEYS = ("author", "creator", "producer", "creationDate", "modDate")
# round-trip gate, plan #Verification gates
MIN_RECOVERY = 0.98
# Ladders/Kickresume: summary cap = longest block detectors never get to read as prose
MAX_BLOCK_WORDS = 57
MAX_BYTES = 1_000_000
WORD_BUDGET = (500, 650)
MAX_PAGES = 2
MIN_LAST_PAGE_FILL = 0.6
# density sets tailor's word window: two-page floor = 1.6 x words/page, so denser page => narrower window
# measured 2026-09-17: these give 312 words/page (window 500-623) + CPL 97; 407-499 words/page yields NO window
MARGIN_X_IN = 1.05
MARGIN_Y_IN = 0.75
PT_PER_IN = 72


def month_label(value: str) -> str:
    if value == schema.PRESENT:
        return "Present"
    year, month = value.split("-")
    return f"{MONTH_NAMES[int(month) - 1]} {year}"


def span_label(entry: dict) -> str | None:
    if "start" not in entry or "end" not in entry:
        return None
    return f"{month_label(entry['start'])} - {month_label(entry['end'])}"


def joined(*parts) -> str | None:
    kept = [p for p in parts if p]
    return SEP.join(kept) if kept else None


def page_model(master: dict) -> dict:
    """Master facts -> exactly what lands on page, in page order. Tailorer emits same shape."""
    contact = master["contact"]
    sections = [{
        "title": "Experience",
        "entries": [{
            "id": r["id"], "heading": r["title"], "org": r["company"],
            "subline": joined(span_label(r), r.get("location"), r.get("blurb")),
            "bullets": [b["claim"] for b in r["bullets"]],
        } for r in master["roles"]],
    }]
    if master.get("projects"):
        sections.append({"title": "Projects", "entries": [{
            "id": p["id"], "heading": p["name"], "subline": span_label(p), "bullets": [b["claim"] for b in p["bullets"]],
        } for p in master["projects"]]})
    if master.get("skills"):
        sections.append({"title": "Skills", "lines": [
            {"label": g["group"], "text": ", ".join(g["items"])} for g in master["skills"]
        ]})
    if master.get("education"):
        sections.append({"title": "Education", "lines": [{"text": joined(
            ", ".join(p for p in (s["degree"], s.get("field")) if p), s["institution"], s.get("details"),
            s.get("end", "")[:4],
        )} for s in master["education"]]})
    if master.get("certifications"):
        sections.append({"title": "Certifications", "lines": [
            {"text": joined(c["name"], c.get("issuer"), c.get("date") and month_label(c["date"]))}
            for c in master["certifications"]
        ]})
    if master.get("languages"):
        sections.append({"title": "Languages", "lines": [{"text": ", ".join(master["languages"])}]})
    return {
        "title": f"{contact['name']} Resume",
        "contact": {
            "name": contact["name"],
            "parts": [p for p in (contact["location"], contact["email"], contact.get("phone"), *contact.get("links", [])) if p],
        },
        "summary": master.get("summary"),
        "sections": sections,
    }


def with_page(model: dict) -> dict:
    return {**model, "page": {"margin_x_in": MARGIN_X_IN, "margin_y_in": MARGIN_Y_IN}}


def page_strings(model: dict) -> list[str]:
    out = [model["contact"]["name"], SEP.join(model["contact"]["parts"])]
    if model["summary"]:
        out.append(model["summary"])
    for s in model["sections"]:
        out.append(s["title"].upper())
        for e in s.get("entries", []):
            out.append(joined(e["heading"], e.get("org")))
            if e.get("subline"):
                out.append(e["subline"])
            out.extend(e["bullets"])
        for line in s.get("lines", []):
            out.append(f"{line['label']}: {line['text']}" if line.get("label") else line["text"])
    return out


def file_name(model: dict) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", re.sub(r"\s+", "_", model["contact"]["name"].strip())) + "_Resume.pdf"


def compile_pdf(model: dict) -> bytes:
    pdf = typst.compile(
        str(TEMPLATE), font_paths=[str(FONTS)], ignore_system_fonts=True,
        sys_inputs={"data": json.dumps(with_page(model), ensure_ascii=False)}, pdf_standards="ua-1",
    )
    return scrub(pdf, model["title"])


def scrub(pdf: bytes, title: str) -> bytes:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        doc.set_metadata({"title": title, **dict.fromkeys(INFO_LEAK_KEYS, "")})
        doc.set_xml_metadata(XMP_LEAK.sub("", doc.get_xml_metadata()))
        return doc.tobytes(garbage=3, deflate=True)


def tokens(text: str) -> list[str]:
    return WORD.findall(text.casefold())


def pdftotext(path: Path, mode: str | None) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not on PATH - install poppler (poppler-utils)")
    argv = [exe, "-enc", "UTF-8", *([mode] if mode else []), str(path), "-"]
    return subprocess.run(argv, capture_output=True, check=True).stdout.decode("utf-8")


def first_divergence(a: list[str], b: list[str]) -> str:
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"word {i}: {' '.join(a[i:i + 6])!r} vs {' '.join(b[i:i + 6])!r}"


def check(path: Path, model: dict, budget: bool) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    reading, layout, raw = (pdftotext(path, m) for m in (None, "-layout", "-raw"))
    want = [t for s in page_strings(model) for t in tokens(s)]
    got = tokens(reading)
    matcher = difflib.SequenceMatcher(None, want, got, autojunk=False)
    recovered = sum(block.size for block in matcher.get_matching_blocks()) / max(len(want), 1)
    gate("round-trip", recovered >= MIN_RECOVERY, f"{recovered:.1%} in-order word recovery (floor {MIN_RECOVERY:.0%})")

    orders = {"layout": tokens(layout), "raw": tokens(raw)}
    diverged = [f"{mode} {first_divergence(got, seq)}" for mode, seq in orders.items() if seq != got]
    gate("single-column", not diverged, "; ".join(diverged) or "default = layout = raw")
    gate("ligatures", not LIGATURE.search(reading), "U+FB00-FB06 absent")
    missing = [part for part in model["contact"]["parts"] if part.casefold() not in reading.casefold()]
    gate("contact-in-body", not missing, f"missing from text layer: {missing}" if missing else "every contact part in text layer")
    abbreviated = schema.ABBREVIATED_TITLE.findall(reading)
    gate("no-abbreviated-title", not abbreviated, f"{len(abbreviated)} Sr./Jr.")

    longest = max(len(tokens(s)) for s in page_strings(model))
    gate("no-prose-block", longest <= MAX_BLOCK_WORDS, f"longest block {longest} words (cap {MAX_BLOCK_WORDS})")
    size = path.stat().st_size
    gate("size", size <= MAX_BYTES, f"{size / 1000:.0f}KB (ceiling {MAX_BYTES // 1000}KB)")

    with pymupdf.open(path) as doc:
        fonts = {f[0]: f for pno in range(doc.page_count) for f in doc.get_page_fonts(pno)}
        bad_fonts = [
            f[3] for xref, f in fonts.items()
            if f[1] == "n/a" or doc.xref_get_key(xref, "ToUnicode")[0] == "null"
        ]
        gate("fonts", bool(fonts) and not bad_fonts, f"{len(fonts)} embedded w/ ToUnicode" if not bad_fonts else f"missing embed/ToUnicode: {bad_fonts}")
        images = sum(len(page.get_images()) for page in doc)
        gate("no-images", images == 0, f"{images} images")

        catalog = doc.xref_object(doc.pdf_catalog())
        struct_types = {m for x in range(1, doc.xref_length()) for m in re.findall(r"/S /(\w+)", doc.xref_object(x))}
        gate("tagged", "/StructTreeRoot" in catalog, "StructTreeRoot present")
        gate("no-table", not struct_types & {"Table", "TR", "TD", "TH"}, "no Table struct elements")

        leaks = [k for k in INFO_LEAK_KEYS if doc.metadata.get(k)]
        info = doc.xref_get_key(-1, "Info")
        if info[0] == "xref" and doc.xref_get_key(int(info[1].split()[0]), "Company")[0] != "null":
            leaks.append("Company")
        leaks += XMP_LEAK.findall(doc.get_xml_metadata())
        gate("metadata-wiped", not leaks, f"leaks: {leaks}" if leaks else "creator/producer/author/company/dates empty")

        top, bottom = text_area(doc)
        stray = [y for page in baselines(doc) for y in page if not top < y <= bottom]
        gate("no-header-footer", not stray, f"{len(stray)} text spans outside top/bottom margin")

        words = len(got)
        used = pages_used(doc)
        pages, fill = doc.page_count, used - doc.page_count + 1
        page_ok = pages == 1 or (pages <= MAX_PAGES and fill >= MIN_LAST_PAGE_FILL)
        detail = f"{words} words (target {WORD_BUDGET[0]}-{WORD_BUDGET[1]}), {pages} page(s), last {fill:.0%} full"
        if budget:
            ok = WORD_BUDGET[0] <= words <= WORD_BUDGET[1] and page_ok
            windows = " or ".join(f"{low}-{high}" for low, high in word_windows(words, used)) or "none at this density"
            gate("budget", ok, detail if ok else f"{detail}; words fitting page rules at this density: {windows}")
        else:
            windows = " or ".join(f"{low}-{high}" for low, high in word_windows(words, used)) or "NONE at this density"
            gate("budget (info)", True, f"{detail}; tailored page fits at {windows}")
    return results


def text_area(doc) -> tuple[float, float]:
    top = MARGIN_Y_IN * PT_PER_IN
    return top, doc[0].rect.height - top


def baselines(doc) -> list[list[float]]:
    # baselines, never bboxes: 20pt name's ascender overshoots margin while baseline sits in flow
    return [
        [s["origin"][1] for b in page.get_text("dict")["blocks"] for line in b.get("lines", []) for s in line["spans"]]
        for page in doc
    ]


def pages_used(doc) -> float:
    """Full pages before last + last page's filled fraction: 1.35 = page 2 35% full."""
    top, bottom = text_area(doc)
    return doc.page_count - 1 + (max(baselines(doc)[-1], default=top) - top) / (bottom - top)


def word_windows(words: int, used: float) -> list[tuple[int, int]]:
    """Word counts passing budget gate if page density holds: one page, or two w/ last page past fill floor."""
    per_page = words / used
    one = (WORD_BUDGET[0], min(WORD_BUDGET[1], math.floor(per_page)))
    two = (max(WORD_BUDGET[0], math.ceil(per_page * (MAX_PAGES - 1 + MIN_LAST_PAGE_FILL))), min(WORD_BUDGET[1], math.floor(per_page * MAX_PAGES)))
    return [w for w in (one, two) if w[0] <= w[1]]


def render(model: dict, out_dir: Path, budget: bool) -> tuple[Path, list[tuple[str, bool, str]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / file_name(model)
    path.write_bytes(compile_pdf(model))
    return path, check(path, model, budget)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render resume details straight through, no tailoring; run PDF gates")
    ap.add_argument("--master", type=Path, help="master yml (default config resume.master)")
    args = ap.parse_args()
    started = time.perf_counter()
    master_path = args.master or cfg.resume_path(cfg.load(), "master")
    master = schema.load(master_path)
    path, results = render(page_model(master), master_path.parent, budget=False)
    for name, ok, detail in results:
        print(f"  {'pass' if ok else 'FAIL'}  {name:22} {detail}")
    for gap in schema.employment_gaps(master, date.today()):
        print(f"  gap   {gap['after']} -> {gap['before']} ({gap['months']} months)")
    print(f"wrote {path} in {time.perf_counter() - started:.2f}s")
    if not all(ok for _, ok, _ in results):
        sys.exit("render gates failed")


if __name__ == "__main__":
    main()
