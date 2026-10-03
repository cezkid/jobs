"""SmartRecruiters: link shapes, the contact + resume page read off a saved snapshot (tenant A,
anonymised), and the Spark widget rules with fakes. Facts: app/docs/apply/smartrecruiters.md."""
import json
from pathlib import Path

import pytest

from apply import questions, systems
from apply.systems import smartrecruiters as sr

FIXTURES = Path(__file__).parent / "fixtures" / "smartrecruiters"
POSTING = "https://jobs.smartrecruiters.com/acme/744000000000001-example-job?utm_source=freehire.me"
UUID = "00000000-0000-4000-a000-000000000001"
FORM = f"https://jobs.smartrecruiters.com/oneclick-ui/company/acme/publication/{UUID}?dcr_ci=acme"


def snapshot(name: str) -> dict:
    """A saved snapshot, trimmed to what was measured: the rest of dom.snapshot's fields defaulted."""
    snap = json.loads((FIXTURES / name).read_text())
    base = {"password": False, "autocomplete": "", "options": [], "tag": "input"}
    return {"captcha": [], "blocked_frames": [], "not_readable": [], **snap,
            "controls": [{**base, **c} for c in snap["controls"]]}


@pytest.mark.parametrize("link", [POSTING, "https://jobs.smartrecruiters.com/acme/744000000000001",
                                  "https://jobs.smartrecruiters.com/acme/744000000000001-example-job/", FORM])
def test_posting_and_form_links_are_smartrecruiters(link):
    assert systems.for_url(link) is sr


@pytest.mark.parametrize("link", ["https://boards.greenhouse.io/acme/jobs/123",
                                  "https://jobs.smartrecruiters.com/acme",
                                  "https://www.smartrecruiters.com/acme/744000000000001"])
def test_other_links_refused(link):
    assert not sr.matches(link)


def test_application_url_is_the_posting_with_oga_and_the_form_app_as_is():
    assert sr.application_url(POSTING) == "https://jobs.smartrecruiters.com/acme/744000000000001?oga=true"
    assert sr.application_url(FORM) == FORM
    assert sr.parse_url(FORM) == ("acme", UUID)


def test_tab_found_by_posting_id_or_its_form_app(monkeypatch):
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": True})
    assert sr.on_tab(POSTING, "https://jobs.smartrecruiters.com/acme/744000000000001?oga=true")
    assert sr.on_tab(POSTING, FORM)
    other = "https://jobs.smartrecruiters.com/oneclick-ui/company/acme/publication/00000000-0000-4000-a000-000000000002"
    assert not sr.on_tab(POSTING, other)
    assert not sr.on_tab(POSTING, "https://boards.greenhouse.io/acme/jobs/744000000000001")


def test_inactive_posting_is_closed_before_any_browser(monkeypatch):
    monkeypatch.setattr(sr, "record", lambda url: {"uuid": UUID, "active": False})
    with pytest.raises(ValueError, match="closed"):
        sr.questions(POSTING)
    assert not sr.is_closed(FORM)  # the form app link alone carries no record


def test_page_one_read_off_the_snapshot():
    got = sr.from_snapshot(snapshot("page1-tenant-a.json"))
    by = {q["title"]: q for q in got}
    assert got[0]["id"] == sr.RESUME and got[0]["kind"] == "file" and got[0]["key"] == "resume"
    assert {q["page"] for q in got} == {sr.PAGE_ONE}
    # no photo slot, no parsing upload, no phone-country search box
    assert not [t for t in by if "profile image" in t.casefold() or "choose a file" in t.casefold()]
    assert "Search by country/region or code" not in by
    assert by["City"]["kind"] == "location" and by["City"]["key"] == "location" and by["City"]["required"]
    country = next(q for q in got if q["id"] == sr.COUNTRY)
    assert country["kind"] == "choice"
    assert by["Email"]["kind"] == "email" and by["Phone number"]["kind"] == "phone"
    assert by["Let the company know about your interest working there"]["kind"] == "longtext"
    assert by["First name"]["required"] and not by["LinkedIn"]["required"]
    assert set(q["kind"] for q in got) <= set(questions.KINDS)


def test_a_later_step_is_named_screening():
    snap = snapshot("page1-tenant-a.json")
    snap["controls"] = [c for c in snap["controls"] if c["id"] != "first-name-input"]
    got = sr.from_snapshot(snap)
    assert sr.RESUME not in [q["id"] for q in got]
    assert {q["page"] for q in got} == {sr.PAGE_LATER}


class Page:
    def __init__(self, button=None, first_name=True):
        self.button, self.first_name = button, first_name

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, role, name):
        return Found(self.button)

    def evaluate_handle(self, js):
        return Handle()

    def locator(self, selector):
        return Found(self if self.first_name else None)


class Found:
    def __init__(self, el):
        self.el = el
        self.first = el or self  # an empty locator still answers count()

    def count(self):
        return int(self.el is not None)


class Handle:
    def as_element(self):
        return None


class Widget:
    """A Spark list: its options, the pick, every option clicked."""
    def __init__(self, options, value=""):
        self.options, self.value, self.clicked, self.opened = options, value, [], False

    def count(self):
        return 1

    def evaluate(self, js, pick):
        if pick is not None:
            self.clicked.append(pick)
            self.value = self.options[pick]["value"]
        return {"value": self.value, "options": self.options}

    def focus(self):
        self.opened = True


PLACES = [{"value": "US_NJ_CITY_newark", "label": "Newark, NJ, US"},
          {"value": "US_NY_CITY_new_york_city", "label": "New York, NY, US"}]


def test_choose_picks_the_option_by_its_label_never_the_first():
    box = Widget(PLACES)
    assert sr.choose(Page(), box, "New York") == ("New York, NY, US", [p["label"] for p in PLACES])
    assert box.clicked == [1]


def test_choose_picks_nothing_when_no_label_fits():
    box = Widget(PLACES)
    assert sr.choose(Page(), box, "Boston")[0] is None and box.clicked == []


def test_phone_country_already_set_is_left_as_it_is():
    button = Widget([{"value": "CA", "label": "Canada"}, {"value": "US", "label": "United States"}], value="US")
    assert sr.put_country(Page(button), "United States") == "ok"
    assert not button.opened and button.clicked == []


def test_boxes_off_this_step_are_later():
    assert sr.put_country(Page(None), "United States").startswith(questions.LATER)
    assert sr.put_file(Page(first_name=False), "/tmp/r.pdf").startswith(questions.LATER)
    assert sr.put_file(Page(), "/tmp/r.pdf").startswith("ASK")


def test_resume_never_uploaded_without_the_users_yes():
    q = {"id": sr.RESUME, "kind": "file", "answer": None}
    assert sr.fill(Page(), q, "/tmp/r.pdf") == "skipped - upload not approved"
