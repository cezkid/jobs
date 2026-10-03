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
              ("--ink", "--paper"), ("--ink-2", "--paper"), ("--ink", "--mark")]  # sheets + marks keep ink
NON_TEXT_PAIRS = [("--text", "--desk"), ("--ink", "--paper"), ("--ink", "--mark")]  # control borders, frames
RING_BACKGROUNDS = ["--desk", "--paper"]  # focus ring on the desk and on a white sheet, both schemes


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


def budgets(docs: Path, name: str) -> list[str]:
    """Static budgets + markup/CSS rules for one page under docs/ (no network, no browser)."""
    import gzip

    raw = (docs / name).read_text(encoding="utf-8")
    head, problems = Head(raw), []
    css = styles(head)
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
    weight = html_gzip + sum((docs / target(u)).stat().st_size for u in fonts if (docs / target(u)).is_file())
    weight += (docs / "icon.svg").stat().st_size if icon and (docs / "icon.svg").is_file() else 0
    if weight > FIRST_LOAD_MAX:
        problems.append(f"{name}: first load {weight} B (gzip HTML + fonts + icon) > {FIRST_LOAD_MAX}")
    critical = 1 + len(head.links("preload")) + len(head.links("stylesheet")) + icon
    if critical > CRITICAL_MAX:
        problems.append(f"{name}: {critical} critical requests > {CRITICAL_MAX}")
    problems += [f"{name}: <script src={a['src']}> (inline only)" for a in head.all("script") if "src" in a]
    if re.search(r"will-change", css, re.I):
        problems.append(f"{name}: will-change (layers every frame; motion stays on cheap properties)")
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
        bad = sorted(set(re.findall(r"<(a|button|input|select|textarea)\b", inner)))
        if bad:
            problems.append(f"{name}: <figure> holds {bad} (illustrations show controls, never hold one)")
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


def shared(raw: str) -> str:
    m = re.search(r"/\* shared \*/.*?/\* /shared \*/", raw, re.S)
    return m.group(0) if m else ""


def tokens(css: str) -> dict[str, dict[str, str]]:
    """Custom properties of the shared :root, light + dark (dark = light w/ the dark-scheme overrides)."""
    def props(body: str) -> dict[str, str]:
        return {k: " ".join(v.split()) for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body)}
    dark_m = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{([^}]*)\}", css)
    light = {}
    for m in re.finditer(r":root\s*\{([^}]*)\}", css):
        if not dark_m or not (dark_m.start() <= m.start() < dark_m.end()):
            light.update(props(m.group(1)))
    return {"light": light, "dark": {**light, **(props(dark_m.group(1)) if dark_m else {})}}


def colour(value: str, scheme: dict[str, str]) -> list[str]:
    """Hex colours a CSS value paints, var() resolved (depth-capped against loops)."""
    for _ in range(10):
        value, n = re.subn(r"var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)", lambda m: scheme.get(m.group(1), ""), value)
        if not n:
            break
    return re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", value)


def contrasts(raw: str) -> list[str]:
    """Token pairs under the minimum, light + dark, incl. the focus ring on desk + white sheet and the ink selection; empty = fine."""
    css = shared(raw)
    problems = []
    rings = [d for sel, d in re.findall(r"([^{}]*:focus-visible[^{}]*)\{([^}]*)\}", css)]
    if not rings:
        problems.append("shared CSS: no :focus-visible rule")
    selections = [d for sel, d in re.findall(r"([^{}]*::selection[^{}]*)\{([^}]*)\}", css)]
    if not selections:
        problems.append("shared CSS: no ::selection rule")
    for mode, scheme in tokens(css).items():
        for pairs, least in (TEXT_PAIRS, TEXT_MIN), (NON_TEXT_PAIRS, NON_TEXT_MIN):
            for fg, bg in pairs:
                if fg not in scheme or bg not in scheme:
                    problems.append(f"{mode}: token {fg if fg not in scheme else bg} missing")
                    continue
                ratio = contrast(colour(scheme[fg], scheme)[0], colour(scheme[bg], scheme)[0])
                if ratio < least:
                    problems.append(f"{mode}: {fg} on {bg} {ratio:.2f}:1 < {least}:1")
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
    return problems


def token_table(markdown: str) -> dict[str, dict[str, str]]:
    """The site.md tokens table (| `--x` | `light` | `dark` or same | use |) in tokens()' shape."""
    light, dark = {}, {}
    for name, lv, dv in re.findall(r"^\| `(--[\w-]+)` \| `([^`]+)` \| (same|`[^`]+`) \|", markdown, re.M):
        light[name] = lv
        dark[name] = lv if dv == "same" else dv.strip("`")
    return {"light": light, "dark": dark}
