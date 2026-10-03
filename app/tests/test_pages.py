"""app/web/pages.py: builds the site's generated files, reports + prunes stale ones.

Runs on a throwaway site in tmp_path - never app/web/research or the real docs/.
"""

import importlib.util

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
