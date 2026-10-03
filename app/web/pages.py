"""Build the site's generated pages in docs/: research articles + About from Markdown, sitemap.xml.

Sources: app/web/research/<slug>.md - a YAML header between --- lines (KEYS only), then Markdown.
<slug>.md -> /research/<slug>/, methods.md -> /research/methods/, about.md -> /about/, index.md =
hub intro; research/feed.xml (Atom) once an article is published. status: draft => not built.
Shared CSS, header, footer, icon + font links and og:image size are copied from docs/index.html, so every page stays the same as the home page; the share
card itself is CARD (docs/og-research.png).

Hand-written pages (index.html, privacy.html, 404.html) stay as they are; this script reads them
for the sitemap. Everything it writes is generated and committed - never hand-edit those files;
change this script or its sources and rerun. A test (test_site.py) fails when a committed file is
stale, missing, or left over in docs/research/ or docs/about/ (orphan) - rerun to fix.

Output is deterministic: no clock, sorted order, UTF-8, LF. Dates read from sources, spelled with
MONTHS (strftime %B follows the computer's language, %-d breaks on Windows).

Citations: [@id], [@id, p. 12], [@a; @b] in a source -> (Author year, p. 12) linking a Sources list at
the page's end, entries from app/web/research/sources.yml. A published page also needs an
adversarial review in app/web/research/reviews/<name>.md (verdict: publish, reviewed on or after
modified); reviews are never built into docs/.

Run from repo root: uv run app/web/pages.py [--check | --links [sources.yml]]
Writes by default; --check lists problems, writes nothing, exits 1 on any; --links checks every
source is real over the network (DOI, arXiv id, url), exits 1 on a broken one.
Project env (no inline deps): markdown-it-py comes locked through rich.
"""

import argparse
import datetime
import difflib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

ROOT = Path(__file__).resolve().parents[2]
# folders this script owns: files in them it didn't build are orphans and get deleted
OWNED = ("research", "about")
# docs/mac/ + docs/win/ hold install scripts named index.html, not pages
NOT_PAGES = ("mac", "win")
SOURCES = Path("app") / "web" / "research"
REGISTRY = SOURCES / "sources.yml"
REVIEWS = SOURCES / "reviews"
AUTHOR = "Cesar Enrriquez-Zuniga"
SAME_AS = ["https://github.com/cezkid"]  # the author's other profiles (ProfilePage sameAs)
# every generated page's share card: docs/og-research.png from app/web/og-research.html
# (uv run app/web/assets.py --only og); changed => bump ?v=N here. Per-article cards: later.
CARD = "og-research.png"
FEED = "research/feed.xml"  # Atom: published articles, linked (autodiscovery) from the hub + every article
FEED_TITLE = "CEZ Job Finder Research"
CARD_ALT = ("CEZ Job Finder Research - AI and resumes: what the evidence says. A page with one claim"
            " marked in yellow, linked to its list of sources.")
REPO = "https://github.com/cezkid/jobs/blob/main/"
KEYS = {"title", "description", "published", "modified", "status", "og_title", "uncited"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# special sources (about, methods, index) + names later steps use (feed, reviews/, sources.yml)
RESERVED = {"about", "methods", "index", "feed", "reviews", "sources"}
# share card + site font are a subset (assets.UNICODES); a character outside it falls back to another font
_spec = importlib.util.spec_from_file_location("assets", Path(__file__).with_name("assets.py"))
assets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assets)
FONT_CHARS = frozenset(map(chr, assets.UNICODES))
LIMITS = {"title": 60, "description": 155, "og_title": 70}  # cut off past this in results / share previews
# same as app/resume/lint.py INVISIBLE: looks like a space or nothing, breaks search + copy
INVISIBLE = re.compile("[\u00a0\u202f\u200b\u200c\u200d\u2060\ufeff]")
# same as test_docs.py JARGON + JARGON_OK (a test keeps them equal): the site's readers are the app's users
JARGON = re.compile(r"\b(config|yml|json|slug|params|facet|pytest|repo|commit|branch|PR|API|schema)\b")
JARGON_OK = ("Resume details.yml", "API key")
RAW_HTML = re.compile(r"<!--|</?[A-Za-z][A-Za-z0-9-]*(\s[^<>]*)?/?>")
ENTITY = re.compile(r"&(#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
NOTES = re.compile(r"\[owner:|\bTODO\b")
# sources.yml: evidence label (app/docs/resume/fair-screening.md strength labels) -> plain words (Guides scale)
EVIDENCE = {
    "meta-analysis": "Big study (many studies combined)",
    "large field experiment": "Big study (thousands of real applications)",
    "field experiment": "Small study (real applications)",
    "survey": "Survey",
    "vendor survey": "Survey by a company that sells the service",
    "lab/LLM audit": "Lab test (not real hiring)",
    "observational": "Real records, no experiment (a link, not proof of cause)",
    "vendor docs": "The maker's own description of its product",
    "court record": "Court record (what was claimed or ordered, not proven facts)",
    "news report": "News report (used for the event only)",
    "law": "Law",
    "convention": "Convention (no study)",
}
ENTRY_KEYS = {"id", "type", "authors", "org", "year", "title", "venue", "doi", "url", "evidence", "sample",
              "preprint", "checked", "recheck_by"}
# per type, on top of id, type, authors|org, year, title, evidence, checked, doi|url
TYPE_NEEDS = {"article": ("venue",), "book": ("venue",), "report": (), "law": ("url", "recheck_by"), "web": ("url",)}
CITE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
CITE = re.compile(r"\[@[^\[\]]*\]")
CITE_PART = re.compile(r"\s*@([a-z0-9]+(?:-[a-z0-9]+)*)\s*(?:,\s*([^;]*\S))?\s*")
REVIEW_KEYS = {"reviewed", "verdict", "reviewer"}
_NUM = r"(?:\d[\d,]*|one|two|three|four|five|six|seven|eight|nine|ten)"
# a sentence carrying one of these needs a citation (or one of the page's uncited: strings)
STAT = re.compile(
    r"\b\d[\d,.]*\s*%|\bper\s?cent\b|\bpercentage points?\b|\b\d[\d,.]*\s+(?:points?|pts?)\b"
    rf"|\b{_NUM}\s+(?:in|out of)\s+(?:{_NUM}|a hundred|a thousand)\b|\bn\s*=\s*\d"
    r"|\b(?:a|one|two|three|four|five|six|seven|eight|nine)[\s-](?:half|halves|thirds?|quarters?|fourths?|fifths?"
    r"|sixths?|sevenths?|eighths?|ninths?|tenths?)\b", re.I)
# a full stop after these doesn't end a sentence
ABBREV = re.compile(r"\b(et al|pp?|e\.g|i\.e|vs|cf|vol|eds?|approx)\.", re.I)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def long_date(iso: str) -> str:
    """2026-10-02 -> 2 October 2026."""
    year, month, day = (int(x) for x in iso.split("-"))
    return f"{day} {MONTHS[month - 1]} {year}"


class Head(HTMLParser):
    """A page's canonical URL, whether it asks to stay out of search, and its article:modified_time."""

    def __init__(self, text: str):
        super().__init__()
        self.canonical, self.noindex, self.modified = None, False, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical" and self.canonical is None:
            self.canonical = attrs.get("href")
        if tag == "meta" and attrs.get("name") == "robots" and "noindex" in (attrs.get("content") or ""):
            self.noindex = True
        if tag == "meta" and attrs.get("property") == "article:modified_time":
            self.modified = attrs.get("content")


def site(root: Path) -> str:
    return "https://" + (root / "docs" / "CNAME").read_text(encoding="utf-8").strip() + "/"


def listed(docs: Path) -> list[str]:
    """Every file under docs/ as Pages serves it: exact-case relative paths, dotfiles (.DS_Store) left out."""
    return sorted(p.relative_to(docs).as_posix() for p in docs.rglob("*")
                  if p.is_file() and not any(part.startswith(".") for part in p.relative_to(docs).parts))


def sitemap(root: Path, pages: dict[str, str]) -> str:
    """Canonical URL of every indexed page, home first then sorted; once each. <lastmod> = the page's
    article:modified_time (dated pages only: Google uses lastmod only while it's always accurate)."""
    home = site(root)
    urls: dict[str, str | None] = {}
    for text in pages.values():
        head = Head(text)
        if head.canonical and not head.noindex:
            urls[head.canonical] = head.modified
    lines = [f"  <url><loc>{url}</loc>" + (f"<lastmod>{urls[url]}</lastmod>" if urls[url] else "") + "</url>"
             for url in sorted(urls, key=lambda u: (u != home, u))]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(line + "\n" for line in lines) + "</urlset>\n")


