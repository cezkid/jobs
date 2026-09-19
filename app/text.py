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
