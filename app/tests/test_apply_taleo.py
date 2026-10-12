"""Taleo: link shapes + its tab (one address for every step), labels as Taleo writes them, each step read off
a local page rebuilt from one tenant's signed-in application (fixtures/taleo/README.md): privacy agreement,
sign-in, eSignature, review and the sent page left to the applicant; About You + Job Profile Questions read
and filled through dom; the resume attached and ticked as the one Resume / CV; work history + education
made to match the resume, adding entries across the step's reload. A careers page's Apply led to the system."""
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from apply import browser, careers_page, questions, systems
from apply.systems import taleo

FIXTURES = Path(__file__).parent / "fixtures" / "taleo"
LINK = "https://acme.taleo.net/careersection/10000/jobapply.ftl?job=12345"
SITE = "acme.taleo.net"


def test_links_match_taleo_apply_and_posting_pages_only():
    for url, app in ((LINK, LINK), (LINK + "&lang=en", LINK),
                     ("https://acme.taleo.net/careersection/2/jobdetail.ftl?lang=en&job=678",
                      "https://acme.taleo.net/careersection/2/jobapply.ftl?job=678")):
        assert systems.for_url(url) is taleo, url
        assert taleo.application_url(url) == app
    for url in ("https://acme.taleo.net/careersection/10000/jobsearch.ftl", "https://acme.taleo.net/careersection/10000/jobapply.ftl",
                "https://taleo.net.acme.example/careersection/1/jobapply.ftl?job=1", "ftp://acme.taleo.net/careersection/1/jobapply.ftl?job=1",
                "https://careers.acme.example/job/city/test-job/1/2"):
        assert not taleo.matches(url), url


def test_tab_is_this_job_or_the_steps_after_it():
    assert taleo.on_tab(LINK, LINK + "&lang=en&isapplyasguest=true")
    assert taleo.on_tab(LINK, f"https://{SITE}{taleo.FLOW}")
    assert not taleo.on_tab(LINK, LINK.replace("12345", "123456"))
    assert not taleo.on_tab(LINK, f"https://beta.taleo.net{taleo.FLOW}")
    assert not taleo.on_tab(LINK, f"https://{SITE}/careersection/10000/mysubmissions.ftl")


def test_labels_lose_taleos_marks_and_keep_the_question():
    assert taleo.clean("First Name\n \n. \nRequired") == ("First Name", True, None)
    assert taleo.clean("Middle Name") == ("Middle Name", False, None)
    assert taleo.clean("Area of Study\nLimit answer to 50 characters\n \n. \nRequired") == ("Area of Study", True, 50)
    assert taleo.clean("2. How many years of professional experience do you have? (TEC856) . Required") == \
        ("How many years of professional experience do you have?", True, None)
    assert taleo.clean("Are you barred from any government contract(s)? [COI5A] . Required")[0] == \
        "Are you barred from any government contract(s)?"
    assert taleo.clean("Which firm(s)? [COI4C] Choose all applicable fields . Required Choose all applicable fields") == \
        ("Which firm(s)?", True, None)
    # "Required" inside the question is no mark
    assert taleo.clean("Is a license required for this work?")[1] is False


def test_jobs_paired_by_name_and_title_then_the_one_left_then_blanks():
    found = [("beta", "software engineer"), ("delta works", "lead developer"), ("", ""), ("old shop", "clerk")]
    wanted = [("delta works", "web developer"), ("beta", "software engineer"), ("zeta", "engineer"),
              ("delta works", "lead developer")]
    pairs, left = taleo.pair(found, wanted, [False, False, True, False])
    # Web Developer at Delta: no Delta entry left -> the blank one, first come; Zeta -> added
    assert pairs == {1: 0, 3: 1, 0: 2}
    assert left == [3]
    assert taleo.company_key("Beta Inc.") == taleo.company_key("beta inc") == "beta"
    assert taleo.company_key("The Delta Works.") == taleo.company_key("Delta Works LLC")
    assert taleo.plain("Beta County College (BCC)") == taleo.plain("Beta County College")


