"""jobs.enrriquez.com (docs/, GitHub Pages): search + share metadata, icons, no third-party files.

Pages serves docs/ as is - no build step to catch a wrong canonical, a missing icon or a font from
another site, and a share card fails silently (preview just shows no picture). These tests read the
files on disk: no network, stdlib + pymupdf. Assets come from app/web/assets.py + app/web/og.html.
"""

import json
import re
import struct
from html.parser import HTMLParser

import pymupdf

import cfg

DOCS = cfg.ROOT / "docs"
SITE = "https://" + (DOCS / "CNAME").read_text().strip() + "/"
PAGES = ("index.html", "privacy.html", "404.html")
INDEXED = {"index.html": SITE, "privacy.html": SITE + "privacy.html"}


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


def page(name: str) -> Head:
    return Head((DOCS / name).read_text(encoding="utf-8"))


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


def test_each_page_carries_the_same_icons_and_font_preloads():
    # one set of icon links everywhere: browsers pick per page, a missing one => blank tab icon
    for name in PAGES:
        head = page(name)
        assert [(a["href"], a.get("sizes")) for a in head.links("icon")] == [("/favicon.ico", "32x32"), ("/icon.svg", None)], name
        assert [a["href"] for a in head.links("apple-touch-icon")] == ["/apple-touch-icon.png"], name
        assert [a["href"] for a in head.links("manifest")] == ["/manifest.webmanifest"], name
        # font preload w/o crossorigin => browser fetches the font twice; unmatched URL => wasted fetch
        faces = re.findall(r"""url\("([^"]+\.woff2)"\)""", "".join(head.text["style"]))
        preloads = head.all("link", rel="preload", **{"as": "font"})
        assert preloads, name
        for a in preloads:
            assert "crossorigin" in a and a["href"] in faces, (name, a)


def test_indexed_pages_share_one_url_and_fit_search_and_share_limits():
    for name, url in INDEXED.items():
        head = page(name)
        # canonical + og:url differ => search and share cards count two pages
        assert [a["href"] for a in head.links("canonical")] == [url], name
        assert head.meta("og:url") == url, name
        # Google cuts titles ~60 chars, descriptions ~160
        assert len(head.text["title"][0]) <= 60, name
        assert len(head.meta("description")) <= 160, name
        # og:site_name already shows the brand on the card; a suffix repeats it
        assert not re.search(r" [-|] CEZ Job Finder$", head.meta("og:title")), name
        assert head.meta("twitter:card") == "summary_large_image", name
        # image size stated == real size, else some apps crop or skip the picture on first share
        image = DOCS / head.meta("og:image").removeprefix(SITE)
        assert head.meta("og:image").startswith(SITE) and image.is_file(), name
        size = (int(head.meta("og:image:width")), int(head.meta("og:image:height")))
        assert png_size(image) == size == (1200, 630), name
        assert image.stat().st_size < 300_000, name  # WhatsApp skips share images over ~300 KB


def test_404_page_stays_out_of_search_and_loads_from_the_root():
    head = page("404.html")
    assert head.links("canonical") == []
    assert "noindex" in head.meta("robots")
    # Pages serves 404.html at any missing path (/a/b/c) => relative URLs break there
    assert all(u.startswith("/") for u in loaded_urls(head)), loaded_urls(head)


def test_no_page_loads_a_file_from_another_site():
    # privacy page promises "no files from other sites": every fetch stays on this site
    for name in PAGES:
        for url in loaded_urls(page(name)):
            if url.startswith(("data:", "#")):
                continue
            assert not re.match(r"[a-z]+:|//", url), (name, url)
            assert (DOCS / url.lstrip("/")).is_file(), (name, url)


def test_shared_css_is_the_same_on_every_page():
    # fonts, colours and marks copied into each page by hand => one edited, the others drift
    blocks = {name: re.search(r"/\* shared \*/.*?/\* /shared \*/", (DOCS / name).read_text(encoding="utf-8"), re.S).group(0)
              for name in PAGES}
    assert len(set(blocks.values())) == 1, sorted(blocks)


def ico_frames(path) -> list[tuple[int, int]]:
    data = path.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1), path  # ICONDIR: 1 = icon
    frames = []
    for i in range(count):
        w, h, _, _, _, _, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        payload = data[offset:offset + size]
        assert payload[:8] == b"\x89PNG\r\n\x1a\n", (path, i)  # PNG frames: smaller, every browser reads them
        assert struct.unpack(">II", payload[16:24]) == (w or 256, h or 256), (path, i)
        frames.append((w or 256, h or 256))
    return frames


def opaque(path) -> bool:
    pix = pymupdf.Pixmap(str(path))
    return not pix.alpha or set(pix.samples[pix.n - 1::pix.n]) == {255}


def test_icons_have_their_stated_sizes_and_home_screen_ones_are_opaque():
    for name, side in ("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512), ("icon-maskable-512.png", 512):
        assert png_size(DOCS / name) == (side, side), name
    # iOS fills see-through corners black; maskable icons get cropped to any shape => no holes
    for name in "apple-touch-icon.png", "icon-maskable-512.png":
        assert opaque(DOCS / name), name
    assert ico_frames(DOCS / "favicon.ico") == [(16, 16), (32, 32), (48, 48)]
    manifest = json.loads((DOCS / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "browser"  # a web page, not an app: no install prompt
    for icon in manifest["icons"]:
        w, h = map(int, icon["sizes"].split("x"))
        assert png_size(DOCS / icon["src"].lstrip("/")) == (w, h), icon


def test_sitemap_and_robots_point_search_at_the_indexed_pages_only():
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    assert re.findall(r"<loc>(.+?)</loc>", sitemap) == list(INDEXED.values())
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8").splitlines()
    assert f"Sitemap: {SITE}sitemap.xml" in robots
    # /mac/ + /win/ are install scripts served as HTML => keep them out of search results
    assert sorted(l.split(":", 1)[1].strip() for l in robots if l.startswith("Disallow:")) == ["/mac/", "/win/"]


def test_home_page_describes_the_site_not_an_app_or_faq():
    # SoftwareApplication wants ratings + price, FAQPage rich results are limited to gov/health
    # sites since 2023 => both only draw warnings; WebSite gives the site name in results
    head = page("index.html")
    blocks = [json.loads(b) for b in head.text["application/ld+json"]]
    assert len(blocks) == 1
    assert blocks[0]["@type"] == "WebSite"
    assert blocks[0]["url"] == SITE and blocks[0]["name"] == head.meta("og:site_name")
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "SoftwareApplication" not in raw and "FAQPage" not in raw


def test_install_line_shows_without_javascript_and_matches_the_script():
    # no JS (reader mode, blocked script) => the static line is what gets pasted; must equal JS's
    head = page("index.html")
    script = next(s for s in head.text["script"] if "LINES" in s)
    win = re.search(r"win: `(.+?)`,", script).group(1).replace("${SITE}", SITE)
    assert head.text["line"] == [win]
    # pasting a line that runs a script => offer to read that script first
    reads = [a for t, a in head.tags if t == "a" and a.get("href", "").startswith("https://github.com/cezkid/jobs/blob/main/app/install/")]
    assert any(a.get("id") == "script" for a in reads)
    assert "Read the script first" in (DOCS / "index.html").read_text(encoding="utf-8")


def test_web_font_ships_with_its_licence():
    # OFL lets the font be served only w/ its licence alongside
    assert (DOCS / "fonts" / "OFL.txt").read_bytes() == (cfg.APP / "resume" / "fonts" / "Caladea" / "OFL.txt").read_bytes()
