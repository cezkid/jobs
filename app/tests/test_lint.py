import copy

import pytest

import cfg
from resume import lint, render, schema, tailor

EXAMPLE = cfg.APP / "resume" / "master.example.yml"


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


@pytest.fixture
def model(master) -> dict:
    return render.page_model(master)


def rules(findings, severity=lint.FAIL) -> set[str]:
    return {f.rule for f in findings if f.severity == severity}


def acme(model) -> dict:
    return model["sections"][0]["entries"][0]


def with_bullet(model, text: str) -> dict:
    acme(model)["bullets"][0] = text
    return model


def test_untailored_example_has_no_failures(master, model):
    findings = lint.lint(model, master)
    assert rules(findings) == set()
    assert rules(findings, lint.WARN) == {"style-word", "specificity"}


def test_style_word_fails_generated_warns_own_wording(master, model):
    own = lint.lint(model, master)
    assert any(f.rule == "style-word" and f.severity == lint.WARN for f in own)
    generated = with_bullet(model, "Meticulously built Vue search, cutting INP 410ms -> 170ms")
    assert "style-word" in rules(lint.lint(generated, master))


@pytest.mark.parametrize("text, rule", [
    ("Built Vue search — cut INP 410ms -> 170ms", "em-dash"),
    ("Built **Vue** search, cut INP 410ms -> 170ms", "markdown"),
    ("Built Vue search, cut INP 410ms -> 170ms", "invisible-unicode"),
    ("Built Vue search, deflecting 20% of tickets", "round-metric"),
    ("Built Vue search on Kubernetes", "unresolved-entity"),
])
def test_mechanical_rules_fail_generated_text(master, model, text, rule):
    assert rule in rules(lint.lint(with_bullet(model, text), master))


def test_round_metric_present_in_master_passes(master, model):
    master["roles"][0]["bullets"][0]["metrics"] = ["deflected 20% of tier-1 tickets"]
    assert rules(lint.lint(with_bullet(model, "Built Vue search, deflecting 20% of tickets"), master)) == set()


def test_unmeasurable_grade_fails_generated_warns_own_wording(master, model):
    generated = with_bullet(model, "Built Vue search with advanced answer grounding")
    assert "unmeasurable-grade" in rules(lint.lint(generated, master))
    master["roles"][0]["bullets"][0]["claim"] = "Built Vue search with advanced answer grounding"
    own = lint.lint(render.page_model(master), master)
    assert "unmeasurable-grade" in rules(own, lint.WARN)
    assert "unmeasurable-grade" not in rules(own)


def test_grade_word_inside_employer_name_stays_quiet(master):
    master["roles"][0]["company"] = "Seamless Robotics Inc."
    findings = lint.lint(render.page_model(master), master)
    assert "unmeasurable-grade" not in {f.rule for f in findings}


def test_inference_resolves_entity_and_needs_known_source(master, model):
    generated = with_bullet(model, "Built Vue search on Kubernetes")
    ok = [{"claim": "Kubernetes deploy implied by support platform ops", "from": ["acme-rag-search"]}]
    assert rules(lint.lint(generated, master, ok)) == set()
    bad = [{"claim": "Kubernetes", "from": ["nope"]}]
    assert rules(lint.lint(generated, master, bad)) == {"inference-source"}


def test_sentence_initial_capital_not_entity():
    assert lint.entities("Shipped search. Reduced INP to 170ms") == ["INP", "170"]


def test_ai_term_in_pre_ai_role_fails(master, model):
    model["sections"][0]["entries"][1]["bullets"][0] = "Led design system migration w/ LLM codemods, 42 components"
    assert "ai-era" in rules(lint.lint(model, master))


def test_tool_released_after_role_end_fails(master, model):
    master["roles"][1]["ai_era"] = True
    model["sections"][0]["entries"][1]["bullets"][0] = "Led design system migration w/ Claude, 42 components"
    findings = lint.lint(model, master)
    assert [f.detail for f in findings if f.rule == "ai-era"] == ["'Claude' released 2023-03, entry ended 2023-01"]


def test_identity_changes_fail_mirrored_title_passes(master, model):
    entry = acme(model)
    entry["heading"] = "Senior Software Engineer (Senior Vue Engineer)"
    assert rules(lint.lint(model, master)) == set()
    entry["heading"] = "Staff Software Engineer"
    entry["org"] = "Acme"
    entry["subline"] = "Feb 2019 - Present"
    assert rules(lint.lint(model, master)) == {"title-changed", "employer-changed", "dates-changed"}
    entry["id"] = "initech"
    assert rules(lint.lint(model, master)) == {"unknown-entry"}


