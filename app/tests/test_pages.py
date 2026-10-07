"""app/web/pages.py: builds the site's generated files, reports + prunes stale ones.

Runs on a throwaway site in tmp_path - never app/web/research or the real docs/.
"""

import importlib.util
import json
import xml.etree.ElementTree as ET
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
    # US order: the site is en_US and its readers are US job seekers
    assert pages.long_date("2026-10-02") == "October 2, 2026"
    assert pages.long_date("2027-01-31") == "January 31, 2027"


# --- articles from Markdown: a copy of the real site + throwaway sources in tmp_path ---

import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

from site_checks import Head, crumb_clashes, crumbs, files, loaded_urls, own_url, structured_data, target  # noqa: E402
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
Callbacks differ by 36% [@quillian-2017, p. 3]. Firms vary [@kline-2021; @eeoc-2023].

## What the claim says

Read [privacy](https://jobs.enrriquez.com/privacy.html) and [the code](../../docs/site.md#look). [Report a mistake](https://github.com/cezkid/jobs/issues/new?title=Research%20correction).

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

## How is AI used?
""",
    "index.md": """---
title: Research
description: Evidence on AI and resumes, every claim sourced.
published: 2026-09-01
status: published
---
How these are made: [methods](methods.md).
""",
    "about.md": """---
title: About the author
description: Who writes these articles.
published: 2026-09-01
status: published
---
Contact: www.enrriquez.com. Code: github.com/cezkid/jobs.

## Work
""",
}


REGISTRY = """\
- id: quillian-2017
  type: article
  authors: [Quillian, Lincoln, "Pager, Devah", "Hexel, Ole", "Midtboen, Arnfinn H."]
  year: 2017
  title: Meta-analysis of field experiments shows no change in racial discrimination in hiring over time
  venue: Proceedings of the National Academy of Sciences
  doi: 10.1073/pnas.1706255114
  evidence: meta-analysis
  sample: 28 US studies, 55,842 applications
  checked: 2026-09-29
- id: kline-2021
  type: report
  authors: ["Kline, Patrick", "Rose, Evan K.", "Walters, Christopher R."]
  year: 2021
  title: Systemic discrimination among large U.S. employers
  url: https://www.nber.org/papers/w29053
  evidence: large field experiment
  preprint: true
  checked: 2026-09-29
- id: eeoc-2023
  type: law
  org: US Equal Employment Opportunity Commission
  year: 2023
  title: Select issues in AI hiring
  url: https://www.eeoc.gov/ai
  evidence: law
  checked: 2026-09-29
  recheck_by: 2999-01-01
"""
REGISTRY = REGISTRY.replace("authors: [Quillian, Lincoln,", 'authors: ["Quillian, Lincoln",')


def research_site(root, extra=None, reviews=None, registry=REGISTRY):
    """Real docs/ (minus what pages.py builds) + sources in app/web/research + one repo doc to link.
    Every published source gets a publish review unless reviews names it (None = no review file)."""
    shutil.copytree(cfg.ROOT / "docs", root / "docs",
                    ignore=lambda d, names: [n for n in names if n.startswith(".") or
                                             (d == str(cfg.ROOT / "docs") and n in ("research", "about", "sitemap.xml"))])
    folder = root / "app" / "web" / "research"
    folder.mkdir(parents=True)
    (folder / "reviews").mkdir()
    for name, text in {**SOURCES, **(extra or {})}.items():
        if text is not None:
            (folder / name).write_text(text, encoding="utf-8")
            if "status: published" in text:
                review = "---\nreviewed: 2026-09-30\nverdict: publish\n---\nClaims checked.\n"
                (folder / "reviews" / name).write_text(review, encoding="utf-8")
    for name, text in (reviews or {}).items():
        path = folder / "reviews" / name
        if text is None:
            path.unlink()
        else:
            path.write_text(text, encoding="utf-8")
    if registry is not None:
        (folder / "sources.yml").write_text(registry, encoding="utf-8")
    (root / "app" / "docs").mkdir()
    (root / "app" / "docs" / "site.md").write_text("# Site\n\n## Look\n")
    # repo links must name a file git tracks
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "app/docs/site.md"], check=True)
    return folder


def test_published_sources_become_pages_and_drafts_do_not(tmp_path):
    research_site(tmp_path)
    built = pages.build(tmp_path)
    assert [k for k in built if k != "sitemap.xml"] == [
        "about/index.html", "research/ai-bias/index.html", "research/ats-myth/index.html", "research/feed.xml",
        "research/index.html", "research/methods/index.html"]
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
    assert urlsplit(head.meta("og:image")).path == "/og-research.png" == "/" + pages.CARD
    assert head.meta("og:image:alt") == pages.CARD_ALT and head.meta("og:image:width") == "1200"
    # heading ids follow the same rule as links between the Markdown files
    ids = [a["id"] for t, a in head.tags if t in ("h2", "h3") and "id" in a]
    assert set(ids) - {"sources"} == anchors(folder / "ats-myth.md") == {"what-the-claim-says", "what-the-claim-says-again"}
    hrefs = [a["href"] for a in head.all("a")]
    for href in ("/research/ai-bias/#what-was-measured", "/research/methods/", "/privacy.html",
                 "https://github.com/cezkid/jobs/blob/main/app/docs/site.md#look", "#what-the-claim-says", "/about/",
                 "https://github.com/cezkid/jobs/issues/new?title=Research%20correction"):
        assert href in hrefs, href
    assert '<div class="table" role="region" aria-label="Table: What the claim says" tabindex="0">' in html
    assert ('By <a href="/about/">Cesar Enrriquez-Zuniga</a>. Published <time datetime="2026-09-01">September 1, 2026</time>.'
            ' Updated <time datetime="2026-09-20">September 20, 2026</time>.') in html
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
    assert len(raw) == 5
    shared = re.search(r"/\* shared \*/.*?/\* /shared \*/", (docs / "index.html").read_text(encoding="utf-8"), re.S).group(0)
    for name, text in raw.items():
        head = Head(text)
        assert [a["href"] for a in head.links("canonical")] == [own_url(name, "https://jobs.enrriquez.com/")], name
        assert len(head.text["title"][0]) <= 60 and len(head.meta("description")) <= 155, name
        for rel in "icon", "apple-touch-icon", "manifest", "preload":
            assert head.links(rel) == home.links(rel), (name, rel)
        assert head.meta("og:image") == f"https://jobs.enrriquez.com/{pages.CARD}?v={pages.CARD_V}" and head.meta("twitter:card") == "summary_large_image"
        assert head.meta("og:image:alt") == head.meta("twitter:image:alt") == pages.CARD_ALT, name
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
        assert head.duplicate_ids() == [], name


@pytest.mark.parametrize("extra, problem", [
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("See [the myth](ats-myth.md).", "[x](next-one.md)")},
     "ai-bias.md:7: next-one.md is not a published page"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "ats-myth.md#nope")}, "no heading #nope in ats-myth.md"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://example.com/")}, "to other sites through sources"),
    # only the repo's issues page: its look-alikes are other sites
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://github.com/cezkid/jobs/issues-x")}, "to other sites through sources"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://github.com/cezkid/jobs/pulls")}, "to other sites through sources"),
    # the code + the author's site are allowed as named, not their neighbours
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://github.com/cezkid/jobs-x")}, "to other sites through sources"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://www.enrriquez.com/blog")}, "to other sites through sources"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "https://jobs.enrriquez.com/nope.html")}, "is not a page on this site"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "../../docs/gone.md")}, "no such file in the repo"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", "#nope")}, "no heading #nope on this page"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: published\nauthor: me")},
     "ai-bias.md:6: unknown header key 'author'"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: published\ntitle: Again")}, "duplicate key 'title'"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("2026-09-10", "2026-02-30")}, "date must be YYYY-MM-DD"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: live")}, "status must be draft or published"),
    ({"ai-bias.md": SOURCES["ai-bias.md"] + "\n## What was measured\n"}, "heading id 'what-was-measured' used twice"),
    # src-<id> = a Sources entry's id: a heading w/ it => two elements, one id
    ({"ai-bias.md": SOURCES["ai-bias.md"] + "\n## Src quillian 2017\n"}, "heading id 'src-quillian-2017' - start the heading"),
    ({"ai-bias.md": SOURCES["ai-bias.md"] + "\n## ???\n"}, "heading id '' - start the heading"),
    ({"AI_Bias.md": SOURCES["ai-bias.md"]}, "AI_Bias.md:1: file name must be lower-case"),
    ({"feed.md": SOURCES["ai-bias.md"]}, "feed is a reserved name"),
    ({"about.md": None}, "publish about.md with the first page"),
])
def test_source_problems_are_reported_with_file_and_line(tmp_path, extra, problem):
    research_site(tmp_path, extra)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


def test_repo_links_name_tracked_files_in_exact_case(tmp_path):
    # GitHub shows tracked files only, case-sensitive; a macOS disk finds SITE.md for site.md, and a
    # link to an ignored private file would put its name on a public page
    (tmp_path / ".data").mkdir()
    (tmp_path / ".data" / "secret.txt").write_text("private")
    for link in "../../docs/SITE.md", "../../../.data/secret.txt":
        shutil.rmtree(tmp_path / "docs", ignore_errors=True)
        shutil.rmtree(tmp_path / "app", ignore_errors=True)
        research_site(tmp_path, {"ai-bias.md": SOURCES["ai-bias.md"].replace("ats-myth.md", link)})
        with pytest.raises(pages.SourceError) as e:
            pages.build(tmp_path)
        assert f"{link}: no such file in the repo (tracked by git, exact case)" in str(e.value)


def test_link_to_the_feed_lands(tmp_path):
    research_site(tmp_path, {"methods.md": SOURCES["methods.md"] + "\n[Feed](https://jobs.enrriquez.com/research/feed.xml)\n"})
    assert 'href="/research/feed.xml"' in pages.build(tmp_path)["research/methods/index.html"]


def test_write_clears_a_wrong_case_orphan_before_writing(tmp_path):
    # macOS disk: research/AI-Bias/ is research/ai-bias/ => deleting the orphan after writing took the new page
    research_site(tmp_path)
    stale = tmp_path / "docs" / "research" / "AI-Bias" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    pages.write(tmp_path)
    found = files(tmp_path / "docs")
    assert "research/ai-bias/index.html" in found and "research/AI-Bias/index.html" not in found
    assert pages.problems(tmp_path) == []


def test_no_sources_builds_no_pages(tmp_path):
    make_site(tmp_path)
    assert list(pages.build(tmp_path)) == ["sitemap.xml"]


# --- article lints: one bad snippet per rule, in ai-bias.md (line 11 = "Text.") ---

BIAS = SOURCES["ai-bias.md"]


def body(snippet):
    return {"ai-bias.md": BIAS.replace("Text.", snippet)}


@pytest.mark.parametrize("extra, problem", [
    (body("# Top"), "ai-bias.md:11: # heading in the body"),
    (body("#### Deep"), "ai-bias.md:11: h4 after h2 - heading level skipped"),
    (body("## See [the myth](ats-myth.md)"), "ai-bias.md:11: link in a heading"),
    (body("## Measured [@quillian-2017]"), "ai-bias.md:11: citation in a heading"),
    (body("## A <b>bold</b> idea"), "ai-bias.md:11: HTML or &...; entity in a heading"),
    (body("## Fish &amp; chips"), "ai-bias.md:11: HTML or &...; entity in a heading"),
    (body("## Closed ##"), "ai-bias.md:11: closing # in a heading"),
    (body("First line.\nThen <div>raw</div> here."), "ai-bias.md:12: raw HTML '<div>' shows as text"),
    (body("![chart](chart.png)"), "ai-bias.md:11: image - pages carry no images"),
    (body("[owner: check this number]"), "ai-bias.md:11: [owner: note or TODO"),
    (body("TODO cite"), "ai-bias.md:11: [owner: note or TODO"),
    ({"ai-bias.md": BIAS.replace("AI screening and bias", "A" * 61)}, "ai-bias.md:2: title is 61 characters, max 60"),
    ({"ai-bias.md": BIAS.replace("What tests of AI resume screeners found.", "d" * 156)},
     "ai-bias.md:3: description is 156 characters, max 155"),
    ({"ai-bias.md": BIAS.replace("status: published", f"status: published\nog_title: {'o' * 71}")},
     "ai-bias.md:6: og_title is 71 characters, max 70"),
    ({"ai-bias.md": BIAS.replace("2026-09-10", "2999-01-01")}, "ai-bias.md:4: published 2999-01-01 is in the future"),
    ({"ai-bias.md": BIAS.replace("status: published", "modified: 2026-09-01\nstatus: published")},
     "ai-bias.md:5: modified 2026-09-01 is before published 2026-09-10"),
    ({"ai-bias.md": BIAS.replace("(ats-myth.md)", "(<ats-myth.md>)")}, "ai-bias.md:7: link in <...>"),
    (body("Text​."), "ai-bias.md:11: invisible character U+200B"),
    (body("Open the repo."), "ai-bias.md:11: 'repo' is jargon"),
    ({"ai-bias.md": BIAS.replace("AI screening and bias", "The API story")}, "ai-bias.md:2: header uses 'API'"),
    ({"methods.md": SOURCES["methods.md"].replace("How we research", "AI screening and bias")},
     "methods.md:2: same title as app/web/research/ai-bias.md"),
    ({"methods.md": SOURCES["methods.md"].replace("How these articles are researched, reviewed and corrected.",
                                                  "What tests of AI resume screeners found.")},
     "methods.md:3: same description as app/web/research/ai-bias.md"),
])
def test_article_lints_report_file_and_line(tmp_path, extra, problem):
    research_site(tmp_path, extra)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


def test_lints_pass_code_and_drafts_and_warn_on_characters_outside_the_font(tmp_path):
    extra = {**body("`<div>` and `repo` in code, Resume details.yml, an API key, → arrow."),
             "next-one.md": SOURCES["next-one.md"] + "\nTODO [owner: finish] <b>x</b>\n"}
    research_site(tmp_path, extra)
    warnings = []
    assert "research/ai-bias/index.html" in pages.build(tmp_path, warnings)
    assert warnings == ["app/web/research/ai-bias.md:11: U+2192 not in the site font (assets.UNICODES)"]


def test_lint_patterns_match_their_originals():
    import test_docs
    from resume import lint as resume_lint
    assert pages.JARGON.pattern == test_docs.JARGON.pattern and pages.JARGON_OK == test_docs.JARGON_OK
    assert pages.INVISIBLE.pattern == resume_lint.INVISIBLE.pattern



# --- citations, sources.yml, review gate ---

def test_citations_render_author_year_links_and_an_alphabetical_sources_list(tmp_path):
    research_site(tmp_path)
    html = pages.build(tmp_path)["research/ats-myth/index.html"]
    # set small: a skimming eye lands on the finding, not the names (reader-engagement.md)
    assert 'Callbacks differ by 36% <small>(<a href="#src-quillian-2017">Quillian et al. 2017</a>, p. 3)</small>.' in html
    assert ('Firms vary <small>(<a href="#src-kline-2021">Kline et al. 2021</a>; '
            '<a href="#src-eeoc-2023">US Equal Employment Opportunity Commission 2023</a>)</small>.') in html
    # a tap opens the entry in a card: the script once, after the footer; none on a page citing nothing
    assert html.count(f"<script>{pages.CITE_JS}</script>") == 1 and html.index("</footer>") < html.index(pages.CITE_JS)
    assert pages.CITE_JS not in pages.build(tmp_path)["research/ai-bias/index.html"]
    sources = html.split('<h2 id="sources">Sources</h2>\n<ol class="sources">\n')[1].split("</ol>")[0]
    assert re.findall(r'<li id="src-([^"]+)"', sources) == ["kline-2021", "quillian-2017", "eeoc-2023"]
    assert ('<li id="src-quillian-2017"><b class="evidence">Big study (many studies combined)</b> '
            "Quillian, Lincoln, Pager, Devah, Hexel, Ole and Midtboen, Arnfinn H. (2017). "
            "Meta-analysis of field experiments shows no change in racial discrimination in hiring over time. "
            "<i>Proceedings of the National Academy of Sciences.</i> 28 US studies, 55,842 applications. "
            'Checked <time datetime="2026-09-29">September 29, 2026</time>. '
            '<a href="https://doi.org/10.1073/pnas.1706255114">DOI</a></li>') in sources
    # A14: each entry opens with its label; no visible text is a raw URL
    for li in re.findall(r"<li id=.*?</li>", sources):
        assert li.startswith(re.match(r'<li id="[^"]+">', li).group(0) + '<b class="evidence">'), li
        assert not re.search(r">https?://", li)
    assert "Preprint, not peer-reviewed." in sources.split('id="src-kline-2021"')[1].split("</li>")[0]
    assert '<a href="https://www.nber.org/papers/w29053">Open copy</a>' in sources
    # a page that cites nothing gets no list
    assert 'id="sources"' not in pages.build(tmp_path)["research/ai-bias/index.html"]


def test_citation_in_code_or_link_text_stays_text_and_same_labels_get_a_b(tmp_path):
    twin = REGISTRY + """- id: quillian-2017-b
  type: web
  authors: ["Quillian, Lincoln", "Pager, Devah", "Hexel, Ole"]
  year: 2017
  title: Data
  url: https://example.org/data
  evidence: meta-analysis
  checked: 2026-09-29
"""
    research_site(tmp_path, body("Code `[@nope]` and [link [@nope]](ats-myth.md) and [@quillian-2017-b; @quillian-2017]."),
                  registry=twin)
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert '<code translate="no">[@nope]</code>' in html and ">link [@nope]</a>" in html
    assert ('(<a href="#src-quillian-2017-b">Quillian et al. 2017b</a>; '
            '<a href="#src-quillian-2017">Quillian et al. 2017a</a>)') in html


def test_escaped_bracket_keeps_a_citation_as_text(tmp_path):
    research_site(tmp_path, body("Write \\[@quillian-2017] to cite. Cited here [@quillian-2017]."))
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert "Write [@quillian-2017] to cite." in html
    assert html.count('href="#src-quillian-2017"') == 1


def test_page_text_gets_curly_quotes_and_en_dashes_but_code_and_identifiers_stay(tmp_path):
    # A12, D13: typographer on output; (c) stays (c) - its glyph is not in the font subset
    research_site(tmp_path, body("It's \"fine\" - see 10-15 years [@quillian-2017, p. 22-23], FAccT '24, Act 103-0804,"
                                 " case 3:23-cv-00770, on 2026-10-03 (c) and `it's - 10-15`."))
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert "It’s “fine” – see 10–15 years" in html and ", p. 22–23)" in html
    assert "FAccT ’24, Act 103-0804, case 3:23-cv-00770, on 2026-10-03 (c) and <code translate=\"no\">it's - 10-15</code>" in html
    # a URL shown as link text stays as written
    research_site(tmp_path / "b", body("See [jobs.enrriquez.com/x - 1-2](https://jobs.enrriquez.com/privacy.html) [@quillian-2017]."))
    assert ">jobs.enrriquez.com/x - 1-2</a>" not in pages.build(tmp_path / "b")["research/ai-bias/index.html"]
    research_site(tmp_path / "c", body("See [https://jobs.enrriquez.com/x - 1-2](https://jobs.enrriquez.com/privacy.html)."))
    assert ">https://jobs.enrriquez.com/x - 1-2</a>" in pages.build(tmp_path / "c")["research/ai-bias/index.html"]


def test_one_typeset_title_in_h1_title_og_json_ld_and_feed(tmp_path):
    title = "Don't trust \"75%\" - it's a 2012 claim"
    curly = "Don’t trust “75%” – it’s a 2012 claim"
    research_site(tmp_path, {"ai-bias.md": BIAS.replace("title: AI screening and bias", f"title: '{title.replace(chr(39), chr(39) * 2)}'")})
    pages.write(tmp_path)
    html = (tmp_path / "docs" / "research" / "ai-bias" / "index.html").read_text(encoding="utf-8")
    head = Head(html)
    assert head.text["title"] == [curly] and head.meta("og:title") == curly
    assert f"<h1>{curly}</h1>" in html.replace("&quot;", '"')
    graph = json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))["@graph"]
    assert [n["headline"] for n in graph if n["@type"] == "Article"] == [curly]
    feed = ET.parse(tmp_path / "docs" / "research" / "feed.xml").getroot()
    assert curly in [e.findtext("{http://www.w3.org/2005/Atom}title") for e in feed.iter("{http://www.w3.org/2005/Atom}entry")]


def test_heading_ids_come_from_the_source_text_not_the_curly_text(tmp_path):
    folder = research_site(tmp_path, body("[Down](#dont-panic---yet).\n\n## Don't panic - yet\n\nMore."))
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert '<h2 id="dont-panic---yet">Don’t panic – yet</h2>' in html
    ids = {a["id"] for t, a in Head(html).tags if t == "h2" and "id" in a}
    assert ids == anchors(folder / "ai-bias.md") == {"what-was-measured", "dont-panic---yet"}


def test_lints_read_the_source_as_written(tmp_path):
    # an uncited: snippet w/ a straight ' still matches its sentence; the tokens the lints walk keep ' and -
    own = {"ai-bias.md": BIAS.replace("status: published", "status: published\nuncited:\n  - our team's own test")
           .replace("Text.", "In our team's own test - 3 in 10 parsers failed.")}
    folder = research_site(tmp_path, own)
    assert "In our team’s own test – 3 in 10" in pages.build(tmp_path)["research/ai-bias/index.html"]
    src = pages.Source(folder / "ai-bias.md", tmp_path, [])
    text = "".join(c.content for t in src.tokens if t.type == "inline" for c in t.children or [])
    assert "team's own test - 3" in text and src.head["title"] == "AI screening and bias"


def test_review_files_and_registry_are_not_built(tmp_path):
    research_site(tmp_path)
    assert not [k for k in pages.build(tmp_path) if "review" in k or "sources" in k]


def test_unused_entry_and_past_recheck_warn_but_build(tmp_path):
    research_site(tmp_path, registry=REGISTRY.replace("2999-01-01", "2020-01-01") + """- id: spare
  type: web
  org: Someone
  year: 2020
  title: Unused
  url: https://example.org/
  evidence: survey
  checked: 2026-09-29
""")
    warnings = []
    assert "research/ats-myth/index.html" in pages.build(tmp_path, warnings)
    assert "app/web/research/sources.yml:28: eeoc-2023: recheck_by 2020-01-01 has passed - check it again" in warnings
    assert "app/web/research/sources.yml:29: spare is not cited by any page" in warnings


def test_entry_cited_only_by_a_draft_is_not_unused_and_drafts_skip_citation_checks(tmp_path):
    draft = SOURCES["next-one.md"] + "\nCited [@spare] and [@missing], 40% uncited.\n"
    research_site(tmp_path, {"next-one.md": draft}, registry=REGISTRY + """- id: spare
  type: web
  org: Someone
  year: 2020
  title: Unused
  url: https://example.org/
  evidence: survey
  checked: 2026-09-29
""")
    warnings = []
    pages.build(tmp_path, warnings)
    assert not [w for w in warnings if "not cited" in w]


ENTRY = """- id: x
  type: article
  authors: ["Smith, Ann"]
  year: 2020
  title: T
  venue: V
  doi: 10.1000/abc
  evidence: survey
  checked: 2026-09-29
"""


@pytest.mark.parametrize("registry, problem", [
    (ENTRY.replace("  venue: V\n", ""), "sources.yml:1: x: needs venue (type article)"),
    (ENTRY.replace("  title: T\n", ""), "sources.yml:1: x: needs title"),
    (ENTRY.replace("  checked: 2026-09-29\n", ""), "sources.yml:1: x: needs checked"),
    (ENTRY.replace('  authors: ["Smith, Ann"]\n', ""), "sources.yml:1: x: needs authors or org"),
    (ENTRY.replace('"Smith, Ann"', '"Ann Smith"'), "sources.yml:3: x: authors must be a list of 'Surname, Given'"),
    (ENTRY.replace("  doi: 10.1000/abc\n", ""), "sources.yml:1: x: needs doi or url"),
    (ENTRY.replace("10.1000/abc", "https://doi.org/10.1000/abc"), "sources.yml:7: x: doi must look like 10.1234/abc"),
    (ENTRY.replace("10.1000/abc", "10.12/abc"), "sources.yml:7: x: doi must look like"),
    (ENTRY + "  url: http://example.org/\n", "sources.yml:10: x: url must start with https://"),
    (ENTRY.replace("evidence: survey", "evidence: strong"), "sources.yml:8: x: evidence must be one of"),
    (ENTRY.replace("type: article", "type: blog"), "sources.yml:2: x: type must be one of"),
    (ENTRY.replace("year: 2020", "year: twenty"), "sources.yml:4: x: year must be a 4-digit number"),
    (ENTRY.replace("2026-09-29", "2026-02-30"), "sources.yml:9: x: date must be YYYY-MM-DD"),
    (ENTRY.replace("2026-09-29", "2999-01-01"), "sources.yml:9: x: checked 2999-01-01 is in the future"),
    (ENTRY + "  preprint: maybe\n", "sources.yml:10: x: preprint must be true or false"),
    (ENTRY + "  pages: 12\n", "sources.yml:10: x: unknown key 'pages'"),
    (ENTRY + "  doi: 10.1000/b\n", "duplicate key 'doi'"),
    (ENTRY + ENTRY, "sources.yml:10: x: id used twice (first at line 1)"),
    (ENTRY.replace("id: x", "id: Smith_2020"), "sources.yml:1: id must be lower-case words"),
    ("id: x\n", "sources.yml:1: must be a list of entries"),
    ("""- id: law-x
  type: law
  org: State
  year: 2023
  title: A law
  url: https://example.org/law
  evidence: law
  checked: 2026-09-29
""", "sources.yml:1: law-x: needs recheck_by (type law)"),
])
def test_registry_problems_are_reported_with_line(tmp_path, registry, problem):
    research_site(tmp_path, registry=registry)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


@pytest.mark.parametrize("snippet", [
    "Callbacks fell 36% for some names.",
    "About 12 percent heard back.",
    "The gap was 2.1 points on a 24% base.",
    "A gap of 3 percentage points.",
    "One in five employers said so.",
    "Only 4 out of 10 applicants got a call.",
    "The sample was small (n = 200).",
    "About a third of firms did.",
    "Two-thirds of recruiters agreed.",
    "One fifth of firms did most of it.",
    "Smith et al. found it. Then 40% did. [@quillian-2017, p. 3] Next sentence has 5% too.",
    "Over 3/4 of employers found one.",
    "About half of recruiters agreed.",
    "They were twice as likely to be called.",
    "Callbacks were 1.5 times higher.",
    "The firm screened 83,000 applications.",
    "It got 12000 replies.",
    "Some 2 million people applied.",
])
def test_statistic_without_citation_is_an_error(tmp_path, snippet):
    research_site(tmp_path, body(snippet))
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert "ai-bias.md:11: statistic" in str(e.value) and "without a citation" in str(e.value)


@pytest.mark.parametrize("snippet", [
    "Callbacks fell 36% for some names [@quillian-2017].",
    "Callbacks fell 36% for some names. [@quillian-2017]",
    "Smith et al. found a 36% gap [@quillian-2017, p. 12]. Then nothing.",
    "Then 40% did. [@quillian-2017, p. 3] Next one, see p. 4, has no number. E.g. this.",
    "As Quillian et al. (p. 4) put it, 36% fewer calls [@quillian-2017].",
    "Run `grep 50%` to see it.",
    "In 2021 three firms did.",
    "On 2026-10-03 and 10/3/2026, open 24/7, in the first half of 2024, three times a week.",
    "## Twice as likely, 3/4 of them, 83,000 calls\n\nThe text below cites [@quillian-2017].",
])
def test_cited_or_code_or_plain_numbers_pass(tmp_path, snippet):
    research_site(tmp_path, body(snippet))
    assert "research/ai-bias/index.html" in pages.build(tmp_path)


def test_a_later_citation_in_the_paragraph_covers_the_statistics_before_it(tmp_path):
    run = "Calls fell 36%. Then 5% more fell. Both came from one audit [@quillian-2017]."
    research_site(tmp_path, body(run + " Two [@quillian-2017]. Other [@kline-2021]. Three [@quillian-2017]."))
    assert "research/ai-bias/index.html" in pages.build(tmp_path)
    research_site(tmp_path / "b", body("Calls fell 36%.\n\nThe next paragraph cites [@quillian-2017]."))
    with pytest.raises(pages.SourceError, match="ai-bias.md:11: statistic '36%'") as e:
        pages.build(tmp_path / "b")
    assert "in 3 sentences in a row" not in str(e.value)


def test_table_row_cites_from_any_cell_and_uncited_snippets_pass(tmp_path):
    table = "| Finding | Source |\n|---|---|\n| 36% fewer calls | [@quillian-2017] |"
    research_site(tmp_path, body(table))
    assert "research/ai-bias/index.html" in pages.build(tmp_path)
    research_site(tmp_path / "b", body("| Finding | Source |\n|---|---|\n| 36% fewer calls | none |"))
    with pytest.raises(pages.SourceError, match="ai-bias.md:13: statistic '36%'"):
        pages.build(tmp_path / "b")
    own = {"ai-bias.md": BIAS.replace("status: published", "status: published\nuncited:\n  - our own test")
           .replace("Text.", "In our own test 3 in 10 parsers failed.")}
    research_site(tmp_path / "c", own)
    assert "research/ai-bias/index.html" in pages.build(tmp_path / "c")


@pytest.mark.parametrize("extra, problem", [
    (body("Gap [@nobody]."), "ai-bias.md:11: [@nobody] is not in app/web/research/sources.yml"),
    (body("Gap [@Bad Id]."), "ai-bias.md:11: citation '[@Bad Id]'"),
    (body("Gap [@quillian-2017; nope]."), "citation '[@quillian-2017; nope]'"),
    (body("Gap [@quillian-2017].\n\n## Sources"), "ai-bias.md:13: heading id 'sources' is the citation list's"),
    (body("One [@quillian-2017]. Two [@quillian-2017]. Three [@quillian-2017]."),
     "ai-bias.md:11: [@quillian-2017] cited in 3 sentences in a row - cite it once, at the end of the run"),
    ({"ai-bias.md": BIAS.replace("status: published", "status: published\nuncited: our test")}, "uncited must be a list"),
])
def test_citation_problems_are_reported_with_file_and_line(tmp_path, extra, problem):
    research_site(tmp_path, extra)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


@pytest.mark.parametrize("review, problem", [
    (None, "ai-bias.md:1: published page needs an adversarial review in app/web/research/reviews/ai-bias.md"),
    ("---\nreviewed: 2026-09-30\nverdict: revise\n---\n", "reviews/ai-bias.md:3: verdict is 'revise'"),
    ("---\nreviewed: 2026-09-01\nverdict: publish\n---\n", "reviews/ai-bias.md:2: reviewed 2026-09-01 is before the page's modified 2026-09-10"),
    ("---\nverdict: publish\n---\n", "reviews/ai-bias.md:2: needs reviewed:"),
    ("---\nreviewed: 2026-09-31\nverdict: publish\n---\n", "reviews/ai-bias.md:2: date must be YYYY-MM-DD"),
    ("---\nreviewed: 2026-09-30\nverdict: publish\nscore: 9\n---\n", "reviews/ai-bias.md:4: unknown header key 'score'"),
    ("No header.\n", "reviews/ai-bias.md:1: needs a YAML header"),
])
def test_review_gate(tmp_path, review, problem):
    research_site(tmp_path, reviews={"ai-bias.md": review})
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


def test_review_same_day_as_modified_passes_and_orphan_review_warns(tmp_path):
    folder = research_site(tmp_path, reviews={"ai-bias.md": "---\nreviewed: 2026-09-10\nverdict: publish\nreviewer: fresh AI session\n---\n",
                                              "gone.md": "---\nreviewed: 2026-09-10\nverdict: publish\n---\n"})
    warnings = []
    assert "research/ai-bias/index.html" in pages.build(tmp_path, warnings)
    assert "app/web/research/reviews/gone.md:1: review of a page that doesn't exist" in warnings
    # drafts need no review
    assert not (folder / "reviews" / "next-one.md").exists()



# --- hub, JSON-LD, sitemap lastmod ---

def test_three_dots_become_the_ellipsis_character_but_code_keeps_them(tmp_path):
    # U+2026 is in the font subset (assets.UNICODES); three periods read as three periods
    assert pages.typeset("A, B ... AA, AB ...") == "A, B … AA, AB …"
    research_site(tmp_path, body("Letters A, B ... AA and `a...b`."))
    assert 'Letters A, B … AA and <code translate="no">a...b</code>.' in pages.build(tmp_path)["research/ai-bias/index.html"]


def test_code_and_the_apps_name_stay_as_written_when_a_browser_translates_the_page(tmp_path):
    research_site(tmp_path, body("Run `uv run x`; CEZ Job Finder does it.\n\n```\ncurl x | bash\n```"))
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert '<code translate="no">uv run x</code>; <span translate="no">CEZ Job Finder</span> does it.' in html
    assert '<pre><code translate="no">curl x | bash\n</code></pre>' in html
    # a heading keeps the span on the page and in On this page; ids + the table label read the plain text
    research_site(tmp_path / "b", body("A.\n\n## How CEZ Job Finder uses this\n\nB.\n\n## Three\n\nC."))
    html = pages.build(tmp_path / "b")["research/ai-bias/index.html"]
    named = 'How <span translate="no">CEZ Job Finder</span> uses this'
    assert f'<h2 id="how-cez-job-finder-uses-this">{named}</h2>' in html
    assert html.count(f'<li><a href="#how-cez-job-finder-uses-this">{named}</a></li>') == 2  # both lists
    assert 'install <span translate="no">CEZ Job Finder</span> on Windows or Mac' in html


def test_body_may_link_the_apps_code_and_the_authors_site(tmp_path):
    # About's contact + code are links, not addresses to copy (look-alikes: the problem table above)
    research_site(tmp_path, {"ai-bias.md": SOURCES["ai-bias.md"].replace(
        "See [the myth](ats-myth.md).", "See [the code](https://github.com/cezkid/jobs) or [write](https://www.enrriquez.com/#contact).")})
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    assert '<a href="https://github.com/cezkid/jobs">the code</a>' in html
    assert '<a href="https://www.enrriquez.com/#contact">write</a>' in html

def test_hub_lists_articles_newest_first_by_title_and_breadcrumbs_link_it(tmp_path):
    research_site(tmp_path)
    built = pages.build(tmp_path)
    hub = built["research/index.html"]
    # each title a heading holding its link: screen readers jump article to article
    listed = re.findall(r'<li><h2><a href="([^"]+)">([^<]+)</a></h2>', hub.split('<ul class="list">')[1])
    assert listed == [("/research/ai-bias/", "AI screening and bias"), ("/research/ats-myth/", "Do resume robots reject you?")]
    assert '<a href="/research/methods/">methods</a>' in hub and 'class="meta"' not in hub
    assert Head(hub).meta("og:type") == "website"
    assert ('<li><a href="/">Home</a></li><li><a href="/research/">Research</a></li>'
            '<li aria-current="page">Do resume robots reject you?</li>') in built["research/ats-myth/index.html"]
    assert '<li><a href="/">Home</a></li><li aria-current="page">Research</li>' in hub


def test_wide_screen_second_column_hub_labels_from_methods_and_about_sections(tmp_path):
    table = ("\n## What the labels mean\n\n| In the text | In the Sources list | What it means |\n|---|---|---|\n"
             "| Big study | Big study (pooled) | Many studies pooled |\n| Big study | Big study (field) | Real applications sent |\n"
             "| Law | Law | The law's own text |\n")
    research_site(tmp_path, {"methods.md": SOURCES["methods.md"] + table,
                             "about.md": SOURCES["about.md"].replace("## Work", "Intro line.\n\n## Work\n\nWork line.")})
    built = pages.build(tmp_path)
    hub, about = built["research/index.html"], built["about/index.html"]
    side = hub.split('<div class="side labels">')[1].split("</div>")[0]
    assert "<dt>Big study</dt><dd>Many studies pooled, or real applications sent</dd>" in side
    assert "<dt>Law</dt><dd>The law’s own text</dd>" in side
    assert '<a href="/research/methods/#what-the-labels-mean">How we research</a>' in side
    assert side.lstrip("\n").startswith("<h2>Evidence labels</h2>")
    # the list right after the page column (a phone shows the articles under the h1), then the labels column
    assert hub.index('class="page"') < hub.index('<ul class="list">') < hub.index('class="side labels"') < hub.index("</main>")
    # about: text before the first h2 stays in the page column, the h2 sections go to the second column
    page, rest = about.split('<div class="side">')
    assert "Intro line." in page and '<h2 id="work">Work</h2>' not in page
    assert rest.index('<h2 id="work">Work</h2>') < rest.index("Work line.") < rest.index("</main>")
    # no labels table on methods: no labels column
    research_site(tmp_path / "b")
    assert "labels" not in pages.build(tmp_path / "b")["research/index.html"].split("<body>")[1]


def test_one_breadcrumb_name_per_url(tmp_path):
    # D22: /research/ is named by the hub's own title in every crumb + BreadcrumbList, not "Research" on articles
    research_site(tmp_path, {"index.md": SOURCES["index.md"].replace("title: Research\n", "title: Research on X\n")})
    built = pages.build(tmp_path)
    assert ("/research/", "Research on X") in crumbs(built["research/ats-myth/index.html"])
    found = [crumbs(html) for name, html in built.items() if name.endswith(".html")]
    assert crumb_clashes(found) == {}
    # the check trips on the audited state: an article naming the hub "Research"
    assert crumb_clashes(found + [{("/research/", "Research")}]) == {"/research/": ["Research", "Research on X"]}


def test_hub_intro_first_line_under_h1_method_lines_beside(tmp_path):
    # A16: the hub's first paragraph stays under the h1; the rest goes to the second column, before the labels;
    # the articles come before both, so a phone reaches them first
    research_site(tmp_path, {"index.md": SOURCES["index.md"].rstrip("\n") + "\n\nSecond line.\n"})
    hub = pages.build(tmp_path)["research/index.html"]
    page, side = hub.split('<div class="side intro">')
    assert "<p>Second line.</p>" in side.split("</div>")[0] and "Second line." not in page
    assert "<h1>" in page and page.count("<p>") >= 1
    assert hub.index('<ul class="list">') < hub.index('class="side intro"')


def test_no_article_no_hub_and_an_article_needs_the_hub_intro(tmp_path):
    research_site(tmp_path, {"ats-myth.md": None, "ai-bias.md": None})
    built = pages.build(tmp_path)
    assert "research/index.html" not in built and "research/methods/index.html" in built
    # Research crumb stays text w/o a hub, and out of the JSON-LD (it must point at a page)
    assert "<li>Research</li>" in built["research/methods/index.html"]
    assert '"name":"Research"' not in built["research/methods/index.html"]
    research_site(tmp_path / "b", {"index.md": None})
    with pytest.raises(pages.SourceError, match="index.md:1: the hub /research/ lists the articles"):
        pages.build(tmp_path / "b")


def test_structured_data_and_sitemap_lastmod(tmp_path):
    research_site(tmp_path)
    pages.write(tmp_path)
    docs = tmp_path / "docs"
    assert structured_data(docs, "https://jobs.enrriquez.com/") == []
    sitemap = (docs / "sitemap.xml").read_text(encoding="utf-8")
    assert "<url><loc>https://jobs.enrriquez.com/research/ats-myth/</loc><lastmod>2026-09-20</lastmod></url>" in sitemap
    assert "<url><loc>https://jobs.enrriquez.com/research/ai-bias/</loc><lastmod>2026-09-10</lastmod></url>" in sitemap
    # hand-written pages: no lastmod (Google drops lastmod for a site once it's seen wrong)
    assert "<url><loc>https://jobs.enrriquez.com/</loc></url>" in sitemap
    # C7: about = about.md modified (== ProfilePage dateModified); hub = max(index.md, newest article modified)
    assert "<url><loc>https://jobs.enrriquez.com/about/</loc><lastmod>2026-09-01</lastmod></url>" in sitemap
    assert "<url><loc>https://jobs.enrriquez.com/research/</loc><lastmod>2026-09-20</lastmod></url>" in sitemap
    about = (docs / "about" / "index.html").read_text(encoding="utf-8")
    assert '"sameAs":["https://github.com/cezkid","https://www.enrriquez.com/"]' in about and '"@type":"ProfilePage"' in about
    assert '"dateModified":"2026-09-01"' in about


def test_hub_lastmod_is_the_newest_of_index_and_articles(tmp_path):
    research_site(tmp_path, {"index.md": SOURCES["index.md"].replace("status: published", "modified: 2026-10-02\nstatus: published")})
    assert "<loc>https://jobs.enrriquez.com/research/</loc><lastmod>2026-10-02</lastmod>" in pages.build(tmp_path)["sitemap.xml"]


DATA = {"counts.md": """---
title: Counts of form questions
description: One row per form we read, how we counted, and the limits of the count.
published: 2026-09-15
status: published
data: counts.csv
---
Our count, see [the myth](ats-myth.md).
""", "counts.csv": "form,field,asks\n1,Sales,1\n2,Law,0\n3,Sales,1\n"}


def test_data_page_ships_its_file_with_a_dataset_and_stays_off_the_hub_and_feed(tmp_path):
    research_site(tmp_path, DATA)
    built = pages.build(tmp_path)
    assert built["research/counts/counts.csv"] == DATA["counts.csv"]
    html = built["research/counts/index.html"]
    assert ('<p class="download"><a href="/research/counts/counts.csv" download>Download the data</a>'
            " (CSV, 3 rows, 1 KB).</p>") in html and "License" not in html
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html).group(1))
    dataset = data["@graph"][0]
    assert dataset["@type"] == "Dataset" and dataset["name"] == "Counts of form questions"
    assert dataset["variableMeasured"] == ["form", "field", "asks"] and "license" not in dataset
    assert dataset["distribution"] == [{"@type": "DataDownload", "encodingFormat": "text/csv",
                                        "contentUrl": "https://jobs.enrriquez.com/research/counts/counts.csv"}]
    assert '"@type":"Article"' not in html and "/research/counts/" not in built["research/index.html"] + built["research/feed.xml"]
    assert "https://jobs.enrriquez.com/research/counts/</loc><lastmod>2026-09-15<" in built["sitemap.xml"]
    pages.write(tmp_path)
    assert structured_data(tmp_path / "docs", "https://jobs.enrriquez.com/") == [] and pages.problems(tmp_path) == []
    (tmp_path / "docs" / "research" / "counts" / "counts.csv").unlink()
    assert structured_data(tmp_path / "docs", "https://jobs.enrriquez.com/") == [
        "research/counts/index.html: Dataset download ['https://jobs.enrriquez.com/research/counts/counts.csv'] is not a file on this site"]


def test_data_page_license_is_named_on_the_page_and_in_the_dataset(tmp_path):
    research_site(tmp_path, {**DATA, "counts.md": DATA["counts.md"].replace("data: counts.csv", "data: counts.csv\nlicense: CC BY 4.0")})
    html = pages.build(tmp_path)["research/counts/index.html"]
    assert ' License: <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>.</p>' in html
    assert '"license":"https://creativecommons.org/licenses/by/4.0/"' in html


@pytest.mark.parametrize("extra, problem", [
    ({"counts.md": DATA["counts.md"].replace("data: counts.csv", "data: other.csv")}, "counts.md:6: data must be counts.csv"),
    ({"counts.md": DATA["counts.md"]}, "counts.md:6: counts.csv not found next to the page"),
    ({**DATA, "counts.csv": "form,field\n1,Sales,1\n"}, "needs a header row, every row as wide as it"),
    ({**DATA, "counts.md": DATA["counts.md"].replace("data: counts.csv", "data: counts.csv\nlicense: MIT")}, "counts.md:7: license goes on a data page"),
    ({"ai-bias.md": SOURCES["ai-bias.md"].replace("status: published", "status: published\nlicense: CC BY 4.0")}, "license goes on a data page"),
])
def test_data_page_problems_are_reported_with_file_and_line(tmp_path, extra, problem):
    research_site(tmp_path, extra)
    with pytest.raises(pages.SourceError) as e:
        pages.build(tmp_path)
    assert problem in str(e.value)


def test_every_article_links_how_ai_is_used_under_the_byline_and_never_says_approved(tmp_path):
    # owner decision 5: a label + one link, never a claim of approval; not on the hub, about or methods
    research_site(tmp_path)
    built = pages.build(tmp_path)
    for name in "research/ats-myth/index.html", "research/ai-bias/index.html":
        html = built[name]
        note = re.search(r'<p class="meta">By [^\n]*?\. (How this was made: .*?)</p>', html)
        assert note and note.group(1) == 'How this was made: <a href="/research/methods/#how-is-ai-used">How we research</a>', name
        assert "approved" not in html.lower()
    assert "how-is-ai-used" not in built["about/index.html"] + built["research/index.html"]
    assert 'id="how-is-ai-used"' in built["research/methods/index.html"]



def test_atom_feed_lists_published_articles_and_pages_link_it(tmp_path):
    research_site(tmp_path)
    pages.write(tmp_path)
    docs, home = tmp_path / "docs", "https://jobs.enrriquez.com/"
    atom = "{http://www.w3.org/2005/Atom}"
    feed = ET.parse(docs / "research" / "feed.xml").getroot()
    stamp = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")  # RFC 3339 date-time
    assert feed.tag == f"{atom}feed"
    for tag in "title", "id", "updated":
        assert (feed.findtext(f"{atom}{tag}") or "").strip(), tag
    assert stamp.match(feed.findtext(f"{atom}updated")) and feed.findtext(f"{atom}updated") == "2026-09-20T00:00:00Z"
    assert feed.findtext(f"{atom}author/{atom}name") == pages.AUTHOR
    links = {a.get("rel"): a.get("href") for a in feed.findall(f"{atom}link")}
    assert links == {"self": home + "research/feed.xml", "alternate": home + "research/"}
    entries = feed.findall(f"{atom}entry")
    # entries == published articles (draft, about, methods, hub left out), newest first
    assert [e.findtext(f"{atom}id") for e in entries] == [home + "research/ai-bias/", home + "research/ats-myth/"]
    for e in entries:
        for tag in "title", "id", "updated", "published", "summary":
            assert (e.findtext(f"{atom}{tag}") or "").strip(), tag
        assert stamp.match(e.findtext(f"{atom}updated")) and stamp.match(e.findtext(f"{atom}published"))
        assert e.find(f"{atom}link").get("href") == e.findtext(f"{atom}id")
        assert (docs / target(urlsplit(e.findtext(f"{atom}id")).path)).is_file()
    assert entries[1].findtext(f"{atom}published") == "2026-09-01T00:00:00Z"
    assert entries[1].findtext(f"{atom}title") == "Do resume robots reject you?"
    # autodiscovery: root-relative, on the hub + articles only
    for name in "research/index.html", "research/ats-myth/index.html", "research/ai-bias/index.html":
        alt = Head((docs / name).read_text(encoding="utf-8")).links("alternate")
        assert [(a["type"], a["href"]) for a in alt] == [("application/atom+xml", "/research/feed.xml")], name
    for name in "research/methods/index.html", "about/index.html":
        assert Head((docs / name).read_text(encoding="utf-8")).links("alternate") == [], name
    # no article => no hub, no feed
    research_site(tmp_path / "b", {"ats-myth.md": None, "ai-bias.md": None})
    assert "research/feed.xml" not in pages.build(tmp_path / "b")

@pytest.mark.parametrize("old, new, problem", [
    ('"dateModified":"2026-09-20"', '"dateModified":"2026-09-21"', "Article dates"),
    ('"author":{"@type":"Person","@id":"https://jobs.enrriquez.com/about/#person"',
     '"author":{"@type":"Person","@id":"https://jobs.enrriquez.com/me"', "author @id"),
    ('"item":"https://jobs.enrriquez.com/research/"', '"item":"https://jobs.enrriquez.com/nope/"', "is not a page"),
    ('"image":"https://jobs.enrriquez.com/og-research.png', '"image":"https://jobs.enrriquez.com/x.png', "image != og:image"),
    ("</script>", "</script>\n<script type=\"application/ld+json\">{}</script>", "2 JSON-LD blocks"),
])
def test_structured_data_check_catches_breaks(tmp_path, old, new, problem):
    research_site(tmp_path)
    pages.write(tmp_path)
    path = tmp_path / "docs" / "research" / "ats-myth" / "index.html"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split("</head>", 1)
    assert old in head
    path.write_text(head.replace(old, new, 1) + "</head>" + rest, encoding="utf-8")
    assert any(problem in p for p in structured_data(tmp_path / "docs", "https://jobs.enrriquez.com/"))


def test_sitemap_lastmod_must_match(tmp_path):
    research_site(tmp_path)
    pages.write(tmp_path)
    path = tmp_path / "docs" / "sitemap.xml"
    path.write_text(path.read_text(encoding="utf-8").replace("2026-09-20", "2026-09-19"), encoding="utf-8")
    assert any("sitemap lastmod" in p for p in structured_data(tmp_path / "docs", "https://jobs.enrriquez.com/"))


def test_json_ld_is_compact_utf8_and_cannot_end_its_script_block():
    block = pages.jsonld([{"name": "Café </script><b>"}])
    assert block == ('<script type="application/ld+json">{"@context":"https://schema.org",'
                     '"@graph":[{"name":"Café \\u003c/script>\\u003cb>"}]}</script>')


# --- --links: every source real? Network faked w/ httpx.MockTransport ---

import httpx  # noqa: E402

TITLE = "Meta-analysis of field experiments shows no change in racial discrimination in hiring over time"
ARXIV = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2311.09735v3</id>
<published>2023-11-16T10:00:00Z</published><title>GEO: Generative Engine
  Optimization</title></entry></feed>"""
ARXIV_ERROR = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#incorrect_id_format_for_x</id>
<title>Error</title></entry></feed>"""
LINKS_REGISTRY = REGISTRY + """- id: geo-2024
  type: article
  authors: ["Aggarwal, Pranjal", "Murahari, Vishvak"]
  year: 2024
  title: "GEO: generative engine optimization"
  venue: KDD
  url: https://arxiv.org/abs/2311.09735
  evidence: lab/LLM audit
  checked: 2026-09-29
"""


def links_client(routes):
    """routes: URL -> (status, body) | Exception; anything not listed answers 200."""
    seen = []

    def handler(request):
        url = str(request.url)
        seen.append(url)
        answer = routes.get(url, (200, ""))
        if isinstance(answer, Exception):
            raise answer
        status, body = answer
        if isinstance(body, dict):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=body)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    client.seen = seen
    return client


def crossref(title=TITLE, year=2017):
    return (200, {"message": {"title": [f"<i>{title}</i>"], "issued": {"date-parts": [[year, 9, 12]]}}})


HANDLE = "https://doi.org/api/handles/10.1073/pnas.1706255114"
CROSSREF = "https://api.crossref.org/works/10.1073/pnas.1706255114"
ARXIV_API = "https://export.arxiv.org/api/query?id_list=2311.09735"


def run_links(tmp_path, routes, registry=LINKS_REGISTRY):
    folder = research_site(tmp_path, registry=registry)
    pauses = []
    with links_client(routes) as client:
        errors, warnings = [], []
        reg = pages.Registry(tmp_path, errors, warnings)
        results = pages.check_links(reg, client, pause=pauses.append)
        seen = client.seen
    return [(ref, level, what) for ref, _, level, what in results], seen, pauses, folder


def test_links_real_sources_pass_and_arxiv_page_is_checked_through_its_api(tmp_path):
    routes = {HANDLE: (200, {"responseCode": 1}), CROSSREF: crossref(), ARXIV_API: (200, ARXIV)}
    results, seen, _, _ = run_links(tmp_path, routes)
    assert {level for _, level, _ in results} == {"ok"}
    assert [ref for ref, _, _ in results] == ["quillian-2017", "kline-2021", "eeoc-2023", "geo-2024"]
    assert "https://arxiv.org/abs/2311.09735" not in seen  # the page itself isn't fetched


@pytest.mark.parametrize("routes, problem", [
    ({HANDLE: (404, {"responseCode": 100})}, "doi 10.1073/pnas.1706255114 does not exist"),
    ({CROSSREF: crossref(title="Deep learning for protein folding")}, "names another work"),
    ({CROSSREF: crossref(year=2012)}, "(Crossref) says 2012, entry says 2017"),
    ({ARXIV_API: (200, ARXIV_ERROR)}, "arXiv 2311.09735 does not exist"),
    ({ARXIV_API: (200, '<feed xmlns="http://www.w3.org/2005/Atom"></feed>')}, "arXiv 2311.09735 does not exist"),
    ({ARXIV_API: (200, ARXIV.replace("GEO: Generative Engine\n  Optimization", "Attention is all you need"))},
     "arXiv 2311.09735 names another work"),
    ({"https://www.nber.org/papers/w29053": (404, "")}, "https://www.nber.org/papers/w29053 answered 404"),
    ({"https://www.eeoc.gov/ai": (410, "")}, "https://www.eeoc.gov/ai answered 410"),
])
def test_links_invented_or_dead_sources_are_broken(tmp_path, routes, problem):
    base = {HANDLE: (200, {"responseCode": 1}), CROSSREF: crossref(), ARXIV_API: (200, ARXIV)}
    results, _, _, _ = run_links(tmp_path, {**base, **routes})
    broken = [what for _, level, what in results if level == "broken"]
    assert len(broken) == 1 and problem in broken[0]


@pytest.mark.parametrize("routes, problem", [
    ({"https://www.nber.org/papers/w29053": (403, "")}, "answered 403 - open it in a browser"),
    ({"https://www.nber.org/papers/w29053": (401, "")}, "answered 401"),
    ({"https://www.eeoc.gov/ai": (429, "")}, "answered 429"),
    ({"https://www.eeoc.gov/ai": (503, "")}, "answered 503"),
    ({"https://www.eeoc.gov/ai": httpx.ConnectTimeout("slow")}, "no answer (ConnectTimeout)"),
    ({CROSSREF: (404, "")}, "Crossref has no record (registered elsewhere, e.g. DataCite)"),
    ({HANDLE: (500, "")}, "doi.org answered 500"),
    ({ARXIV_API: (429, "Rate exceeded.")}, "arXiv 2311.09735: API answered 429"),
])
def test_links_unclear_answers_are_left_to_check_by_hand(tmp_path, routes, problem):
    base = {HANDLE: (200, {"responseCode": 1}), CROSSREF: crossref(), ARXIV_API: (200, ARXIV)}
    results, _, _, _ = run_links(tmp_path, {**base, **routes})
    assert [level for _, level, what in results if problem in what] == ["check"]
    assert "broken" not in {level for _, level, _ in results}


def test_links_arxiv_doi_skips_crossref_and_arxiv_calls_are_spaced(tmp_path):
    second = LINKS_REGISTRY.replace("id: geo-2024", "id: geo-doi").replace(
        "url: https://arxiv.org/abs/2311.09735", "doi: 10.48550/arXiv.2311.09735")
    registry = LINKS_REGISTRY + second[len(REGISTRY):]
    routes = {HANDLE: (200, {"responseCode": 1}), CROSSREF: crossref(), ARXIV_API: (200, ARXIV)}
    results, seen, pauses, _ = run_links(tmp_path, routes, registry)
    assert {level for _, level, _ in results} == {"ok"}
    assert not any("crossref.org/works/10.48550" in url for url in seen)
    assert seen.count(ARXIV_API) == 2 and pauses == [pages.ARXIV_PAUSE]


def test_links_command_prints_file_line_and_exits_1_on_broken(tmp_path, capsys):
    research_site(tmp_path, registry=LINKS_REGISTRY)
    routes = {HANDLE: (404, {"responseCode": 100}), ARXIV_API: (200, ARXIV),
              "https://www.eeoc.gov/ai": (403, "")}
    with links_client(routes) as client:
        assert pages.links(tmp_path, client=client) == 1
    out = capsys.readouterr().out.splitlines()
    assert "app/web/research/sources.yml:1: quillian-2017: BROKEN: doi 10.1073/pnas.1706255114 does not exist (doi.org)" in out
    assert "app/web/research/sources.yml:20: eeoc-2023: check by hand: https://www.eeoc.gov/ai answered 403 - open it in a browser" in out
    assert out[-1] == "4 sources: 1 broken, 1 to check by hand, 2 fine"


def test_links_reads_the_repo_sources_from_any_folder_and_a_missing_file_fails(tmp_path, monkeypatch, capsys):
    # default was read from the current folder => run elsewhere, "no sources to check", exit 0
    seen = []
    monkeypatch.setattr(pages, "links", lambda root, path=None: seen.append(path) or 0)
    monkeypatch.chdir(tmp_path)
    for argv, want in ((["--links"], None), (["--links", "mine.yml"], tmp_path.resolve() / "mine.yml")):
        monkeypatch.setattr("sys.argv", ["pages.py", *argv])
        with pytest.raises(SystemExit):
            pages.main()
        assert seen.pop() == want
    monkeypatch.undo()
    assert pages.links(tmp_path, tmp_path / "nope.yml") == 1
    assert "nope.yml: no such file" in capsys.readouterr().out


def test_links_registry_problems_stop_before_any_request(tmp_path, capsys):
    research_site(tmp_path, registry="- id: x\n  type: blog\n")
    with links_client({}) as client:
        assert pages.links(tmp_path, client=client) == 1
        assert client.seen == []
    assert "sources.yml:2: x: type must be one of" in capsys.readouterr().out


def test_every_evidence_label_is_in_the_research_guide_and_the_methods_page():
    guide = (cfg.APP / "docs" / "research.md").read_text(encoding="utf-8")
    methods = (cfg.APP / "web" / "research" / "methods.md").read_text(encoding="utf-8")
    for label, words in pages.EVIDENCE.items():
        assert f"| `{label}` |" in guide, label
        assert f"| {words} |" in methods, words


def test_toc_script_fits_its_budget():
    assert len(pages.TOC_JS.encode()) <= 400
    assert "</" not in pages.TOC_JS and 'aria-current","true"' in pages.TOC_JS


def test_cite_script_fits_its_budget_and_keeps_the_jump_for_modified_clicks():
    assert len(pages.CITE_JS.encode()) <= 1000
    assert "</" not in pages.CITE_JS and "showModal()" in pages.CITE_JS and "autofocus" in pages.CITE_JS
    assert all(key in pages.CITE_JS for key in ("e.button", "e.ctrlKey", "e.metaKey", "e.shiftKey", "e.altKey"))


TOP = """**What to do**

- First step.
- Second step.

**What the evidence says**

- A finding.

## A question?

Answer.

## Another one?

More.

## What helps

- First step, longer.

## What was measured

Text.
"""


def test_article_first_screen_answer_byline_notes_then_on_this_page(tmp_path):
    # a phone's first screen: h1, the answer in a sentence (the description), the byline line, What to do; On this
    # page right after that note (owner 2026-10-07), then the evidence note
    head = SOURCES["ai-bias.md"].split("---\n")[1]
    research_site(tmp_path, {"ai-bias.md": f"---\n{head}---\n{TOP}"})
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    article = html.split('<article class="page">')[1]
    order = ["<h1>", '<p class="answer">What tests of AI resume screeners found.</p>', '<p class="meta">By ',
             '<p class="box"><strong>What to do</strong></p>', '<ul class="box-list">\n<li>First step.</li>',
             '<p class="box-more"><a href="#what-helps">More in What helps</a></p>', '<nav class="toc-mini"',
             '<p class="box"><strong>What the evidence says</strong></p>', '<h2 id="a-question">']
    at = [article.index(part) for part in order]
    assert at == sorted(at)
    assert article.count('class="box"') == 2 and article.count('<ul class="box-list">') == 2
    # no What helps section: no link to it; a bold line inside a paragraph, or after the first heading, is no note
    top = TOP.replace("## What helps", "## Last one").replace("- A finding.", "- A **finding**.") + "\n**Not a note**\n\n- Item.\n"
    research_site(tmp_path / "b", {"ai-bias.md": f"---\n{head}---\n{top}"})
    html = pages.build(tmp_path / "b")["research/ai-bias/index.html"]
    assert "box-more" not in html.split("</style>")[1] and html.split("</style>")[1].count('class="box"') == 2
    # hub, about: no answer line
    built = pages.build(tmp_path)
    assert 'class="answer"' not in built["research/index.html"] + built["about/index.html"]


def test_keep_reading_picks_linked_pages_then_linking_pages_then_hub_order(tmp_path):
    def article(title, day, text):
        return f"---\ntitle: {title}\ndescription: {title} in a sentence.\npublished: 2026-09-{day}\nstatus: published\n---\n{text}\n"
    research_site(tmp_path, {
        "ai-bias.md": article("Bias", "10", "Links [a](gaps.md) and [b](laws.md#x).\n\n## What was measured\n\nText."),
        "gaps.md": article("Gaps", "11", "Nothing."),
        "laws.md": article("Laws", "12", "Nothing.\n\n## X\n\nY."),
        "age.md": article("Age", "13", "See [bias](ai-bias.md)."),
        "pay.md": article("Pay", "14", "Nothing."),
    })
    built = pages.build(tmp_path)
    more = built["research/ai-bias/index.html"].split('aria-label="Keep reading"')[1]
    picks = re.findall(r'<li><a href="(/research/[^"]+/)">', more)
    assert picks == ["/research/gaps/", "/research/laws/", "/research/age/"]  # out, out, in; 3 at most
    assert "<p>Gaps in a sentence.</p>" in more
    # a page linking nowhere and linked from nowhere: the next ones in hub order, wrapping round
    order = re.findall(r'<li><h2><a href="(/research/[^"]+/)">', built["research/index.html"])
    pay = re.findall(r'<li><a href="(/research/[^"]+/)">', built["research/pay/index.html"].split('aria-label="Keep reading"')[1])
    i = order.index("/research/pay/")
    assert pay == (order[i + 1:] + order[:i])[:3]


def test_articles_end_with_keep_reading_and_on_this_page_comes_before_the_article(tmp_path):
    third = SOURCES["ai-bias.md"].replace("AI screening and bias", "Third one").replace("2026-09-10", "2026-09-05").replace(
        "What tests of AI resume screeners found.", "A third page.")
    research_site(tmp_path, {"third.md": third.replace("## What was measured", "## One\n\nA.\n\n## Two\n\nB.\n\n## Three")})
    built = pages.build(tmp_path)
    for name in "ats-myth", "ai-bias", "third":
        html = built[f"research/{name}/index.html"]
        article = html.split('<article class="page">')[1].split("</article>")[0].rstrip()
        more = article[article.rindex('<nav class="more" aria-label="Keep reading">'):]
        assert more.endswith("</nav>"), name  # nothing after it in the article
        hrefs = re.findall(r'href="([^"]+)"', more)
        others = [h for h in hrefs if h.startswith("/research/") and h not in ("/research/", f"/research/{name}/")]
        assert len(others) == 2 and f"/research/{name}/" not in hrefs, (name, hrefs)
        assert "/research/" in hrefs and "/#install" in hrefs and "#main" in hrefs, name
        # source order: the wide-screen column first (after the article it was the 85th Tab stop, behind every
        # citation link); the h1 is still main's first heading (the list's label is a <p>)
        main = html.split('<main id="main" class="wrap">')[1].split("</main>")[0]
        assert re.search(r"<h[1-6]\b", main).group(0) == "<h1", name
        if '<nav class="toc"' in main:
            assert main.index('<nav class="toc" aria-label="On this page">') < main.index('<article class="page">'), name
            # narrow screens: the same list, closed, right under the byline; no ids repeated
            mini = main.split('<nav class="toc-mini" aria-label="Contents">')[1].split("</nav>")[0]
            assert main.index('class="meta"') < main.index('class="toc-mini"') < main.index("<h2")
            assert "<details>\n<summary>On this page</summary>" in mini
            assert re.findall(r'href="(#[^"]+)"', mini) == ["#" + i for i in re.findall(r'<h2 id="([^"]+)"', main)]
            # the section-in-view script: after the footer, once, in its 400 B budget (A23); none without a list
            assert html.count(f"<script>{pages.TOC_JS}</script>") == 1
            assert html.index("</footer>") < html.index(pages.TOC_JS)
        else:
            assert "<script>(" not in html, name
        ids = re.findall(r'\sid="([^"]+)"', html)
        assert len(ids) == len(set(ids)), name
    # related first: ai-bias links to ats-myth, so ats-myth leads though third comes next in hub order
    order = re.findall(r'<li><h2><a href="(/research/[^"]+/)">', built["research/index.html"])
    assert order.index("/research/third/") < order.index("/research/ats-myth/")
    ai = re.findall(r'href="(/research/[^"#]+/)"', built["research/ai-bias/index.html"].split('aria-label="Keep reading"')[1])
    assert ai[:2] == ["/research/ats-myth/", "/research/third/"]
    # each pick carries its one-line answer (the description)
    assert "<p>A third page.</p>" in built["research/ai-bias/index.html"].split('aria-label="Keep reading"')[1]


@pytest.mark.parametrize("title, html", [
    ("Is AI screening biased? What the studies show", 'Is AI screening biased? <span class="deck">What the studies show</span>'),
    ("Keep chats out of training: ChatGPT, Claude", 'Keep chats out of training: <span class="deck">ChatGPT, Claude</span>'),
    ("Do ATS reject 75%? Where: the number", 'Do ATS reject 75%? <span class="deck">Where: the number</span>'),
    ("Can employers tell if AI wrote it?", "Can employers tell if AI wrote it?"),
    ("How we research", "How we research"),
    ("Fish & chips: A <b>", 'Fish &amp; chips: <span class="deck">A &lt;b&gt;</span>'),
])
def test_two_part_title_splits_at_the_first_question_or_colon(title, html):
    assert pages.headline(title) == html


def test_split_title_keeps_its_text_in_the_h1_the_hub_and_the_headline(tmp_path):
    title = "Do resume robots reject you? What the studies show"
    research_site(tmp_path, {"ats-myth.md": SOURCES["ats-myth.md"].replace("Do resume robots reject you?", title)})
    built = pages.build(tmp_path)
    html = built["research/ats-myth/index.html"]
    h1 = re.search(r"<h1>(.*?)</h1>", html).group(1)
    assert '<span class="deck">What the studies show</span>' in h1
    assert re.sub(r"<[^>]+>", "", h1) == title == Head(html).text["title"][0]
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    article = next(n for n in ld["@graph"] if n["@type"] == "Article")
    assert article["headline"] == title
    item = re.search(r'<a href="/research/ats-myth/">(.*?)</a>', built["research/index.html"]).group(1)
    assert "deck" in item and re.sub(r"<[^>]+>", "", item) == title


BARS = "```bars\nWho got called, share of tests (Lab study) [@quillian-2017]\nGroup | Called\nWhite | 85.1% of tests\nBlack | 8.6% of tests\n```"


def test_bars_block_is_a_figure_with_caption_citation_and_a_real_table(tmp_path):
    research_site(tmp_path, body(BARS))
    html = pages.build(tmp_path)["research/ai-bias/index.html"]
    figure = html[html.index('<figure class="bars">'):html.index("</figure>")]
    assert '<figcaption>Who got called, share of tests <small>(Lab study; <a href="#src-quillian-2017">' in figure
    assert '<th scope="col">Group</th>' in figure and '<th scope="row">White</th>' in figure
    assert '<td>85.1% of tests<span class="bar" style="width:85.1%" aria-hidden="true"></span></td>' in figure
    assert 'role="region"' not in figure  # no scroll box: short, and the figure names it
    assert '<li id="src-quillian-2017">' in html  # the caption's citation reaches Sources


@pytest.mark.parametrize("values, widths", [
    (["99 of 143", "13 of 143"], [69.2, 9.1]),
    (["51%", "32%"], [51.0, 32.0]),
    (["0.3", "1.2"], [25.0, 100.0]),
    (["1,000", "500"], [100.0, 50.0]),
])
def test_bar_length_is_the_values_share_of_its_whole(values, widths):
    assert pages._bar_widths(values) == (widths, None)


@pytest.mark.parametrize("block, problem", [
    ("```bars\nCaption [@quillian-2017]\nGroup | Called\n```", "needs a caption line"),
    ("```bars\nCaption [@quillian-2017]\nGroup | Called\nA | 5\nB\n```", "needs a caption line"),
    ("```bars\nCaption [@quillian-2017]\nGroup | Called\nA | 5%\nB | 7\n```", "one kind per figure"),
    ("```bars\nCaption [@quillian-2017]\nGroup | Called\nA | about half\n```", "starts with a number"),
    ("```bars\nCaption [@quillian-2017]\nGroup | Called\nA | 150%\n```", "larger than its whole"),
    ("```bars\nCalls fell\nGroup | Called\nA | 36%\n```", "statistic '36%' without a citation"),
])
def test_bars_problems_are_reported_with_file_and_line(tmp_path, block, problem):
    research_site(tmp_path, body(block))
    # block problems at the fence's first line; an uncited statistic at its own row
    line = 14 if "statistic" in problem else 11
    with pytest.raises(pages.SourceError, match=f"ai-bias.md:{line}: .*{problem}"):
        pages.build(tmp_path)
