"""Helpers for the site tests (test_site.py): parse a page, list docs/ files, map URLs to files.

Not collected (no test_ prefix). Reads nothing at import: installed copies have no docs/ worth testing.
"""

import json
import re
import struct
from html import unescape
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


def loaded_urls(head: Head, docs: Path | None = None) -> list[str]:
    """What a browser fetches on load: every src, every <link> but canonical, every CSS url() - in the page's
    <style> and, given docs/, in the stylesheets it links (site.css: the fonts)."""
    urls = [a["src"] for _, a in head.tags if "src" in a]
    urls += [a["href"] for a in head.all("link") if a.get("rel") != "canonical"]
    for css in head.text.get("style", []) + (linked_css(docs, head) if docs else []):
        urls += re.findall(r"""url\(\s*["']?([^"')]+)""", css)
    return urls


def linked_css(docs: Path, head: Head) -> list[str]:
    """Text of each stylesheet the page links (root-relative, from docs/; a missing one reads as empty)."""
    out = []
    for a in head.links("stylesheet"):
        path = docs / target(a["href"])
        out.append(path.read_text(encoding="utf-8") if path.is_file() else "")
    return out


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


def crumbs(html: str) -> set[tuple[str, str]]:
    """(site-relative url, name) for each crumb (links + the current page) and each BreadcrumbList item."""
    nav = re.search(r'<nav class="crumbs".*?</nav>', html, re.S)
    if not nav:
        return set()
    here = urlsplit(re.search(r'<link rel="canonical" href="([^"]*)">', html).group(1)).path
    pairs = {(url, unescape(name)) for url, name in re.findall(r'<a href="([^"]+)">([^<]+)</a>', nav.group(0))}
    pairs |= {(here, unescape(re.sub(r"<[^>]+>", "", name)))
              for name in re.findall(r'aria-current="page">(.*?)</li>', nav.group(0))}
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        for node in json.loads(block).get("@graph", []):
            if node.get("@type") == "BreadcrumbList":
                pairs |= {(urlsplit(i["item"]).path, i["name"]) for i in node["itemListElement"]}
    return pairs


def crumb_clashes(pages: list[set[tuple[str, str]]]) -> dict[str, list[str]]:
    """url -> its names, for each url that crumbs name more than one way across the pages (D22)."""
    names: dict[str, set[str]] = {}
    for pairs in pages:
        for url, name in pairs:
            names.setdefault(url, set()).add(name)
    return {url: sorted(n) for url, n in names.items() if len(n) > 1}


