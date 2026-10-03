"""app/web/pages.py: builds the site's generated files, reports + prunes stale ones.

Runs on a throwaway site in tmp_path - never app/web/research or the real docs/.
"""

import importlib.util
from urllib.parse import urlsplit

import cfg

spec = importlib.util.spec_from_file_location("pages", cfg.APP / "web" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

HOME = '<link rel="canonical" href="https://example.test/">'


def make_site(root):
    docs = root / "docs"
    docs.mkdir()
    (docs / "CNAME").write_text("example.test\n")
    (docs / "index.html").write_text(f"<html><head>{HOME}</head></html>\n")
    (docs / "b.html").write_text('<link rel="canonical" href="https://example.test/b.html">\n')
    (docs / "a.html").write_text('<link rel="canonical" href="https://example.test/a.html">\n')
    (docs / "404.html").write_text('<meta name="robots" content="noindex">\n')
    (docs / "mac").mkdir()
    (docs / "mac" / "index.html").write_text("echo install\n")
    return docs


def test_sitemap_lists_indexed_pages_home_first_then_sorted(tmp_path):
    make_site(tmp_path)
    assert pages.build(tmp_path)["sitemap.xml"] == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>https://example.test/</loc></url>\n"
        "  <url><loc>https://example.test/a.html</loc></url>\n"
        "  <url><loc>https://example.test/b.html</loc></url>\n"
        "</urlset>\n")


def test_missing_file_is_reported_then_written_and_a_second_run_changes_nothing(tmp_path):
    docs = make_site(tmp_path)
    assert pages.problems(tmp_path) == ["missing: docs/sitemap.xml"]
    assert pages.write(tmp_path) == ["wrote: docs/sitemap.xml"]
    first = (docs / "sitemap.xml").read_bytes()
    assert b"\r" not in first
    assert pages.problems(tmp_path) == [] and pages.write(tmp_path) == []
    assert (docs / "sitemap.xml").read_bytes() == first


def test_orphan_is_reported_then_deleted_and_finder_files_are_ignored(tmp_path):
    docs = make_site(tmp_path)
    pages.write(tmp_path)
    (docs / "research" / "old-article").mkdir(parents=True)
    (docs / "research" / "old-article" / "index.html").write_text("gone\n")
    (docs / "research" / ".DS_Store").write_bytes(b"\0")
    (docs / ".DS_Store").write_bytes(b"\0")
    assert pages.problems(tmp_path) == ["orphaned: docs/research/old-article/index.html"]
    assert pages.write(tmp_path) == ["deleted: docs/research/old-article/index.html"]
    # emptied folder goes too (Pages never serves .DS_Store); hand-written files stay
    assert not (docs / "research").exists()
    assert (docs / ".DS_Store").exists() and (docs / "a.html").exists()
    assert pages.problems(tmp_path) == []


def test_orphan_page_stays_out_of_the_sitemap(tmp_path):
    docs = make_site(tmp_path)
    (docs / "about").mkdir()
    (docs / "about" / "index.html").write_text('<link rel="canonical" href="https://example.test/about/">\n')
    assert "about/" not in pages.build(tmp_path)["sitemap.xml"]


def test_crlf_copy_is_not_stale_but_an_edit_is(tmp_path):
    # git autocrlf on Windows checks files out w/ CRLF: same content, not a problem
    docs = make_site(tmp_path)
    pages.write(tmp_path)
    path = docs / "sitemap.xml"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert pages.problems(tmp_path) == []
    path.write_bytes(path.read_bytes() + b" ")
    assert pages.problems(tmp_path) == ["stale: docs/sitemap.xml"]


def test_dates_spelled_in_english_without_the_clock():
    assert pages.long_date("2026-10-02") == "2 October 2026"
    assert pages.long_date("2027-01-31") == "31 January 2027"


# --- articles from Markdown: a copy of the real site + throwaway sources in tmp_path ---

import re  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

from site_checks import Head, files, loaded_urls, own_url, target  # noqa: E402
from test_docs import anchors  # noqa: E402