class SourceError(Exception):
    """One or more research sources can't be built; message = one "file:line: problem" per line."""


class Loader(yaml.SafeLoader):
    """SafeLoader that rejects a key given twice (plain YAML keeps the last one silently)."""


def _mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep)


Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
# dates stay text: YAML would turn 2026-02-30 into a crash instead of a reported problem
Loader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))


def slugify(text: str) -> str:
    """Heading id: same rule as test_docs.anchors() (GitHub / VS Code), so x.md#h works in both."""
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def iso(value, where: str, errors: list[str]) -> str | None:
    text = str(value)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            datetime.date.fromisoformat(text)
            return text
    except ValueError:
        pass
    errors.append(f"{where}: date must be YYYY-MM-DD, got {text!r}")
    return None


class Source:
    """One app/web/research/<name>.md: header fields, Markdown tokens, heading ids, output path."""

    def __init__(self, path: Path, root: Path, errors: list[str]):
        self.path, self.name = path, path.stem
        self.rel = path.relative_to(root).as_posix()
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.text = text
        head, body, self.offset = {}, text, 0
        match = re.match(r"---\n(.*?\n)---\n", text, re.S)
        if not match:
            errors.append(f"{self.rel}:1: needs a YAML header between --- lines")
        else:
            try:
                head = yaml.load(match.group(1), Loader=Loader) or {}
            except yaml.YAMLError as e:
                mark = getattr(e, "problem_mark", None)
                line = mark.line + 2 if mark else 1
                errors.append(f"{self.rel}:{line}: header: {getattr(e, 'problem', None) or e}")
            body, self.offset = text[match.end():], match.group(0).count("\n")
        if not isinstance(head, dict):
            errors.append(f"{self.rel}:2: header must be key: value lines")
            head = {}
        for key in sorted(set(head) - KEYS, key=str):
            errors.append(f"{self.rel}:{self.line_of(text, key)}: unknown header key {key!r} (allowed: {', '.join(sorted(KEYS))})")
        for key in "title", "description", "status":
            if not isinstance(head.get(key), str) or not head[key].strip():
                errors.append(f"{self.rel}:2: header needs {key}")
        self.status = head.get("status")
        if self.status not in ("draft", "published", None):
            errors.append(f"{self.rel}:{self.line_of(text, 'status')}: status must be draft or published")
        self.title, self.description = str(head.get("title", "")), str(head.get("description", ""))
        self.og_title = str(head.get("og_title") or self.title)
        self.uncited = head.get("uncited") or []
        if not isinstance(self.uncited, list) or not all(isinstance(u, str) and u.strip() for u in self.uncited):
            errors.append(f"{self.rel}:{self.line_of(text, 'uncited')}: uncited must be a list of text snippets")
            self.uncited = []
        self.head = head
        self.hub = False  # index.md: set once an article is published (the hub lists them)
        self.published = self.modified = None
        if self.status == "published":
            if "published" not in head:
                errors.append(f"{self.rel}:2: published page needs a published date")
            else:
                self.published = iso(head["published"], f"{self.rel}:{self.line_of(text, 'published')}", errors)
            self.modified = (iso(head["modified"], f"{self.rel}:{self.line_of(text, 'modified')}", errors)
                             if "modified" in head else self.published)
        if self.name in RESERVED - {"about", "methods", "index"}:
            errors.append(f"{self.rel}:1: {self.name} is a reserved name")
        elif not SLUG.match(self.name):
            errors.append(f"{self.rel}:1: file name must be lower-case words joined by - (a-z, 0-9)")
        self.tokens = MD.parse(body)
        self.ids: dict[str, int] = {}
        for i, token in enumerate(self.tokens):
            if token.type == "heading_open":
                slug = slugify(self.tokens[i + 1].content)
                if slug in self.ids:
                    errors.append(f"{self.rel}:{self.line(token)}: heading id {slug!r} used twice")
                if not slug or slug.startswith("src-"):  # src-<id> = the Sources list's entries
                    errors.append(f"{self.rel}:{self.line(token)}: heading id {slug!r} - start the heading with a word other than Src")
                self.ids[slug] = self.line(token)
                token.attrSet("id", slug)

    @staticmethod
    def line_of(text: str, key: str) -> int:
        match = re.search(rf"^{re.escape(key)}\s*:", text, re.M)
        return text[:match.start()].count("\n") + 1 if match else 2

    def line(self, token) -> int:
        return self.offset + (token.map[0] + 1 if token.map else 1)

    def line_text(self, token) -> str:
        return self.text.split("\n")[self.line(token) - 1]

    def find(self, token, needle: str) -> int:
        """Line of the first occurrence of needle inside token's block; its first line if none."""
        start = self.line(token)
        end = self.offset + token.map[1] if token.map else start
        lines = self.text.split("\n")
        return next((n for n in range(start, end + 1) if needle in lines[n - 1]), start)

    @property
    def built(self) -> bool:
        return self.status == "published" and (self.name != "index" or self.hub)

    @property
    def article(self) -> bool:
        return self.name not in ("about", "methods", "index")

    @property
    def out(self) -> str:
        """docs-relative output file."""
        return {"about": "about/index.html", "index": "research/index.html"}.get(self.name, f"research/{self.name}/index.html")

    @property
    def url(self) -> str:
        return "/" + self.out.removesuffix("index.html")


def lint(sources: list[Source], errors: list[str], warnings: list[str]) -> None:
    """Article rules for published sources: one "file:line: problem" each. Drafts may still hold notes."""
    today = datetime.date.today().isoformat()
    seen: dict[tuple[str, str], str] = {}
    for src in sources:
        if src.status != "published":
            continue
        lines = src.text.split("\n")
        for n, line in enumerate(lines, 1):
            at = f"{src.rel}:{n}"
            if NOTES.search(line):
                errors.append(f"{at}: [owner: note or TODO left in a published page")
            if "](<" in line:
                errors.append(f"{at}: link in <...> - write the destination plainly")
            if INVISIBLE.search(line):
                errors.append(f"{at}: invisible character U+{ord(INVISIBLE.search(line).group(0)):04X} - use a plain space")
            odd = sorted({c for c in line if c not in FONT_CHARS and not INVISIBLE.match(c)})
            if odd:
                warnings.append(f"{at}: {' '.join(f'U+{ord(c):04X}' for c in odd)} not in the site font (assets.UNICODES)")
        for key, limit in LIMITS.items():
            value = str(src.head.get(key) or "")
            if len(value) > limit:
                errors.append(f"{src.rel}:{src.line_of(src.text, key)}: {key} is {len(value)} characters, max {limit}")
        for key in "title", "description":
            value = " ".join(str(src.head.get(key, "")).split()).lower()
            if (key, value) in seen:
                errors.append(f"{src.rel}:{src.line_of(src.text, key)}: same {key} as {seen[key, value]}")
            seen.setdefault((key, value), src.rel)
        for key in "published", "modified":
            if str(src.head.get(key, "")) > today:
                errors.append(f"{src.rel}:{src.line_of(src.text, key)}: {key} {src.head[key]} is in the future")
        if src.published and src.modified and src.modified < src.published:
            errors.append(f"{src.rel}:{src.line_of(src.text, 'modified')}: modified {src.modified} is before published {src.published}")
        words = " ".join(str(src.head.get(k, "")) for k in ("title", "description", "og_title"))
        for ok in JARGON_OK:
            words = words.replace(ok, "")
        if JARGON.search(words):
            errors.append(f"{src.rel}:2: header uses {JARGON.search(words).group(0)!r} - say it in plain words")
        level = 1
        for i, token in enumerate(src.tokens):
            if token.type == "heading_open":
                depth = int(token.tag[1])
                raw = src.line_text(token)
                if depth == 1:
                    errors.append(f"{src.rel}:{src.line(token)}: # heading in the body - the title is the page's only h1, start at ##")
                elif depth > level + 1:
                    errors.append(f"{src.rel}:{src.line(token)}: h{depth} after h{level} - heading level skipped")
                level = depth
                inline = src.tokens[i + 1]
                if any(c.type in ("link_open", "image") for c in inline.children or []):
                    errors.append(f"{src.rel}:{src.line(token)}: link in a heading - put it in the text below")
                if any(c.type == "cite" for c in inline.children or []):
                    errors.append(f"{src.rel}:{src.line(token)}: citation in a heading - cite in the text below")
                if RAW_HTML.search(raw) or ENTITY.search(raw):
                    errors.append(f"{src.rel}:{src.line(token)}: HTML or &...; entity in a heading - plain text only")
                if token.markup.startswith("#") and re.search(r"\s#+\s*$", raw):
                    errors.append(f"{src.rel}:{src.line(token)}: closing # in a heading - drop it")
            if token.type != "inline":
                continue
            for child in token.children or []:
                if child.type == "image":
                    errors.append(f"{src.rel}:{src.find(token, '![')}: image - pages carry no images")
                elif child.type == "text":
                    tag = RAW_HTML.search(child.content)
                    if tag:
                        errors.append(f"{src.rel}:{src.find(token, tag.group(0))}: raw HTML {tag.group(0)!r} shows as text - put it in `code` or drop it")
                    text = child.content
                    for ok in JARGON_OK:
                        text = text.replace(ok, "")
                    word = JARGON.search(text)
                    if word:
                        errors.append(f"{src.rel}:{src.find(token, word.group(0))}: {word.group(0)!r} is jargon - say it in plain words")