def structured_data(docs: Path, site: str) -> list[str]:
    """JSON-LD problems on the generated pages (research/, about/) + the home page; empty = fine.

    One block per page. Article (+ BreadcrumbList) on articles, BreadcrumbList on the hub + methods,
    ProfilePage (+ BreadcrumbList) on about/. Article dates == the byline's <time> values, author
    @id == the ProfilePage Person's, image == og:image, sitemap <lastmod> == dateModified; every
    breadcrumb points at a canonical that exists. About: lastmod == ProfilePage dateModified, sameAs >= 2
    URLs each shown on the page; hub lastmod >= every article's dateModified. Every article links the
    methods page's "How is AI used?" under the byline and never says "approved". A data page (Dataset +
    BreadcrumbList) holds the same rules with name / creator for headline / author, and its download is a
    file in docs/. Home keeps exactly one WebSite block.
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
    person, authors, modified = None, [], []
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
        types = {node.get("@type") for node in data.get("@graph", [])}
        want = ({"ProfilePage", "BreadcrumbList"} if name == "about/index.html"
                else {"BreadcrumbList"} if name in ("research/index.html", "research/methods/index.html")
                else {"Dataset", "BreadcrumbList"} if "Dataset" in types
                else {"Article", "BreadcrumbList"})
        if data.get("@context") != "https://schema.org" or set(graph) != want or len(graph) != len(data["@graph"]):
            problems.append(f"{name}: JSON-LD types {sorted(graph)}, want {sorted(want)}")
            continue
        items = graph["BreadcrumbList"]["itemListElement"]
        if [i["position"] for i in items] != list(range(1, len(items) + 1)) or items[-1]["item"] != url:
            problems.append(f"{name}: breadcrumb positions or last item wrong")
        problems += [f"{name}: breadcrumb {i['item']} is not a page" for i in items if i["item"] not in canonicals]
        if "ProfilePage" in graph:
            profile = graph["ProfilePage"]
            person = profile["mainEntity"]
            shown = re.sub(r"<[^>]+>", " ", text)
            same = person.get("sameAs") or []
            if len(same) < 2 or [u for u in same if re.sub(r"^https?://|/$", "", u) not in shown]:
                problems.append(f"{name}: sameAs needs >= 2 URLs, each shown on the page ({same})")
            if lastmod.get(url) != profile.get("dateModified"):
                problems.append(f"{name}: sitemap lastmod {lastmod.get(url)} != dateModified {profile.get('dateModified')}")
            if not (person.get("@type") == "Person" and person.get("name") and person.get("url") and person.get("sameAs")):
                problems.append(f"{name}: ProfilePage mainEntity needs Person name, url, sameAs")
        if "Dataset" in graph:
            dataset = graph["Dataset"]
            downloads = [d.get("contentUrl", "") for d in dataset.get("distribution", [])]
            if not downloads or [u for u in downloads if not u.startswith(site) or u[len(site):] not in found]:
                problems.append(f"{name}: Dataset download {downloads} is not a file on this site")
            # same checks as an article's, under the Dataset's own names; never on the hub or in its lastmod
            graph["Article"] = {**dataset, "headline": dataset.get("name"), "author": dataset.get("creator"),
                                "image": head.meta("og:image")}
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
            if "Dataset" not in graph:
                modified.append(article["dateModified"])
            after = byline.group(0) + text[byline.end():byline.end() + 200] if byline else ""
            if "/research/methods/#how-is-ai-used" not in after or "approved" in text.lower():
                problems.append(f"{name}: needs the How we research link under the byline and no 'approved'")
    hub = lastmod.get(site + "research/")
    if modified and (not hub or hub < max(modified)):
        problems.append(f"research/index.html: sitemap lastmod {hub} older than the newest article {max(modified)}")
    for name, ref in authors:
        if person is None or ref != person.get("@id"):
            problems.append(f"{name}: author @id {ref} != the About page's Person")
    return problems


# --- budgets + markup/CSS rules (app/docs/site.md#budgets): each returns problems, empty = fine ---

KB = 1000
HTML_GZIP_MAX = 25 * KB       # 7.5 KB at the redesign start
INLINE_JS_MAX = 5 * KB        # raw bytes of every inline script but JSON-LD (2.9 KB at start)
BODY_ELEMENTS_MAX = 800       # 162 at start
FIRST_LOAD_MAX = 100 * KB     # gzip HTML + every @font-face woff2 + icon.svg (colophon promises "under 100 KB")
CRITICAL_MAX = 5              # HTML + preloads + stylesheets + icon.svg
HEAD_SCRIPT_MAX = 600         # <head> script: html classes before first paint, nothing else
# paint-free or cheap properties only; anything else animates layout or repaints big areas
ANIMATABLE = {"transform", "opacity", "clip-path", "stroke-dashoffset", "background-size"}
TEXT_MIN, NON_TEXT_MIN = 4.5, 3.0  # WCAG 1.4.3 text, 1.4.11 controls + focus ring
# (foreground, background) token pairs; tokens resolved per colour scheme from the shared :root
TEXT_PAIRS = [("--text", "--desk"), ("--text-2", "--desk"), ("--desk", "--text"),  # step numbers
              ("--accent", "--desk"),  # links in running text (the tint)
              ("--ink", "--paper"), ("--ink-2", "--paper"), ("--ink", "--mark"),  # sheets + marks keep ink
              ("--win-ink", "--win"), ("--win-ink-2", "--win")]  # the hero window (dark grey in dark mode)
NON_TEXT_PAIRS = [("--text", "--desk"), ("--ink", "--paper"), ("--ink", "--mark"),  # control borders, frames
                  ("--win-ink", "--win")]
# Increase Contrast (prefers-contrast: more; Apple HIG: a higher-contrast variant of every custom colour): secondary
# text = text, hairlines 3:1 (WCAG 1.4.11), the tint 7:1 (WCAG 1.4.6)
MORE_SAME = [("--text-2", "--text")]
MORE_PAIRS = [(("--line", "--desk"), 3.0), (("--accent", "--desk"), 7.0)]
RING_BACKGROUNDS = ["--desk", "--paper"]  # focus ring on the desk and on a white sheet, both schemes
# APCA (perceptual lightness contrast, WCAG 3 drafts): text pairs >= Lc 75, its floor for body-size text (the
# secondary grey sets 12-17px bylines, footer + Sources); hairlines >= Lc 15, its floor for a line still seen.
# WCAG 2 rated dark mode too kindly: #bdbdbd on #1c1c1e passed at 9.1:1 but read at Lc 65 (light: Lc 96)
APCA_TEXT_MIN, APCA_LINE_MIN = 75, 15
LINE_PAIRS = [("--line", "--desk"), ("--rule", "--paper"), ("--win-rule", "--win")]  # sections, sheets, window


def styles(head: Head) -> str:
    """Every <style> block + style="" attribute of a page, as one CSS text."""
    return "\n".join(head.text.get("style", []) + [a["style"] for _, a in head.tags if a.get("style")])


def inline_scripts(head: Head) -> list[str]:
    """Text of every inline script that runs (JSON-LD left out)."""
    return head.text.get("script", []) + head.text.get("module", []) + head.text.get("text/javascript", [])


def head_scripts(raw: str) -> list[str]:
    """Inline scripts inside <head> (JSON-LD left out): they run before first paint."""
    head = raw.split("</head>", 1)[0]
    return re.findall(r"<script(?![^>]*ld\+json)[^>]*>(.*?)</script>", head, re.S)


def blocks(css: str, at: str) -> list[str]:
    """Bodies of every `@at ... { ... }` block, nested braces kept (e.g. @keyframes frames)."""
    found = []
    for m in re.finditer(rf"@{at}\b[^{{]*\{{", css):
        depth, i = 1, m.end()
        while depth and i < len(css):
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        found.append(css[m.end():i - 1])
    return found


def animated(css: str) -> set[str]:
    """Properties set inside @keyframes + named by transition / transition-property."""
    props = set()
    for body in blocks(css, "keyframes"):
        props |= {p.lower() for p in re.findall(r"([\w-]+)\s*:", re.sub(r"[^{};]*\{", ";", body))}
    for value in re.findall(r"(?<![\w-])transition(?:-property)?\s*:\s*([^;}]+)", css):
        props |= {part.split()[0].lower() for part in value.split(",") if part.split()}
    return {p for p in props if not re.fullmatch(r"\d[\w.]*|none|initial|inherit|unset", p)}


NO_PREFERENCE = r"@media\s*\(\s*prefers-reduced-motion\s*:\s*no-preference\s*\)\s*\{"


def outside_no_preference(css: str) -> str:
    """css w/ every `@media (prefers-reduced-motion: no-preference) { ... }` body cut out."""
    out, last = [], 0
    for m in re.finditer(NO_PREFERENCE, css):
        if m.start() < last:
            continue
        depth, i = 1, m.end()
        while depth and i < len(css):
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        out.append(css[last:m.start()])
        last = i
    return "".join(out) + css[last:]


def budgets(docs: Path, name: str) -> list[str]:
    """Static budgets + markup/CSS rules for one page under docs/ (no network, no browser)."""
    import gzip

    raw = (docs / name).read_text(encoding="utf-8")
    head, problems = Head(raw), []
    sheets = linked_css(docs, head)
    css = "\n".join([*sheets, styles(head)])  # cascade order: the linked sheets, then the page's own
    html_gzip = len(gzip.compress(raw.encode(), 9, mtime=0))
    if html_gzip > HTML_GZIP_MAX:
        problems.append(f"{name}: HTML {html_gzip} B gzip > {HTML_GZIP_MAX}")
    scripts = inline_scripts(head)
    js = sum(len(s.encode()) for s in scripts)
    if js > INLINE_JS_MAX:
        problems.append(f"{name}: inline JS {js} B > {INLINE_JS_MAX}")
    tags = [t for t, _ in head.tags]
    body = len(tags) - tags.index("body") - 1 if "body" in tags else 0
    if body > BODY_ELEMENTS_MAX:
        problems.append(f"{name}: {body} elements in <body> > {BODY_ELEMENTS_MAX}")
    fonts = sorted({u for face in re.findall(r"@font-face\s*\{([^}]*)\}", css)
                    for u in re.findall(r"""url\(\s*["']?([^"')]+\.woff2)""", face)})
    icon = "/icon.svg" in loaded_urls(head)
    weight = html_gzip + sum(len(gzip.compress(t.encode(), 9, mtime=0)) for t in sheets)
    weight += sum((docs / target(u)).stat().st_size for u in fonts if (docs / target(u)).is_file())
    weight += (docs / "icon.svg").stat().st_size if icon and (docs / "icon.svg").is_file() else 0
    if weight > FIRST_LOAD_MAX:
        problems.append(f"{name}: first load {weight} B (gzip HTML + CSS + fonts + icon) > {FIRST_LOAD_MAX}")
    critical = 1 + len(head.links("preload")) + len(head.links("stylesheet")) + icon
    if critical > CRITICAL_MAX:
        problems.append(f"{name}: {critical} critical requests > {CRITICAL_MAX}")
    problems += [f"{name}: <script src={a['src']}> (inline only)" for a in head.all("script") if "src" in a]
    if re.search(r"will-change", css, re.I):
        problems.append(f"{name}: will-change (layers every frame; motion stays on cheap properties)")
    if re.search(r"@view-transition\b|view-transition-name", outside_no_preference(css)):
        problems.append(f"{name}: view transition outside @media (prefers-reduced-motion: no-preference)")
    problems += [f"{name}: animates {p} (allowed: {sorted(ANIMATABLE)})" for p in sorted(animated(css) - ANIMATABLE)]
    ids = head.ids()
    for t, a in head.tags:
        if t != "use":
            continue
        ref = a.get("href") or a.get("xlink:href") or ""
        if not ref.startswith("#") or ref[1:] not in ids:
            problems.append(f"{name}: <use href={ref!r}> has no target on the page")
    for tag, inner in re.findall(r"<(header|footer)\b(.*?)</\1>", raw, re.S):
        bad = sorted(set(re.findall(r"<(title|style)\b", inner)) | ({"id"} if re.search(r"\sid\s*=", inner) else set()))
        if bad:
            problems.append(f"{name}: <{tag}> holds {bad} (copied to every page: one id twice, a second title)")
    for code in head_scripts(raw):
        if len(code.encode()) > HEAD_SCRIPT_MAX:
            problems.append(f"{name}: <head> script {len(code.encode())} B > {HEAD_SCRIPT_MAX} (blocks first paint)")
        if "LINES" in code:
            problems.append(f"{name}: <head> script names LINES (install line + Copy live in the body script)")
    for inner in re.findall(r"<figure\b(.*?)</figure>", raw, re.S):
        # a bar or case figure cites its sources (caption, a case row's cells): links there are the citation, not a
        # control (A15)
        held = inner
        if inner.startswith((' class="bars"', ' class="case"')):
            held = re.sub(r"<small>\(.*?\)</small>", "", re.sub(r"<figcaption\b.*?</figcaption>", "", inner, flags=re.S), flags=re.S)
        bad = sorted(set(re.findall(r"<(a|button|input|select|textarea)\b", held)))
        if bad:
            problems.append(f"{name}: <figure> holds {bad} (illustrations show controls, never hold one)")
        if "<figcaption" in inner and not (inner.split(">", 1)[1].lstrip().startswith("<figcaption")
                                           or inner.rstrip().endswith("</figcaption>")):
            problems.append(f"{name}: <figcaption> not the first or last child of its <figure> (W3C error)")
        if re.search(r"<h[1-6]\b", inner):
            problems.append(f"{name}: heading inside <figure> (an illustration's text joins the page outline)")
    if re.search(r"vector-effect", css):
        problems.append(f"{name}: vector-effect in CSS (unknown to the W3C CSS checker; an SVG attribute instead)")
    if re.search(r"body\.is-", css):
        problems.append(f"{name}: body.is-* selector (head script sets html.is-* before first paint)")
    if sum("LINES" in s for s in scripts) > 1:
        problems.append(f"{name}: more than one script names LINES (tests read the install line from the one that does)")
    return problems


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def apca(text: str, background: str) -> float:
    """APCA Lc (APCA-W3 0.0.98G-4g), either polarity, as a positive number."""
    def y(hex_colour: str) -> float:
        h = hex_colour.lstrip("#")
        h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        v = 0.2126729 * r ** 2.4 + 0.7151522 * g ** 2.4 + 0.0721750 * b ** 2.4
        return v + (0.022 - v) ** 1.414 if v < 0.022 else v  # soft clamp near black
    t, b = y(text), y(background)
    if b > t:  # dark text on a light background
        s = (b ** 0.56 - t ** 0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (b ** 0.65 - t ** 0.62) * 1.14
    return 0.0 if s > -0.1 else (-s - 0.027) * 100


def shared(raw: str) -> str:
    """The shared CSS: a page's inline /* shared */ ... /* /shared */ block (test fixtures), else the text itself
    (app/web/css/site.css, the real site's source)."""
    m = re.search(r"/\* shared \*/.*?/\* /shared \*/", raw, re.S)
    return m.group(0) if m else raw


def props(body: str) -> dict[str, str]:
    return {k: " ".join(v.split()) for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body)}


def root_in(css: str, query: str) -> dict[str, str]:
    """The :root custom properties inside @media <query> { :root { ... } } (query exactly as written)."""
    m = re.search(r"@media\s*" + re.escape(query).replace(r"\ ", r"\s*") + r"\s*\{\s*:root\s*\{([^}]*)\}", css)
    return props(m.group(1)) if m else {}


DARK, MORE, MORE_DARK = ("(prefers-color-scheme: dark)", "(prefers-contrast: more)",
                         "(prefers-contrast: more) and (prefers-color-scheme: dark)")


def tokens(css: str) -> dict[str, dict[str, str]]:
    """Custom properties of the shared :root, light + dark (dark = light w/ the dark-scheme overrides); the
    (min-width: 768px) overrides are wide_tokens()', the Increase Contrast ones more_tokens()'."""
    inside = [m.span() for m in re.finditer(r"@media[^{]*\{\s*:root\s*\{[^}]*\}", css)]
    light = {}
    for m in re.finditer(r":root\s*\{([^}]*)\}", css):
        if not any(a <= m.start() < b for a, b in inside):
            light.update(props(m.group(1)))
    return {"light": light, "dark": {**light, **root_in(css, DARK)}}


def more_tokens(css: str) -> dict[str, dict[str, str]]:
    """The Increase Contrast overrides (prefers-contrast: more), per scheme: light = the more block, dark = the
    more block + the more-and-dark one."""
    more = root_in(css, MORE)
    return {"light more": more, "dark more": {**more, **root_in(css, MORE_DARK)}}


def schemes(css: str) -> dict[str, dict[str, str]]:
    """Every scheme a visitor can get, resolved: light, dark and both with Increase Contrast."""
    base, more = tokens(css), more_tokens(css)
    return {**base, "light more": {**base["light"], **more["light more"]},
            "dark more": {**base["dark"], **more["dark more"]}}


def wide_tokens(css: str) -> dict[str, str]:
    """The shared :root's (min-width: 768px) overrides: spacing that grows with the display type (plan-dxn.37)."""
    m = re.search(r"@media\s*\(min-width:\s*768px\)\s*\{\s*:root\s*\{([^}]*)\}", css)
    return {k: " ".join(v.split()) for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1))} if m else {}


