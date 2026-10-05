"""jobs.enrriquez.com (docs/, GitHub Pages): search + share metadata, icons, no third-party files.

Pages serves docs/ as is - no build step to catch a wrong canonical, a missing icon or a font from
another site, and a share card fails silently (preview just shows no picture). These tests read the
files on disk: no network, stdlib + pymupdf. Assets come from app/web/assets.py + app/web/og.html.
"""

import datetime
import hashlib
import importlib.util
import json
import random
import re
import struct
import subprocess
from urllib.parse import urlsplit

import pytest

import cfg

# installed copies have no .git, and may keep a stale docs/ from an older download => nothing to test
if not (cfg.ROOT / ".git").exists():
    pytest.skip("installed copy: the site is tested in the developer checkout", allow_module_level=True)

import pymupdf  # noqa: E402

from site_checks import (HEAD_SCRIPT_MAX, NO_PREFERENCE, Head, budgets, contrasts, crumb_clashes, crumbs, files, head_scripts,  # noqa: E402
                         loaded_urls, outside_no_preference, own_url, png_size, shared, structured_data, target, token_table, tokens,
                         run_together, wide_table, wide_tokens, stroke_on_paper, typewriter, yellow_fills, claim_problems)

DOCS = cfg.ROOT / "docs"
SITE = "https://" + (DOCS / "CNAME").read_text().strip() + "/"
FILES = files(DOCS)
# docs/mac/ + docs/win/ hold install scripts named index.html, not pages
PAGES = sorted(f for f in FILES if f.endswith(".html") and f.split("/")[0] not in ("mac", "win"))


def page(name: str) -> Head:
    return Head((DOCS / name).read_text(encoding="utf-8"))


INDEXED = {name: own_url(name, SITE) for name in PAGES if page(name).links("canonical")}


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
        # Google cuts titles ~60 chars, descriptions ~155-160: 155 (pages.LIMITS) keeps every one whole
        assert len(head.text["title"][0]) <= 60, name
        assert len(head.meta("description")) <= 155, name
        # og:site_name already shows the brand on the card; a suffix repeats it
        assert not re.search(r" [-|] CEZ Job Finder$", head.meta("og:title")), name
        assert head.meta("twitter:card") == "summary_large_image", name
        # image size stated == real size, else some apps crop or skip the picture on first share
        # read as a URL: ?v=N (bumped so LinkedIn refetches a changed card) isn't part of the file name
        assert head.meta("og:image").startswith(SITE), name
        image = target(urlsplit(head.meta("og:image")).path)
        assert image in FILES, (name, image)
        image = DOCS / image
        size = (int(head.meta("og:image:width")), int(head.meta("og:image:height")))
        assert png_size(image) == size == (1200, 630), name
        assert image.stat().st_size < 300_000, name  # WhatsApp skips share images over ~300 KB


def test_share_cards_fit_every_app_and_each_has_its_source():
    # og.png (home) + og-research.png (research pages, before any is published); assets.py renders
    # each from app/web/<name>.html
    cards = sorted(n for n in FILES if re.fullmatch(r"og(-[a-z]+)?\.png", n))
    assert cards == ["og-research.png", "og.png"]
    for name in cards:
        assert png_size(DOCS / name) == (1200, 630), name
        assert (DOCS / name).stat().st_size < 300_000, name  # WhatsApp skips share images over ~300 KB
        assert (cfg.ROOT / "app" / "web" / name.replace(".png", ".html")).is_file(), name


def test_each_indexed_page_is_its_own_canonical_and_the_rest_stay_out_of_search():
    # canonical pointing elsewhere => search drops this page for that one
    assert INDEXED["index.html"] == SITE and "404.html" not in INDEXED
    for name, url in INDEXED.items():
        assert [a["href"] for a in page(name).links("canonical")] == [url], name
    # no canonical + indexable => /x and /x/index.html both answer 200 and compete
    for name in set(PAGES) - set(INDEXED):
        assert "noindex" in (page(name).meta("robots") or ""), name


def test_no_page_loads_a_file_from_another_site_or_a_missing_one():
    # privacy page promises "no files from other sites": every fetch stays on this site.
    # Root-relative only: 404.html is served at any missing path (/a/b/c) => relative URLs break there.
    # Exact case: macOS disks match /Fonts/x for fonts/x, Pages answers 404
    for name in PAGES:
        for url in loaded_urls(page(name)):
            if url.startswith("data:"):
                continue
            assert url.startswith("/") and not url.startswith("//"), (name, url)
            assert target(url) in FILES, (name, url)


def test_every_link_lands_on_a_file_and_a_heading_that_exist():
    ids = {name: page(name).ids() for name in PAGES}
    for name in PAGES:
        for a in page(name).all("a"):
            href = a.get("href")
            if href is None:
                continue
            url = urlsplit(href)
            if href.startswith("#"):
                assert url.fragment in ids[name], (name, href)
            elif href.startswith("/") and not href.startswith("//"):
                file = target(url.path)
                assert file in FILES, (name, href)
                # /research => Pages redirects to /research/ (an extra hop, and a second URL for one page)
                assert url.path.endswith("/") or target(url.path + "/") not in FILES, (name, href, "folder link w/o /")
                if url.fragment:
                    assert file in ids and url.fragment in ids[file], (name, href)
            else:
                # relative links break on 404.html (served at any depth); http: drops to an insecure hop
                assert url.scheme in ("https", "mailto"), (name, href)


