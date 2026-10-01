"""The typeface the resume is set in, and the file every width is measured from.

One family ships: Caladea, which carries Cambria's metrics under the OFL. It was picked on
numbers that can be re-run, not on taste - `app/docs/resume/typeface.md` records them. A page fits
what it fits because of the font: swap the family and column fits, stub lines and word budgets
all move with it, so the family is a setting (`resume.font`) and nothing downstream hardcodes
a file name.

A different family is a folder of TTFs in `.data/fonts/`, named exactly as the font names
itself, plus that name in the user's settings - no code change. `check()` is what
makes that safe: it runs before the first compile and says, in plain words, what a folder
is missing. Typst is handed that one folder and no system fonts - but it still carries fonts of
its own (Libertinus, New Computer Modern) and draws any character the family lacks in one of them,
without a word. `missing_glyphs` names those characters before the compile, so lint can say so.
"""
import functools
import unicodedata
from pathlib import Path

import pymupdf

import cfg

DIR = Path(__file__).resolve().parent / "fonts"
# fonts user adds: update replaces app/ whole => folder beside Caladea gone next launch
USER_DIR = cfg.DATA / "fonts"
# the family that ships; what renders unless the user's settings name another
DEFAULT = "Caladea"
# body size the template sets; every measurement in measure.py is taken at it
SIZE = 11.0
# weights resume.typ asks for: body, headings/entry titles, the name
REGULAR, SEMIBOLD, BOLD = 400, 600, 700
# a family may answer 600 with its bold face - Typst picks the nearest weight it has, and a
# heading one step heavy still reads as a heading. Caladea does exactly that; size and colour
# are what separate its headings. Missing 400 or 700 is not recoverable.
REQUIRED = (REGULAR, BOLD)
# every codepoint resume.typ puts on the page that is not a plain letter, digit or ASCII mark:
# the list marker, the separator between contact parts, and the en dash a pasted title can carry
NEEDED_GLYPHS = "•|–’"
STYLE_WEIGHTS = {
    "regular": REGULAR, "book": REGULAR, "roman": REGULAR,
    "medium": 500, "semibold": SEMIBOLD, "demibold": SEMIBOLD, "bold": BOLD, "black": 900,
}


def folder(family: str) -> Path:
    """Folder holding `family`, named as the font names itself."""
    for base in (DIR, USER_DIR):
        if (base / family).is_dir():
            return base / family
    raise SystemExit(
        f"No font called {family!r}. Installed: {', '.join(installed()) or 'none'}. "
        f"To add one, put its .ttf files in {USER_DIR / family}, named exactly as the font names itself."
    )


def installed() -> list[str]:
    return sorted({p.name for base in (DIR, USER_DIR) if base.is_dir()
                   for p in base.iterdir() if p.is_dir() and any(p.glob("*.ttf"))})


def faces(family: str) -> dict[int, Path]:
    """Weight -> file, for the upright faces of `family`. Italics are left out: they carry
    no weight the template asks for, and keeping them out of the table keeps `check` honest."""
    out: dict[int, Path] = {}
    for path in sorted(folder(family).glob("*.ttf")):
        style = path.stem.rsplit("-", 1)[-1].casefold() if "-" in path.stem else "regular"
        if "italic" in style or style.endswith("it"):
            continue
        weight = STYLE_WEIGHTS.get(style)
        if weight is not None:
            out[weight] = path
    return out


@functools.cache
def regular(family: str) -> pymupdf.Font:
    """The face every width is measured from - the one the body text is set in."""
    return pymupdf.Font(fontfile=str(faces(family)[REGULAR]))


@functools.cache
def advance(family: str, text: str) -> float:
    """Advance width of `text` at body size, in points - the one primitive every page rule
    is built on. resume/measure.py wraps it; render.py calls it straight to avoid a cycle."""
    return regular(family).text_length(text, fontsize=SIZE)


@functools.cache
def upright(family: str) -> tuple[pymupdf.Font, ...]:
    return tuple(pymupdf.Font(fontfile=str(path)) for path in faces(family).values())


@functools.cache
def covered(family: str, char: str) -> bool:
    """Every upright face draws it, or draws every piece of it: Typst builds a letter the font
    lacks from its base + accent marks (Caladea draws "ễ" that way; "ị" needs U+0323, which
    Caladea lacks, so Typst takes the whole letter from Libertinus)."""
    def drawn(c: str) -> bool:
        return all(face.has_glyph(ord(c)) for face in upright(family))
    if char.isspace() or drawn(char):
        return True
    pieces = unicodedata.normalize("NFD", char)
    return len(pieces) > 1 and all(drawn(c) for c in pieces)


def missing_glyphs(family: str, text: str) -> list[str]:
    """Characters `family` can't draw, in order of first use. Typst prints each in a typeface of
    its own, so the line mixes typefaces and its width is off from measure.py. Measured
    2026-10-01, Caladea: ✓ -> NewCMMath; α β Δ μ (Greek mu) ⁹ ★ ị Ạ Cyrillic -> LibertinusSerif."""
    return [c for c in dict.fromkeys(text) if not covered(family, c)]


def check(family: str) -> list[str]:
    """What stops this family rendering a correct resume, in words a non-typographer can act on."""
    problems = []
    found = faces(family)
    for weight in REQUIRED:
        if weight not in found:
            name = "regular" if weight == REGULAR else "bold"
            problems.append(f"{family}: no {name} face - expected a file named like {family}-{name.title()}.ttf")
    for _, path in sorted(found.items()):
        named = pymupdf.Font(fontfile=str(path)).name
        if not named.casefold().startswith(family.casefold()):
            problems.append(f"{family}: {path.name} calls itself {named!r} - rename the folder to match, "
                            "or Typst will not find the font")
    if REGULAR in found:
        font = regular(family)
        missing = [c for c in NEEDED_GLYPHS if not font.has_glyph(ord(c))]
        if missing:
            problems.append(f"{family}: missing {' '.join(missing)} - the page needs them for bullets and separators")
    return problems


@functools.cache
def use(family: str) -> str:
    """Family name to hand Typst, once it is known to render a correct page. Cached: the
    tailor loop compiles the same family many times and the files do not change under it."""
    problems = check(family)
    if problems:
        raise SystemExit("\n".join(problems))
    return family