def colour(value: str, scheme: dict[str, str]) -> list[str]:
    """Hex colours a CSS value paints, var() resolved (depth-capped against loops)."""
    for _ in range(10):
        value, n = re.subn(r"var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)", lambda m: scheme.get(m.group(1), ""), value)
        if not n:
            break
    return re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", value)


SHEETS = {".window": "--win", ".proof": "--paper"}  # home's app window + resume sheet: their own ground


def contrasts(raw: str) -> list[str]:
    """Token pairs under the minimum, light + dark + both w/ Increase Contrast (its own floors too), incl. the focus
    ring on desk + white sheet, the ink selection and each sheet's selection against its own ground (3:1); text +
    hairlines in APCA too; empty = fine."""
    css = shared(raw)
    problems = []
    rings = [d for sel, d in re.findall(r"([^{}]*:focus-visible[^{}]*)\{([^}]*)\}", css)]
    if not rings:
        problems.append("shared CSS: no :focus-visible rule")
    selections_by = [(re.sub(r"/\*.*?\*/", "", sel, flags=re.S), d)
                     for sel, d in re.findall(r"([^{}]*::selection[^{}]*)\{([^}]*)\}", css)]
    selections = [d for sel, d in selections_by]
    if not any(sel.strip() == "::selection" for sel, d in selections_by):
        problems.append("shared CSS: no ::selection rule")
    if not more_tokens(css)["light more"]:
        problems.append("shared CSS: no @media (prefers-contrast: more) :root block (Increase Contrast)")
    for mode, scheme in schemes(css).items():
        if mode.endswith(" more"):
            for a, b in MORE_SAME:
                ca, cb = colour(scheme.get(a, ""), scheme), colour(scheme.get(b, ""), scheme)
                if not ca or ca[:1] != cb[:1]:
                    problems.append(f"{mode}: {a} is not {b} ({ca[:1] or 'unset'} vs {cb[:1] or 'unset'})")
            for (fg, bg), least in MORE_PAIRS:
                ratio = contrast(colour(scheme[fg], scheme)[0], colour(scheme[bg], scheme)[0])
                if ratio < least:
                    problems.append(f"{mode}: {fg} on {bg} {ratio:.2f}:1 < {least}:1")
        for pairs, least in (TEXT_PAIRS, TEXT_MIN), (NON_TEXT_PAIRS, NON_TEXT_MIN):
            for fg, bg in pairs:
                if fg not in scheme or bg not in scheme:
                    problems.append(f"{mode}: token {fg if fg not in scheme else bg} missing")
                    continue
                ratio = contrast(colour(scheme[fg], scheme)[0], colour(scheme[bg], scheme)[0])
                if ratio < least:
                    problems.append(f"{mode}: {fg} on {bg} {ratio:.2f}:1 < {least}:1")
        for pairs, least, kind in (TEXT_PAIRS, APCA_TEXT_MIN, "text"), (LINE_PAIRS, APCA_LINE_MIN, "hairline"):
            for fg, bg in pairs:
                if fg not in scheme or bg not in scheme:
                    problems.append(f"{mode}: token {fg if fg not in scheme else bg} missing")
                    continue
                lc = apca(colour(scheme[fg], scheme)[0], colour(scheme[bg], scheme)[0])
                if lc < least:
                    problems.append(f"{mode}: {kind} {fg} on {bg} APCA Lc {lc:.1f} < {least}")
        ring = [c for d in rings for k, v in re.findall(r"(outline(?:-color)?|box-shadow)\s*:\s*([^;]+)", d)
                for c in colour(v, scheme)]
        for bg in RING_BACKGROUNDS:
            best = max((contrast(c, colour(scheme[bg], scheme)[0]) for c in ring), default=0)
            if best < NON_TEXT_MIN:
                problems.append(f"{mode}: focus ring on {bg} {best:.2f}:1 < {NON_TEXT_MIN}:1")
        # selection in ink, never the highlighter: yellow means "marked by the app"
        for d in selections:
            fg = colour(" ".join(re.findall(r"(?<![-\w])color\s*:\s*([^;]+)", d)), scheme)
            bg = colour(" ".join(re.findall(r"background(?:-color)?\s*:\s*([^;]+)", d)), scheme)
            if colour(scheme.get("--mark", ""), scheme)[0].lower() in {c.lower() for c in fg + bg}:
                problems.append(f"{mode}: ::selection paints the highlighter")
            elif fg and bg and contrast(fg[0], bg[0]) < TEXT_MIN:
                problems.append(f"{mode}: ::selection {contrast(fg[0], bg[0]):.2f}:1 < {TEXT_MIN}:1")
        # the app window + resume sheet keep their own ground in dark mode (the desk's selection vanished on a
        # white sheet): their selection must show on it (their own ::selection rule, else the page-wide one)
        for sheet, ground in SHEETS.items():
            paper = colour(scheme.get(ground, ""), scheme)
            rules = [d for sel, d in selections_by if sheet in sel] or \
                    [d for sel, d in selections_by if sel.strip() == "::selection"]
            bg = [c for d in rules for c in colour(" ".join(re.findall(r"background(?:-color)?\s*:\s*([^;]+)", d)), scheme)]
            ratio = contrast(bg[-1], paper[0]) if bg and paper else 0
            if ratio < NON_TEXT_MIN:
                problems.append(f"{mode}: selection on the sheet {sheet} {ratio:.2f}:1 against {ground} "
                                f"< {NON_TEXT_MIN}:1")
    return problems