def test_guides_link_only_to_site_pages_that_exist():
    # in-app Guides point at their web versions: a slug rename would leave the user a 404
    linked = 0
    for guide in sorted((cfg.ROOT / "Guides").glob("*.md")):
        for url in re.findall(re.escape(SITE) + r"[^\s)>\]]*", guide.read_text(encoding="utf-8")):
            path = urlsplit(url).path
            assert target(path) in FILES, (guide.name, url)
            assert path.endswith("/") or target(path + "/") not in FILES, (guide.name, url, "folder link w/o /")
            linked += 1
    assert linked >= 2


def test_ids_are_unique_on_every_page():
    # two elements w/ one id (a heading "Src x" next to the Sources entry src-x) => #links land on the first
    for name in PAGES:
        assert page(name).duplicate_ids() == [], name


def test_titles_and_descriptions_are_unique():
    # two pages w/ one title => search shows both the same, or picks one and folds the other
    for key in "title", "description":
        seen = [(page(n).text["title"][0] if key == "title" else page(n).meta(key)) for n in PAGES]
        seen = [s for s in seen if s]
        assert len(seen) == len(set(seen)), key


# the only dot / underscore paths on purpose: security.txt must live in .well-known, and
# _config.yml's include list is what stops Jekyll dropping that folder
JEKYLL_DOT_OK = {"docs/_config.yml", "docs/.well-known/security.txt"}