# --- a careers page's Apply ---

PAGE = """<a class="button job-apply top" data-selector-name="job-apply-link" data-apply-url="https://acme.taleo.net/careersection/10000/jobapply.ftl?job=12345&amp;lang=en"
 href="https://acme.taleo.net/careersection/10000/jobapply.ftl?job=12345" rel="nofollow">Apply</a>
<a class="btn-internal-apply" href="https://acme.taleo.net/careersection/10020/jobapply.ftl?job=12345">Internal applicants</a>"""


class Answer:
    def __init__(self, url, text="", status=200):
        self.url, self.text, self.status_code = url, text, status


def test_careers_page_apply_leads_to_the_system_never_the_internal_one():
    assert careers_page.links(PAGE) == ["https://acme.taleo.net/careersection/10000/jobapply.ftl?job=12345&lang=en",
                                        "https://acme.taleo.net/careersection/10000/jobapply.ftl?job=12345"]
    post = "https://careers.acme.example/job/city/test-job/1/2"
    got = careers_page.apply_link(post, get=lambda url, **kw: Answer(url, PAGE))
    assert systems.for_url(got) is taleo
    other = PAGE.replace("acme.taleo.net/careersection/10000/jobapply.ftl?job=12345", "acme.avature.net/externalCareers/JobApplication?pipelineId=1")
    assert careers_page.apply_link(post, get=lambda url, **kw: Answer(url, other)) is None
    with pytest.raises(ValueError, match="may have closed"):
        careers_page.apply_link(post, get=lambda url, **kw: Answer("https://careers.acme.example/search-jobs", "<html/>"))

    def down(url, **kw):
        raise httpx.ConnectError("no network")
    assert careers_page.apply_link(post, get=down) is None


# --- each step on a local page ---

@pytest.fixture(scope="module")
def chrome():
    pw = pytest.importorskip("playwright.sync_api")
    try:
        exe = browser.chrome()
    except SystemExit:
        pytest.skip("Chrome not installed")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, headless=True)
        yield b
        b.close()


@pytest.fixture
def at(chrome):
    """at(name) -> a page showing fixtures/taleo/<name> as Taleo's site; nothing reaches the network."""
    context = chrome.new_context()
    asked = []

    def serve(route):
        u = urlsplit(route.request.url)
        asked.append(u.hostname)
        file = FIXTURES / u.path.lstrip("/")
        return route.fulfill(path=str(file)) if u.hostname == SITE and file.is_file() else route.abort()

    context.route("**/*", serve)
    page = context.new_page()

    def go(name):
        page.goto(f"https://{SITE}/{name}", wait_until="load")
        return page
    yield go
    assert set(asked) <= {SITE}, asked
    context.close()


def test_before_and_after_the_steps_nothing_is_ours(at, capsys):
    with pytest.raises(SystemExit, match="privacy agreement"):
        taleo.read(at("privacy.html"))
    with pytest.raises(SystemExit, match="Process completed"):
        taleo.read(at("done.html"))
    for name, words in (("esign.html", "type your full name"), ("review.html", "click Submit yourself")):
        page = at(name)
        assert taleo.read(page) == [] and taleo.ids_on_page(page) == []
        assert words in capsys.readouterr().out