def stroke_on_paper(raw: str, selector: str, site_css: str = "") -> dict[str, float]:
    """Contrast of the stroke a page's own CSS rule for selector paints against --paper, per scheme (light, dark),
    tokens from site_css (the page's inline shared block when not given); 0 = no such rule or no colour."""
    css = re.sub(r"/\*.*?\*/", "", raw.split("/* /shared */", 1)[-1], flags=re.S)
    rule = next((d for sel, d in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
                 if selector in [x.strip() for x in sel.split(",")]), "")
    stroke = " ".join(re.findall(r"(?<![-\w])stroke\s*:\s*([^;]+)", rule))
    out = {}
    for mode, scheme in tokens(shared(site_css or raw)).items():
        fg, paper = colour(stroke, scheme), colour(scheme.get("--paper", ""), scheme)
        out[mode] = contrast(fg[0], paper[0]) if fg and paper else 0.0
    return out


def token_table(markdown: str) -> dict[str, dict[str, str]]:
    """The site.md tokens table (| `--x` | `light` | `dark` or same | use |) in tokens()' shape."""
    light, dark = {}, {}
    for name, lv, dv in re.findall(r"^\| `(--[\w-]+)` \| `([^`]+)` \| (same|`[^`]+`) \|", markdown, re.M):
        light[name] = lv
        dark[name] = lv if dv == "same" else dv.strip("`")
    return {"light": light, "dark": dark}