def test_nothing_in_docs_trips_jekyll():
    # Pages runs Jekyll on docs/: .md becomes HTML, front matter (---) gets templated, and
    # _x / .x / #x / x~ files are dropped from the site
    tracked = subprocess.run(["git", "-C", str(cfg.ROOT), "ls-files", "docs"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    assert tracked
    assert {p for p in tracked if any(seg.startswith(("_", ".")) for seg in p.split("/")[1:])} == JEKYLL_DOT_OK
    for path in tracked:
        assert not path.endswith(".md"), path
        if path in JEKYLL_DOT_OK:
            continue
        assert not any(seg.startswith(("_", ".", "#")) or seg.endswith("~") for seg in path.split("/")[1:]), path
        assert not (cfg.ROOT / path).read_bytes().startswith(b"---"), path


def test_shared_css_is_the_same_on_every_page():
    # fonts, colours and marks copied into each page by hand => one edited, the others drift
    blocks = {name: re.search(r"/\* shared \*/.*?/\* /shared \*/", (DOCS / name).read_text(encoding="utf-8"), re.S).group(0)
              for name in PAGES}
    assert len(set(blocks.values())) == 1, sorted(blocks)


def test_header_and_footer_are_the_same_on_every_page():
    # hand-copied per page => a link added to one page goes missing on the others
    # (phone fit of the header is checked in a real browser: uv run app/web/qa.py)
    for tag in "header", "footer":
        found = {name: re.findall(rf"<{tag}\b.*?</{tag}>", (DOCS / name).read_text(encoding="utf-8"), re.S) for name in PAGES}
        assert all(len(f) == 1 for f in found.values()), (tag, found)
        assert len({f[0] for f in found.values()}) == 1, (tag, sorted(found))


def test_footer_links_home_research_install_about_and_the_author():
    # the bottom of a 20-screen article is a dead end w/o them; Made by keeps the author's site (owner, plan-dxn)
    for name in PAGES:
        footer = Head(re.search(r"<footer\b.*?</footer>", (DOCS / name).read_text(encoding="utf-8"), re.S).group(0))
        hrefs = {a.get("href") for a in footer.all("a")}
        assert {"/", "/research/", "/#install", "/about/", "https://www.enrriquez.com"} <= hrefs, (name, hrefs)


def test_404_offers_install_and_research():
    # a missing research link lands here too: the way out names both halves of the site (A18), not only install
    raw = (DOCS / "404.html").read_text(encoding="utf-8")
    main = Head(re.search(r"<main\b.*?</main>", raw, re.S).group(0))
    assert {"/", "/research/"} <= {a.get("href") for a in main.all("a")}


def test_404_cut_line_shows_on_the_paper_in_both_schemes():
    # the dashed cut crosses the white sheet; --text turns near-white in dark mode and the line vanishes (A17)
    raw = (DOCS / "404.html").read_text(encoding="utf-8")
    assert all(r >= 3 for r in stroke_on_paper(raw, ".cut .dash").values()), stroke_on_paper(raw, ".cut .dash")
    faint = raw.replace(".cut .dash { fill: none; stroke: var(--ink)", ".cut .dash { fill: none; stroke: var(--text)", 1)
    assert faint != raw and stroke_on_paper(faint, ".cut .dash")["dark"] < 3


def test_about_is_one_click_from_home():
    # Google: a byline should lead to more about the author; a page deep in the link graph reads as minor
    graph = {name: {target(a["href"]) for a in page(name).all("a")
                    if a.get("href", "").startswith("/") and not a["href"].startswith("//")} for name in INDEXED}
    depth, todo = {"index.html": 0}, ["index.html"]
    while todo:
        name = todo.pop(0)
        for nxt in graph.get(name, ()):
            if nxt in INDEXED and nxt not in depth:
                depth[nxt] = depth[name] + 1
                todo.append(nxt)
    assert depth.get("about/index.html") == 1, depth
    assert all(depth.get(name, 99) <= 2 for name in INDEXED), {n: depth.get(n) for n in INDEXED}


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


ART = ("icon*.svg", "mark*.svg")  # as assets.ART


def stale_icons(root) -> list[str]:
    """Faults vs app/web/icon-sync.json (written by assets.py): an art file (Desktop icon*.svg, bare
    bird mark*.svg) changed or added / removed since the site's icons were made, or a made file
    changed since (hand edit)."""
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sync = json.loads((root / "app/web/icon-sync.json").read_text(encoding="utf-8"))
    now = {f"app/install/{p.name}": sha(p) for pattern in ART for p in sorted((root / "app/install").glob(pattern))}
    faults = [f"{f}: app icon changed - rerun uv run app/web/assets.py --only icons + og" for f in sorted(now.keys() | sync["source"].keys()) if now.get(f) != sync["source"].get(f)]
    faults += [f"{f}: differs from what assets.py made" for f, h in sync["made"].items() if not (root / f).exists() or sha(root / f) != h]
    return faults


# the app's desktop icon changed but the website still shows the old one (owner: "the website should
# always sync with how the vscode is"); also a hand-edited favicon assets.py would overwrite
def test_site_icons_follow_the_app_icon():
    assert stale_icons(cfg.ROOT) == []
    made = json.loads((cfg.ROOT / "app/web/icon-sync.json").read_text(encoding="utf-8"))["made"]
    assert sorted(made) == sorted(f"docs/{n}" for n in ("icon.svg", "icon-192.png", "icon-512.png", "apple-touch-icon.png",
                                                         "icon-maskable-512.png", "favicon.ico", "og.png", "og-research.png"))


# a guard that can't fail guards nothing: one byte of the app icon or the bare bird changed => the test above fails
def test_stale_icon_check_trips_on_a_changed_app_icon(tmp_path):
    for f in ["app/web/icon-sync.json", *json.loads((cfg.ROOT / "app/web/icon-sync.json").read_text())["made"]]:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_bytes((cfg.ROOT / f).read_bytes())
    (tmp_path / "app/install").mkdir(parents=True, exist_ok=True)
    for pattern in ART:
        for src in (cfg.ROOT / "app/install").glob(pattern):
            (tmp_path / "app/install" / src.name).write_bytes(src.read_bytes())
    assert stale_icons(tmp_path) == []
    for name in "icon.svg", "mark.svg", "mark-32.svg":
        svg = tmp_path / "app/install" / name
        was = svg.read_bytes()
        svg.write_bytes(was.replace(b"#ffe433", b"#ffe434", 1))
        assert stale_icons(tmp_path) == [f"app/install/{name}: app icon changed - rerun uv run app/web/assets.py --only icons + og"]
        svg.write_bytes(was)


def assets():
    spec = importlib.util.spec_from_file_location("site_assets", cfg.ROOT / "app/web/assets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def birds(name: str) -> list[str]:
    return re.findall(r'<svg class="bird".*?</svg>', (DOCS / name).read_text(encoding="utf-8"), re.S)


def test_every_page_draws_the_bird_inline_as_the_mark_file_has_it():
    # the bird redrawn but a page keeps the old one, or a page's header bird differs from the home page's
    bird = assets().inline_bird()
    assert birds("index.html") == [bird, bird]  # header + hero title bar
    for name in PAGES:
        assert birds(name)[:1] == [bird], name
        header = re.search(r"<header\b.*?</header>", (DOCS / name).read_text(encoding="utf-8"), re.S).group(0)
        assert header.count('<svg class="bird"') == 1, name


def test_no_page_shows_the_mark_as_an_img():
    # an <img> bird switching by its own colour scheme prints pale on white paper from a dark-mode machine;
    # icon.svg stays the tab's file only
    for name in PAGES:
        raw = (DOCS / name).read_text(encoding="utf-8")
        assert not re.search(r"<img\b[^>]*\bsrc=\"/(?:icon|favicon|apple-touch-icon)[^\"]*\"", raw), name
        assert "<img" not in re.search(r"<header\b.*?</header>", raw, re.S).group(0), name


def test_inline_bird_follows_the_text_colour_and_keeps_a_yellow_beak():
    # hard-coded black => no bird on the dark page; currentColor also gives black in print + CanvasText in forced colours
    css = shared((DOCS / "index.html").read_text(encoding="utf-8"))
    assert re.search(r"\.bird \{[^}]*fill: currentColor", css)
    assert re.search(r"\.bird :is\(\.beak, \.eye\) \{ fill: var\(--mark\); \}", css)
    # pale bird: a yellow eye is lost on it => a hole to the page, on screen only (print is ink on white)
    assert "@media screen and (prefers-color-scheme: dark) { .brand .eye { fill: var(--desk); } }" in css
    assert "fill=" not in assets().inline_bird()


def test_tab_icon_is_the_bare_bird_in_both_schemes():
    # black bird on a dark tab strip = no tab icon; a tile here = the site no longer shows the bare mark
    svg = (DOCS / "icon.svg").read_text(encoding="utf-8")
    assert "<rect" not in svg and "<desc" not in svg
    assert svg.count('class="ink" fill="#000000"') >= 1 and 'class="beak" fill="#ffe433"' in svg
    dark = re.search(r"@media \(prefers-color-scheme:dark\)\{(.*)\}</style>", svg).group(1)
    assert ".ink{fill:#f2f2f2}" in dark and ".eye{fill:#1c1c1e}" in dark and "beak" not in dark
    # the dark tones are the page's own dark --text + --desk
    root = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "--desk: #1c1c1e; --text: #f2f2f2;" in root


def test_small_tab_frames_keep_a_full_yellow_beak():
    # a bird scaled into the 16 px tile instead of drawn on whole pixels: beak blurs to beige, the frame reads as a grey blob
    data = (DOCS / "favicon.ico").read_bytes()
    for i, side in enumerate((16, 32)):
        size, offset = struct.unpack("<II", data[14 + 16 * i:22 + 16 * i])
        pix = pymupdf.Pixmap(data[offset:offset + size])
        assert pix.width == side
        dots = {pix.pixel(x, y)[:3] for x in range(side) for y in range(side)}
        assert any(r >= 250 and g >= 223 and b <= 60 for r, g, b in dots), side  # #ffe433


@pytest.mark.parametrize("was, now", [
    ('d="M22 6', 'transform="scale(2)" d="M22 6'),  # the inline bird + dark cut assume the 32 grid as drawn
    ('class="beak" fill="#ffe433"', 'class="beak" fill="#FFE433"'),
    ('class="ink" fill="#000000"', 'class="ink" fill="#111111"'),  # page draws currentColor: tab + share card would differ
    ("<circle", '<circle id="eye"'),  # header is copied to every page: ids would repeat
    ("</svg>", '<line class="ink" fill="#000000" x1="0" y1="0" x2="1" y2="1"/>\n</svg>'),
])
def test_mark_file_off_its_contract_stops_the_icon_step(tmp_path, was, now):
    # final art is delivered to the contract in desktop-icon.md: what it says fails must fail, not draw wrong
    module = assets()
    module.mark_shapes()
    svg = module.MARK_SMALL.read_text(encoding="utf-8")
    assert was in svg
    module.MARK_SMALL = tmp_path / "mark-32.svg"
    module.MARK_SMALL.write_text(svg.replace(was, now, 1), encoding="utf-8")
    with pytest.raises(SystemExit, match="contract"):
        module.mark_shapes()


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
    locs = re.findall(r"<loc>(.+?)</loc>", sitemap)
    assert len(locs) == len(set(locs)) and set(locs) == set(INDEXED.values())
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8").splitlines()
    assert f"Sitemap: {SITE}sitemap.xml" in robots
    # /mac/ + /win/ are install scripts served as HTML => keep them out of search results
    assert sorted(l.split(":", 1)[1].strip() for l in robots if l.startswith("Disallow:")) == ["/mac/", "/win/"]


def test_robots_says_why_training_bots_are_allowed():
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8").splitlines()
    assert any(l.startswith("# Training bots:") for l in robots)
    groups = [l for l in robots if l.lower().startswith("user-agent:")]
    assert [g.split(":", 1)[1].strip() for g in groups] == ["*"]  # no per-bot group blocks a search bot or Google-Extended


def test_security_txt_is_current():
    path = DOCS / ".well-known" / "security.txt"
    fields = dict(l.split(": ", 1) for l in path.read_text(encoding="utf-8").splitlines() if ": " in l)
    assert fields["Contact"].startswith("https://"), path
    assert fields["Canonical"] == f"{SITE}.well-known/security.txt", path
    expires = datetime.datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
    left = expires - datetime.datetime.now(datetime.timezone.utc)
    assert left > datetime.timedelta(days=30), f"{path} expires {fields['Expires']}: renew it (Expires <= 1 year out)"
    assert ".well-known" in (DOCS / "_config.yml").read_text(encoding="utf-8")


def test_readme_links_research_and_has_no_stale_tracking_line():
    readme = (cfg.ROOT / "README.md").read_text(encoding="utf-8")
    assert "no application tracking" not in " ".join(readme.split()).lower()
    assert "https://jobs.enrriquez.com/research/" in readme and "https://jobs.enrriquez.com/privacy.html" in readme


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


def test_home_h1_is_the_literal_answer_to_is_this_a_website():
    # owner's fix for "is this a website?": the h1 says what it is, in plain words, unchanged
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", (DOCS / "index.html").read_text(encoding="utf-8"), re.S)
    assert h1 == ["A free job-search app for your Windows or Mac computer."]


def test_every_page_has_one_h1():
    # two h1s => search + screen readers can't tell which is the page's subject; none => no subject
    for name in PAGES:
        raw = (DOCS / name).read_text(encoding="utf-8")
        assert len(re.findall(r"<h1[\s>]", raw)) == 1, name


def test_home_says_what_it_is_and_what_it_costs_in_search_results():
    # "free" alone in a snippet, then a paid AI plan, reads as bait (D5); the title stays (C1 cut)
    head = page("index.html")
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    assert head.text["title"] == ["CEZ Job Finder – free AI job search app for Windows and Mac"]
    description = head.meta("description")
    assert len(description) <= 155 and all(w in description for w in ("resume", "your own", "plan"))
    # one sentence with the name as its subject, for search + AI answers (D3); the name sits in a
    # translate="no" span, so read the text
    assert "CEZ Job Finder is" in re.sub(r"<[^>]+>", "", raw)
    # the ledger's "switch it off" leads to how, as privacy.html does (D11a)
    assert 'href="/research/keep-chats-out-of-ai-training/"' in raw
    # job-tailor allows a second page 60%+ full (app/skills/job-tailor.md)
    assert "One page, set to fit" not in raw


HAND_WRITTEN = ("index.html", "privacy.html", "404.html")


def test_hand_written_pages_use_typographic_quotes_and_dashes():
    # a straight ' at 90-112px reads as typewriter text (A12); the app window + resume sheet keep
    # ' - ' because they mirror what the app prints (app/today.py)
    scanned, found = 0, []
    for name in HAND_WRITTEN:
        chars, hits = typewriter((DOCS / name).read_text(encoding="utf-8"))
        scanned += chars
        found += [f"{name}: {hit!r}" for hit in hits]
    assert scanned >= 2000, f"only {scanned} chars of prose scanned - the parser lost the pages"
    assert not found, found
    assert "See your first jobs today." in (DOCS / "index.html").read_text(encoding="utf-8")


def test_sample_corrections_add_no_number_the_old_line_lacks():
    # "Nothing made up" beside a correction that adds a number would show the app inventing one
    # (AGENTS.md Hold); the hero shows no correction since P-b2, the resume sheet does
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    pairs = re.findall(r"<del>(.*?)</del>.*?<ins>(.*?)</ins>", raw, re.S)
    assert pairs, "no <del>/<ins> correction found on home - the parser lost the sheet"
    for old, new in pairs:
        old, new = re.sub(r"<[^>]+>", "", old), re.sub(r"<[^>]+>", "", new)
        assert set(re.findall(r"\d+", new)) <= set(re.findall(r"\d+", old)), (old, new)


def test_home_ledger_names_the_same_recipients_as_privacy_in_order():
    # the home ledger is the short form of privacy.html's table (privacy.html says "in full"): a
    # recipient on one and not the other = a promise only half-made. Names are worded per page, so
    # each row is matched by the one word that identifies it.
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    ledger = re.search(r'<ol class="ledger">(.*?)</ol>', home, re.S)
    assert ledger, "no ledger on home - the parser lost it"
    on_home = re.findall(r"<h3>(.*?)</h3>", ledger.group(1))
    table = re.search(r'<h2 id="leaves">.*?<tbody>(.*?)</tbody>', (DOCS / "privacy.html").read_text(encoding="utf-8"), re.S)
    assert table, "no recipients table on privacy.html - the parser lost it"
    in_privacy = re.findall(r'<th scope="row">(.*?)</th>', table.group(1))
    keys = ("freehire.me", "AI", "mployer", "email", "maintainer")
    assert len(on_home) == len(in_privacy) == len(keys), (on_home, in_privacy)
    for key, h, pv in zip(keys, on_home, in_privacy):
        assert key in h and key in pv, (key, h, pv)


# every file a claim rests on (app/web/claims.yml) + the pages: enough for a scratch copy
CLAIM_FILES = ("docs/index.html", "docs/privacy.html", "app/web/claims.yml", "AGENTS.md", "START HERE.md",
               "app/vscode/say.json", "app/install/install-mac.sh", "app/install/install-windows.ps1",
               "app/alert.py", "app/launch.py", "app/workspace.py", "app/docs/app-window.md")


def claim_copy(tmp_path):
    import shutil
    for rel in CLAIM_FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cfg.ROOT / rel, tmp_path / rel)
    shutil.copytree(cfg.ROOT / "app/apply/systems", tmp_path / "app/apply/systems")
    return tmp_path


def test_site_claims_still_match_the_app():
    # the site says the app does something it no longer does (old button name, a privacy row the
    # app added, a hiring system dropped) - visitors install on a promise the app breaks
    assert not claim_problems(cfg.ROOT), "\n".join(claim_problems(cfg.ROOT))


def test_claim_check_names_page_and_claim_when_the_app_changes(tmp_path):
    # a renamed button or a new hiring system passing unnoticed = the guard above guards nothing
    root = claim_copy(tmp_path)
    assert claim_problems(root) == []
    say = root / "app/vscode/say.json"
    say.write_text(say.read_text(encoding="utf-8").replace('"Make my resume"', '"Make the resume"'), encoding="utf-8")
    (root / "app/apply/systems/dayforce.py").write_text('NAME = "Dayforce"\n', encoding="utf-8")
    problems = claim_problems(root)
    assert any(p.startswith("index.html: claim today-page:") and "'Make the resume'" in p for p in problems), problems
    assert any(p.startswith("index.html: claim apply-systems:") and "Dayforce" in p for p in problems), problems
    assert all("app/web/claims.yml" in p for p in problems), problems


def test_home_research_teaser_quotes_only_the_articles_own_titles_and_descriptions():
    # a teaser line no article says is a new claim on the home page, unreviewed by the research loop
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    picks = re.findall(r'<li><a href="/research/([^"/]+)/">(.*?)</a><p>(.*?)</p></li>',
                       re.search(r'<ul class="picks">(.*?)</ul>', home, re.S).group(1))
    assert len(picks) == 3, picks
    for slug, title, line in picks:
        head = page(f"research/{slug}/index.html")
        assert head.text["title"] == [title], (slug, title)
        assert line in head.meta("description"), (slug, line)


def test_every_page_uses_typographic_quotes_and_dashes():
    # hand-written + generated (pages.py typesets research pages, About, the hub); mac/ + win/ = install scripts
    found, seen = [], 0
    for rel in sorted(files(DOCS)):
        if rel.endswith(".html") and rel.split("/")[0] not in ("mac", "win"):
            seen += 1
            found += [f"{rel}: {hit!r}" for hit in typewriter((DOCS / rel).read_text(encoding="utf-8"))[1]]
    assert seen >= 10 and not found, found


def test_typographic_check_trips_on_a_straight_quote_and_a_hyphen_dash():
    clean = "<main><p>It’s here – kept.</p><code>it's - code</code><div class=\"window\">Job 11 - x</div></main>"
    assert typewriter(clean)[1] == []
    assert typewriter(clean.replace("It’s", "It's"))[1]
    assert typewriter(clean.replace(" – ", " - "))[1]
    assert typewriter('<p title="it\'s">ok</p>')[1] == []


def test_no_words_run_together_in_page_text():
    # raw HTML w/o CSS (AI crawlers): "Install on WindowsMac" is one made-up word (C4, D10)
    found = [f"{name}: {hit!r}" for name in HAND_WRITTEN for hit in run_together((DOCS / name).read_text(encoding="utf-8"))]
    assert not found, found


def test_run_together_check_trips_on_touching_inline_text():
    assert run_together('<h2>On <span>Windows</span>\n<span>Mac</span></h2><p>Done.\n<span>Next</span></p>') == []
    assert run_together('<h2>On <span>Windows</span><span>Mac</span></h2>')
    assert run_together('<p><b>Today</b><span>3 new</span></p>')
    assert run_together('<p>You press Submit.<span>Works with</span></p>')
    assert run_together('<style>b</b><b>x</style><script>"a</b><b>b"</script>') == []


def test_home_resume_scene_shows_the_correction_as_del_and_ins():
    # signature scene: the old line is struck (<del>), the new one inserted (<ins>), and you approved it
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    scene = re.search(r'<section class="[^"]*\bresume\b[^"]*".*?</section>', raw, re.S)
    assert scene, "resume scene section missing"
    assert re.search(r"<del>.+?</del>", scene.group(0), re.S)
    assert re.search(r"<ins>.+?</ins>", scene.group(0), re.S)
    assert "You approved this line" in scene.group(0)



def test_copy_is_the_only_filled_yellow_control_on_home():
    # the highlighter marks words; one filled yellow control (Copy) says "press this" - the illustrated
    # Submit stays an ink outline, never filled (A21), so a juror never takes it for a working button
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    css = raw[raw.index("<style>"):raw.index("</style>")]
    assert yellow_fills(css) == ["#copy"]
    submit = re.search(r"\n  \.submit \{([^}]*)\}", css)
    assert submit and "background: none" in submit.group(1) and "border: 2px solid var(--text)" in submit.group(1)


def test_yellow_fill_check_trips_on_a_second_filled_control():
    css = "#copy { background: var(--mark); } mark { background: linear-gradient(var(--mark), var(--mark)); }"
    assert yellow_fills(css) == ["#copy"]
    assert yellow_fills(css + " .submit { color: var(--ink); background: #FFE433 }") == ["#copy", ".submit"]

def test_one_breadcrumb_name_per_url():
    # D22: every crumb + BreadcrumbList names a URL one way (/research/ = the hub's own title)
    found = [crumbs((DOCS / name).read_text(encoding="utf-8")) for name in PAGES]
    assert sum(1 for pairs in found if pairs) > 3 and any(url == "/research/" for pairs in found for url, _ in pairs)
    assert crumb_clashes(found) == {}


def test_research_pages_carry_matching_structured_data():
    # Article / ProfilePage / BreadcrumbList on the generated pages (none until the first article ships):
    # dates == the byline, author == the About page's Person, breadcrumbs land, sitemap lastmod == dateModified
    assert structured_data(DOCS, SITE) == []


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


def test_head_script_sets_html_classes_before_first_paint():
    # OS + phone classes on <html> before first paint (no flash of the wrong OS, no layout shift);
    # html.seen = opening moment once per session, skipped after a page-change crossfade
    [code] = head_scripts((DOCS / "index.html").read_text(encoding="utf-8"))
    assert len(code.encode()) <= HEAD_SCRIPT_MAX and "LINES" not in code
    for part in ('"is-phone"', '"is-mac"', '"seen"', "sessionStorage", "pagereveal", "viewTransition"):
        assert part in code, part
    body = next(s for s in page("index.html").text["script"] if "LINES" in s)
    assert "body.classList" not in body


def test_web_font_ships_with_its_licence():
    # OFL lets the font be served only w/ its licence alongside
    assert (DOCS / "fonts" / "OFL.txt").read_bytes() == (cfg.APP / "resume" / "fonts" / "Caladea" / "OFL.txt").read_bytes()


def test_generated_files_are_fresh():
    # sitemap.xml (+ research/, about/) come from app/web/pages.py; hand-edited or stale => rerun it
    spec = importlib.util.spec_from_file_location("pages", cfg.APP / "web" / "pages.py")
    pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pages)
    assert pages.problems(cfg.ROOT) == [], "run: uv run app/web/pages.py"


def test_every_page_fits_the_budgets():
    # speed is the brief (Lighthouse 100): size, requests + motion caps checked w/o a browser (site.md#budgets)
    assert [p for name in PAGES for p in budgets(DOCS, name)] == []


def test_shared_colours_meet_contrast_in_both_schemes():
    # text 4.5:1, controls + focus ring 3:1 (WCAG 1.4.3, 1.4.11); ring also on a white sheet in dark mode
    assert contrasts((DOCS / "index.html").read_text(encoding="utf-8")) == []


def test_every_page_lays_its_sheet_down_only_without_reduced_motion():
    # page change (PICK P-d2) opted in by every page: masthead held, main = the sheet that is laid
    # down; reduced motion => no transition at all
    for name in PAGES:
        css = shared((DOCS / name).read_text(encoding="utf-8"))
        assert re.search(NO_PREFERENCE + r"[^}]*@view-transition\s*\{\s*navigation:\s*auto", css), name
        assert re.search(r"\.masthead\s*\{\s*view-transition-name:\s*masthead", css), name
        assert re.search(r"(?<![\w.-])main\s*\{\s*view-transition-name:\s*sheet", css), name
        assert not re.search(r"@view-transition|view-transition-name", outside_no_preference(css)), name


def test_page_change_moves_only_transform_and_opacity_within_400ms():
    # ::view-transition-* keyframes animate transform + opacity only (compositor, no layout or paint)
    # and each pseudo is done (delay + duration) by 400 ms, so a click never waits on the motion
    for name in PAGES:
        css = shared((DOCS / name).read_text(encoding="utf-8"))
        rules = re.findall(r"::view-transition-[\w-]+\([^)]*\)\s*\{([^}]*)\}", css)
        assert rules, name
        frames = dict(re.findall(r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^}]*\})*)\s*\}", css))
        for body in rules:
            animation = re.search(r"animation\s*:\s*([^;]+)", body).group(1)
            used = [w for w in animation.split() if w in frames]
            assert used, (name, animation)
            for frame in used:
                props = {p.lower() for p in re.findall(r"([\w-]+)\s*:", re.sub(r"[^{};]*\{", ";", frames[frame]))}
                assert props <= {"opacity", "transform"}, (name, frame, props)
            times = [float(t) * (1000 if unit == "s" else 1) for t, unit in re.findall(r"(?<![\w.-])([\d.]+)(m?s)\b", animation)]
            assert times and sum(times[:2]) <= 400, (name, animation)


