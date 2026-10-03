"""Build the site's generated pages in docs/: sitemap.xml now, docs/research/** + docs/about/** next.

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
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# folders this script owns: files in them it didn't build are orphans and get deleted
OWNED = ("research", "about")
# docs/mac/ + docs/win/ hold install scripts named index.html, not pages
NOT_PAGES = ("mac", "win")
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


def build(root: Path) -> dict[str, str]:
    """Every generated file: docs-relative path -> text. Reads, never writes."""
    docs = root / "docs"
    out: dict[str, str] = {}
    hand = {rel: (docs / rel).read_text(encoding="utf-8") for rel in listed(docs)
            if rel.endswith(".html") and rel.split("/")[0] not in NOT_PAGES + OWNED}
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
    if args.check:
        found = problems(ROOT)
        print("\n".join(found) if found else "docs/ up to date")
        sys.exit(1 if found else 0)
    changed = write(ROOT)
    print("\n".join(changed) if changed else "docs/ up to date")


if __name__ == "__main__":
    main()
