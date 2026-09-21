"""Rendered text width in points, from the font itself - never from character counts.

At 11pt Caladea a 'W' is 9.94pt and an 'i' is 3.21pt, so counting characters mis-sizes a line
by up to 3.1x per glyph. Which family renders is a setting (`resume.font`, resolved by
`resume/typeface.py`), so every function here takes the family and the exact advance width of
any string in it is knowable before anything renders. Checked in Caladea against 41 rendered
bullet, summary and skills lines - the text the page rules act on - it agrees with the page to
a median 0.4% and never worse than 1.4%. The contact line is the exception at up to 4%, because
the template spaces its separators itself; no gate reads it. The line-fill gate in render.py
measures the real PDF and remains the authority.
"""
import functools
import math

from resume import render, typeface

SIZE = typeface.SIZE


def width(font: str, text: str) -> float:
    """Advance width of `text` at body size, in points, tracking included.

    Typst adds `tracking` after every glyph, spaces among them, so the letterspacing the page
    is set with is exactly `TRACKING_EM * SIZE` per character - measured off a rendered page to
    four decimals, not assumed. Leave it out and every width here is short by 1.5%.
    """
    return typeface.advance(font, text) + render.TRACKING_EM * SIZE * len(text)


def wrap(font: str, text: str, avail: float) -> list[str]:
    """Greedy break at spaces - what the template does with hyphenate off and hyphens boxed."""
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}" if current else word
        if current and width(font, trial) > avail:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def rows(font: str, line: str, avail: float) -> int:
    """Rows one wrapped line occupies - >1 only for a word too long to break, which overflows."""
    return max(1, math.ceil(width(font, line) / avail)) if avail else 1


def fit(font: str, text: str, avail: float) -> tuple[int, float]:
    """(rows it takes, how full the last one is) - the two numbers the page rules are about."""
    lines = wrap(font, text, avail)
    filled = width(font, lines[-1]) / avail if avail else 0.0
    return (sum(rows(font, l, avail) for l in lines),
            filled - math.floor(filled) if filled > 1 else filled)


def chars_for(font: str, text: str, points: float) -> int:
    """Points expressed as characters of THIS text, so advice reads in the writer's units."""
    per_char = width(font, text) / len(text) if text else 0
    return math.ceil(points / per_char) if per_char else 0


# geometry the template lays out to, so callers never re-derive it from a rendered page
PAGE_WIDTH_IN = 8.5  # us-letter, set in resume.typ
COLUMN = (PAGE_WIDTH_IN - 2 * render.MARGIN_X_IN) * render.PT_PER_IN
SUMMARY = COLUMN * render.SUMMARY_WIDTH
# resume.typ hangs list bodies at indent 0.2em + marker + body-indent 0.5em
LIST_HANG_EM = 0.7


@functools.cache
def bullet(font: str) -> float:
    """Width a bullet's text actually gets: the column less the hanging indent, which is part
    em and part the marker glyph, so it moves with the font (12.6pt of the 489.6pt column here).

    The marker's own advance, not `width()`: measured off the rendered page, Typst lays the
    body indent out from the glyph without the tracking that follows it. It is 0.17pt, and the
    test holds the formula to 0.05.
    """
    return COLUMN - (LIST_HANG_EM * SIZE + typeface.advance(font, "•"))