def test_site_md_tokens_table_is_the_shared_root():
    # site.md lists every token: one edited w/o the other => the doc lies about the colours
    css = shared((DOCS / "index.html").read_text(encoding="utf-8"))
    doc = (cfg.APP / "docs" / "site.md").read_text(encoding="utf-8")
    assert token_table(doc) == tokens(css)
    assert wide_table(doc) == wide_tokens(css) != {}


PAGE = """<!doctype html><html lang="en"><head><title>x</title>{head}<style>
  /* shared */
  :root {{ --paper: #ffffff; --ink: #000000; --ink-2: #3a3a3a; --mark: #ffe433; --rule: #c8c8c8; --desk: #ffffff; --text: #000000; --line: #c8c8c8; --text-2: #3a3a3a; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --desk: #1c1c1e; --text: #f2f2f2; --text-2: #cfcfcf; --line: #5c5c5e; }} }}
  :focus-visible {{ outline: 3px solid var(--text); box-shadow: 0 0 0 3px var(--desk); }}
  ::selection {{ background: var(--text); color: var(--desk); }}
  .window ::selection, .proof ::selection {{ background: var(--ink); color: var(--paper); }}
  {css}
  /* /shared */
</style></head><body><header><a href="/">x</a>{header}</header><main>{body}</main><footer>{footer}</footer>{scripts}</body></html>"""


