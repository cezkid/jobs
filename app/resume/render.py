import argparse
import difflib
import json
import math
import re
import sys
import time
from datetime import date
from pathlib import Path

import pymupdf
import typst

import cfg
from resume import schema, typeface

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "templates" / "resume.typ"
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
MAX_PAGES = 2
MIN_LAST_PAGE_FILL = 0.6
# a one-page resume is judged full from here: the floor is a share of what this page holds,
# never a fixed count. The fixed 500 it replaced sat above a full page (378 words in Caladea),
# so the one-page window was empty and every one-page resume failed the budget - the page
# length best practice prefers for a short career was the one the gate could not pass.
ONE_PAGE_FILL = 0.75
# density sets tailor's word windows: one page = 0.75-1 x words/page, two = 1.6-2 x. Measured
# in Caladea 2026-09-21 on a full-length resume: 378 words a page (windows 284-378, 605-756),
# 100 characters on a bullet line. Only the ceiling is a count, and it is what a change of font
# moves, so it is set clear of one: 860 keeps a two-page window open on any page up to 537 words
MAX_WORDS = 860
# a wrapped paragraph's last line stops here; below it the line is a stub wasting its whole row.
# measured 2026-09-21: tails cluster low and then stop - 3-30% full in Source Sans 3, 24-35%
# in Caladea, nothing between there and a filled line either way. Any cut inside that empty
# gap flags the same lines, so this is a threshold, not a knob to tune, and not font-specific
MIN_LINE_FILL = 0.40
# what a short line is told to AIM at, which is not where the gate stops failing. Advice worked
# back from the floor answers "what clears the gate", and on a 39%-full row that came out as
# "add ~1" - true, and useless, since one character leaves the row 60% empty. Measured in
# Caladea 2026-09-22: the wrapped blocks on the corpus that read as filled land at 93% and 98%,
# so 90% is the nearest round edge under both, and the 10% it leaves is what keeps an added
# word from spilling into a row of its own. Raising MIN_LINE_FILL to here instead would fail
# three lines on a resume that passes today, two of them skills lists - the floor stays put.
TARGET_LINE_FILL = 0.90
# resume.typ holds the summary to this share of the column, so its lines wrap short of the edge
SUMMARY_WIDTH = 0.90
# 0.85in, not the 1.05 this started at: the text needs the width back that tracking spends.
# Wider than this buys nothing - past the point where every bullet fits one line, the page is
# bound vertically, and 0.75in moved neither page count nor widow count on a real resume
MARGIN_X_IN = 0.85
MARGIN_Y_IN = 0.75
# letterspacing added to every glyph. Caladea is fitted tight for economy, which at 11pt reads
# cramped; +0.015em opens it for 1.5% of the line, which the column above pays for. Not a free
# knob: measure.py adds tracking * SIZE per character, so moving it moves every width with it
TRACKING_EM = 0.015
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


def href(text: str) -> str:
    """Contact link as the user writes it (linkedin.com/in/name) -> address a PDF reader opens."""
    return text if text.startswith(("http://", "https://")) else f"https://{text}"


def dial(text: str) -> str:
    """Phone as written -> tel: address. Keeps a written +country code, never invents one."""
    return "tel:" + ("+" if text.lstrip().startswith("+") else "") + re.sub(r"\D", "", text)


def contact_parts(contact: dict) -> list[tuple[str, str]]:
    """Every contact part in page order, each with the address it opens ("" = plain text)."""
    pairs = [(contact["location"], ""), (contact["email"], f"mailto:{contact['email']}")]
    if contact.get("phone"):
        pairs.append((contact["phone"], dial(contact["phone"])))
    pairs += [(link, href(link)) for link in contact.get("links", [])]
    return [(text, url) for text, url in pairs if text]


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
    parts = contact_parts(contact)
    return {
        "title": f"{contact['name']} Resume",
        "contact": {
            "name": contact["name"],
            "parts": [text for text, _ in parts],
            # same length as parts, "" where the part is not a link => template zips them by index
            "part_urls": [url for _, url in parts],
        },
        "summary": master.get("summary"),
        "sections": sections,
    }


