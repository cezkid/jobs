"""Workable: link shapes, the saved form definitions -> shared questions, each widget rule. Facts: app/docs/apply/workable.md."""
import json
from pathlib import Path

import pytest

from apply import systems
from apply.systems import workable

FIXTURES = Path(__file__).parent / "fixtures" / "workable"
APPLY = "https://apply.workable.com/j/1A2B3C4D5E/apply/"


def read(tenant: str) -> dict:
    return {q["id"]: q for q in workable.from_definition(json.loads((FIXTURES / f"tenant-{tenant}.json").read_text()))}


# --- links ---

@pytest.mark.parametrize("url", ["https://apply.workable.com/j/1A2B3C4D5E", "https://apply.workable.com/j/1a2b3c4d5e/",
                                 "https://apply.workable.com/j/1A2B3C4D5E?utm_source=freehire.me",
                                 "https://apply.workable.com/j/1A2B3C4D5E/apply"])
def test_workable_short_link_and_freehire_tail(url):
    assert workable.matches(url) and workable.application_url(url) == APPLY
    assert systems.for_url(url) is workable


@pytest.mark.parametrize("url", ["https://apply.workable.com/acme/j/1A2B3C4D5E/", "https://apply.workable.com/acme/j/1A2B3C4D5E/apply/",
                                 "https://apply.workable.com/acme/j/1A2B3C4D5E?utm_source=freehire.me"])
def test_workable_account_link_keeps_its_account(url):
    assert workable.parse_url(url) == ("acme", "1A2B3C4D5E")
    assert workable.application_url(url) == "https://apply.workable.com/acme/j/1A2B3C4D5E/apply/"


@pytest.mark.parametrize("url", ["https://apply.workable.com/acme/", "https://apply.workable.com/j/12",
                                 "https://apply.workable.com/api/v1/jobs/1A2B3C4D5E/form",
                                 "https://www.example.com/j/1A2B3C4D5E", "https://apply.workable.com.example.com/j/1A2B3C4D5E",
                                 "https://jobs.lever.co/acme/1b2c3d4e-5f60-4718-9a0b-1c2d3e4f5a6b"])
def test_not_a_workable_posting_refused(url):
    assert not workable.matches(url)
    with pytest.raises(ValueError):
        workable.application_url(url)


# --- the form, read off the saved definitions ---

def test_workable_standard_boxes_keys_and_required():
    a, e = read("a"), read("e")
    assert [(a[i]["kind"], a[i]["key"]) for i in ("firstname", "lastname", "email", "phone", "resume", "cover_letter")] == \
        [("text", "first_name"), ("text", "last_name"), ("email", "email"), ("phone", "phone"), ("file", "resume"),
         ("longtext", "cover_letter")]
    assert a["resume"]["required"] and not e["resume"]["required"]  # optional on tenant E only
    assert a["headline"]["key"] is None and a["summary"]["kind"] == "longtext" and not a["summary"]["required"]


def test_workable_address_prefill_is_never_the_users_answer():
    a = read("a")["address"]
    assert (a["kind"], a["key"], a["title"]) == ("location", "location", workable.PREFILLED)
    assert "internet address" in a["title"]


def test_workable_photo_and_entry_groups_are_not_questions():
    for t in "abcdef":
        qs = read(t)
        assert not {"avatar", "education", "experience"} & set(qs)
        assert not any(q["native"] and q["native"].endswith(":group") for q in qs.values())


def test_workable_question_types_to_shared_kinds():
    a, c, d, e, f = (read(t) for t in "acdef")
    assert (a["QA_9530805"]["kind"], a["QA_9530805"]["native"]) == ("yesno", "QA:boolean")
    assert c["QA_11399512"]["kind"] == "longtext" and c["QA_11399509"]["kind"] == "text"
    assert d["QA_12550683"]["kind"] == "number" and f["QA_12170790"]["kind"] == "date"
    # a dropdown is a choice; Yes / No only -> yesno, its options kept
    assert e["CA_27590"]["kind"] == "choice" and "Associate" in e["CA_27590"]["options"]
    assert (e["CA_26351"]["kind"], e["CA_26351"]["options"]) == ("yesno", ["Yes", "No"])
    # `multiple`: one pick -> choice, several -> multichoice
    assert a["QA_9530809"]["kind"] == "choice" and a["QA_9530809"]["required"]
    assert a["QA_9831316"]["kind"] == "multichoice"


def test_workable_ticks_carry_their_option_names_and_trimmed_text():
    f = read("f")["CA_11867"]
    # each tick is named after its option, not the question; "Evenings " on the definition read trimmed
    assert f["native"] == "CA:multiple:152176,152177,152178" and f["options"] == ["Weekends", "Evenings", "Holiday"]


