"""Build the site's generated pages in docs/: research articles + About from Markdown, sitemap.xml.

Sources: app/web/research/<slug>.md - a YAML header between --- lines (KEYS only), then Markdown.
<slug>.md -> /research/<slug>/, methods.md -> /research/methods/, about.md -> /about/, index.md =
hub intro. status: draft => not built. Shared CSS, header, footer, icon + font links and og:image
are copied from docs/index.html, so every page stays the same as the home page.

Hand-written pages (index.html, privacy.html, 404.html) stay as they are; this script reads them
for the sitemap. Everything it writes is generated and committed - never hand-edit those files;
change this script or its sources and rerun. A test (test_site.py) fails when a committed file is
stale, missing, or left over in docs/research/ or docs/about/ (orphan) - rerun to fix.

Output is deterministic: no clock, sorted order, UTF-8, LF. Dates read from sources, spelled with
MONTHS (strftime %B follows the computer's language, %-d breaks on Windows).

Run from repo root: uv run app/web/pages.py [--check]
Writes by default; --check lists problems, writes nothing, exits 1 on any.
Project env (no inline deps): markdown-it-py comes locked through rich.
"""

import argparse
import datetime
import re
import shutil
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit

import yaml
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
# folders this script owns: files in them it didn't build are orphans and get deleted
OWNED = ("research", "about")
# docs/mac/ + docs/win/ hold install scripts named index.html, not pages
NOT_PAGES = ("mac", "win")
SOURCES = Path("app") / "web" / "research"
AUTHOR = "Cesar Enrriquez-Zuniga"
REPO = "https://github.com/cezkid/jobs/blob/main/"
KEYS = {"title", "description", "published", "modified", "status", "og_title", "uncited"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# special sources (about, methods, index) + names later steps use (feed, reviews/, sources.yml)
RESERVED = {"about", "methods", "index", "feed", "reviews", "sources"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def long_date(iso: str) -> str:
    """2026-10-02 -> 2 October 2026."""
    year, month, day = (int(x) for x in iso.split("-"))
    return f"{day} {MONTHS[month - 1]} {year}"


class Head(HTMLParser):
    """A page's canonical URL and whether it asks to stay out of search."""

    def __init__(self, text: str):
        super().__init__()
        self.canonical, self.noindex = None, False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical" and self.canonical is None:
            self.canonical = attrs.get("href")
        if tag == "meta" and attrs.get("name") == "robots" and "noindex" in (attrs.get("content") or ""):
            self.noindex = True


def site(root: Path) -> str:
    return "https://" + (root / "docs" / "CNAME").read_text(encoding="utf-8").strip() + "/"


def listed(docs: Path) -> list[str]:
    """Every file under docs/ as Pages serves it: exact-case relative paths, dotfiles (.DS_Store) left out."""
    return sorted(p.relative_to(docs).as_posix() for p in docs.rglob("*")
                  if p.is_file() and not any(part.startswith(".") for part in p.relative_to(docs).parts))


def sitemap(root: Path, pages: dict[str, str]) -> str:
    """Canonical URL of every indexed page, home first then sorted; once each."""
    home = site(root)
    urls = set()
    for text in pages.values():
        head = Head(text)
        if head.canonical and not head.noindex:
            urls.add(head.canonical)
    lines = [f"  <url><loc>{url}</loc></url>" for url in sorted(urls, key=lambda u: (u != home, u))]
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
                self.ids[slug] = self.line(token)
                token.attrSet("id", slug)

    @staticmethod
    def line_of(text: str, key: str) -> int:
        match = re.search(rf"^{re.escape(key)}\s*:", text, re.M)
        return text[:match.start()].count("\n") + 1 if match else 2

    def line(self, token) -> int:
        return self.offset + (token.map[0] + 1 if token.map else 1)

    @property
    def built(self) -> bool:
        return self.status == "published" and self.name != "index"

    @property
    def out(self) -> str:
        """docs-relative output file."""
        return "about/index.html" if self.name == "about" else f"research/{self.name}/index.html"

    @property
    def url(self) -> str:
        return "/" + self.out.removesuffix("index.html")


MD = MarkdownIt("js-default")  # raw HTML escaped, tables on, no typographer


def _table_open(self, tokens, idx, options, env):
    # wide table scrolls inside its own box, not the page; focusable so keyboards can scroll it
    label = escape(tokens[idx].meta.get("label", "Table"))
    return f'<div class="table" role="region" aria-label="{label}" tabindex="0">\n' + self.renderToken(tokens, idx, options, env)


def _table_close(self, tokens, idx, options, env):
    return self.renderToken(tokens, idx, options, env) + "</div>\n"


MD.add_render_rule("table_open", _table_open)
MD.add_render_rule("table_close", _table_close)


def rewrite(href: str, src: Source, by_name: dict[str, Source], root: Path, site_files: set[str]) -> str:
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
    if not target.exists():
        raise ValueError(f"{href}: no such file in the repo")
    return REPO + quote(rel) + (f"#{url.fragment}" if url.fragment else "")


def body_html(src: Source, by_name: dict[str, Source], root: Path, site_files: set[str], errors: list[str]) -> str:
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
                        child.attrSet("href", rewrite(child.attrGet("href"), src, by_name, root, site_files))
                    except ValueError as e:
                        errors.append(f"{src.rel}:{src.line(token)}: {e}")
    return MD.renderer.render(src.tokens, MD.options, {})


def home_parts(root: Path) -> dict[str, str]:
    """What every generated page copies from docs/index.html: shared CSS, header, footer, head links, og:image."""
    text = (root / "docs" / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'^<link rel="(?:icon|apple-touch-icon|manifest|preload)".*$', text, re.M)
    return {
        "css": re.search(r"  /\* shared \*/.*?/\* /shared \*/", text, re.S).group(0),
        "header": re.search(r"<header\b.*?</header>", text, re.S).group(0),
        "footer": re.search(r"<footer\b.*?</footer>", text, re.S).group(0),
        "links": "\n".join(links),
        "og": "\n".join(re.findall(r'^<meta property="og:image.*$', text, re.M)),
        "twitter": "\n".join(re.findall(r'^<meta name="twitter:.*$', text, re.M)),
    }


PAGE_CSS = """
  main { padding: 24px 0 72px; }
  .page { max-width: 68ch; }
  .crumbs ol { list-style: none; margin: 0 0 16px; padding: 0; display: flex; flex-wrap: wrap; font-size: 17px; color: var(--text-2); }
  .crumbs li { margin: 0; }
  .crumbs li + li::before { content: "/"; padding: 0 0.5em; }
  h1 { font-size: clamp(30px, 5vw, 52px); line-height: 1.1; font-weight: 700; margin: 0 0 12px; text-wrap: balance; }
  h2 { font-size: 24px; line-height: 1.25; margin: 36px 0 12px; }
  h3 { font-size: 20px; line-height: 1.3; margin: 28px 0 10px; }
  .meta { margin: 0 0 24px; color: var(--text-2); font-size: 17px; }
  p { margin: 0 0 14px; }
  ul, ol { margin: 0 0 14px; padding-left: 1.3em; }
  li { margin: 0 0 8px; }
  blockquote { margin: 0 0 14px; padding-left: 16px; border-left: 3px solid var(--line); color: var(--text-2); }
  code { font-family: var(--mono); font-size: 0.85em; }
  pre { overflow-x: auto; padding: 12px 16px; border: 1px solid var(--line); }
  .table { overflow-x: auto; margin: 0 0 14px; }
  table { border-collapse: collapse; font-size: 17px; }
  th, td { text-align: left; vertical-align: top; padding: 6px 12px 6px 0; border-bottom: 1px solid var(--line); }
  @media (max-width: 600px) {
    main { padding-top: 8px; }
  }
"""


def page(src: Source, root: Path, body: str, parts: dict[str, str]) -> str:
    home = site(root)
    url = home + src.url.lstrip("/")
    article = src.name != "about"
    crumbs = ['<li><a href="/">Home</a></li>']
    if article:
        # Research links to the hub once it exists (plan-xsy.8)
        crumbs.append("<li>Research</li>")
    crumbs.append(f'<li aria-current="page">{escape(src.title)}</li>')
    dates = [f'Published <time datetime="{src.published}">{long_date(src.published)}</time>']
    if src.modified != src.published:
        dates.append(f'Updated <time datetime="{src.modified}">{long_date(src.modified)}</time>')
    if article:
        meta = " · ".join([f'By <a href="/about/">{AUTHOR}</a>', *dates])
    else:
        meta = f'Updated <time datetime="{src.modified}">{long_date(src.modified)}</time>'
    head = [
        f"<title>{escape(src.title)}</title>",
        f'<meta name="description" content="{escape(src.description)}">',
        f'<link rel="canonical" href="{url}">',
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<meta name="color-scheme" content="light dark">',
        '<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#1c1c1e" media="(prefers-color-scheme: dark)">',
        f'<meta property="og:type" content="{"article" if article else "profile"}">',
        '<meta property="og:site_name" content="CEZ Job Finder">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:title" content="{escape(src.og_title)}">',
        f'<meta property="og:description" content="{escape(src.description)}">',
    ]
    if article:
        head += [f'<meta property="article:published_time" content="{src.published}">',
                 f'<meta property="article:modified_time" content="{src.modified}">']
    head += [parts["og"], parts["twitter"], parts["links"]]
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
        '<main class="wrap">',
        f'<{"article" if article else "div"} class="page">',
        f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(crumbs)}</ol></nav>',
        f"<h1>{escape(src.title)}</h1>",
        f'<p class="meta">{meta}</p>',
        body.rstrip("\n"),
        f'</{"article" if article else "div"}>',
        "</main>",
        parts["footer"],
        "</body>",
        "</html>",
        "",
    ])