def test_about_you_read_with_taleos_words_and_filled(at, capsys):
    page = at("about.html")
    qs = taleo.read(page)
    assert "Job Number 12345" in capsys.readouterr().out
    by = {q["title"]: q for q in qs}
    assert {"Source Type", "First Name", "Middle Name", "Last Name", "Email Address", "City", "Zip/Postal Code",
            "Street Address (line 1)", "Cellular Number xxx-xxx-xxxx"} <= set(by)
    assert by["First Name"]["required"] and not by["Middle Name"]["required"]
    assert by["Source Type"]["options"] == ["Company Web Site", "Job Board", "Other"]
    covenant = by["Are you subject to a restrictive covenant, such as a non-compete or a non-solicit, with a current or former employer?"]
    assert covenant["kind"] == "yesno" and covenant["required"]
    firms = by["Please indicate the firm(s) which you or a close family member* are presently or previously employed?"]
    assert firms["kind"] == "multichoice" and firms["options"] == ["Deloitte", "KPMG", "None of the above"] and firms["required"]
    assert (by["Email Address"]["kind"], by["Email Address"]["key"]) == ("email", "email")
    assert (by["Cellular Number xxx-xxx-xxxx"]["kind"], by["Cellular Number xxx-xxx-xxxx"]["key"]) == ("phone", "phone")
    # under "Please provide full legal name": the legal name's parts, never a name the user goes by
    assert [by[t]["key"] for t in ("First Name", "Middle Name", "Last Name")] == ["legal_first", "legal_middle", "legal_last"]
    assert by["City"]["key"] == "city" and by["Zip/Postal Code"]["key"] == "zip"
    # drafted: contact from the resume, the address from search settings (never the resume)
    drafted = {a["title"]: a for a in questions.draft(qs, {"name": "Jane Doe", "email": "jane@example.com", "phone": "(555) 555-0199"},
                                                      [], {"home_address": {"street": "2 Elm St", "city": "Newtown", "zip": "00001"}})}
    assert drafted["City"]["answer"] == "Newtown" and drafted["Email Address"]["answer"] == "jane@example.com"
    assert taleo.fill(page, drafted["Cellular Number xxx-xxx-xxxx"], None) == "ok"
    assert page.locator("#cell").input_value() == "555-555-0199"  # in the box's own shape
    assert all(q["page"] == taleo.ABOUT for q in qs)
    assert set(taleo.ids_on_page(page)) == {q["id"] for q in qs}

    def put(title, answer):
        q = by[title] | {"answer": answer}
        assert taleo.fill(page, q, None) == "ok", title
        assert taleo.holds(page, q), title
    put("Source Type", "Other")
    put(covenant["title"], "No")
    put(firms["title"], ["None of the above"])
    put("City", "Newtown")
    # Other shows its own box: read again, it is there to fill
    spec = next(q for q in taleo.read(page) if q["title"] == "Please Specify")
    assert taleo.fill(page, spec | {"answer": "Job search site"}, None) == "ok"
    # a box gone from this step is on another one; one whose words changed is never typed into
    assert taleo.fill(page, by["City"] | {"id": "[id=\"nope\"]", "answer": "x"}, None).startswith(questions.LATER)
    assert taleo.fill(page, by["City"] | {"title": "Town", "answer": "x"}, None).startswith("FAIL box label changed")


def test_profile_questions_titled_from_the_words_around_their_buttons(at):
    page = at("questions.html")
    qs = taleo.read(page)
    titles = [q["title"] for q in qs]
    assert titles == ["Please indicate the highest level of education you have completed.",
                      "Are you currently sponsored or will you in the future require sponsorship for employment visa status "
                      "(e.g., H-1B, TN, F-1, OPT, CPT, EAD, or other employment-based visa status)?",
                      "Please state your desired minimum base salary and total compensation expectations for this role."]
    level, sponsor, pay = qs
    assert level["kind"] == "choice" and sponsor["kind"] == "yesno" and pay["kind"] == "longtext"
    assert all(q["required"] for q in qs)
    for q, answer in ((level, "Bachelor's Degree"), (sponsor, "No"), (pay, "$150,000")):
        assert taleo.fill(page, q | {"answer": answer}, None) == "ok"
        assert taleo.holds(page, q | {"answer": answer})
    # the pay box is the user's: never drafted from the resume
    drafted = questions.draft([pay], {"name": "Jane Doe"}, [], {})
    assert questions.blank(drafted[0]["answer"])


def resume_pdf(tmp_path, kb=40):
    pdf = tmp_path / "Jane_Doe_Resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n" + b"0" * (kb * 1024))
    return str(pdf)