def fixture(tmp_path, **parts) -> str:
    """A one-page docs/ in tmp_path: PAGE w/ the given parts filled in; returns the page name."""
    fields = dict.fromkeys(("head", "css", "header", "body", "footer", "scripts"), "") | parts
    (tmp_path / "index.html").write_text(PAGE.format(**fields), encoding="utf-8")
    return "index.html"


def test_budget_fixture_passes_clean(tmp_path):
    assert budgets(tmp_path, fixture(tmp_path)) == []
    assert contrasts((tmp_path / "index.html").read_text(encoding="utf-8")) == []


NOISE = random.Random(0).randbytes(30_000).hex()  # 60 KB of hex = 30 KB of entropy: gzip stays over 25 KB


@pytest.mark.parametrize("parts, files, trips", [
    ({"body": f"<p>{NOISE}</p>"}, {}, "gzip >"),
    ({"scripts": f"<script>{'x' * 5001}</script>"}, {}, "inline JS"),
    ({"body": "<i></i>" * 801}, {}, "elements in <body>"),
    ({"css": '@font-face { font-family: "X"; src: url("/fonts/big.woff2") format("woff2"); }'},
     {"fonts/big.woff2": 101_000}, "first load"),
    ({"head": '<link rel="preload" href="/a.woff2" as="font" crossorigin>' * 5}, {}, "critical requests"),
    ({"scripts": '<script src="/app.js"></script>'}, {}, "<script src="),
    ({"css": ".x { will-change: transform; }"}, {}, "will-change"),
    ({"css": "@keyframes grow { from { width: 0; } to { width: 10px; } }"}, {}, "animates width"),
    ({"css": ".x { transition: opacity .2s, height .2s; }"}, {}, "animates height"),
    ({"css": ".x { transition: all .2s; }"}, {}, "animates all"),
    ({"body": '<svg><use href="#gone"></use></svg>'}, {}, "has no target"),
    ({"header": '<a id="brand" href="/">x</a>'}, {}, "<header> holds ['id']"),
    ({"footer": "<style>p{}</style>"}, {}, "<footer> holds ['style']"),
    ({"scripts": "<script>const LINES = 1;</script><script>// LINES</script>"}, {}, "names LINES"),
    ({"head": f"<script>{'x' * 601}</script>"}, {}, "<head> script"),
    ({"head": "<script>const LINES = 1;</script>"}, {}, "<head> script names LINES"),
    ({"css": "body.is-mac .x { display: none; }"}, {}, "body.is-*"),
    ({"body": '<figure><p>Form</p><button>Submit</button></figure>'}, {}, "<figure> holds ['button']"),
    ({"body": '<figure class="bars"><figcaption>x</figcaption><table><tr><td><a href="#">x</a></td></tr></table></figure>'},
     {}, "<figure> holds ['a']"),
    ({"body": "<figure><p>Job 12</p><figcaption>x</figcaption><div>sheet</div></figure>"}, {}, "<figcaption> not the first"),
    ({"body": "<figure><figcaption>x</figcaption><h3>EXPERIENCE</h3></figure>"}, {}, "heading inside <figure>"),
    ({"css": ".ring { vector-effect: non-scaling-stroke; }"}, {}, "vector-effect in CSS"),
    ({"css": "@view-transition { navigation: auto; }"}, {}, "view transition outside"),
    ({"css": "@media (prefers-reduced-motion: no-preference) { .x { opacity: 1; } }"
             " header { view-transition-name: top; }"}, {}, "view transition outside"),
], ids=["html-gzip", "inline-js", "elements", "first-load", "critical", "script-src", "will-change",
        "keyframes", "transition", "transition-all", "use-target", "header-id", "footer-style", "lines-twice",
        "head-script-size", "head-script-lines", "body-class", "figure-control", "bars-control", "figcaption-middle",
        "figure-heading", "vector-effect-css", "view-transition",
        "view-transition-name"])