def with_page(model: dict, font: str = typeface.DEFAULT) -> dict:
    """Page setup the template needs but the page content does not carry: margins, family, fit."""
    return {**model, "page": {"margin_x_in": MARGIN_X_IN, "margin_y_in": MARGIN_Y_IN,
                              "tracking_em": TRACKING_EM, "font": font}}


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


def compile_pdf(model: dict, font: str = typeface.DEFAULT) -> bytes:
    # one family's folder, no system fonts: a face the family lacks can never be filled in
    # silently from another, so what renders is what measure.py measured
    pdf = typst.compile(
        str(TEMPLATE), font_paths=[str(typeface.folder(typeface.use(font)))], ignore_system_fonts=True,
        sys_inputs={"data": json.dumps(with_page(model, font), ensure_ascii=False)}, pdf_standards="ua-1",
    )
    return scrub(pdf, model["title"])


def scrub(pdf: bytes, title: str) -> bytes:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        doc.set_metadata({"title": title, **dict.fromkeys(INFO_LEAK_KEYS, "")})
        doc.set_xml_metadata(XMP_LEAK.sub("", doc.get_xml_metadata()))
        return doc.tobytes(garbage=3, deflate=True)


def tokens(text: str) -> list[str]:
    return WORD.findall(text.casefold())


def pdf_text(path: Path, sort: bool) -> str:
    """sort=True: order a reader sees. sort=False: order the content stream hands a parser."""
    # pymupdf, never poppler's pdftotext: already a dependency, so no install the user cannot do
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text(sort=sort) for page in doc)


def first_divergence(a: list[str], b: list[str]) -> str:
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"word {i}: {' '.join(a[i:i + 6])!r} vs {' '.join(b[i:i + 6])!r}"


def check(path: Path, model: dict, budget: bool, font: str = typeface.DEFAULT,
          available: int | None = None) -> list[tuple[str, bool, str]]:
    """`available` = words the user's facts reach when every one is on the page. Below the
    lowest window, the budget is reported and never failed: only invention could close it."""
    results: list[tuple[str, bool, str]] = []

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    reading, stream = (pdf_text(path, sort) for sort in (True, False))
    want = [t for s in page_strings(model) for t in tokens(s)]
    got = tokens(reading)
    matcher = difflib.SequenceMatcher(None, want, got, autojunk=False)
    recovered = sum(block.size for block in matcher.get_matching_blocks()) / max(len(want), 1)
    gate("round-trip", recovered >= MIN_RECOVERY, f"{recovered:.1%} in-order word recovery (floor {MIN_RECOVERY:.0%})")

    # columns/tables read down one side visually but jump across in the stream => the two orders split
    in_stream = tokens(stream)
    diverged = in_stream != got
    gate("single-column", not diverged, first_divergence(got, in_stream) if diverged else "read order = stream order")
    gate("ligatures", not LIGATURE.search(reading), "U+FB00-FB06 absent")
    missing = [part for part in model["contact"]["parts"] if part.casefold() not in reading.casefold()]
    gate("contact-in-body", not missing, f"missing from text layer: {missing}" if missing else "every contact part in text layer")
    # role headings only: "Jr." in a name or "Martin Luther King Jr. Hospital" is not a title
    abbreviated = [h for h in role_headings(model) if schema.ABBREVIATED_TITLE.search(h)]
    gate("no-abbreviated-title", not abbreviated, f"Sr./Jr. in {abbreviated}" if abbreviated else "role titles spelled out")

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
        page_detail = f"{pages} page(s), last {fill:.0%} full (at most {MAX_PAGES}; a 2nd page fills {MIN_LAST_PAGE_FILL:.0%}+)"
        stubs = runts(doc, model, font)
        blocked = [s for s in stubs if s["fixable"]]
        gate("contact-line (info)", True, contact_detail(contact_rows(doc, model)))
        fits = word_windows(words, used)
        windows = " or ".join(f"{low}-{high}" for low, high in fits)
        detail = f"{words} words (fits page rules at {windows or 'none at this density'})"
        if budget:
            gate("pages", page_ok, page_detail)
            gate("line-fill", not blocked, stub_detail(stubs))
            if thin(fits, available):
                gate("budget (info)", True, f"{detail}; every fact on the page reaches {available} - "
                                           "short of a full page, reported only, never padded")
            else:
                gate("budget", any(low <= words <= high for low, high in fits), detail)
        else:
            gate("pages (info)", True, page_detail)
            gate("line-fill (info)", True, stub_detail(stubs))
            gate("budget (info)", True, f"{detail}; tailored page fits at {windows or 'NONE at this density'}")
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


