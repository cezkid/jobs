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


def test_privacy_statements_name_the_per_job_request():
    """Tailoring + "still open?" send a listed job's id to the job search: every place that says
    what leaves the computer must say so, not "search settings only"."""
    places = {"AGENTS.md": "listing id", "Guides/Who sees what.md": "Which job from your list",
              "docs/privacy.html": "which job from your list", "docs/index.html": "which job from your list",
              "app/skills/job-setup.md": "listing id"}
    missing = [f for f, words in places.items() if words not in (cfg.ROOT / f).read_text(encoding="utf-8")]
    assert missing == []


def test_agents_md_names_the_three_ais_and_their_fallbacks():
    """The installer offers Claude, ChatGPT and Copilot (.data/ai): AGENTS.md says all three read it,
    asks for the resume on My Resume (Copilot gets a chat-dropped PDF with no path), and carries the
    numbered-reply fallback + the all-in-one-apps answer."""
    text = (cfg.ROOT / "AGENTS.md").read_text(encoding="utf-8")
    read_by = " ".join(text[text.index("Read by"):].split("\n\n")[0].split())
    for ai in ("Claude Code", "Codex (ChatGPT)", "GitHub Copilot"):
        assert ai in read_by
    assert "Cursor" not in read_by and "Gemini" not in read_by
    for words in ("drag it onto My Resume in the file list", "reply with the number", "Nova",
                  "can't run programs"):
        assert words in " ".join(text.split())
    setup = (cfg.ROOT / "app/skills/job-setup.md").read_text(encoding="utf-8")
    assert "drag it onto My Resume in the file list" in setup and "drag into chat" not in setup


# AGENTS.md #User = not technical: words a user never reads (exceptions: the user's own file name,
# an AI account's "API key")
JARGON = re.compile(r"\b(config|yml|json|slug|params|facet|pytest|repo|commit|branch|PR|API|schema)\b")
JARGON_OK = ("Resume details.yml", "API key")


def test_user_guides_carry_no_jargon():
    found = {}
    for guide in sorted((cfg.ROOT / "Guides").glob("*.md")):
        text = guide.read_text(encoding="utf-8")
        for ok in JARGON_OK:
            text = text.replace(ok, "")
        hits = sorted(set(JARGON.findall(text)))
        if hits:
            found[guide.name] = hits
    assert found == {}


def _text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split()).lower()


# one phrase per recipient (and its condition) the home page's Who sees what and privacy.html share
RECIPIENT_PHRASES = (
    "freehire.me", "your search words", "which job from your list you make a resume for or ask about",
    "your resume and what you tell it", "claude, chatgpt or github copilot",
    "personal plans may train on chats unless you switch it off",
    "what you apply with", "when you click save or submit",
    "your email provider", "only if you turn on email alerts", "sent to yourself",
    "the maintainer", "only if you say yes", "never your files",
)


def test_who_sees_what_matches_privacy_page_item_for_item():
    """The home page's Who sees what scene lists every recipient privacy.html names, in the
    same words, one ledger row per "What leaves your computer" table row."""
    home = (cfg.ROOT / "docs/index.html").read_text(encoding="utf-8")
    privacy = (cfg.ROOT / "docs/privacy.html").read_text(encoding="utf-8")
    missing = {page: [w for w in RECIPIENT_PHRASES if w not in _text(html)]
               for page, html in (("index", home), ("privacy", privacy))}
    assert missing == {"index": [], "privacy": []}
    ledger = re.search(r'<ol class="ledger">(.*?)</ol>', home, re.S).group(1)
    leaves = re.search(r'What leaves your computer</h2>\s*<table class="ledger".*?<tbody>(.*?)</tbody>', privacy, re.S).group(1)
    assert ledger.count("<li>") == leaves.count('<th scope="row">') == 5