SOURCES = {
    "ats-myth.md": """---
title: Do resume robots reject you?
description: What the evidence says about software that screens resumes.
published: 2026-09-01
modified: 2026-09-20
status: published
og_title: Do resume robots reject most resumes?
---
Short intro, see [the other one](ai-bias.md#what-was-measured) and [methods](methods.md).

## What the claim says

Read [privacy](https://jobs.enrriquez.com/privacy.html) and [the code](../../docs/site.md#look).

| Study | Year |
|---|---|
| One | 2021 |

## What the claim says *again*

[Back up](#what-the-claim-says).
""",
    "ai-bias.md": """---
title: AI screening and bias
description: What tests of AI resume screeners found.
published: 2026-09-10
status: published
---
See [the myth](ats-myth.md).

## What was measured

Text.
""",
    "next-one.md": """---
title: Not ready yet
description: A draft.
status: draft
---
## Draft heading
""",
    "methods.md": """---
title: How we research
description: How these articles are researched, reviewed and corrected.
published: 2026-09-01
status: published
---
## Sources first
""",
    "about.md": """---
title: About the author
description: Who writes these articles.
published: 2026-09-01
status: published
---
## Work
""",
}


def research_site(root, extra=None):
    """Real docs/ (minus what pages.py builds) + sources in app/web/research + one repo doc to link."""
    shutil.copytree(cfg.ROOT / "docs", root / "docs",
                    ignore=lambda d, names: [n for n in names if n.startswith(".") or
                                             (d == str(cfg.ROOT / "docs") and n in ("research", "about", "sitemap.xml"))])
    folder = root / "app" / "web" / "research"
    folder.mkdir(parents=True)
    for name, text in {**SOURCES, **(extra or {})}.items():
        if text is not None:
            (folder / name).write_text(text, encoding="utf-8")
    (root / "app" / "docs").mkdir()
    (root / "app" / "docs" / "site.md").write_text("# Site\n\n## Look\n")
    return folder


def test_published_sources_become_pages_and_drafts_do_not(tmp_path):
    research_site(tmp_path)
    built = pages.build(tmp_path)
    assert [k for k in built if k != "sitemap.xml"] == [
        "about/index.html", "research/ai-bias/index.html", "research/ats-myth/index.html", "research/methods/index.html"]
    assert "next-one" not in built["sitemap.xml"]
    assert "https://jobs.enrriquez.com/research/ats-myth/" in built["sitemap.xml"]
    assert pages.write(tmp_path) and pages.problems(tmp_path) == [] and pages.write(tmp_path) == []


def test_article_head_body_and_links(tmp_path):
    folder = research_site(tmp_path)
    html = pages.build(tmp_path)["research/ats-myth/index.html"]
    head = Head(html)
    url = "https://jobs.enrriquez.com/research/ats-myth/"
    assert head.text["title"] == ["Do resume robots reject you?"]
    assert [a["href"] for a in head.links("canonical")] == [url] and head.meta("og:url") == url
    assert head.meta("og:type") == "article" and head.meta("og:title") == "Do resume robots reject most resumes?"
    assert head.meta("article:published_time") == "2026-09-01" and head.meta("article:modified_time") == "2026-09-20"
    assert urlsplit(head.meta("og:image")).path == "/og.png"
    # heading ids follow the same rule as links between the Markdown files
    ids = [a["id"] for t, a in head.tags if t in ("h2", "h3") and "id" in a]
    assert set(ids) == anchors(folder / "ats-myth.md") == {"what-the-claim-says", "what-the-claim-says-again"}
    hrefs = [a["href"] for a in head.all("a")]
    for href in ("/research/ai-bias/#what-was-measured", "/research/methods/", "/privacy.html",
                 "https://github.com/cezkid/jobs/blob/main/app/docs/site.md#look", "#what-the-claim-says", "/about/"):
        assert href in hrefs, href
    assert '<div class="table" role="region" aria-label="Table: What the claim says" tabindex="0">' in html
    assert ('By <a href="/about/">Cesar Enrriquez-Zuniga</a> · Published <time datetime="2026-09-01">1 September 2026</time>'
            ' · Updated <time datetime="2026-09-20">20 September 2026</time>') in html
    assert '<nav class="crumbs" aria-label="Breadcrumb">' in html
    # no update => one date
    assert "Updated" not in pages.build(tmp_path)["research/ai-bias/index.html"].split('class="meta"')[1].split("</p>")[0]