def squeezed(text: str) -> str:
    return "".join(text.split())


def line_edges(line: dict) -> tuple[str, float, float]:
    """Line's text with its left and right ink edges; spans, never the block bbox."""
    spans = line["spans"]
    return ("".join(s["text"] for s in spans),
            min(s["bbox"][0] for s in spans), max(s["bbox"][2] for s in spans))


def first_word_widths(page) -> dict[tuple[int, int], float]:
    """(block, line) -> width of that line's first word; "words" numbers lines as "dict" does."""
    return {(b, l): x1 - x0 for x0, _, x1, _, _, b, l, w in page.get_text("words") if w == 0}


def rewritable(model: dict) -> set[str]:
    """Page text the tailorer may reword: summary, bullets, skills lines.

    Headings, dates, contact and education come straight from the user's own facts, so a stub
    in one is reported and never failed - nothing the tailorer writes could move it.
    """
    out = {squeezed(model["summary"])} if model["summary"] else set()
    for section in model["sections"]:
        for entry in section.get("entries", []):
            out.update(squeezed(b) for b in entry["bullets"])
        if section["title"] == "Skills":
            out.update(squeezed(f"{l['label']}: {l['text']}") for l in section.get("lines", []))
    return out


def paragraphs(page, lines: list[dict], block: int, edge: float, space: float) -> list[list[tuple[str, float, float]]]:
    """Split a block where the text did NOT wrap.

    A line continues the one above only when that line had no room left for this line's first
    word. Measured, never guessed from how full a line looks: a deliberate break (an entry
    subline after "\\") leaves room, so it starts a paragraph of its own. `space` is the word
    space the wrap would have had to fit into, which is the font's, not a constant.
    """
    firsts = first_word_widths(page)
    runs, current = [], [line_edges(lines[0])]
    for i, line in enumerate(lines[1:], 1):
        edges = line_edges(line)
        if current[-1][2] + space + firsts.get((block, i), 0.0) > edge:
            current.append(edges)
        else:
            runs.append(current)
            current = [edges]
    runs.append(current)
    return runs


def runts(doc, model: dict, font: str = typeface.DEFAULT) -> list[dict]:
    """Paragraphs ending in a stub line: the text, how full it is, chars to cut or to add.

    `cut` pulls the tail up onto the line above; `add` fills the row it is on, aiming at
    TARGET_LINE_FILL and not at the floor the gate happens to fail below. Neither number can
    start a new row: `add` stops short of the edge by design.

    Every measurement is in points off the rendered page - character counts never decide, since
    one glyph runs 3.2x the width of another. Chars appear only in the advice, converted at the
    paragraph's own measured width per character.
    """
    left = MARGIN_X_IN * PT_PER_IN
    width = doc[0].rect.width - 2 * left
    space = typeface.advance(font, " ") + TRACKING_EM * typeface.SIZE
    summary = squeezed(model["summary"] or "")
    can_fix = rewritable(model)
    found = []
    for page in doc:
        for block, raw in enumerate(page.get_text("dict")["blocks"]):
            lines = raw.get("lines", [])
            if not lines:
                continue
            whole = squeezed("".join(line_edges(l)[0] for l in lines))
            narrow = bool(summary) and summary in whole
            edge = left + width * (SUMMARY_WIDTH if narrow else 1.0)
            for run in paragraphs(page, lines, block, edge, space):
                if len(run) < 2:
                    continue
                text, ink_left, ink_right = run[-1]
                fill = (ink_right - ink_left) / (edge - ink_left)
                if fill >= MIN_LINE_FILL:
                    continue
                chars = sum(len(t) for t, _, _ in run)
                per_char = sum(r - l for _, l, r in run) / chars if chars else 0
                tail, slack = ink_right - ink_left, edge - run[-2][2]
                body = squeezed("".join(t for t, _, _ in run)).replace("\u2022", "")
                found.append({
                    "text": text.strip(), "fill": fill,
                    "cut": math.ceil((tail + space - slack) / per_char) if per_char else 0,
                    "add": math.ceil((TARGET_LINE_FILL * (edge - ink_left) - tail) / per_char) if per_char else 0,
                    "fixable": any(body and body in c for c in can_fix),
                })
    return found