def research(root: Path, site_files: set[str]) -> dict[str, str]:
    """Every published research source as docs-relative path -> HTML. Raises SourceError on any problem."""
    folder = root / SOURCES
    errors: list[str] = []
    sources = [Source(p, root, errors) for p in sorted(folder.glob("*.md"))] if folder.is_dir() else []
    if errors:  # header problems first: a page can't be drawn w/o its title + dates
        raise SourceError("\n".join(errors))
    by_name = {s.name: s for s in sources}
    built = [s for s in sources if s.built]
    out: dict[str, str] = {}
    if built:
        parts = home_parts(root)
        if any(s.name != "about" for s in built) and not (by_name.get("about") and by_name["about"].built):
            errors.append(f"{SOURCES.as_posix()}/about.md:1: bylines link /about/ - publish about.md with the first page")
        files = site_files | {s.out for s in built}
        for src in built:
            out[src.out] = page(src, root, body_html(src, by_name, root, files, errors), parts)
    if errors:
        raise SourceError("\n".join(errors))
    return out


def build(root: Path) -> dict[str, str]:
    """Every generated file: docs-relative path -> text. Reads, never writes."""
    docs = root / "docs"
    hand = {rel: (docs / rel).read_text(encoding="utf-8") for rel in listed(docs)
            if rel.endswith(".html") and rel.split("/")[0] not in NOT_PAGES + OWNED}
    out = research(root, set(listed(docs)) - {rel for rel in listed(docs) if rel.split("/")[0] in OWNED})
    out["sitemap.xml"] = sitemap(root, {**hand, **{k: v for k, v in out.items() if k.endswith(".html")}})
    return dict(sorted(out.items()))


