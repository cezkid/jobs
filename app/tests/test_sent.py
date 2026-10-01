import sqlite3
from datetime import datetime, timedelta, timezone

import sent

T0 = datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc)
GH = {"url": "https://job-boards.greenhouse.io/acme/jobs/7000001?utm_source=freehire.me",
      "company": "Acme", "title": "Senior Engineer"}
ASHBY = {"url": "https://jobs.ashbyhq.com/acme/0a1b2c3d-0000-4000-8000-0000000000a1?utm_source=freehire.me",
         "company": "Acme", "title": "Frontend Engineer"}
# Workday job listed under the employer's own careers site: no id the Workday pages carry
WD = {"url": "https://careers.example.com/job/123/99999", "company": "Example Media Group",
      "title": "Sr Product Engineer (News Front-End)"}
UKG = {"url": "https://recruiting2.ultipro.com/acme1001/JobBoard/0a1b2c3d-0000-4000-8000-00000000b0a4/"
              "OpportunityDetail?opportunityId=0a1b2c3d-0000-4000-8000-0000000000f1", "company": "Acme", "title": "Dev"}


def visit(url, minutes=0, title="", browser="Chrome"):
    return sent.Visit(T0 + timedelta(minutes=minutes), url, title, browser)


def test_greenhouse_sent_page_settles_it_any_browser():
    v = [visit("https://job-boards.greenhouse.io/acme/jobs/7000001"),
         visit("https://job-boards.greenhouse.io/acme/jobs/7000001/confirmation", 5, browser="Brave")]
    assert sent.verdict(GH, v) == ("sent", "Greenhouse sent page 2026-09-24 (Brave)")


def test_greenhouse_opened_without_sent_page_is_likely_not_sent():
    word, why = sent.verdict(GH, [visit("https://job-boards.greenhouse.io/acme/jobs/7000001")])
    assert word == "likely not sent" and "none was seen" in why


def test_ashby_never_more_sure_than_cant_tell():
    v = [visit("https://jobs.ashbyhq.com/acme/0a1b2c3d-0000-4000-8000-0000000000a1/application")]
    word, why = sent.verdict(ASHBY, v)
    assert word == "can't tell" and "confirmation email" in why


def test_workday_sent_page_counts_only_right_after_this_jobs_form():
    form = visit("https://example.wd5.myworkdayjobs.com/en-US/ext/job/NY/Sr-Product-Engineer_1015/apply",
                 title="Sr Product Engineer (News Front-End)")
    done = visit("https://example.wd5.myworkdayjobs.com/en-US/ext/jobTasks/completed/application", 3)
    assert sent.verdict(WD, [form, done])[0] == "sent"
    late = visit("https://example.wd5.myworkdayjobs.com/en-US/ext/jobTasks/completed/application", 60 * 5)
    assert sent.verdict(WD, [form, late])[0] == "likely not sent"  # another job's Submit, hours later


def test_ukg_board_id_alone_is_not_this_job():
    other_job = visit("https://recruiting2.ultipro.com/acme1001/JobBoard/0a1b2c3d-0000-4000-8000-00000000b0a4/"
                      "OpportunityApply?opportunityId=0a1b2c3d-0000-4000-8000-0000000000f2")
    assert sent.verdict(UKG, [other_job])[0] == "no visits"


def test_title_match_needs_the_company_in_the_address():
    elsewhere = visit("https://ats.rippling.com/other/jobs/x/apply", title="Apply - Frontend Engineer")
    assert sent.verdict(ASHBY, [elsewhere])[0] == "no visits"
    assert sent.verdict(ASHBY, [visit("https://ats.rippling.com/acme/jobs/x/apply",
                                      title="Apply - Frontend Engineer")])[0] == "can't tell"


def test_chromium_history_read_from_a_copy(tmp_path):
    path = tmp_path / "History"
    conn = sqlite3.connect(path)
    conn.executescript("CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT);"
                       "CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER);")
    micros = int((T0 - sent.CHROME_EPOCH).total_seconds() * 1e6)
    conn.execute("INSERT INTO urls VALUES (1, 'https://job-boards.greenhouse.io/acme/jobs/7000001/confirmation', 'Thanks')")
    conn.execute("INSERT INTO visits VALUES (1, 1, ?)", (micros,))
    conn.commit()
    conn.close()
    [v] = sent.read("Chrome", path, "chromium")
    assert v.at == T0 and v.browser == "Chrome" and sent.verdict(GH, [v])[0] == "sent"


def test_every_browser_found_on_each_platform(tmp_path):
    for rel in ("Library/Application Support/Google/Chrome/Default/History",
                "Library/Application Support/BraveSoftware/Brave-Browser/Profile 1/History",
                "Library/Application Support/Firefox/Profiles/abc.default/places.sqlite"):
        (tmp_path / rel).parent.mkdir(parents=True)
        (tmp_path / rel).touch()
    found = {(b, k) for b, _, k in sent.history_files("darwin", tmp_path) if b != "Job Finder window"}
    assert found == {("Chrome", "chromium"), ("Brave", "chromium"), ("Firefox", "firefox")}