def test_workable_acknowledgment_date_and_attestations_are_the_applicants():
    e, f = read("e"), read("f")
    for q in (f["QA_12170790"], e["CA_27976"], read("a")["QA_9530819"]):
        assert workable.fill(None, q | {"answer": "x"}, None).startswith("ASK yours to do on the page"), q["title"]


def test_workable_posting_gone_is_said_plainly(monkeypatch):
    monkeypatch.setattr(workable.httpx, "get", lambda url, timeout: type("R", (), {"status_code": 404})())
    with pytest.raises(ValueError, match="may have closed"):
        workable.questions(APPLY)


# --- widgets, with fakes ---

class Box:
    """A named <input> / <textarea>, or one tick of a checkbox set."""
    def __init__(self, type="text", checked=False):
        self.type, self.value, self.checked = type, "", checked

    def evaluate(self, js, *a):
        if "tagName" in js:
            return self.type
        if "e.click()" in js:
            self.checked = not self.checked
        if "e.checked" in js:
            return self.checked
        return None  # change + blur

    def fill(self, v):
        self.value = v

    def input_value(self):
        return self.value

    def scroll_into_view_if_needed(self, timeout=None):
        pass


class Radio:
    """A [role=radio] option; `covered`: something sits over it, as measured - a click times out,
    one where it sits lands on what's on top, Space on it focused works."""
    def __init__(self, text, group, page, covered=True):
        self.text, self.group, self.page, self.covered, self.ticked = text, group, page, covered, False

    def evaluate(self, js):
        return self.text

    def get_attribute(self, name):
        return "true" if self.ticked else "false"

    def scroll_into_view_if_needed(self, timeout=None):
        pass

    def click(self, timeout=None, force=False):
        if self.covered and not force:
            raise TimeoutError("Locator.click: Timeout 3000ms exceeded.")
        if not self.covered:
            self.pick()

    def focus(self):
        pass

    def press(self, key):
        if key == "Space":
            self.pick()

    def pick(self):
        for r in self.group:
            r.ticked = r is self


class Dropdown:
    """A dropdown's wrapper + combobox + list: clicks covered, Down on it focused opens the list."""
    def __init__(self, options):
        self.options, self.open, self.chosen = options, False, ""

    def locator(self, css):  # the wrapper's [role=combobox]
        return Many([self])

    def click(self, timeout=None, force=False):
        raise TimeoutError("Locator.click: Timeout 2000ms exceeded.")

    def count(self):
        return 1

    def focus(self):
        pass

    def press(self, key):
        self.open = self.open or key == "ArrowDown"

    def evaluate(self, js):  # SHOWN, off the wrapper
        return [self.chosen] if self.chosen else []


class Options:
    def __init__(self, dropdown):
        self.dropdown = dropdown

    @property
    def first(self):
        return self

    def wait_for(self, timeout=None):
        if not (self.dropdown and self.dropdown.open):
            raise TimeoutError("Timeout 3000ms exceeded.")

    def all_inner_texts(self):
        return self.dropdown.options

    def nth(self, i):
        d = self.dropdown
        return type("Option", (), {"click": lambda s, timeout=None: (setattr(d, "chosen", d.options[i]), setattr(d, "open", False))})()


class Many:
    def __init__(self, members):
        self.members = members
        self.first = members[0] if members else None

    def count(self):
        return len(self.members)

    def all(self):
        return self.members

    def nth(self, i):
        return self.members[i]


class Page:
    def __init__(self, named=(), radios=(), dropdowns=(), files=(), resume_at=-1):
        self.named, self.radios, self.dropdowns, self.files, self.resume_at = dict(named), dict(radios), dict(dropdowns), list(files), resume_at
        self.open = None
        self.keyboard = type("Keyboard", (), {"press": lambda s, key: None})()

    def locator(self, css):
        between = lambda a, b: css.split(a, 1)[1].split(b, 1)[0]
        if css.startswith("form [name="):
            return Many(self.named.get(between('[name="', '"]'), []))
        if css.startswith("fieldset:has"):
            return Many(self.radios.get(between('[name="', '"]'), []))
        if css.startswith("[data-ui="):
            self.open = self.dropdowns.get(between('[data-ui="', '"]'))
            return self.open or Many([])
        if css == "[role=option]:visible":
            return Options(self.open)
        if css == "input[type=file]":
            return Many(self.files)
        raise AssertionError(css)

    def evaluate(self, js):
        assert js == workable.RESUME_INPUT
        return self.resume_at

    def wait_for_timeout(self, ms):
        pass


