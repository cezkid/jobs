"""Text of a Word (.docx) resume, read here so the AI never opens the file itself.

A .docx is a zip of XML: word/document.xml cost 19-45x the Claude tokens of its text (4 Word
resume templates, measured 2026-10-06, app/docs/resume/resume-file.md) - an AI reading it raw
spends that. Reading it here hands the AI the text only, inside the import task.

Lines come out as Word shows them: header first (Word templates put the name + contact there),
body, footer last. Left out: what Word doesn't show - hidden text, tracked deletions + moved-from
copies, field codes, a template's unfilled prompt text, the old-Word copy of a text box
(mc:Fallback repeats the mc:Choice text). Tags matched by local name, so Strict Open XML
(purl.oclc.org namespace) reads the same as the usual kind. A file is told by its first bytes, not
its name: a PDF renamed .docx still reads as a PDF.
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

BODY = "word/document.xml"
HEADER = re.compile(r"word/header(\d*)\.xml$")
FOOTER = re.compile(r"word/footer(\d*)\.xml$")
# a resume's part is a few hundred KB at most; past this it is no resume (or a zip bomb)
MAX_PART_BYTES = 20_000_000
# skipped with everything inside: tracked deletion, field instruction, old-Word text box copy,
# footnote mark, run + paragraph properties (vanish read off them first)
SKIP = {"del", "delText", "delInstrText", "instrText", "moveFrom", "Fallback", "footnoteReference",
        "endnoteReference", "rPr", "pPr", "sdtPr"}
ZIP, OLE, PDF = b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"%PDF"
# soft hyphen: Word shows it only at a line end
CHARS = {"tab": "\t", "br": "\n", "cr": "\n", "noBreakHyphen": "-", "softHyphen": ""}
# read as is: a macro file's macros sit in their own part, never run
WORD_SUFFIXES = {".docx", ".docm"}
# macOS ships textutil, which reads these without Word
MAC_CONVERTS = {".doc", ".rtf", ".odt"}
OTHER_FORMATS = {
    ".doc": "an older Word file", ".dotx": "a Word template", ".rtf": "a rich-text file",
    ".odt": "an OpenDocument file", ".pages": "a Pages file", ".txt": "a plain-text file",
    ".gdoc": "a Google Docs shortcut",
}
SAVE_AS = "Open it and save a copy as Word Document (.docx) or PDF, then drag that onto My Resume."
# a web address hidden behind a word ("Reel", "Portfolio", "LinkedIn" - the way resume templates and
# Canva link them): the text alone loses it, and a printed or pasted copy shows the word only. Marked
# after the word, the AI copies the address into contact.links (import_pdf.SYSTEM); a word that
# already shows an address keeps no mark
LINK_MARK = " <link: {}>"
LINKED = re.compile(r"<link: (\S+?)>")
SHOWS_ADDRESS = re.compile(r"\w\.[a-z]{2,}", re.I)
FIELD_LINK = re.compile(r'^\s*HYPERLINK\s+"([^"]+)"', re.I)


class NotReadable(ValueError):
    """Plain words for the user: what the file is and the one step that makes it readable."""


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def hidden(run: ElementTree.Element) -> bool:
    props = next((c for c in run if local(c.tag) == "rPr"), None)
    if props is None:
        return False
    for c in props:
        if local(c.tag) in ("vanish", "webHidden"):
            # <w:vanish w:val="false"/> switches hiding off
            val = next((v for k, v in c.attrib.items() if local(k) == "val"), "true")
            if val not in ("0", "false", "off"):
                return True
    return False


def placeholder(sdt: ElementTree.Element) -> bool:
    """Content control still showing its template prompt ("[Your Name]", "Click to enter a date")."""
    props = next((c for c in sdt if local(c.tag) == "sdtPr"), None)
    return props is not None and any(local(c.tag) == "showingPlcHdr" for c in props)


def address(url: str) -> str:
    """Web address as a resume writes it: vimeo.com/name, never https://www.vimeo.com/name/."""
    return re.sub(r"^https?://(?:www\.)?", "", url.strip(), flags=re.I).rstrip("/")


def link_mark(label: str, url: str | None) -> str:
    """Mark for a web link behind `label`, "" when the label already shows an address (or no web link)."""
    if not url or not url.strip().lower().startswith(("http://", "https://")) or not label.strip():
        return ""
    return "" if SHOWS_ADDRESS.search(label) else LINK_MARK.format(address(url))


def attr(el: ElementTree.Element, name: str) -> str | None:
    return next((v for k, v in el.attrib.items() if local(k) == name), None)