MD = MarkdownIt("js-default")  # raw HTML escaped, tables on, no typographer


def _table_open(self, tokens, idx, options, env):
    # wide table scrolls inside its own box, not the page; focusable so keyboards can scroll it
    label = escape(tokens[idx].meta.get("label", "Table"))
    return f'<div class="table" role="region" aria-label="{label}" tabindex="0">\n' + self.renderToken(tokens, idx, options, env)


def _table_close(self, tokens, idx, options, env):
    return self.renderToken(tokens, idx, options, env) + "</div>\n"


MD.add_render_rule("table_open", _table_open)
MD.add_render_rule("table_close", _table_close)


def _cite(state):
    """[@id], [@id, p. 12], [@a; @b] in text -> one "cite" token, meta refs = [(id, locator)] (None if
    malformed). Runs after text_join: code is its own token, so citations in code stay text; none in link text."""
    for block in state.tokens:
        if block.type != "inline" or not block.children:
            continue
        out, depth = [], 0
        for child in block.children:
            depth += {"link_open": 1, "link_close": -1}.get(child.type, 0)
            if child.type != "text" or depth or "[@" not in child.content:
                out.append(child)
                continue
            pos = 0
            for match in CITE.finditer(child.content):
                if match.start() > pos:
                    out.append(Token("text", "", 0, content=child.content[pos:match.start()]))
                parts = [CITE_PART.fullmatch(p) for p in match.group(0)[1:-1].split(";")]
                refs = [(m.group(1), m.group(2)) for m in parts] if all(parts) else None
                out.append(Token("cite", "", 0, content=match.group(0), meta={"refs": refs}))
                pos = match.end()
            if pos < len(child.content):
                out.append(Token("text", "", 0, content=child.content[pos:]))
        block.children = out


def _render_cite(self, tokens, idx, options, env):
    links = [f'<a href="#src-{ref}">{escape(env["labels"][ref])}</a>' + (f", {escape(loc)}" if loc else "")
             for ref, loc in tokens[idx].meta["refs"]]
    return "(" + "; ".join(links) + ")"


ESCAPED = "\ue000"  # \[ in a source: kept out of the cite rule, turned back into [ after it


def _hide_escaped(state):
    for block in state.tokens:
        for child in block.children or []:
            if child.type == "text_special" and child.info == "escape" and child.content == "[":
                child.content = ESCAPED


def _show_escaped(state):
    for block in state.tokens:
        for child in block.children or []:
            if child.type == "text" and ESCAPED in child.content:
                child.content = child.content.replace(ESCAPED, "[")


MD.core.ruler.before("text_join", "hide_escaped", _hide_escaped)
MD.core.ruler.after("text_join", "cite", _cite)
MD.core.ruler.after("cite", "show_escaped", _show_escaped)
MD.add_render_rule("cite", _render_cite)