def contact_rows(doc, model: dict) -> int:
    """Rows the contact line really occupies. Read off the page, never measured - measure.py is
    up to 4% out on this one line because the template spaces its separators itself. A wrap here
    costs a row at the top of the page and, on a full page, a whole extra page."""
    parts = model.get("contact", {}).get("parts") or []
    anchor = next((p for p in parts if "@" in p), next(iter(parts), ""))
    if not anchor or not doc.page_count:
        return 1
    for raw in doc[0].get_text("dict")["blocks"]:
        lines = raw.get("lines", [])
        text = "".join(span.get("text", "") for line in lines for span in line.get("spans", []))
        if anchor in text:
            return len(lines)
    return 1


def contact_detail(rows: int) -> str:
    if rows == 1:
        return "fits one row"
    return f"wraps to {rows} rows - shorten the location or a link; on a full page this costs a whole page"


def stub_detail(found: list[dict], show: int = 8) -> str:
    """One line per gate, so: shortest wording that still says which text and how much."""
    if not found:
        return "every wrapped block fills its last line"
    listed = "; ".join(
        f"{r['text']!r} {r['fill']:.0%} full, cut {r['cut']} or add ~{r['add']} to fill"
        + ("" if r["fixable"] else " (user's own facts - reported only)")
        for r in found[:show]
    )
    more = f" (+{len(found) - show} more)" if len(found) > show else ""
    return f"{len(found)} line(s) end in a stub: {listed}{more}"


def word_windows(words: int, used: float) -> list[tuple[int, int]]:
    """Word counts passing budget gate if page density holds: one page mostly full, or two w/ last page past fill floor."""
    per_page = words / used
    one = (math.ceil(per_page * ONE_PAGE_FILL), min(MAX_WORDS, math.floor(per_page)))
    two = (math.ceil(per_page * (MAX_PAGES - 1 + MIN_LAST_PAGE_FILL)), min(MAX_WORDS, math.floor(per_page * MAX_PAGES)))
    return [w for w in (one, two) if w[0] <= w[1]]


def thin(windows: list[tuple[int, int]], available: int | None) -> bool:
    """Facts too few to reach even the lowest window: the gate must not ask for more words."""
    return available is not None and bool(windows) and available < min(low for low, _ in windows)


def role_headings(model: dict) -> list[str]:
    return [e["heading"] for s in model["sections"] if s["title"] == "Experience" for e in s.get("entries", [])]


def render(model: dict, out_dir: Path, budget: bool, font: str = typeface.DEFAULT,
           available: int | None = None) -> tuple[Path, list[tuple[str, bool, str]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / file_name(model)
    path.write_bytes(compile_pdf(model, font))
    return path, check(path, model, budget, font, available)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render resume details straight through, no tailoring; run PDF gates")
    ap.add_argument("--master", type=Path, help="master yml (default config resume.master)")
    args = ap.parse_args()
    started = time.perf_counter()
    config = cfg.load() if args.master is None else cfg.load_or_defaults()
    master_path = args.master or cfg.resume_path(config, "master")
    master = schema.load(master_path)
    path, results = render(page_model(master), master_path.parent, budget=False, font=cfg.resume_font(config))
    for name, ok, detail in results:
        print(f"  {'pass' if ok else 'FAIL'}  {name:22} {detail}")
    for gap in schema.employment_gaps(master, date.today()):
        print(f"  gap   {gap['after']} -> {gap['before']} ({gap['months']} months)")
    print(f"wrote {path} in {time.perf_counter() - started:.2f}s")
    if not all(ok for _, ok, _ in results):
        sys.exit("render gates failed")


if __name__ == "__main__":
    main()