def test_resume_attached_and_ticked_as_the_one_resume(at, tmp_path):
    page = at("attachments.html")
    qs = taleo.read(page)
    assert [q["id"] for q in qs] == [taleo.RESUME] and qs[0]["kind"] == "file"
    assert taleo.ids_on_page(page) == [taleo.RESUME]
    q = qs[0] | {"answer": True}
    pdf = resume_pdf(tmp_path)
    said = taleo.fill(page, q, pdf)
    # an older file still marked Relevant goes along: named, never unticked for the user
    assert said.startswith("ASK also ticked as Relevant from earlier: References.pdf")
    got = {r["name"] + " " + r["date"]: r for r in taleo.rows(page)}
    new = next(r for k, r in got.items() if k.startswith("Jane_Doe_Resume.pdf") and r["date"] in taleo.today_shown())
    assert new["resume"] and new["relevant"]
    old_copy = got["Jane_Doe_Resume.pdf 9/30/26"]  # an earlier job's resume, same file name
    assert not old_copy["resume"] and not old_copy["relevant"]
    assert not got["Jane_Doe_resume_2022_11.pdf 11/10/22"]["resume"]
    assert taleo.holds(page, q)
    # again: today's copy is there - nothing attached twice
    n = len(taleo.rows(page))
    assert taleo.fill(page, q, pdf).startswith("ASK also ticked")
    assert len(taleo.rows(page)) == n
    # not approved: skipped; not on this step: later
    assert taleo.fill(page, qs[0] | {"answer": False}, pdf) == "skipped - upload not approved"
    assert taleo.fill(at("about.html"), q, pdf).startswith(questions.LATER)


def test_resume_over_the_pages_size_limit_never_attached(at, tmp_path):
    page = at("attachments.html")
    said = taleo.fill(page, taleo.read(page)[0] | {"answer": True}, resume_pdf(tmp_path, kb=1100))
    assert said.startswith("FAIL the resume is") and "up to 1024 KB" in said
    assert len(taleo.rows(page)) == 3


MASTER = {
    "contact": {"name": "Jane Doe"},
    "roles": [
        {"id": "zeta", "company": "Zeta", "title": "Software Engineer", "start": "2019-08", "end": "present", "bullets": []},
        {"id": "beta", "company": "Beta Inc.", "title": "Software Engineer", "start": "2018-03", "end": "2019-06", "bullets": []},
        {"id": "gamma", "company": "Gamma Partners LLC", "title": "Lead Developer", "start": "2015-04", "end": "2017-09", "bullets": []},
        {"id": "delta", "company": "Delta Works LLC", "title": "Lead Developer", "start": "2012-02", "end": "2014-11", "bullets": []},
        {"id": "delta-web", "company": "Delta Works LLC", "title": "Web Developer", "start": "2010-05", "end": "2011-12", "bullets": []}],
    "education": [{"institution": "Acme State University", "degree": "BA", "field": "Studio Art and Community Programs"},
                  {"institution": "Beta County College", "degree": "AA", "field": "Digital Media Arts"},
                  {"institution": "Epsilon Institute", "degree": "MS", "field": "Computer Science"}],
}