class Registry:
    """app/web/research/sources.yml: every source an article may cite, checked field by field."""

    def __init__(self, root: Path, errors: list[str], warnings: list[str], path: Path | None = None):
        self.entries: dict[str, dict] = {}
        self.labels: dict[str, str] = {}
        self.lines: dict[str, int] = {}
        path = root / REGISTRY if path is None else path
        self.rel = path.resolve().relative_to(root.resolve()).as_posix() if path.resolve().is_relative_to(root.resolve()) else str(path)
        if not path.is_file():
            return
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        try:
            data = yaml.load(text, Loader=Loader)
            nodes = yaml.compose(text, Loader=Loader)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            errors.append(f"{self.rel}:{mark.line + 1 if mark else 1}: {getattr(e, 'problem', None) or e}")
            return
        if data is None:
            return
        if not isinstance(data, list):
            errors.append(f"{self.rel}:1: must be a list of entries, each starting with - id:")
            return
        today = datetime.date.today().isoformat()
        for entry, node in zip(data, nodes.value):
            line = node.start_mark.line + 1
            if not isinstance(entry, dict):
                errors.append(f"{self.rel}:{line}: entry must be key: value lines")
                continue
            at = {k.value: k.start_mark.line + 1 for k, _ in node.value}
            ref = entry.get("id")
            if not isinstance(ref, str) or not CITE_ID.match(ref):
                errors.append(f"{self.rel}:{at.get('id', line)}: id must be lower-case words joined by - (a-z, 0-9)")
                continue
            where = lambda key: f"{self.rel}:{at.get(key, line)}: {ref}"  # noqa: E731
            if ref in self.entries:
                errors.append(f"{where('id')}: id used twice (first at line {self.lines[ref]})")
                continue
            before = len(errors)
            for key in sorted(set(entry) - ENTRY_KEYS, key=str):
                errors.append(f"{where(key)}: unknown key {key!r} (allowed: {', '.join(sorted(ENTRY_KEYS))})")
            kind = entry.get("type")
            if kind not in TYPE_NEEDS:
                errors.append(f"{where('type')}: type must be one of {', '.join(TYPE_NEEDS)}")
            for key in ("title", "evidence", "checked", *TYPE_NEEDS.get(kind, ())):
                if entry.get(key) in (None, ""):
                    errors.append(f"{where('id')}: needs {key}" + (f" (type {kind})" if key in TYPE_NEEDS.get(kind, ()) else ""))
            for key in "title", "venue", "org", "sample":
                if key in entry and not (isinstance(entry[key], str) and entry[key].strip()):
                    errors.append(f"{where(key)}: {key} must be text")
            authors = entry.get("authors")
            if authors is not None and not (isinstance(authors, list) and authors and all(
                    isinstance(a, str) and re.fullmatch(r"[^,]*\S\s*,\s*\S.*", a) for a in authors)):
                errors.append(f"{where('authors')}: authors must be a list of 'Surname, Given' names")
            if not authors and not entry.get("org"):
                errors.append(f"{where('id')}: needs authors or org")
            year = entry.get("year")
            if not (type(year) is int and 1000 <= year <= 9999):
                errors.append(f"{where('year')}: year must be a 4-digit number")
            if "evidence" in entry and entry["evidence"] not in EVIDENCE:
                errors.append(f"{where('evidence')}: evidence must be one of {', '.join(EVIDENCE)}")
            if not entry.get("doi") and not entry.get("url"):
                errors.append(f"{where('id')}: needs doi or url")
            if "doi" in entry and not (isinstance(entry["doi"], str) and DOI.match(entry["doi"])):
                errors.append(f"{where('doi')}: doi must look like 10.1234/abc (no https://doi.org/ in front)")
            if "url" in entry and not (isinstance(entry["url"], str) and entry["url"].startswith("https://")
                                       and urlsplit(entry["url"]).netloc and not re.search(r"\s", entry["url"])):
                errors.append(f"{where('url')}: url must start with https:// (no http)")
            if "preprint" in entry and not isinstance(entry["preprint"], bool):
                errors.append(f"{where('preprint')}: preprint must be true or false")
            for key in "checked", "recheck_by":
                if entry.get(key) not in (None, "") and iso(entry[key], where(key), errors):
                    if key == "checked" and str(entry[key]) > today:
                        errors.append(f"{where(key)}: checked {entry[key]} is in the future")
                    if key == "recheck_by" and str(entry[key]) < today:
                        warnings.append(f"{where(key)}: recheck_by {entry[key]} has passed - check it again")
            self.lines[ref] = line
            if len(errors) == before:
                self.entries[ref] = entry
        self._label()

    def _label(self) -> None:
        """Author-year label: Smith 2017, Smith and Jones 2017, Smith et al. 2017, Org 2017; a/b when two match."""
        plain = {}
        for ref, entry in self.entries.items():
            names = [a.split(",")[0].strip() for a in entry.get("authors") or []]
            who = (names[0] if len(names) == 1 else f"{names[0]} and {names[1]}" if len(names) == 2
                   else f"{names[0]} et al." if names else entry["org"].strip())
            plain[ref] = f"{who} {entry['year']}"
        for ref in sorted(plain):
            twins = sorted(r for r in plain if plain[r] == plain[ref])
            self.labels[ref] = plain[ref] + ("abcdefghijklmnopqrstuvwxyz"[twins.index(ref)] if len(twins) > 1 else "")

    def item(self, ref: str) -> str:
        """One <li> of a page's Sources list."""
        entry = self.entries[ref]
        authors = entry.get("authors") or []
        who = (", ".join(authors[:-1]) + " and " + authors[-1]) if len(authors) > 1 else authors[0] if authors else entry["org"]
        parts = [f"{escape(who.strip())} ({entry['year']}).", escape(stop(entry["title"].strip()))]
        if entry.get("venue"):
            parts.append(f"<i>{escape(stop(entry['venue'].strip()))}</i>")
        if entry.get("doi"):
            doi = "https://doi.org/" + quote(entry["doi"], safe="/:;()._-")
            parts.append(f'<a href="{escape(doi)}">{escape(doi)}</a>')
        if entry.get("url"):
            parts.append(f'<a href="{escape(entry["url"])}">{escape(entry["url"])}</a>')
        evidence = EVIDENCE[entry["evidence"]] + (f", {entry['sample'].strip()}" if entry.get("sample") else "")
        parts.append(f'<span class="evidence">{escape(stop(evidence))}</span>')
        if entry.get("preprint"):
            parts.append("Preprint, not peer-reviewed.")
        parts.append(f'Checked <time datetime="{entry["checked"]}">{long_date(str(entry["checked"]))}</time>.')
        return f'<li id="src-{ref}">' + " ".join(parts) + "</li>"


def stop(text: str) -> str:
    """Text ending in a full stop (or the ?/! it already has)."""
    return text if text[-1:] in ".?!" else text + "."


def cites(src: Source) -> list[tuple[Token, Token]]:
    """(inline token, cite token) for every citation in a source, in page order."""
    return [(t, c) for t in src.tokens if t.type == "inline" for c in t.children or [] if c.type == "cite"]


def units(src: Source):
    """Text a citation must cover: (inline token, text) per sentence; a table row is one unit (its source
    may sit in another cell). Citations -> \\x01, code -> \\x02. Headings skipped: the text below cites."""
    def flat(inline):
        return "".join({"text": c.content, "cite": "\x01", "code_inline": "\x02", "softbreak": " ",
                        "hardbreak": " "}.get(c.type, "") for c in inline.children or [])

    row = None
    for i, token in enumerate(src.tokens):
        if token.type == "tr_open":
            row = []
        elif token.type == "tr_close":
            if row:
                yield row[0], " | ".join(flat(t) for t in row)
            row = None
        elif token.type == "inline" and row is not None and src.tokens[i - 1].type in ("th_open", "td_open"):
            row.append(token)
        elif token.type == "inline" and src.tokens[i - 1].type != "heading_open":
            text = ABBREV.sub(lambda m: m.group(0)[:-1] + "\x03", flat(token))
            sentences = []
            for piece in re.split(r"(?<=[.!?])\s+", text):
                # "... 36%. [@q] Next" - citations opening a piece belong to the sentence before it
                lead = re.match(r"[\x01\s]*", piece).end() if sentences else 0
                if lead:
                    sentences[-1] += " " + piece[:lead]
                if re.search(r"[^\W_]", piece[lead:]) or not sentences:
                    sentences.append(piece[lead:])
            for sentence in sentences:
                yield token, sentence.replace("\x03", ".")


def citations(sources: list[Source], registry: Registry, errors: list[str], warnings: list[str]) -> None:
    """Every [@id] known; every statistic cited; registry entries nobody cites = warning."""
    used = set()
    for src in sources:
        for inline, cite in cites(src):
            refs = cite.meta["refs"]
            used.update(ref for ref, _ in refs or [])
            if src.status != "published":
                continue
            if refs is None:
                errors.append(f"{src.rel}:{src.find(inline, cite.content)}: citation {cite.content!r} - write [@id], [@id, p. 12] or [@a; @b]")
                continue
            for ref, _ in refs:
                if ref not in registry.entries:
                    errors.append(f"{src.rel}:{src.find(inline, '@' + ref)}: [@{ref}] is not in {registry.rel}"
                                  + (" (entry has problems above)" if ref in registry.lines else ""))
        if src.status != "published":
            continue
        if cites(src) and "sources" in src.ids:
            errors.append(f"{src.rel}:{src.ids['sources']}: heading id 'sources' is the citation list's - rename the heading")
        for inline, text in units(src):
            stat = STAT.search(text.replace("\x02", " "))
            if stat and "\x01" not in text and not any(u in text for u in src.uncited):
                errors.append(f"{src.rel}:{src.find(inline, stat.group(0))}: statistic {stat.group(0)!r} without a citation"
                              " - add [@id], or list a snippet of the sentence under uncited: in the header")
    for ref in sorted(set(registry.entries) - used):
        warnings.append(f"{registry.rel}:{registry.lines[ref]}: {ref} is not cited by any page")


