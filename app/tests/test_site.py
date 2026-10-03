"""jobs.enrriquez.com (docs/, GitHub Pages): search + share metadata, icons, no third-party files.

Pages serves docs/ as is - no build step to catch a wrong canonical, a missing icon or a font from
another site, and a share card fails silently (preview just shows no picture). These tests read the
files on disk: no network, stdlib + pymupdf. Assets come from app/web/assets.py + app/web/og.html.
"""

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

from site_checks import (HEAD_SCRIPT_MAX, Head, budgets, contrasts, files, head_scripts, loaded_urls, own_url,  # noqa: E402
                         png_size, shared, structured_data, target, token_table, tokens)

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
        # Google cuts titles ~60 chars, descriptions ~160
        assert len(head.text["title"][0]) <= 60, name
        assert len(head.meta("description")) <= 160, name
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


def test_nothing_in_docs_trips_jekyll():
    # Pages runs Jekyll on docs/: .md becomes HTML, front matter (---) gets templated, and
    # _x / .x / #x / x~ files are dropped from the site
    tracked = subprocess.run(["git", "-C", str(cfg.ROOT), "ls-files", "docs"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    assert tracked
    for path in tracked:
        assert not path.endswith(".md"), path
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
    locs = re.findall(r"<loc>(.+?)</loc>", sitemap)
    assert len(locs) == len(set(locs)) and set(locs) == set(INDEXED.values())
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


def test_home_h1_is_the_literal_answer_to_is_this_a_website():
    # owner's fix for "is this a website?": the h1 says what it is, in plain words, unchanged
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", (DOCS / "index.html").read_text(encoding="utf-8"), re.S)
    assert h1 == ["A free job-search app for your Windows or Mac computer."]


def test_home_resume_scene_shows_the_correction_as_del_and_ins():
    # signature scene: the old line is struck (<del>), the new one inserted (<ins>), and you approved it
    raw = (DOCS / "index.html").read_text(encoding="utf-8")
    scene = re.search(r'<section class="[^"]*\bresume\b[^"]*".*?</section>', raw, re.S)
    assert scene, "resume scene section missing"
    assert re.search(r"<del>.+?</del>", scene.group(0), re.S)
    assert re.search(r"<ins>.+?</ins>", scene.group(0), re.S)
    assert "You approved this line" in scene.group(0)


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


def test_site_md_tokens_table_is_the_shared_root():
    # site.md lists every token: one edited w/o the other => the doc lies about the colours
    css = shared((DOCS / "index.html").read_text(encoding="utf-8"))
    doc = (cfg.APP / "docs" / "site.md").read_text(encoding="utf-8")
    assert token_table(doc) == tokens(css)


PAGE = """<!doctype html><html lang="en"><head><title>x</title>{head}<style>
  /* shared */
  :root {{ --paper: #ffffff; --ink: #000000; --ink-2: #3a3a3a; --mark: #ffe433; --desk: #ffffff; --text: #000000; --text-2: #3a3a3a; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --desk: #1c1c1e; --text: #f2f2f2; --text-2: #bdbdbd; }} }}
  :focus-visible {{ outline: 3px solid var(--text); box-shadow: 0 0 0 3px var(--desk); }}
  ::selection {{ background: var(--text); color: var(--desk); }}
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
], ids=["html-gzip", "inline-js", "elements", "first-load", "critical", "script-src", "will-change",
        "keyframes", "transition", "transition-all", "use-target", "header-id", "footer-style", "lines-twice",
        "head-script-size", "head-script-lines", "body-class", "figure-control"])
def test_each_budget_rule_trips_on_its_fixture(tmp_path, parts, files, trips):
    for rel, size in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"\0" * size)
    found = budgets(tmp_path, fixture(tmp_path, **parts))
    assert any(trips in p for p in found), found


@pytest.mark.parametrize("old, new, trips", [
    ("--text-2: #3a3a3a; }}", "--text-2: #999999; }}", "light: --text-2 on --desk"),
    ("--text-2: #bdbdbd;", "--text-2: #555555;", "dark: --text-2 on --desk"),
    ("--mark: #ffe433;", "--mark: #333333;", "--ink on --mark"),
    (" box-shadow: 0 0 0 3px var(--desk);", "", "dark: focus ring on --paper"),
    (":focus-visible", ":focus", "no :focus-visible rule"),
    ("::selection", "::marker", "no ::selection rule"),
    ("background: var(--text); color: var(--desk)", "background: var(--mark); color: var(--ink)", "paints the highlighter"),
    ("background: var(--text); color: var(--desk)", "background: var(--text); color: var(--text-2)", "dark: ::selection"),
], ids=["text-light", "text-dark", "mark", "ring-on-sheet-dark", "no-ring", "no-selection", "selection-yellow",
        "selection-faint"])
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
    assert token_table(table.replace("`#3a3a3a` | `#bdbdbd`", "`#3a3a3a` | same", 1)) != tokens(css)
