"""Helpers for the site tests (test_site.py): parse a page, list docs/ files, map URLs to files.

Not collected (no test_ prefix). Reads nothing at import: installed copies have no docs/ worth testing.
"""

import re
import struct
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Head(HTMLParser):
    """Every tag's attributes in order, plus the text of <title>, <style>, <script> and #line."""

    def __init__(self, text: str):
        super().__init__()
        self.tags, self.text, self._open = [], {}, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag in ("title", "style", "script") or attrs.get("id") == "line":
            self._open = attrs.get("type", tag) if tag == "script" else attrs.get("id", tag)
            self.text.setdefault(self._open, [])
            self.text[self._open].append("")

    def handle_endtag(self, tag):
        self._open = None

    def handle_data(self, data):
        if self._open:
            self.text[self._open][-1] += data

    def all(self, tag, **match):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in match.items())]

    def meta(self, key: str) -> str | None:
        found = self.all("meta", property=key) or self.all("meta", name=key)
        return found[0]["content"] if found else None

    def links(self, rel: str) -> list[dict]:
        return self.all("link", rel=rel)

    def ids(self) -> set[str]:
        return {a["id"] for _, a in self.tags if a.get("id")}


def png_size(path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR", path
    return struct.unpack(">II", data[16:24])


def loaded_urls(head: Head) -> list[str]:
    """What a browser fetches on load: every src, every <link> but canonical, every CSS url()."""
    urls = [a["src"] for _, a in head.tags if "src" in a]
    urls += [a["href"] for a in head.all("link") if a.get("rel") != "canonical"]
    for css in head.text.get("style", []):
        urls += re.findall(r"""url\(\s*["']?([^"')]+)""", css)
    return urls


def files(docs: Path) -> set[str]:
    """Every file under docs/ as Pages serves it: exact-case relative paths, dotfiles (.DS_Store) left out.

    macOS disks ignore case, Pages doesn't => compare against these names, never Path.is_file().
    """
    return {p.relative_to(docs).as_posix() for p in docs.rglob("*")
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(docs).parts)}


def own_url(rel: str, site: str) -> str:
    """The URL a file is served at: a folder's index.html is the folder (ending in /)."""
    if rel == "index.html" or rel.endswith("/index.html"):
        rel = rel.removesuffix("index.html")
    return site + rel


def target(url: str) -> str:
    """The docs/ file a root-relative URL fetches: query + fragment dropped, / or trailing / -> index.html."""
    path = unquote(urlsplit(url).path).lstrip("/")
    return path + "index.html" if path == "" or path.endswith("/") else path
