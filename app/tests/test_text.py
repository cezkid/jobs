import re
from pathlib import Path

from markdown_it import MarkdownIt

from text import html_to_text, inert_md


def test_html_to_text_strips_tags_keeps_breaks():
    assert html_to_text("<p>One &amp; two</p><ul><li>Vue</li></ul>") == "One & two\n\nVue"


def test_html_to_text_drops_mojibake():
    assert "�" not in html_to_text("<p>Vue�Node</p>")


# hostile posting: every way employer text could load, link or run something in a .md preview
HOSTILE = """Great role! Apply today.
![pixel](https://track.example/p.png)
<img src="https://track.example/i.png">
[Click to continue](vscode://anthropic.claude-code/open?prompt=x)
[Open settings](command:workbench.action.openSettings)
<a href="https://evil.example">Apply here</a>
<script>alert(1)</script>
<https://evil.example/auto>
Visit https://evil.example/bare or evil.example or hr@evil.example
[ref]: https://evil.example/ref
See [the ref][ref]
&lt;img src=x&gt; &#60;img src=y&#62;
\\![escaped](https://track.example/x.png)
`code <b>bold</b>`"""
PLAIN = "We hire analysts.\n\n- Build dashboards in Excel\n- 5+ years, e.g. SQL\n\n1. Apply\n2. Talk to us\n\n**Pay** 50% of 401(k) *matched* # not a heading"
# render as VS Code's preview does: markdown-it, raw HTML + linkify on
TAG = re.compile(r"<(/?)([a-z0-9]+)")
SAFE_TAGS = {"p", "ul", "ol", "li", "em", "strong", "h1", "h2", "h3", "hr", "table", "thead", "tbody", "tr", "th", "td", "code", "pre"}
RAW = ("![", "<img", "](vscode:", "](command:", "<a ", "<script", "<https")


def render(text: str) -> str:
    return MarkdownIt("commonmark", {"html": True, "linkify": True}).enable(["linkify", "table"]).render(text)


def assert_inert(md: str) -> None:
    html_out = render(md)
    assert {t for _, t in TAG.findall(html_out)} <= SAFE_TAGS, html_out
    assert not [s for s in RAW if s in md], md


# a posting's hidden image pinged the employer when the user opened it, or a link ran a VS Code command
def test_inert_md_renders_no_link_image_or_html():
    assert_inert(inert_md(HOSTILE))
    assert TAG.findall(render(HOSTILE)) != TAG.findall(render(inert_md(HOSTILE)))  # the fixture is live raw


# making it safe must not garble the posting: bullets, lists, bold + words read as before
def test_inert_md_reads_the_same():
    assert render(inert_md(PLAIN)) == render(PLAIN)
    words = re.sub(r"<[^>]+>", "", render(inert_md(HOSTILE)))
    assert "Click to continue" in words and "https://evil.example/bare" in words and "hr@evil.example" in words


# Job posting.md + Check before sending.md: the employer's title, company, asks and text all inert
def test_posting_and_check_pages_inert(tmp_path):
    from resume import report
    line = "[Click](command:x) <img src=https://t.example/p.png> see https://t.example"
    job = {"public_slug": "s", "title": f"Analyst {line}", "company": f"Example Co {line}", "url": "https://jobs.example/1",
           "source": "pasted", "text": HOSTILE, "enrichment": {"seniority": line}, "reality": {},
           "requirements": [{"text": line, "priority": "required"}]}
    assert_inert(report.posting_md(job).replace(job["url"], ""))
    rows = [{"priority": "required", "status": "gap", "index": 0, "text": line, "note": line, "trait": False}]
    result = {"pdf": tmp_path / "Your_Name_Resume.pdf", "failed": [], "gates": [], "selection": [], "findings": []}
    assert_inert(report.report_md(job, {"entries": []}, result, rows, []).replace(job["url"], ""))


# Application answers.md: question words come off the employer's page
def test_application_answers_questions_inert(tmp_path, monkeypatch):
    from apply import form, questions
    folder = tmp_path / "Job 5 - Example Co - Analyst"
    (folder / ".data").mkdir(parents=True)
    questions.save(folder / ".data" / questions.FILE, {"system": form.PASTE, "url": "https://x.example", "questions": [
        {"title": HOSTILE, "kind": "text", "required": True, "answer": "Yes", "options": [], "source": "user"}]})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    monkeypatch.setattr(form.cfg, "load", lambda: {})
    monkeypatch.setattr(form, "resume_for", lambda config, folder: None)
    monkeypatch.setattr(form, "remember", lambda *a: None)
    form.paste("5")
    assert_inert((folder / form.ANSWERS_FILE).read_text(encoding="utf-8"))


# Today.md: a job's title + company come from the posting
def test_today_item_inert():
    import today
    assert_inert("\n".join(today.item({"num": 3, "title": HOSTILE.replace("\n", " "), "company": "Example Co"})))


# Follow-up email.md: the role + company named in it are the employer's
def test_follow_up_email_inert(tmp_path, monkeypatch):
    import followup
    import status
    import store
    from test_status import make_folder
    jobs_dir = tmp_path / "My Jobs"
    title = "Analyst [Click](vscode://x) <img src=https://t.example/p.png>"
    folder = make_folder(jobs_dir / "2 Applied", "1 - Example Co - Analyst", "https://jobs.example/1",
                         "Example Co https://evil.example", title, "ex-1")
    config = {"db": str(tmp_path / "jobs.db"), "resume": {"jobs_dir": str(jobs_dir), "master": str(tmp_path / "r.yml")}}
    monkeypatch.setattr(followup.cfg, "load", lambda: config)
    monkeypatch.setattr(followup.cfg, "resume_path", lambda c, key: Path(c["resume"][key]))
    monkeypatch.setattr(followup.schema, "load", lambda path: {"contact": {"name": "Your Name"}, "roles": []})
    conn = store.connect(tmp_path / "jobs.db")
    status.set_state(conn, status.resolve(conn, jobs_dir, "https://jobs.example/1"), "applied", "2026-09-01T12:00:00Z")
    conn.close()
    monkeypatch.setattr(followup.sys, "argv", ["follow-up", "https://jobs.example/1"])
    followup.main()
    assert_inert((folder / followup.FILE).read_text(encoding="utf-8"))