def test_craft_rules_only_warn(master, model):
    acme(model)["bullets"] = [
        "Leveraged Vue to cut INP 410ms -> 170ms",
        "Leveraged pgvector, Claude, and TypeScript for search",
    ]
    findings = lint.lint(model, master)
    assert rules(findings) == set()
    assert {"resume-verb", "rule-of-three", "same-verb-opening"} <= rules(findings, lint.WARN)


def test_lead_bullet_without_number_warns_when_a_later_one_carries_it(master, model):
    acme(model)["bullets"] = [
        "Rebuilt the Vue design system with the platform team",
        "Cut INP 410ms -> 170ms",
    ]
    findings = lint.lint(model, master)
    assert "lead-bullet-weak" in rules(findings, lint.WARN)
    assert rules(findings) == set()


def test_strongest_bullet_first_clears_the_order_rule(master, model):
    acme(model)["bullets"] = [
        "Cut INP 410ms -> 170ms",
        "Rebuilt the Vue design system with the platform team",
    ]
    assert "lead-bullet-weak" not in rules(lint.lint(model, master), lint.WARN)


def test_role_dates_overlapping_next_role_warn(master):
    master["roles"][1]["end"] = master["roles"][0]["start"]
    findings = lint.lint(render.page_model(master), master)
    assert "role-dates-overlap" in rules(findings, lint.WARN)
    assert rules(findings) == set()


def test_same_employer_overlap_says_so_in_the_detail(master):
    master["roles"][1]["company"] = master["roles"][0]["company"]
    master["roles"][1]["end"] = master["roles"][0]["start"]
    findings = lint.lint(render.page_model(master), master)
    detail = next(f.detail for f in findings if f.rule == "role-dates-overlap")
    assert "SAME employer" in detail


def test_canonical_casing_warns_on_drifted_spelling(master, model):
    acme(model)["bullets"] = ["Rebuilt the Typescript design system"]
    findings = lint.lint(model, master)
    assert "canonical-casing" in rules(findings, lint.WARN)
    assert rules(findings) == set()


def test_canonical_casing_quiet_when_spelling_is_right(master, model):
    acme(model)["bullets"] = ["Rebuilt the TypeScript design system"]
    assert "canonical-casing" not in rules(lint.lint(model, master), lint.WARN)


def test_a_domain_in_the_contact_line_is_not_a_misspelling(master, model):
    assert "canonical-casing" not in rules(lint.lint(model, master), lint.WARN)


def test_older_role_with_more_bullets_than_a_newer_one_warns(master, model):
    entries = [e for s in model["sections"] for e in s.get("entries", [])
               if e.get("id") in {r["id"] for r in master["roles"]}]
    entries[0]["bullets"] = ["Cut INP 410ms -> 170ms"]
    entries[1]["bullets"] = ["Cut INP 410ms -> 170ms", "Shipped 4 Vue screens", "Wrote 9 Jest suites"]
    assert "bullet-taper" in rules(lint.lint(model, master), lint.WARN)


def test_company_without_legal_id_warns_never_fails(master):
    master["roles"][1]["company"] = "Mount Sinai Hospital"
    findings = lint.lint(render.page_model(master), master)
    assert "company-legal-id" in rules(findings, lint.WARN)
    assert rules(findings) == set()


def filler(words: int) -> str:
    return "Shipped " + " ".join(f"item{n}" for n in range(words - 1))


def set_bullets(model: dict, sizes: list[int]) -> None:
    pool = iter(sizes * 20)
    for section in model["sections"]:
        for entry in section.get("entries", []):
            entry["bullets"] = [filler(next(pool)) for _ in entry["bullets"]]


# the craft floor counts WORDS, where the page rules measure rendered width: a bullet that
# fills one line runs about 14 words, one that fills two about 27
ONE_LINE, TWO_LINE = 14, 27


def test_bullets_all_in_one_band_read_uniform(master, model):
    # two-line bullets alone cluster word counts, and the craft floor is what asks for a mix
    set_bullets(model, [TWO_LINE])
    assert "uniform-bullet-length" in rules(lint.lint(model, master), lint.WARN)


def test_one_line_bullet_every_fifth_clears_the_craft_floor(master, model):
    set_bullets(model, [ONE_LINE, *[TWO_LINE] * (tailor.ONE_LINE_SHARE - 1)])
    assert "uniform-bullet-length" not in rules(lint.lint(model, master), lint.WARN)