def test_work_history_and_education_made_to_match_the_resume(at, monkeypatch):
    monkeypatch.setattr(taleo, "resume_facts", lambda resume: (MASTER, {}))
    page = at("history.html")
    qs = taleo.read(page)
    assert [q["id"] for q in qs] == [taleo.PROFILE]  # every entry's boxes are this one step
    q = qs[0] | {"answer": "Yes"}
    said = taleo.fill(page, q, "resume.pdf")
    assert said.startswith("ASK"), said
    assert "Clerk, Old Shop - left as is" in said  # on the account, not on the resume: never removed
    work = [(taleo.value(e, "Employer"), taleo.value(e, "Job Title"), e["boxes"][taleo.WORK]["checked"],
             [b["value"] for b in e["months"]], [b["value"] for b in e["years"]])
            for e in taleo.entries(page) if e["kind"] == "work"]
    assert work == [
        ("Beta Inc.", "Software Engineer", False, ["Mar", "Jun"], ["2018", "2019"]),
        ("Gamma Partners LLC", "Lead Developer", False, ["Apr", "Sep"], ["2015", "2017"]),
        ("Delta Works LLC", "Lead Developer", False, ["Feb", "Nov"], ["2012", "2014"]),
        ("Old Shop", "Clerk", False, ["Jun", "Aug"], ["2008", "2009"]),
        ("Zeta", "Software Engineer", True, ["Aug", "Month"], ["2019", "Year"]),
        ("Delta Works LLC", "Web Developer", False, ["May", "Dec"], ["2010", "2011"])]
    schools = [(taleo.value(e, taleo.SCHOOL), taleo.value(e, "Area of Study"), taleo.value(e, "Education Level"),
                taleo.value(e, "Education Level Completed?")) for e in taleo.entries(page) if e["kind"] == "school"]
    assert schools == [("Acme State University", "Studio Art and Community Programs", "Bachelor's Degree", "Yes"),
                       ("Beta County College (BCC)", "Digital Media Arts", "Associate's Degree/College Diploma", "Yes"),
                       ("Epsilon Institute", "Computer Science", "Master's Degree", "Yes")]
    assert taleo.holds(page, q)
    # again: nothing left to change, nothing added
    n = len(taleo.entries(page))
    assert taleo.fill(page, q, "resume.pdf").count("added") == 0
    assert len(taleo.entries(page)) == n
    assert taleo.fill(page, q | {"answer": "No"}, None) == "skipped - user said no"


def test_jobs_not_chosen_yet_asked_never_guessed(at, monkeypatch):
    tailored = {"entries": [{"id": r["id"], "bullets": []} for r in MASTER["roles"][:3]]}
    monkeypatch.setattr(taleo, "resume_facts", lambda resume: (MASTER, tailored))
    page = at("history.html")
    said = taleo.fill(page, taleo.read(page)[0] | {"answer": "Yes"}, "resume.pdf")
    assert said.startswith("ASK no jobs added yet")
    assert len([e for e in taleo.entries(page) if e["kind"] == "work"]) == 4


def test_prepare_follows_a_careers_page_apply_to_its_system(tmp_path, monkeypatch, capsys):
    import contextlib
    import json

    from apply import form
    folder = tmp_path / "7 - Acme - Test Job"
    (folder / ".data").mkdir(parents=True)
    monkeypatch.setattr(form.cfg, "load", lambda: {})
    monkeypatch.setattr(form.cfg, "resume_path", lambda c, k: tmp_path / "r.yml")
    monkeypatch.setattr(form.schema, "load", lambda p: {"contact": {"name": "Jane Doe"}})
    monkeypatch.setattr(form, "job_dir", lambda config, slug: folder)
    post = "https://careers.acme.example/job/city/test-job/1/2"
    monkeypatch.setattr(form.careers_page, "apply_link", lambda url: LINK if url == post else None)
    opened = []

    @contextlib.contextmanager
    def tab(url, match=None):
        opened.append((url, match(f"https://{SITE}{taleo.FLOW}")))
        yield "page"
    monkeypatch.setattr(form.browser, "page_at", tab)
    monkeypatch.setattr(taleo, "read", lambda page: [questions.question("x", "City", "text", True, key="city", page=taleo.ABOUT)])
    form.prepare("7", post)
    assert f"the posting's Apply leads to {LINK}" in capsys.readouterr().out
    assert opened == [(LINK, True)]  # the user's own tab on the steps after the first
    saved = json.loads((folder / ".data" / questions.FILE).read_text())
    assert (saved["system"], saved["url"]) == ("Taleo", LINK)

    def gone(url):
        raise ValueError("the posting's page now opens the employer's job search instead - it may have closed")
    monkeypatch.setattr(form.careers_page, "apply_link", gone)
    with pytest.raises(SystemExit, match="may have closed - nothing read"):
        form.prepare("7", post)