def radio_set(page, id, *texts):
    group = []
    group.extend(Radio(t, group, page) for t in texts)
    page.named[id], page.radios[id] = [Box("radio")], group
    return group


def q(id, kind, answer, options=(), key=None, native=None, title="Question"):
    return {"id": id, "title": title, "kind": kind, "key": key, "answer": answer, "options": list(options), "native": native}


def test_workable_text_boxes_by_name():
    name, salary = Box(), Box()
    page = Page(named={"firstname": [name], "QA_1": [salary]})
    assert workable.fill(page, q("firstname", "text", "Test", key="first_name"), None) == "ok" and name.value == "Test"
    assert workable.fill(page, q("QA_1", "number", "1"), None) == "ok" and salary.value == "1"
    assert workable.fill(page, q("QA_2", "text", "a"), None) == "FAIL question not on page"


def test_workable_yes_no_radio_ticks_though_a_click_is_covered():
    page = Page()
    no = radio_set(page, "QA_1", "YES", "NO")  # the page's own capitals
    assert workable.fill(page, q("QA_1", "yesno", True, native="QA:boolean"), None) == "ok"
    assert [r.ticked for r in no] == [True, False]
    assert workable.fill(page, q("QA_1", "yesno", "No", native="QA:boolean"), None) == "ok"
    assert [r.ticked for r in no] == [False, True]


def test_workable_single_choice_radio_by_its_text():
    page = Page()
    group = radio_set(page, "QA_2", "Yes– please add details below", "No")
    assert workable.fill(page, q("QA_2", "choice", "no", ["Yes– please add details below", "No"]), None) == "ok"
    assert [r.ticked for r in group] == [False, True]
    assert workable.fill(page, q("QA_2", "choice", "Maybe"), None).startswith("ASK no option 'Maybe'")


def test_workable_radio_that_never_takes_says_why():
    page = Page()
    group = radio_set(page, "QA_3", "YES", "NO")
    for r in group:
        r.press = lambda key: None  # nothing ticks it
    got = workable.fill(page, q("QA_3", "yesno", "Yes"), None)
    assert got.startswith("FAIL 'YES' didn't take") and "click: " in got


def test_workable_dropdown_opens_by_keyboard_and_clicks_the_answer():
    deg = Dropdown(["High School/GED", "Trade/Technical School", "Associate"])
    adult = Dropdown(["Yes", "No"])
    page = Page(named={"CA_1": [Box()], "CA_2": [Box()]}, dropdowns={"CA_1": deg, "CA_2": adult})
    assert workable.fill(page, q("CA_1", "choice", "Associate", deg.options), None) == "ok" and deg.chosen == "Associate"
    assert workable.fill(page, q("CA_2", "yesno", True, ["Yes", "No"]), None) == "ok" and adult.chosen == "Yes"
    assert workable.fill(page, q("CA_1", "choice", "PhD"), None).startswith("ASK no option 'PhD'")


def test_workable_ticks_by_option_name():
    ticks = {n: [Box("checkbox")] for n in ("152176", "152177", "152178")}
    page = Page(named=ticks)
    multi = q("CA_9", "multichoice", ["Weekends", "Holiday"], ["Weekends", "Evenings", "Holiday"],
              native="CA:multiple:152176,152177,152178")
    assert workable.fill(page, multi, None) == "ok"
    assert [ticks[n][0].checked for n in ("152176", "152177", "152178")] == [True, False, True]
    assert workable.fill(Page(), multi, None) == "FAIL question not on page"


def test_workable_resume_found_by_its_words_and_only_with_a_yes(tmp_path):
    cv = tmp_path / "Test_Resume.pdf"
    cv.write_bytes(b"%PDF")
    photo, resume = Box("file"), Box("file")
    resume.set_input_files = lambda path: setattr(resume, "files", [Path(path).name])
    resume.evaluate = lambda js, *a: resume.files[0] if "files[0]" in js else None
    box = q("resume", "file", True, key="resume")
    assert workable.fill(Page(files=[photo, resume], resume_at=1), box, str(cv)) == "ok" and resume.files == [cv.name]
    assert workable.fill(Page(files=[photo]), box, str(cv)) == "FAIL no resume box on page"
    assert workable.fill(Page(files=[photo, resume], resume_at=1), box | {"answer": False}, str(cv)) == "skipped - upload not approved"
    assert workable.fill(None, q("QA_5", "file", True), str(cv)).startswith("ASK not the resume box")
