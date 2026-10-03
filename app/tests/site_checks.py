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

    def duplicate_ids(self) -> list[str]:
        """Ids on more than one element: a #link to one lands on the first."""
        found = [a["id"] for _, a in self.tags if a.get("id")]
        return sorted({i for i in found if found.count(i) > 1})


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


def structured_data(docs: Path, site: str) -> list[str]:
    """JSON-LD problems on the generated pages (research/, about/) + the home page; empty = fine.

    One block per page. Article (+ BreadcrumbList) on articles, BreadcrumbList on the hub + methods,
    ProfilePage (+ BreadcrumbList) on about/. Article dates == the byline's <time> values, author
    @id == the ProfilePage Person's, image == og:image, sitemap <lastmod> == dateModified; every
    breadcrumb points at a canonical that exists. Home keeps exactly one WebSite block.
    """
    import json

    found = files(docs)
    pages = {n: (docs / n).read_text(encoding="utf-8") for n in sorted(found)
             if n.endswith(".html") and n.split("/")[0] in ("research", "about")}
    canonicals = {own_url(n, site) for n in found if n.endswith(".html")
                  and Head((docs / n).read_text(encoding="utf-8")).links("canonical")}
    sitemap = (docs / "sitemap.xml").read_text(encoding="utf-8") if "sitemap.xml" in found else ""
    lastmod = dict(re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", sitemap))
    problems = []
    home = Head((docs / "index.html").read_text(encoding="utf-8")).text.get("application/ld+json", [])
    if [json.loads(b).get("@type") for b in home] != ["WebSite"]:
        problems.append("index.html: needs exactly one WebSite block")
    person, authors = None, []
    for name, text in pages.items():
        head, url = Head(text), own_url(name, site)
        blocks = head.text.get("application/ld+json", [])
        if len(blocks) != 1:
            problems.append(f"{name}: {len(blocks)} JSON-LD blocks, want 1")
            continue
        if "<" in blocks[0]:
            problems.append(f"{name}: unescaped < in JSON-LD")
        data = json.loads(blocks[0])
        graph = {node["@type"]: node for node in data.get("@graph", [])}
        want = ({"ProfilePage", "BreadcrumbList"} if name == "about/index.html"
                else {"BreadcrumbList"} if name in ("research/index.html", "research/methods/index.html")
                else {"Article", "BreadcrumbList"})
        if data.get("@context") != "https://schema.org" or set(graph) != want or len(graph) != len(data["@graph"]):
            problems.append(f"{name}: JSON-LD types {sorted(graph)}, want {sorted(want)}")
            continue
        items = graph["BreadcrumbList"]["itemListElement"]
        if [i["position"] for i in items] != list(range(1, len(items) + 1)) or items[-1]["item"] != url:
            problems.append(f"{name}: breadcrumb positions or last item wrong")
        problems += [f"{name}: breadcrumb {i['item']} is not a page" for i in items if i["item"] not in canonicals]
        if "ProfilePage" in graph:
            person = graph["ProfilePage"]["mainEntity"]
            if not (person.get("@type") == "Person" and person.get("name") and person.get("url") and person.get("sameAs")):
                problems.append(f"{name}: ProfilePage mainEntity needs Person name, url, sameAs")
        if "Article" in graph:
            article = graph["Article"]
            missing = {"headline", "datePublished", "dateModified", "author", "image"} - set(article)
            if missing:
                problems.append(f"{name}: Article lacks {sorted(missing)}")
                continue
            byline = re.search(r'<p class="meta">(.*?)</p>', text, re.S)
            times = set(re.findall(r'<time datetime="([^"]+)">', byline.group(1) if byline else ""))
            if not article["datePublished"] <= article["dateModified"] or times != {article["datePublished"], article["dateModified"]}:
                problems.append(f"{name}: Article dates {article['datePublished']}/{article['dateModified']} != byline {sorted(times)}")
            if article["image"] != head.meta("og:image"):
                problems.append(f"{name}: Article image != og:image")
            if article["headline"] != head.text["title"][0]:
                problems.append(f"{name}: headline != title")
            if lastmod.get(url) != article["dateModified"]:
                problems.append(f"{name}: sitemap lastmod {lastmod.get(url)} != dateModified {article['dateModified']}")
            authors.append((name, article["author"].get("@id")))
    for name, ref in authors:
        if person is None or ref != person.get("@id"):
            problems.append(f"{name}: author @id {ref} != the About page's Person")
    return problems