def walk(el: ElementTree.Element, out: list[str], rels: dict[str, str] | None = None) -> None:
    tag = local(el.tag)
    if tag in SKIP or (tag == "r" and hidden(el)) or (tag == "sdt" and placeholder(el)):
        return
    if tag in ("hyperlink", "fldSimple"):
        # Insert > Link writes <w:hyperlink r:id>, its address in the part's .rels; a pasted link
        # may come as a simple HYPERLINK field. Its words read as usual, the address marked after them
        url = (rels or {}).get(attr(el, "id") or "") if tag == "hyperlink" else \
            (m[1] if (m := FIELD_LINK.match(attr(el, "instr") or "")) else None)
        inner: list[str] = []
        for child in el:
            walk(child, inner, rels)
        out += inner
        if mark := link_mark("".join(inner), url):
            out.append(mark)
        return
    if tag == "p" and out and not out[-1].endswith("\n"):
        # a text box's paragraph sits inside the page's paragraph: its words start a line of their own
        out.append("\n")
    if tag == "t":
        out.append(el.text or "")
    elif tag in CHARS:
        out.append(CHARS[tag])
    elif tag == "sym":
        # Symbol / Wingdings bullet typed as a character: private-use code, stripped like a PDF's
        code = next((v for k, v in el.attrib.items() if local(k) == "char"), "")
        if re.fullmatch(r"[0-9A-Fa-f]{4}", code):
            out.append(chr(int(code, 16)))
    for child in el:
        walk(child, out, rels)
    if tag == "p":
        out.append("\n")


def part_lines(z: zipfile.ZipFile, name: str) -> list[str]:
    # the size a zip states can lie: read at most the cap + 1 byte
    with z.open(name) as f:
        data = f.read(MAX_PART_BYTES + 1)
    if len(data) > MAX_PART_BYTES:
        raise NotReadable(f"{name} is over {MAX_PART_BYTES:,} bytes - too large for a resume")
    # no DTD in real Word XML: refusing one rules out entity tricks before the parser sees them
    if b"<!DOCTYPE" in data[:4096] or b"<!ENTITY" in data:
        raise NotReadable(f"{name} declares XML entities - not a file Word made")
    out: list[str] = []
    walk(ElementTree.fromstring(data), out, link_targets(z, name))
    return [line.strip() for line in "".join(out).splitlines() if line.strip()]


def link_targets(z: zipfile.ZipFile, name: str) -> dict[str, str]:
    """Relationship id -> address for a part's external links (word/_rels/document.xml.rels)."""
    folder, _, base = name.rpartition("/")
    rels = f"{folder}/_rels/{base}.rels"
    if rels not in z.namelist():
        return {}
    with z.open(rels) as f:
        data = f.read(MAX_PART_BYTES + 1)
    if len(data) > MAX_PART_BYTES or b"<!DOCTYPE" in data[:4096] or b"<!ENTITY" in data:
        return {}
    return {attr(r, "Id"): attr(r, "Target") for r in ElementTree.fromstring(data)
            if (attr(r, "Type") or "").endswith("/hyperlink") and attr(r, "TargetMode") == "External"}


def numbered(z: zipfile.ZipFile, pattern: re.Pattern) -> list[str]:
    found = [(int(m[1] or 0), n) for n in z.namelist() if (m := pattern.fullmatch(n))]
    return [n for _, n in sorted(found)]


def kind(path: Path) -> str:
    """"pdf", "word" or "ole" (an older .doc, or any Word file locked with a password) by first bytes."""
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(PDF):
        return "pdf"
    if head.startswith(ZIP):
        return "word"
    return "ole" if head.startswith(OLE) else "other"


def mac_converts(path: Path) -> bool:
    return path.suffix.lower() in MAC_CONVERTS and sys.platform == "darwin" and bool(shutil.which("textutil"))


def mac_text(path: Path) -> str | None:
    """.doc / .rtf / .odt as plain text through macOS's own textutil; None elsewhere or on failure."""
    if not mac_converts(path):
        return None
    try:
        done = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode:
        return None
    lines = [line.strip() for line in done.stdout.decode("utf-8", "replace").splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def read(path: Path) -> str:
    """Text of any resume file but a PDF: Word by its XML, .doc / .rtf / .odt through macOS."""
    if kind(path) != "word" and mac_converts(path):
        if (text := mac_text(path)) is not None:
            return text
        raise NotReadable(f"{path.name} could not be read (locked with a password?). {SAVE_AS}")
    return extract(path)


def extract(path: Path) -> str:
    if (got := kind(path)) == "ole":
        raise NotReadable(f"{path.name} is an older Word file, or one locked with a password. {SAVE_AS}")
    if got != "word":
        raise NotReadable(f"{path.name} is not a Word (.docx) file inside. {SAVE_AS}")
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise NotReadable(f"{path.name} is not a Word (.docx) file inside. {SAVE_AS}") from None
    with z:
        if BODY not in z.namelist():
            raise NotReadable(f"{path.name} has no Word document inside. {SAVE_AS}")
        lines: list[str] = []
        seen: set[str] = set()
        # first-page, even-page and default headers often repeat the same name + contact line
        for name in numbered(z, HEADER):
            for line in part_lines(z, name):
                if line not in seen:
                    seen.add(line)
                    lines.append(line)
        lines += part_lines(z, BODY)
        body = set(lines)
        for name in numbered(z, FOOTER):
            for line in part_lines(z, name):
                if line not in seen and line not in body:
                    seen.add(line)
                    lines.append(line)
    return "\n".join(lines) + "\n"


def refusal(path: Path) -> str | None:
    """Plain line for a resume file the program can't read, else None."""
    suffix = path.suffix.lower()
    if suffix == ".pdf" or suffix in WORD_SUFFIXES or mac_converts(path):
        return None
    if path.exists() and kind(path) in ("pdf", "word"):
        return None
    what = OTHER_FORMATS.get(suffix, f"a {suffix or 'nameless'} file")
    return f"{path.name} is {what}. {SAVE_AS}"