def reviews(root: Path, sources: list[Source], errors: list[str], warnings: list[str]) -> None:
    """Review gate: a built page needs reviews/<name>.md, verdict publish, reviewed on or after modified."""
    folder = root / REVIEWS
    # names listed from disk: a macOS disk would find Ai-Bias.md for ai-bias.md
    found = {p.name: p for p in folder.iterdir() if p.is_file()} if folder.is_dir() else {}
    names = {s.name for s in sources}
    for name in sorted(found):
        if name.endswith(".md") and name[:-3] not in names:
            warnings.append(f"{REVIEWS.as_posix()}/{name}:1: review of a page that doesn't exist")
    for src in sources:
        if not src.built or src.name == "index":  # hub intro: a few lines over the list, not a claim page
            continue
        rel = f"{REVIEWS.as_posix()}/{src.name}.md"
        if f"{src.name}.md" not in found:
            errors.append(f"{src.rel}:1: published page needs an adversarial review in {rel} (verdict: publish)")
            continue
        text = found[f"{src.name}.md"].read_bytes().decode("utf-8").replace("\r\n", "\n")
        match = re.match(r"---\n(.*?\n)---\n", text, re.S)
        try:
            head = yaml.load(match.group(1), Loader=Loader) if match else None
        except yaml.YAMLError as e:
            errors.append(f"{rel}:1: header: {getattr(e, 'problem', None) or e}")
            continue
        if not isinstance(head, dict):
            errors.append(f"{rel}:1: needs a YAML header between --- lines with reviewed: and verdict:")
            continue
        for key in sorted(set(head) - REVIEW_KEYS, key=str):
            errors.append(f"{rel}:{Source.line_of(text, key)}: unknown header key {key!r} (allowed: {', '.join(sorted(REVIEW_KEYS))})")
        if head.get("verdict") != "publish":
            errors.append(f"{rel}:{Source.line_of(text, 'verdict')}: verdict is {head.get('verdict')!r} - the page publishes only on verdict: publish")
        if "reviewed" not in head:
            errors.append(f"{rel}:2: needs reviewed: YYYY-MM-DD")
        else:
            day = iso(head["reviewed"], f"{rel}:{Source.line_of(text, 'reviewed')}", errors)
            if day and src.modified and day < src.modified:
                errors.append(f"{rel}:{Source.line_of(text, 'reviewed')}: reviewed {day} is before the page's modified {src.modified} - review the change")


def tracked(root: Path) -> set[str]:
    """Files git tracks, exact case: the only repo paths a link may name (GitHub shows those; a macOS
    disk also finds SITE.md for site.md, and an ignored private file would put its name on the page)."""
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=False).stdout
    return set(out.decode("utf-8").split("\0")) - {""}


def rewrite(href: str, src: Source, by_name: dict[str, Source], root: Path, site_files: set[str],
            repo_files: set[str]) -> str:
    """A link in a source -> its URL on the site. Raises ValueError w/ the reason when it can't land."""
    home = site(root)
    url = urlsplit(href)
    if href.startswith("#"):
        if url.fragment not in src.ids:
            raise ValueError(f"no heading #{url.fragment} on this page")
        return href
    if href.startswith(home):
        path = url.path
        file = path.lstrip("/") + "index.html" if path.endswith("/") else path.lstrip("/")
        if file not in site_files:
            raise ValueError(f"{href} is not a page on this site")
        if not path.endswith("/") and file + "/index.html" in site_files:
            raise ValueError(f"{href}: folder link needs a / at the end")
        return path + (f"?{url.query}" if url.query else "") + (f"#{url.fragment}" if url.fragment else "")
    if url.scheme or url.netloc or href.startswith("/"):
        raise ValueError(f"{href}: link to research pages as x.md, to this site as {home}..., to other sites through sources")
    target = (src.path.parent / url.path).resolve()
    sources = (root / SOURCES).resolve()
    if target.parent == sources and target.suffix == ".md":
        dest = by_name.get(target.stem)
        if dest is None or not dest.built:
            raise ValueError(f"{url.path} is not a published page")
        if url.fragment and url.fragment not in dest.ids:
            raise ValueError(f"no heading #{url.fragment} in {url.path}")
        return dest.url + (f"#{url.fragment}" if url.fragment else "")
    try:
        rel = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{href} points outside the repo") from None
    if rel not in repo_files and not any(f.startswith(rel + "/") for f in repo_files):
        raise ValueError(f"{href}: no such file in the repo (tracked by git, exact case)")
    return REPO + quote(rel) + (f"#{url.fragment}" if url.fragment else "")


def body_html(src: Source, by_name: dict[str, Source], root: Path, site_files: set[str], errors: list[str],
              registry: Registry, repo_files: set[str]) -> str:
    label = src.title
    for i, token in enumerate(src.tokens):
        if token.type == "heading_open":
            label = src.tokens[i + 1].content
        elif token.type == "table_open":
            token.meta["label"] = f"Table: {label}"
        elif token.type == "inline":
            for child in token.children or []:
                if child.type == "link_open":
                    try:
                        child.attrSet("href", rewrite(child.attrGet("href"), src, by_name, root, site_files, repo_files))
                    except ValueError as e:
                        errors.append(f"{src.rel}:{src.line(token)}: {e}")
    html = MD.renderer.render(src.tokens, MD.options, {"labels": registry.labels})
    cited = {ref for _, cite in cites(src) for ref, _ in cite.meta["refs"] or []} & set(registry.entries)
    if cited:
        # alphabetical by label, so a reader scanning for "Quillian et al. 2017" finds it
        items = [registry.item(ref) for ref in sorted(cited, key=lambda r: (registry.labels[r].casefold(), r))]
        html += '<h2 id="sources">Sources</h2>\n<ol class="sources">\n' + "\n".join(items) + "\n</ol>\n"
    return html


def home_parts(root: Path) -> dict[str, str]:
    """What every generated page copies from docs/index.html: shared CSS, header, footer, head links,
    og:image size + type lines (image + alt swapped for CARD)."""
    text = (root / "docs" / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'^<link rel="(?:icon|apple-touch-icon|manifest|preload)".*$', text, re.M)
    alt = escape(CARD_ALT)
    og = re.sub(r'^(<meta property="og:image" content=")[^"]*', rf"\g<1>{site(root)}{CARD}", text, flags=re.M)
    og = re.sub(r'^(<meta (?:property="og|name="twitter):image:alt" content=")[^"]*', rf"\g<1>{alt}", og, flags=re.M)
    return {
        "css": re.search(r"  /\* shared \*/.*?/\* /shared \*/", text, re.S).group(0),
        "header": re.search(r"<header\b.*?</header>", text, re.S).group(0),
        "footer": re.search(r"<footer\b.*?</footer>", text, re.S).group(0),
        "links": "\n".join(links),
        "og": "\n".join(re.findall(r'^<meta property="og:image.*$', og, re.M)),
        "twitter": "\n".join(re.findall(r'^<meta name="twitter:.*$', og, re.M)),
    }