def more_table(markdown: str) -> dict[str, dict[str, str]]:
    """site.md's Increase Contrast rows (| more | `--x` | `light` | `dark` or same | use |) in more_tokens()' shape."""
    light, dark = {}, {}
    for name, lv, dv in re.findall(r"^\| more \| `(--[\w-]+)` \| `([^`]+)` \| (same|`[^`]+`) \|", markdown, re.M):
        light[name] = lv
        dark[name] = lv if dv == "same" else dv.strip("`")
    return {"light more": light, "dark more": dark}


def wide_table(markdown: str) -> dict[str, str]:
    """site.md's 768px-up rows (| 768px+ | `--x` | `value` | use |) in wide_tokens()' shape."""
    return dict(re.findall(r"^\| 768px\+ \| `(--[\w-]+)` \| `([^`]+)` \|", markdown, re.M))


class Prose(HTMLParser):
    """Visible text a reader sees as prose: outside code/pre/script/style, attributes and the
    illustrations (.window = the app, .proof = the resume sheet) that mirror what the app prints."""

    SKIP_TAGS = {"code", "pre", "script", "style", "kbd", "samp"}
    SKIP_CLASSES = {"window", "proof"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.stack, self.chunks = [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        classes = set((dict(attrs).get("class") or "").split())
        self.stack.append(tag in self.SKIP_TAGS or bool(classes & self.SKIP_CLASSES))

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not any(self.stack):
            self.chunks.append(data)


def typewriter(raw: str) -> tuple[int, list[str]]:
    """(chars of prose scanned, each straight quote or ' - ' dash found w/ its context)."""
    text = " ".join(" ".join(Prose(raw).chunks).split())
    found = [text[max(0, m.start() - 30):m.end() + 30] for m in re.finditer(r"['\"]| - ", text)]
    return len(text), found


# C4: raw-HTML readers (AI crawlers) skip CSS: text in two adjacent inline elements, or a sentence and the
# inline element after it, reads as one word ("Install on WindowsMac") unless whitespace sits between
INLINE = r"(?:span|b|strong|em|mark|a|code|del|ins|time)"
RUN_TOGETHER = re.compile(rf"[A-Za-z0-9]</{INLINE}>(?:<[^>]+>)*<{INLINE}\b[^>]*>[A-Za-z0-9]"
                          rf"|[A-Za-z0-9][.!?]<{INLINE}\b[^>]*>[A-Za-z0-9]")


def run_together(raw: str) -> list[str]:
    """Each place two words would touch in the page's raw text (style + script removed)."""
    text = re.sub(r"<(style|script)\b.*?</\1>", "", raw, flags=re.S)
    return [text[max(0, m.start() - 30):m.end() + 30] for m in RUN_TOGETHER.finditer(text)]


SOLID_MARK = re.compile(r"background(?:-color)?\s*:\s*(?:var\(--mark\)|#ffe433)\s*[;}]", re.I)


def yellow_fills(css: str) -> list[str]:
    """Selectors whose rule fills a solid highlighter background (marks use a sized gradient instead)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [sel.strip() for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css) if SOLID_MARK.search(body + ";")]


class Claimed(HTMLParser):
    """Text inside each element carrying data-claim="<id>" (nested tags included), whitespace collapsed."""

    VOID = Prose.VOID

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.stack, self.text = [], {}
        self.feed(text)
        self.text = {k: [" ".join(t.split()) for t in v] for k, v in self.text.items()}

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        claim = dict(attrs).get("data-claim")
        if claim:
            self.text.setdefault(claim, []).append("")
        self.stack.append(claim)

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        for claim in {c for c in self.stack if c}:
            self.text[claim][-1] += data


def say_labels(root: Path) -> dict[str, str]:
    data = json.loads((root / "app/vscode/say.json").read_text(encoding="utf-8"))
    return {t["id"]: t["label"] for t in data["templates"]}


def apply_systems(root: Path) -> tuple[set[str], set[str]]:
    """(filled from the resume, start box only) as the code has them: one module per system
    (NAME), start-box ones define start_box(); Workday = ELSEWHERE (Chrome extension)."""
    full, start = set(), set()
    folder = root / "app/apply/systems"
    for module in sorted(folder.glob("*.py")):
        source = module.read_text(encoding="utf-8")
        name = re.search(r'^NAME = "(.+)"', source, re.M)
        if name:
            (start if "def start_box(" in source else full).add(name.group(1))
    if re.search(r'"myworkdayjobs\.com": "Workday', (folder / "__init__.py").read_text(encoding="utf-8")):
        full.add("Workday")
    return full, start


def fact_problems(root: Path, fact: dict, text: str) -> list[str]:
    """What no longer holds of one `rests_on` fact (app/web/claims.yml)."""
    if "contains" in fact:
        path = root / fact["file"]
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        return [] if fact["contains"] in body else [f"{fact['file']} no longer says {fact['contains']!r}"]
    if "rows" in fact:
        path = root / fact["file"]
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        now = [line.rstrip() for line in lines if re.search(fact["rows"], line)]
        if now == fact["are"]:
            return []
        added = [r for r in now if r not in fact["are"]]
        gone = [r for r in fact["are"] if r not in now]
        return [f"{fact['file']} lines matching {fact['rows']!r} changed - new or changed: {added}; gone or changed: {gone}"]
    if "say" in fact:
        label = say_labels(root).get(fact["say"])
        if label != fact["label"]:
            return [f"app/vscode/say.json button {fact['say']!r} now reads {label!r}, not {fact['label']!r}"]
        return [] if fact["label"] in text else [f"button label {fact['label']!r} not in the page text"]
    if "apply_systems" in fact:
        full, start = apply_systems(root)
        out = []
        for kind, now, said in (("filled", full, fact["filled"]), ("start box", start, fact["start_box"])):
            said = [(n, n) if isinstance(n, str) else tuple(n) for n in said]
            if now != {n for n, _ in said}:
                out.append(f"app/apply/systems {kind}: code has {sorted(now)}, claim has {sorted(n for n, _ in said)}")
            out += [f"{kind} system {shown!r} not in the page text" for _, shown in said if shown not in text]
        return out
    return [f"unknown fact {fact!r}"]


def claim_problems(root: Path) -> list[str]:
    """Every site sentence about the app (data-claim="<id>", app/web/claims.yml) against the
    app fact it rests on: '<page>: claim <id>: <what> -> <what to update>'."""
    import yaml
    claims = yaml.safe_load((root / "app/web/claims.yml").read_text(encoding="utf-8"))
    docs, out, fix = root / "docs", [], " -> update the page sentence to match the app, then its text + rests_on in app/web/claims.yml"
    on_pages = {}
    for path in sorted(docs.rglob("*.html")):
        rel = path.relative_to(docs).as_posix()
        for claim, texts in Claimed(path.read_text(encoding="utf-8")).text.items():
            on_pages.setdefault(claim, []).extend((rel, t) for t in texts)
    for claim in sorted(set(on_pages) - set(claims)):
        out.append(f"{on_pages[claim][0][0]}: claim {claim}: on the page, not in app/web/claims.yml{fix}")
    for claim, entry in claims.items():
        page, recorded = entry["page"], " ".join(entry["text"].split())
        found = [t for rel, t in on_pages.get(claim, []) if rel == page]
        if len(found) != 1:
            out.append(f"{page}: claim {claim}: {len(found)} elements carry data-claim=\"{claim}\" (want 1){fix}")
            continue
        if found[0] != recorded:
            out.append(f"{page}: claim {claim}: page text changed - page {found[0]!r}, claims.yml {recorded!r}{fix}")
        if not entry.get("rests_on"):
            out.append(f"{page}: claim {claim}: names no app fact (rests_on){fix}")
        for fact in entry.get("rests_on") or []:
            out += [f"{page}: claim {claim}: {p}{fix}" for p in fact_problems(root, fact, found[0])]
    return out