def test_generated_pages_keep_the_site_rules(tmp_path):
    # same invariants test_site.py holds the real docs/ to
    research_site(tmp_path)
    pages.write(tmp_path)
    docs = tmp_path / "docs"
    found = files(docs)
    home = Head((docs / "index.html").read_text(encoding="utf-8"))
    raw = {n: (docs / n).read_text(encoding="utf-8") for n in found if n.endswith(".html") and n.split("/")[0] in ("research", "about")}
    assert len(raw) == 4
    shared = re.search(r"/\* shared \*/.*?/\* /shared \*/", (docs / "index.html").read_text(encoding="utf-8"), re.S).group(0)
    for name, text in raw.items():
        head = Head(text)
        assert [a["href"] for a in head.links("canonical")] == [own_url(name, "https://jobs.enrriquez.com/")], name
        assert len(head.text["title"][0]) <= 60 and len(head.meta("description")) <= 160, name
        for rel in "icon", "apple-touch-icon", "manifest", "preload":
            assert head.links(rel) == home.links(rel), (name, rel)
        assert head.meta("og:image") == home.meta("og:image") and head.meta("twitter:card") == "summary_large_image"
        assert shared in text, name
        for tag in "header", "footer":
            assert re.findall(rf"<{tag}\b.*?</{tag}>", text, re.S) == re.findall(
                rf"<{tag}\b.*?</{tag}>", (docs / "index.html").read_text(encoding="utf-8"), re.S), (name, tag)
        for url in loaded_urls(head):
            assert url.startswith("data:") or (url.startswith("/") and target(url) in found), (name, url)
        for a in head.all("a"):
            href = urlsplit(a["href"])
            if a["href"].startswith("#"):
                assert href.fragment in head.ids(), (name, a)
            elif a["href"].startswith("/"):
                assert target(href.path) in found and (href.path.endswith("/") or "." in href.path), (name, a)
                if href.fragment:
                    assert href.fragment in Head((docs / target(href.path)).read_text(encoding="utf-8")).ids(), (name, a)
            else:
                assert href.scheme == "https", (name, a)
        assert not text.startswith("---") and "\r" not in text


@pytest.mark.parametrize("extra, problem", [
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("See [the myth](ats-myth.md).", "[x](next-one.md)")},
     "ai-bias.md:7: next-one.md is not a published page"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "ats-myth.md#nope")}, "no heading #nope in ats-myth.md"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://example.com/")}, "to other sites through sources"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://jobs.enrriquez.com/nope.html")}, "is not a page on this site"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "../../docs/gone.md")}, "no such file in the repo"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "#nope")}, "no heading #nope on this page"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: published\nauthor: me")},
     "ai-bias.md:6: unknown header key 'author'"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: published\ntitle: Again")}, "duplicate key 'title'"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("2026-09-10", "2026-02-30")}, "date must be YYYY-MM-DD"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: live")}, "status must be draft or published"),
    ({"ai-bias.md": SOURCES["ai-bias.md"] + "\n## What was measured\n"}, "heading id 'what-was-measured' used twice"),
    ({"AI_Bias.md": SOURCES["ai-bias.md"]}, "AI_Bias.md:1: file name must be lower-case"),
    ({"feed.md": SOURCES["ai-bias.md"]}, "feed is a reserved name"),
    ({"about.md": None}, "publish about.md with the first page"),
])
def test_source_problems_are_reported_with_file_and_line(tmp_path, extra, problem):
    research_site(tmp_path, extra)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


def test_no_sources_builds_no_pages(tmp_path):
    make_site(tmp_path)
    assert list(pages.build(tmp_path)) == ["sitemap.xml"]