PAGE_CSS = """
  /* main.wrap: .wrap's own padding shorthand would otherwise win and zero the top + bottom */
  main.wrap { padding-top: clamp(24px, 4vh, 48px); padding-bottom: clamp(56px, 9vh, 104px); }
  /* editorial measure: one column of reading text, never wider than 68ch */
  .page { max-width: 68ch; }
  .crumbs ol { list-style: none; margin: 0 0 20px; padding: 0; display: flex; flex-wrap: wrap; font-size: var(--step--1); color: var(--text-2); }
  .crumbs li { margin: 0; }
  .crumbs li + li::before { content: "/"; padding: 0 0.5em; }
  h1 { font-size: clamp(2.25rem, 1.4rem + 2.6vw, 4rem); line-height: 1.04; letter-spacing: -0.012em; font-weight: 700; margin: 0 0 16px; }
  h2 { font-size: clamp(1.5rem, 1.25rem + 0.8vw, 2rem); line-height: 1.15; letter-spacing: -0.005em; margin: 48px 0 14px; padding-top: 14px; border-top: 1px solid var(--line); }
  h3 { font-size: var(--step-1); line-height: 1.3; margin: 32px 0 8px; }
  h2, h3 { scroll-margin-top: 16px; }
  .meta { margin: 0 0 32px; color: var(--text-2); font-size: var(--step--1); }
  p { margin: 0 0 16px; }
  ul, ol { margin: 0 0 16px; padding-left: 1.3em; }
  li { margin: 0 0 8px; }
  li::marker { color: var(--text-2); }
  /* real italics: the Caladea Italic face, never a slanted roman */
  i, em, cite { font-style: italic; font-synthesis: none; }
  strong, b { font-weight: 700; }
  blockquote { margin: 24px 0; padding-left: 20px; border-left: 3px solid var(--text); font-size: var(--step-1); line-height: 1.45; }
  code { font-family: var(--mono); font-size: 0.85em; }
  pre { overflow-x: auto; padding: 12px 16px; border: 1px solid var(--line); }
  /* "Short answer": the bold line right under the byline + its list = a ruled note (thick rule over, thin under) */
  .meta + p:has(> strong:only-child):has(+ ul) { margin: 0; padding-top: 12px; border-top: 3px solid var(--text); font-size: var(--step-1); }
  .meta + p:has(> strong:only-child) + ul { margin: 0 0 40px; padding: 10px 0 14px 1.3em; border-bottom: 1px solid var(--text); }
  .meta + p:has(> strong:only-child) + ul li::marker { color: var(--text); }
  /* tables: lining, tabular figures so columns of numbers line up */
  .table { overflow-x: auto; margin: 24px 0; }
  table { border-collapse: collapse; font-size: var(--step--1); line-height: 1.45; font-variant-numeric: lining-nums tabular-nums; }
  thead th { border-bottom: 2px solid var(--text); }
  th, td { text-align: left; vertical-align: top; padding: 8px 16px 8px 0; border-bottom: 1px solid var(--line); }
  /* evidence labels (methods table): the label column set bold, kept on one line where it fits */
  .table td:first-child { font-weight: 700; }
  /* Sources: hanging numbers in tabular lining figures, smaller set, hairline between entries */
  #sources { margin-top: 64px; border-top: 3px solid var(--text); }
  .sources { list-style: none; padding: 0; counter-reset: src; font-size: var(--step--1); line-height: 1.5; }
  .sources li { position: relative; margin: 0; padding: 10px 0 10px 2.6em; border-bottom: 1px solid var(--line); counter-increment: src; overflow-wrap: anywhere; scroll-margin-top: 16px; }
  .sources li::before { content: counter(src) "."; position: absolute; left: 0; width: 2em; text-align: right; font-variant-numeric: lining-nums tabular-nums; color: var(--text-2); }
  .sources li:target { outline: 2px solid var(--text); outline-offset: 2px; }
  .sources a { text-decoration-color: var(--text-2); }
  .sources .evidence { font-style: italic; font-synthesis: none; }
  /* On this page: a second column on wide screens (sticky, the article's h2s); hidden below 1280px */
  .toc { display: none; }
  @media (min-width: 1280px) {
    main.wrap:has(> .toc) { display: grid; grid-template-columns: minmax(0, 68ch) minmax(0, 1fr); column-gap: var(--gutter); }
    main.wrap:has(> .toc) > .page { grid-column: 1; grid-row: 1; }
    .toc {
      display: block; grid-column: 2; grid-row: 1; justify-self: end; align-self: start; width: min(100%, 20rem);
      position: sticky; top: 24px; max-height: calc(100vh - 48px); overflow-y: auto;
      margin-top: 2.5rem; font-size: var(--step--1); line-height: 1.4;
    }
    .toc p { margin: 0; padding-bottom: 8px; font-weight: 700; border-bottom: 2px solid var(--text); }
    .toc ol { list-style: none; margin: 0; padding: 0; }
    .toc li { margin: 0; border-bottom: 1px solid var(--line); }
    .toc a { display: block; padding: 8px 0 9px; text-decoration-color: var(--text-2); }
  }
  /* hub: each article a clipping under a thick rule, like the home page's research picks */
  .list { list-style: none; margin: 32px 0 0; padding: 0; }
  .list li { margin: 0; padding: 16px 0 22px; border-top: 2px solid var(--text); }
  .list li:last-child { border-bottom: 1px solid var(--line); }
  .list a { font-size: clamp(1.375rem, 1.2rem + 0.7vw, 1.75rem); font-weight: 700; line-height: 1.2; }
  .list p { margin: 8px 0 0; color: var(--text-2); }
  .list .date { margin-top: 6px; }
  .date { color: var(--text-2); font-size: var(--step--1); }
  @media (max-width: 600px) {
    main.wrap { padding-top: 22px; }
    h2 { margin-top: 36px; }
    .sources li { padding-left: 2.2em; }
    .sources li::before { width: 1.7em; }
  }
  @media print {
    main.wrap { padding-top: 0; padding-bottom: 0; }
    .crumbs, .toc { display: none !important; }
    .page { max-width: none; }
    .sources li { break-inside: avoid; }
  }
"""


def jsonld(graph: list[dict]) -> str:
    """One <script> block: stable bytes (no spaces, UTF-8 as is); < escaped so a title can't end the block."""
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + data.replace("<", "\\u003c") + "</script>"


def dates(src: Source) -> str:
    """Published <time>, + Updated <time> only when it differs; sentences, no middle-dot separators."""
    out = [f'Published <time datetime="{src.published}">{long_date(src.published)}</time>']
    if src.modified != src.published:
        out.append(f'Updated <time datetime="{src.modified}">{long_date(src.modified)}</time>')
    return ". ".join(out) + "."


def newest(articles: list[Source]) -> list[Source]:
    """Newest published first, then by name."""
    return sorted(sorted(articles, key=lambda s: s.name), key=lambda s: s.published, reverse=True)


def listing(articles: list[Source]) -> str:
    """Hub list: newest first, link text = title."""
    items = []
    for src in newest(articles):
        items.append(f'<li><a href="{src.url}">{escape(src.title)}</a>'
                     f'<p>{escape(src.description)}</p><p class="date">{dates(src)}</p></li>')
    return '<ul class="list">\n' + "\n".join(items) + "\n</ul>\n"


def stamp(day: str) -> str:
    """2026-10-02 -> 2026-10-02T00:00:00Z: Atom needs an RFC 3339 date-time (a date alone is invalid)."""
    return day + "T00:00:00Z"


def feed(root: Path, index: Source, articles: list[Source]) -> str:
    """Atom feed of the published articles, newest first; updated = latest modified. Stable bytes."""
    home = site(root)
    url = home + FEED

    def add(parent, tag: str, text: str | None = None, **attrs) -> ET.Element:
        el = ET.SubElement(parent, tag, attrs)
        el.text = text
        return el

    top = ET.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom", "xml:lang": "en"})
    add(top, "title", FEED_TITLE)
    add(top, "subtitle", index.description)
    add(top, "link", rel="self", type="application/atom+xml", href=url)
    add(top, "link", rel="alternate", type="text/html", href=home + index.url.lstrip("/"))
    add(top, "id", url)
    add(top, "updated", stamp(max(s.modified for s in articles)))
    author = add(top, "author")
    add(author, "name", AUTHOR)
    add(author, "uri", home + "about/")
    for src in newest(articles):
        link = home + src.url.lstrip("/")
        entry = add(top, "entry")
        add(entry, "title", src.title)
        add(entry, "link", rel="alternate", type="text/html", href=link)
        add(entry, "id", link)
        add(entry, "published", stamp(src.published))
        add(entry, "updated", stamp(src.modified))
        add(entry, "summary", src.description)
    ET.indent(top)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(top, encoding="unicode") + "\n"