def test_each_budget_rule_trips_on_its_fixture(tmp_path, parts, files, trips):
    for rel, size in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"\0" * size)
    found = budgets(tmp_path, fixture(tmp_path, **parts))
    assert any(trips in p for p in found), found


@pytest.mark.parametrize("old, new, trips", [
    ("--text-2: #3a3a3a; }}", "--text-2: #999999; }}", "light: --text-2 on --desk"),
    ("--text-2: #cfcfcf;", "--text-2: #555555;", "dark: --text-2 on --desk"),
    # passes WCAG 2 (9.1:1), reads weak: the dark grey before the APCA check (Lc 65)
    ("--text-2: #cfcfcf;", "--text-2: #bdbdbd;", "dark: text --text-2 on --desk APCA"),
    ("--line: #5c5c5e;", "--line: #48484a;", "dark: hairline --line on --desk APCA"),
    ("--rule: #c8c8c8;", "--rule: #f4f4f4;", "light: hairline --rule on --paper APCA"),
    ("--mark: #ffe433;", "--mark: #333333;", "--ink on --mark"),
    (" box-shadow: 0 0 0 3px var(--desk);", "", "dark: focus ring on --paper"),
    (":focus-visible", ":focus", "no :focus-visible rule"),
    ("::selection", "::marker", "no ::selection rule"),
    ("background: var(--text); color: var(--desk)", "background: var(--mark); color: var(--ink)", "paints the highlighter"),
    ("background: var(--text); color: var(--desk)", "background: var(--text); color: var(--text-2)", "dark: ::selection"),
    (".window ::selection, .proof ::selection {", ".gone {",
     "dark: selection on the paper sheet .window"),
    ("background: var(--ink); color: var(--paper)", "background: #dddddd; color: var(--ink)",
     "light: selection on the paper sheet .proof"),
], ids=["text-light", "text-dark", "text-dark-apca", "line-dark-apca", "rule-light-apca", "mark", "ring-on-sheet-dark", "no-ring", "no-selection", "selection-yellow",
        "selection-faint", "selection-on-sheet-gone", "selection-on-sheet-faint"])
def test_each_contrast_rule_trips_on_its_fixture(tmp_path, old, new, trips):
    template = PAGE.format(**dict.fromkeys(("head", "css", "header", "body", "footer", "scripts"), ""))
    old, new = old.replace("}}", "}"), new.replace("}}", "}")
    assert old in template
    found = contrasts(template.replace(old, new, 1))
    assert any(trips in p for p in found), found


def test_token_table_check_trips_on_a_stale_row():
    css = shared(PAGE.format(**dict.fromkeys(("head", "css", "header", "body", "footer", "scripts"), "")))
    rows = "".join(f"| `{k}` | `{v}` | {'same' if tokens(css)['dark'][k] == v else '`' + tokens(css)['dark'][k] + '`'} | x |\n"
                   for k, v in tokens(css)["light"].items())
    table = "| Token | Light | Dark | Use |\n|---|---|---|---|\n" + rows
    assert token_table(table) == tokens(css)
    assert token_table(table.replace("`#3a3a3a` | `#cfcfcf`", "`#3a3a3a` | same", 1)) != tokens(css)
