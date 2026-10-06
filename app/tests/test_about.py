from datetime import date

import pytest
import yaml

import about
import cfg
from apply import answers

TODAY = date(2026, 10, 6)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(about, "FILE", tmp_path / "My Settings" / "About me.yml")
    monkeypatch.setattr(about, "VIEW", tmp_path / ".data" / "What Job Finder knows about you.md")
    monkeypatch.setattr(about.cfg, "DATA", tmp_path / ".data")
    monkeypatch.setattr(answers, "FILE", tmp_path / "My Settings" / "Saved answers.yml")
    monkeypatch.setattr(about.cfg, "resume_path", lambda c, key: tmp_path / c["resume"][key])
    config = cfg.defaults() | {"profile": {"name": "warehouse jobs"}}
    monkeypatch.setattr(about.cfg, "load_or_defaults", lambda: config)
    return tmp_path, config


def test_notes_keep_their_words_by_kind_and_number(home):
    assert about.add("goals", "  Move from  shift lead to operations manager ", TODAY) == 1
    assert about.add("values", "No tobacco or gambling companies", TODAY) == 1
    assert about.read("goals") == ["1. Move from shift lead to operations manager"]
    saved = yaml.safe_load(about.FILE.read_text(encoding="utf-8"))
    assert saved == {"goals": [{"said": "Move from shift lead to operations manager", "on": "2026-10-06"}],
                     "values": [{"said": "No tobacco or gambling companies", "on": "2026-10-06"}]}
    assert about.FILE.read_text(encoding="utf-8").startswith("# Notes about you")


def test_forget_takes_a_number_and_the_page_drops_it_at_once(home):
    about.add("personal", "Caring for a parent - need set hours", TODAY)
    about.add("personal", "Can't lift over 25 lb", TODAY)
    about.show(TODAY)
    assert about.forget("personal", 1) == "Caring for a parent - need set hours"
    about.refresh(TODAY)
    page = about.VIEW.read_text(encoding="utf-8")
    assert "Caring for a parent" not in page and "1. Can't lift over 25 lb" in page
    with pytest.raises(SystemExit, match="no note 5"):
        about.forget("personal", 5)


def test_reading_one_kind_never_reads_another(home):
    about.add("values", "Faith-based employers welcome", TODAY)
    about.add("voice", "Plain and warm, no buzzwords", TODAY)
    assert about.read("voice") == ["1. Plain and warm, no buzzwords"]
    assert about.read("goals") == []


def test_only_sensitive_kinds_are_values_and_personal():
    assert about.SENSITIVE == {"values", "personal"} <= set(about.KINDS)
    for kind in about.SENSITIVE:
        assert "Never on a resume, a form or a letter" in about.KINDS[kind][1]
        assert "never sent to the job search" in about.KINDS[kind][1]


def test_page_shows_every_store_with_use_who_and_how_to_change(home):
    root, config = home
    config["work_authorization"] |= {"authorized_us": True, "needs_sponsorship": False}
    config["home_address"] = {"street": None, "city": "Riverton", "state": "Ohio", "zip": "45000"}
    config["self_identification"] = {"protected_veteran": False, "fill_on_forms": True}
    answers.FILE.parent.mkdir(parents=True)
    answers.FILE.write_text(yaml.safe_dump([{"key": "notice period", "question": "Notice period?", "answer": "2 weeks",
                                             "job": "3", "company": "Acme", "on": "2026-10-01"}]), encoding="utf-8")
    (root / "My Resume").mkdir()
    (root / "My Resume" / "Original resume.docx").write_bytes(b"PK")
    (root / "My Resume" / "Resume details.yml").write_text(
        yaml.safe_dump({"roles": [{}, {}], "education": [{}]}), encoding="utf-8")
    about.add("never_mention", "My old employer's name change", TODAY)
    page = about.VIEW.read_text(encoding="utf-8") if about.VIEW.exists() else about.page(config, about.load(), TODAY)
    for want in ("Looking for: warehouse jobs", "Allowed to work in the US without restriction: yes",
                 "Can hold a US security clearance: not asked yet", "Riverton, Ohio, 45000",
                 "Voluntary answer - protected veteran: no", '"Notice period?" -> 2 weeks',
                 "Resume details: 2 jobs, 1 schools", "Resume file you gave: My Resume/Original resume.docx",
                 "1. My old employer's name change (2026-10-06)", "30 days by default"):
        assert want in page
    assert page.count("**Used for:**") == page.count("**Who sees it:**") == page.count("**To change it:**") == 11
    assert "edit" not in page.lower()


def test_show_prints_the_path_not_the_contents(home, monkeypatch, capsys):
    about.add("values", "No defense contractors", TODAY)
    monkeypatch.setattr("sys.argv", ["about", "show"])
    about.main()
    out = capsys.readouterr().out
    assert "No defense contractors" not in out and "never read it into the chat" in out
    assert "No defense contractors" in about.VIEW.read_text(encoding="utf-8")


def test_list_gives_counts_only(home, monkeypatch, capsys):
    about.add("values", "No defense contractors", TODAY)
    monkeypatch.setattr("sys.argv", ["about", "list"])
    about.main()
    out = capsys.readouterr().out
    assert "values (sensitive): 1" in out and "defense" not in out