def page(src: Source, root: Path, body: str, parts: dict[str, str], hub: bool) -> str:
    home = site(root)
    url = home + src.url.lstrip("/")
    person = {"@type": "Person", "@id": home + "about/#person", "name": AUTHOR, "url": home + "about/"}
    # breadcrumb: (name, path); Research is a link once the hub exists, plain text (and not in JSON-LD) before
    crumbs = [("Home", "/")]
    if src.name not in ("about", "index"):
        crumbs.append(("Research", "/research/" if hub else None))
    crumbs.append((src.title, src.url))
    visible = [f'<li aria-current="page">{escape(name)}</li>' if i == len(crumbs) - 1
               else f'<li><a href="{path}">{escape(name)}</a></li>' if path else f"<li>{escape(name)}</li>"
               for i, (name, path) in enumerate(crumbs)]
    linked = [(name, path) for name, path in crumbs if path]
    graph = [{"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": n, "name": name, "item": home + path.lstrip("/")}
        for n, (name, path) in enumerate(linked, 1)]}]
    image = unescape(re.search(r'<meta property="og:image" content="([^"]*)"', parts["og"]).group(1))
    if src.article:
        # dates == the visible <time> values; publisher left out (not in Google's Article table)
        graph.insert(0, {"@type": "Article", "@id": url + "#article", "headline": src.title,
                         "description": src.description, "url": url, "mainEntityOfPage": url,
                         "datePublished": src.published, "dateModified": src.modified, "author": person,
                         "image": image, "inLanguage": "en"})
    elif src.name == "about":
        graph.insert(0, {"@type": "ProfilePage", "@id": url, "url": url, "name": src.title,
                         "dateModified": src.modified, "mainEntity": {**person, "sameAs": SAME_AS}})
    if src.name == "index":
        meta = ""
    elif src.name == "about":
        meta = f'Updated <time datetime="{src.modified}">{long_date(src.modified)}</time>'
    else:
        meta = f'By <a href="/about/">{AUTHOR}</a>. {dates(src)}'
    kind = {"about": "profile", "index": "website"}.get(src.name, "article")
    head = [
        f"<title>{escape(src.title)}</title>",
        f'<meta name="description" content="{escape(src.description)}">',
        f'<link rel="canonical" href="{url}">',
        *([f'<link rel="alternate" type="application/atom+xml" title="{escape(FEED_TITLE)}" href="/{FEED}">']
          if hub and (src.article or src.name == "index") else []),
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<meta name="color-scheme" content="light dark">',
        '<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#1c1c1e" media="(prefers-color-scheme: dark)">',
        f'<meta property="og:type" content="{kind}">',
        '<meta property="og:site_name" content="CEZ Job Finder">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:title" content="{escape(src.og_title)}">',
        f'<meta property="og:description" content="{escape(src.description)}">',
    ]
    if kind == "article":
        head += [f'<meta property="article:published_time" content="{src.published}">',
                 f'<meta property="article:modified_time" content="{src.modified}">']
    head += [parts["og"], parts["twitter"], parts["links"], jsonld(graph)]
    wrapper = "article" if kind == "article" else "div"
    # articles: "On this page" = every h2 (Sources too), shown beside the column on wide screens only
    heads = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.S) if kind == "article" else []
    toc = ['<nav class="toc" aria-label="On this page">', "<p>On this page</p>", "<ol>",
           *(f'<li><a href="#{slug}">{re.sub(r"<[^>]+>", "", text)}</a></li>' for slug, text in heads),
           "</ol>", "</nav>"] if len(heads) > 2 else []
    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        *head,
        "<style>",
        parts["css"],
        PAGE_CSS.rstrip("\n"),
        "</style>",
        "</head>",
        "<body>",
        parts["header"],
        '<main id="main" class="wrap">',
        *toc,
        f'<{wrapper} class="page">',
        f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(visible)}</ol></nav>',
        f"<h1>{escape(src.title)}</h1>",
        *([f'<p class="meta">{meta}</p>'] if meta else []),
        body.rstrip("\n"),
        f"</{wrapper}>",
        "</main>",
        parts["footer"],
        "</body>",
        "</html>",
        "",
    ])


def research(root: Path, site_files: set[str], warnings: list[str] | None = None) -> dict[str, str]:
    """Every published research source as docs-relative path -> HTML. Raises SourceError on any problem;
    warnings (page still built) go to the list given."""
    folder = root / SOURCES
    errors: list[str] = []
    warnings = [] if warnings is None else warnings
    sources = [Source(p, root, errors) for p in sorted(folder.glob("*.md"))] if folder.is_dir() else []
    registry = Registry(root, errors, warnings)
    if errors:  # header + registry problems first: a page can't be drawn w/o its title, dates, sources
        raise SourceError("\n".join(errors))
    lint(sources, errors, warnings)
    citations(sources, registry, errors, warnings)
    reviews(root, sources, errors, warnings)
    if errors:  # an unknown [@id] can't be drawn
        raise SourceError("\n".join(errors))
    by_name = {s.name: s for s in sources}
    articles = [s for s in sources if s.article and s.built]
    if articles:
        index = by_name.get("index")
        if index is None or index.status != "published":
            errors.append(f"{SOURCES.as_posix()}/index.md:1: the hub /research/ lists the articles - publish index.md with the first one")
        else:
            index.hub = True
    hub = "index" in by_name and by_name["index"].hub
    built = [s for s in sources if s.built]
    out: dict[str, str] = {}
    if built:
        parts = home_parts(root)
        if any(s.name != "about" for s in built) and not (by_name.get("about") and by_name["about"].built):
            errors.append(f"{SOURCES.as_posix()}/about.md:1: bylines link /about/ - publish about.md with the first page")
        files = site_files | {s.out for s in built} | ({FEED} if hub else set())
        repo_files = tracked(root)
        for src in built:
            body = body_html(src, by_name, root, files, errors, registry, repo_files)
            if src.name == "index":
                body += listing(articles)
            out[src.out] = page(src, root, body, parts, hub)
        if hub:
            out[FEED] = feed(root, by_name["index"], articles)
    if errors:
        raise SourceError("\n".join(errors))
    return out


def build(root: Path, warnings: list[str] | None = None) -> dict[str, str]:
    """Every generated file: docs-relative path -> text. Reads, never writes."""
    docs = root / "docs"
    found = [rel for rel in listed(docs) if rel.split("/")[0] not in OWNED]
    hand = {rel: (docs / rel).read_text(encoding="utf-8") for rel in found
            if rel.endswith(".html") and rel.split("/")[0] not in NOT_PAGES}
    out = research(root, set(found), warnings)
    out["sitemap.xml"] = sitemap(root, {**hand, **{k: v for k, v in out.items() if k.endswith(".html")}})
    return dict(sorted(out.items()))


def orphans(root: Path, built: dict[str, str]) -> list[str]:
    docs = root / "docs"
    return [rel for rel in listed(docs) if rel.split("/")[0] in OWNED and rel not in built]


def same(path: Path, text: str) -> bool:
    # CRLF checkout (git autocrlf on Windows) is the same file, not a stale one
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") == text


def problems(root: Path, built: dict[str, str] | None = None) -> list[str]:
    """What --check reports: stale, missing, orphaned. Empty = docs/ matches the sources."""
    docs, built, found = root / "docs", build(root) if built is None else built, []
    for rel, text in built.items():
        path = docs / rel
        if not path.is_file():
            found.append(f"missing: docs/{rel}")
        elif not same(path, text):
            found.append(f"stale: docs/{rel}")
    found += [f"orphaned: docs/{rel}" for rel in orphans(root, built)]
    return found


def write(root: Path, built: dict[str, str] | None = None) -> list[str]:
    """Delete orphans in the owned folders, then write stale + missing files (UTF-8, LF). Returns what changed.
    Orphans go first: on a macOS disk research/Foo/ is research/foo/, so a later delete would take the new file."""
    docs, built, changed = root / "docs", build(root) if built is None else built, []
    for rel in orphans(root, built):
        (docs / rel).unlink()
        changed.append(f"deleted: docs/{rel}")
    # folders the deletes emptied (a .DS_Store alone doesn't keep one: Pages never serves it)
    for name in OWNED:
        top = docs / name
        folders = [top, *(p for p in top.rglob("*") if p.is_dir())] if top.is_dir() else []
        for folder in sorted(folders, key=lambda p: len(p.parts), reverse=True):
            if folder.is_dir() and not listed(folder):
                shutil.rmtree(folder)
    for rel, text in built.items():
        path = docs / rel
        if path.is_file() and same(path, text):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        changed.append(f"wrote: docs/{rel}")
    return changed


# --- --links: is every source real? (network; never run from the tests) ---

ARXIV_ID = r"(\d{4}\.\d{4,5}|[a-z][a-z-]*(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?"
ARXIV_URL = re.compile(rf"^https://(?:export\.)?arxiv\.org/(?:abs|pdf)/{ARXIV_ID}(?:\.pdf)?/?$")
ARXIV_DOI = re.compile(rf"^10\.48550/arxiv\.{ARXIV_ID}$", re.I)
ATOM = "{http://www.w3.org/2005/Atom}"
SIMILAR = 0.9  # title match: below this the DOI / arXiv id names another work (invented or mistyped)
ARXIV_PAUSE = 3.0  # arXiv API terms: one request every 3 seconds
USER_AGENT = "CEZ-Job-Finder-source-check/1 (+https://jobs.enrriquez.com/)"


