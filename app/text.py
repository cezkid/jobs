import html
import re

BLOCK_TAG = re.compile(r"</?(p|br|li|ul|ol|div|h[1-6])\b[^>]*>", re.I)
ANY_TAG = re.compile(r"<[^>]+>")
BLANK_LINE_RUN = re.compile(r"\n{3,}")
# freehire descriptions carry U+FFFD where em-dashes were (measured 2026-09-16)
MOJIBAKE = "�"


def html_to_text(markup: str | None) -> str:
    text = ANY_TAG.sub("", BLOCK_TAG.sub("\n", markup or ""))
    text = html.unescape(text).replace(MOJIBAKE, " ")
    return BLANK_LINE_RUN.sub("\n\n", text).strip()


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
