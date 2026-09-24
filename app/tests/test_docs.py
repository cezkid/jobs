"""Every doc link lands: a moved or renamed doc breaks a test, not a user's click."""
import re
import subprocess
from urllib.parse import unquote

import pytest

import cfg

LINK = re.compile(r"\]\(([^)\s]+)\)")
# code and instructions name docs by path ("docs/resume/bullets.md"), not by link
PATH_REF = re.compile(r"(?<![\w/])(?:app/)?docs/[\w/-]+\.md")


def tracked(*suffixes: str) -> list:
    out = subprocess.run(["git", "-C", str(cfg.ROOT), "ls-files"], capture_output=True, text=True).stdout.splitlines()
    return [cfg.ROOT / f for f in out if f.endswith(suffixes) and not f.startswith("docs/")]


def anchors(path) -> set[str]:
    """GitHub / VS Code heading slugs: lower case, punctuation dropped, spaces to hyphens."""
    return {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
            for h in re.findall(r"^#+ (.+)$", path.read_text(encoding="utf-8"), re.M)}


pytestmark = pytest.mark.skipif(not (cfg.ROOT / ".git").exists(), reason="installed copy: no git to list tracked docs")


def test_every_markdown_link_resolves():
    broken = []
    for doc in tracked(".md"):
        for target in LINK.findall(doc.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", target):
                continue
            file, _, anchor = unquote(target).partition("#")
            dest = (doc.parent / file).resolve() if file else doc
            if not dest.exists():
                broken.append(f"{doc.relative_to(cfg.ROOT)} -> {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                broken.append(f"{doc.relative_to(cfg.ROOT)} -> {target} (no such heading)")
    assert broken == []


def test_every_doc_path_named_in_code_exists():
    missing = sorted({f"{f.relative_to(cfg.ROOT)}: {ref}" for f in tracked(".py", ".md", ".yml", ".js", ".typ")
                      for ref in PATH_REF.findall(f.read_text(encoding="utf-8"))
                      if not (cfg.APP / ref.removeprefix("app/")).exists()})
    assert missing == []


def test_docs_index_lists_every_doc():
    index = (cfg.APP / "docs" / "README.md").read_text(encoding="utf-8")
    docs = sorted(p.relative_to(cfg.APP / "docs").as_posix() for p in (cfg.APP / "docs").rglob("*.md") if p.name != "README.md")
    assert [d for d in docs if f"]({d})" not in index] == []