def similarity(a: str, b: str) -> float:
    """Titles compared as plain lower-case words: Crossref adds <i> tags, &amp;, odd spacing + case."""
    def norm(text):
        return " ".join(re.sub(r"[^\w\s]", " ", unescape(re.sub(r"<[^>]+>", "", text)).casefold()).split())
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def arxiv_id(entry: dict) -> str | None:
    for pattern, value in ((ARXIV_DOI, entry.get("doi") or ""), (ARXIV_URL, entry.get("url") or "")):
        match = pattern.match(value)
        if match:
            return match.group(1)
    return None


def _get(client, url: str):
    """(response, None), or (None, why) when nothing came back."""
    try:
        return client.get(url, follow_redirects=True), None
    except Exception as e:  # httpx.HTTPError, bad URL, TLS: all mean "no answer", never a crash mid-list
        return None, f"no answer ({type(e).__name__})"


def _match(entry: dict, title: str, years: list[int], where: str) -> tuple[str, str]:
    """Title + year against what the record says: ok, or broken when it's another work."""
    score = similarity(entry["title"], title)
    if score < SIMILAR:
        return "broken", f"{where} names another work ({score:.2f} title match): {title!r}"
    if years and min(abs(y - entry["year"]) for y in years) > 1:
        return "broken", f"{where} says {sorted(years)[0]}, entry says {entry['year']}"
    return "ok", f"{where}: title + year match"


def check_doi(client, entry: dict) -> list[tuple[str, str]]:
    """doi.org handle API (does the DOI exist?) then Crossref (is it this title, this year?)."""
    doi = quote(entry["doi"], safe="/:;()._-")
    response, why = _get(client, f"https://doi.org/api/handles/{doi}")
    if response is None:
        return [("check", f"doi {entry['doi']}: doi.org {why}")]
    if response.status_code == 404:
        return [("broken", f"doi {entry['doi']} does not exist (doi.org)")]
    if response.status_code != 200:
        return [("check", f"doi {entry['doi']}: doi.org answered {response.status_code}")]
    if arxiv_id(entry):
        return [("ok", f"doi {entry['doi']} exists (arXiv DOI: title checked through arXiv)")]
    response, why = _get(client, f"https://api.crossref.org/works/{doi}")
    if response is None or response.status_code != 200:
        status = why or (f"has no record (registered elsewhere, e.g. DataCite) - compare the title by hand"
                         if response.status_code == 404 else f"answered {response.status_code}")
        return [("check", f"doi {entry['doi']} exists; Crossref {status}")]
    try:
        work = response.json()["message"]
        titles = [t for t in work.get("title") or [] if t]
        titles += [f"{t}: {s}" for t in titles[:1] for s in work.get("subtitle") or [] if s]
        years = [parts[0][0] for key in ("issued", "published", "published-print", "published-online")
                 if (parts := (work.get(key) or {}).get("date-parts")) and parts[0] and parts[0][0]]
    except (ValueError, KeyError, TypeError, IndexError):
        return [("check", f"doi {entry['doi']}: Crossref record unreadable")]
    if not titles:
        return [("check", f"doi {entry['doi']}: Crossref record has no title")]
    return [_match(entry, max(titles, key=lambda t: similarity(entry["title"], t)), years, f"doi {entry['doi']} (Crossref)")]


def check_arxiv(client, entry: dict, ref: str) -> list[tuple[str, str]]:
    """arXiv export API: an id that answers no paper, or another paper, is broken."""
    response, why = _get(client, f"https://export.arxiv.org/api/query?id_list={ref}")
    if response is None or response.status_code != 200:
        return [("check", f"arXiv {ref}: " + (why or f"API answered {response.status_code}"))]
    try:
        feed = ET.fromstring(response.content)
    except ET.ParseError:
        return [("check", f"arXiv {ref}: API answer unreadable")]
    found = feed.find(f"{ATOM}entry")
    title = " ".join((found.findtext(f"{ATOM}title") or "").split()) if found is not None else ""
    if found is None or not title or title == "Error" or "/api/errors" in (found.findtext(f"{ATOM}id") or ""):
        return [("broken", f"arXiv {ref} does not exist")]
    year = (found.findtext(f"{ATOM}published") or "")[:4]
    return [_match(entry, title, [int(year)] if year.isdigit() else [], f"arXiv {ref}")]


def check_url(client, url: str) -> list[tuple[str, str]]:
    """404/410 = broken; 401/403/429/5xx = check by hand (bot walls, rate limits, outages)."""
    response, why = _get(client, url)
    if response is None:
        return [("check", f"{url}: {why}")]
    code = response.status_code
    if code in (404, 410):
        return [("broken", f"{url} answered {code}")]
    if code >= 400:
        return [("check", f"{url} answered {code} - open it in a browser")]
    return [("ok", f"{url} answered {code}")]


def check_links(registry: Registry, client, pause=time.sleep) -> list[tuple[str, int, str, str]]:
    """Every registry entry's DOI, arXiv id and url, in file order: (ref, line, level, what) with
    level ok | check | broken."""
    results, last_arxiv = [], None
    for ref, entry in registry.entries.items():
        found = []
        if entry.get("doi"):
            found += check_doi(client, entry)
        paper = arxiv_id(entry)
        if paper:
            if last_arxiv is not None:
                pause(ARXIV_PAUSE)
            last_arxiv = paper
            found += check_arxiv(client, entry, paper)
        if entry.get("url") and not ARXIV_URL.match(entry["url"]):  # an arXiv page is checked through its API
            found += check_url(client, entry["url"])
        results += [(ref, registry.lines[ref], level, what) for level, what in found]
    return results


def links(root: Path, path: Path | None = None, client=None) -> int:
    """--links: print one line per problem + a count; exit code 1 when anything is broken."""
    import httpx
    errors, warnings = [], []
    if path is not None and not path.is_file():
        print(f"{path}: no such file")
        return 1
    registry = Registry(root, errors, warnings, path)
    if errors:
        print("\n".join(errors))
        return 1
    if not registry.entries:
        print(f"{registry.rel}: no sources to check")
        return 0
    own = client is None
    client = client or httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT})
    try:
        results = check_links(registry, client)
    finally:
        if own:
            client.close()
    word = {"broken": "BROKEN", "check": "check by hand", "ok": "ok"}
    for ref, line, level, what in results:
        print(f"{registry.rel}:{line}: {ref}: {word[level]}: {what}")
    worst = {}
    for ref, _, level, _ in results:  # an entry counts once, at its worst
        worst[ref] = min(worst.get(ref, "ok"), level, key=list(word).index)
    count = {level: sum(1 for ref in registry.entries if worst.get(ref, "ok") == level) for level in word}
    print(f"{len(registry.entries)} sources: {count['broken']} broken, {count['check']} to check by hand, {count['ok']} fine")
    return 1 if count["broken"] else 0


def main():
    ap = argparse.ArgumentParser(description="Build the site's generated pages in docs/.")
    ap.add_argument("--check", action="store_true", help="list stale, missing or orphaned files; write nothing; exit 1 on any")
    ap.add_argument("--links", nargs="?", const="", metavar="SOURCES_YML",
                    help="check every source's DOI (doi.org + Crossref), arXiv id and url over the network;"
                         " exit 1 on a broken one (default app/web/research/sources.yml)")
    args = ap.parse_args()
    if args.links is not None:  # a path given is read from where you are; none = the repo's sources.yml
        sys.exit(links(ROOT, Path(args.links).resolve() if args.links else None))
    warnings: list[str] = []
    try:
        built = build(ROOT, warnings)
    except SourceError as e:
        print(e)
        sys.exit(1)
    for warning in warnings:
        print(f"warning: {warning}")
    if args.check:
        found = problems(ROOT, built)
        print("\n".join(found) if found else "docs/ up to date")
        sys.exit(1 if found else 0)
    changed = write(ROOT, built)
    print("\n".join(changed) if changed else "docs/ up to date")


if __name__ == "__main__":
    main()
