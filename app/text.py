import html
import re
import unicodedata

BLOCK_TAG = re.compile(r"</?(p|br|li|ul|ol|div|h[1-6])\b[^>]*>", re.I)
ANY_TAG = re.compile(r"<[^>]+>")
BLANK_LINE_RUN = re.compile(r"\n{3,}")
# freehire descriptions carry U+FFFD where em-dashes were (measured 2026-09-16)
MOJIBAKE = "�"

# characters a reader can't see but a model reads: Tags block ("ASCII smuggling" - one tag per
# letter spells hidden instructions), bidi controls (what shows != what's read), runs of 5+
# variation selectors (bytes hidden behind one glyph). Removed + counted. A flag emoji's tag
# sequence (black flag, region code as 3-6 lowercase/digit tags, cancel tag: Scotland = gbsct)
# matches first and stays whole; no space tag in it, so no sentence hides inside a "flag"
FLAG_TAGS = "\U0001F3F4[\U000E0030-\U000E0039\U000E0061-\U000E007A]{3,6}\U000E007F"
SMUGGLED = "[\U000E0000-\U000E007F\u202a-\u202e\u2066-\u2069]|[\ufe00-\ufe0f\U000E0100-\U000E01EF]{5,}"
HIDDEN = re.compile(f"({FLAG_TAGS})|{SMUGGLED}")
# zero-width chars copy-paste + page builders leave inside words ("Py\u200bthon" misses "Python"):
# removed, not counted. A soft hyphen only inside a word; a joiner between two emoji (family) stays
ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]|(?<=\\w)\u00ad(?=\\w)")
EMOJI_PARTS = {"\ufe0f", "\u20e3"}


def is_emoji(char: str) -> bool:
    return unicodedata.category(char) in ("So", "Sk") or char in EMOJI_PARTS


def strip_hidden(text: str | None) -> tuple[str, int]:
    """Employer text w/o characters a reader can't see -> (text, how many were smuggled in).
    Zero-width chars go uncounted: common by accident, they hide nothing on their own."""
    count = 0

    def smuggled(m: re.Match) -> str:
        nonlocal count
        if m[1]:
            return m[1]
        count += len(m[0])
        return ""

    def zero_width(m: re.Match) -> str:
        s, i = m.string, m.start()
        joins = m[0] == "\u200d" and 0 < i < len(s) - 1 and is_emoji(s[i - 1]) and is_emoji(s[i + 1])
        return m[0] if joins else ""

    text = HIDDEN.sub(smuggled, text or "")
    return ZERO_WIDTH.sub(zero_width, text), count


def html_to_text_counted(markup: str | None) -> tuple[str, int]:
    """html_to_text + how many smuggled characters it removed (strip_hidden)."""
    text = ANY_TAG.sub("", BLOCK_TAG.sub("\n", markup or ""))
    text, hidden = strip_hidden(html.unescape(text).replace(MOJIBAKE, " "))
    return BLANK_LINE_RUN.sub("\n\n", text).strip(), hidden


def html_to_text(markup: str | None) -> str:
    return html_to_text_counted(markup)[0]


# markdown chars that start a link, image, html tag or code span ("(" too: no "](x" left in the file);
# backslash first so a "\[" in the text can't unescape ours. * _ # - ")" and line breaks stay:
# bullets, "1)" lists + paragraphs read as before
MD_ACTIVE = re.compile(r"[\\`\[\](<>&]")
# linkify (VS Code preview) turns bare "https://x", "x.com", "a@b.com" into links: an escaped
# ":" before "//" or "." inside a word breaks the match, renders the same (measured, markdown-it 14)
MD_LINKIFY = re.compile(r":(?=//)|\.(?=\w)")
MD_ENTITY = {"<": "&lt;", ">": "&gt;", "&": "&amp;"}


def inert_md(text: str | None) -> str:
    """Employer/page text made plain in a .md the user opens: no link, image, HTML or autolink
    renders from it - reads the same, nothing loads or clicks. Data, never markup (AGENTS.md)."""
    text = MD_ACTIVE.sub(lambda m: MD_ENTITY.get(m[0], "\\" + m[0]), text or "")
    return MD_LINKIFY.sub(lambda m: "\\" + m[0], text)
