import pytest
import yaml

import cfg
import rank
import software
from conftest import make_job

FRONT = ["frontend", "fullstack"]


@pytest.mark.parametrize("title, kinds", [
    # role words decide over language words: back-end work in a front-end language
    ("Senior Backend Engineer (TypeScript)", ["backend"]),
    ("Front-End/Back-End Engineer", ["frontend", "backend"]),
    ("Java Full Stack Developer", ["fullstack"]),
    # no role word: the language says it
    ("Senior Java Developer with Azure", ["backend"]),
    ("React Developer", ["frontend"]),
    ("React Native Developer", ["mobile"]),
    ("iOS_Developer", ["mobile"]),
    ("Embedded Software Engineer II - C++", ["systems"]),
    ("Senior Software Engineer", []),
    # charts in the browser: front-end work as much as data
    ("Staff Software Engineer, Data Visualization", ["data", "frontend"]),
    # "quality" alone is no testing job
    ("Senior Software Engineer, Ads Quality", []),
])
def test_named_kinds(title, kinds):
    assert software.named(title) == kinds


def test_title_of_another_kind_sorts_lower_with_reason():
    assert software.mismatch(make_job("a", title="Senior Backend Engineer (TypeScript)"), FRONT) == ["title says back-end"]
    assert software.mismatch(make_job("b", title="Senior Software Engineer - Front End/Back End"), FRONT) == []
    assert software.mismatch(make_job("c", title="Backend Engineer"), []) == []


def test_plain_title_read_off_skill_tags():
    plain = dict(title="Senior Software Engineer")
    assert software.mismatch(make_job("a", skills=["java", "kafka", "aws"], **plain), FRONT) == \
        ["skills listed are back-end (java, kafka)"]
    # one front-end tag among back-end ones: could be theirs, left alone
    assert software.mismatch(make_job("b", skills=["java", "react"], **plain), FRONT) == []
    # no stack named: can't tell
    assert software.mismatch(make_job("c", skills=["agile", "aws"], **plain), FRONT) == []
    # full-stack alone wants front-end tags: back-end tags only isn't full-stack work
    assert software.mismatch(make_job("d", skills=["java"], **plain), ["fullstack"]) == \
        ["skills listed are back-end (java)"]
    # not a software title: a designer tagged java isn't judged by it
    assert software.mismatch(make_job("e", title="Product Designer", skills=["java"]), FRONT) == []


def test_hidden_only_when_every_kind_named_is_hidden():
    hide = ["backend", "mobile"]
    assert software.hidden(make_job("a", title="Senior Java Developer"), hide)
    assert not software.hidden(make_job("b", title="Java Full Stack Developer"), hide)
    assert not software.hidden(make_job("c", title="Senior Software Engineer", skills=["java"]), hide)
    assert not software.hidden(make_job("d", title="Senior Java Developer"), [])


def config(**rank_over):
    base = cfg.load(cfg.PROFILES / "frontend.yml")
    return cfg.merge(base, {"rank": rank_over, "blocklist": rank_over.pop("blocklist", {})})


def test_rank_puts_their_kind_first_never_hides():
    jobs = [make_job("back", title="Backend Engineer", salary_min=300000, salary_currency="USD", salary_period="year"),
            make_job("front", title="Frontend Engineer")]
    ranked = rank.rank(jobs, config())
    assert [j["public_slug"] for j in ranked] == ["front", "back"]
    assert "title says back-end" in rank.reasons(ranked[1], config())


def test_blocklist_hides_kind_and_would_hide_counts_it():
    jobs = [make_job("back", title="Backend Engineer"), make_job("full", title="Java Full Stack Developer"),
            make_job("front", title="Frontend Engineer")]
    assert [j["public_slug"] for j in rank.would_hide_kind(jobs, "backend", {})] == ["back"]
    hiding = config(blocklist={"software_kinds": ["backend"]})
    assert sorted(j["public_slug"] for j in rank.rank(jobs, hiding)) == ["front", "full"]


def test_unknown_kind_refused(tmp_path):
    path = tmp_path / "settings.yml"
    path.write_text(yaml.safe_dump({**yaml.safe_load((cfg.PROFILES / "frontend.yml").read_text()),
                                    "rank": {"software_kinds": ["front-end"]}}))
    with pytest.raises(ValueError, match="software_kinds"):
        cfg.load(path)