def orphans(root: Path, built: dict[str, str]) -> list[str]:
    docs = root / "docs"
    return [rel for rel in listed(docs) if rel.split("/")[0] in OWNED and rel not in built]


def same(path: Path, text: str) -> bool:
    # CRLF checkout (git autocrlf on Windows) is the same file, not a stale one
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") == text


def problems(root: Path) -> list[str]:
    """What --check reports: stale, missing, orphaned. Empty = docs/ matches the sources."""
    docs, built, found = root / "docs", build(root), []
    for rel, text in built.items():
        path = docs / rel
        if not path.is_file():
            found.append(f"missing: docs/{rel}")
        elif not same(path, text):
            found.append(f"stale: docs/{rel}")
    found += [f"orphaned: docs/{rel}" for rel in orphans(root, built)]
    return found


def write(root: Path) -> list[str]:
    """Write stale + missing files (UTF-8, LF), delete orphans in the owned folders. Returns what changed."""
    docs, built, changed = root / "docs", build(root), []
    for rel, text in built.items():
        path = docs / rel
        if path.is_file() and same(path, text):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        changed.append(f"wrote: docs/{rel}")
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
    return changed


def main():
    ap = argparse.ArgumentParser(description="Build the site's generated pages in docs/.")
    ap.add_argument("--check", action="store_true", help="list stale, missing or orphaned files; write nothing; exit 1 on any")
    args = ap.parse_args()
    try:
        build(ROOT)
    except SourceError as e:
        print(e)
        sys.exit(1)
    if args.check:
        found = problems(ROOT)
        print("\n".join(found) if found else "docs/ up to date")
        sys.exit(1 if found else 0)
    changed = write(ROOT)
    print("\n".join(changed) if changed else "docs/ up to date")


if __name__ == "__main__":
    main()
