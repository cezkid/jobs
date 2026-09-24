import copy
import re

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
    assert rules(findings, lint.WARN) == {"specificity"}


def test_style_word_fails_generated_warns_own_wording(master, model):
    generated = with_bullet(model, "Meticulously built Vue search, cutting INP 410ms -> 170ms")
    assert "style-word" in rules(lint.lint(generated, master))
    master["roles"][0]["bullets"][0]["claim"] = "Meticulously built Vue search"
    own = lint.lint(render.page_model(master), master)
    assert "style-word" in rules(own, lint.WARN) and "style-word" not in rules(own)


def test_scope_words_are_evidence_not_style(master, model):
    generated = with_bullet(model, "Built Vue search across 6 teams, within 2 quarters")
    assert "style-word" not in {f.rule for f in lint.lint(generated, master)}


def test_grade_word_the_facts_or_posting_use_is_a_term_not_a_grade(master, model):
    posted = with_bullet(copy.deepcopy(model), "Built advanced Vue search for the insights team")
    assert {"unmeasurable-grade", "style-word"} <= rules(lint.lint(posted, master))
    assert rules(lint.lint(posted, master, posting="Advanced search for our Consumer Insights group")) == set()
    world = with_bullet(copy.deepcopy(model), "Built world-class Vue search")
    assert "unmeasurable-grade" in rules(lint.lint(world, master, posting="Advanced search"))
    master["certifications"] = [{"name": "Advanced Cardiac Life Support (ACLS)"}]
    spelled = with_bullet(copy.deepcopy(model), "Held Advanced Cardiac Life Support (ACLS) on 6 teams")
    assert rules(lint.lint(spelled, master)) == set()


def test_hedge_the_facts_use_is_their_account_of_their_part(master, model):
    master["roles"][0]["bullets"][1]["claim"] = "Assisted with checkout INP work in Vue"
    generated = with_bullet(model, "Assisted with Vue checkout INP work")
    assert "hedge" not in rules(lint.lint(generated, master), lint.WARN)
    assert "hedge" in rules(lint.lint(with_bullet(model, "Helped build Vue search"), master), lint.WARN)


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


def test_empty_purpose_clause_only_ever_warns(master, model):
    text = "Expanded the Vue component library, so new screens assemble from existing pieces"
    generated = lint.lint(with_bullet(model, text), master)
    assert "empty-clause" in rules(generated, lint.WARN) and "empty-clause" not in rules(generated)
    master["roles"][0]["bullets"][0]["claim"] = text
    own = lint.lint(render.page_model(master), master)
    assert "empty-clause" in rules(own, lint.WARN)
    assert "empty-clause" not in rules(own)


def test_thousands_separator_is_the_same_number(master, model):
    master["roles"][0]["bullets"][0]["metrics"] = ["1000 tickets a week"]
    assert rules(lint.lint(with_bullet(model, "Built Vue search over 1,000 tickets a week"), master)) == set()


@pytest.mark.parametrize("written", ["20 percent", "20 per cent"])
def test_round_metric_written_out_in_master_passes(master, model, written):
    master["roles"][0]["bullets"][0]["metrics"] = [f"deflected {written} of tickets"]
    assert rules(lint.lint(with_bullet(model, "Built Vue search, deflecting 20% of tickets"), master)) == set()


def test_purpose_clause_naming_something_stays_quiet(master, model):
    named = with_bullet(model, "Rebuilt the Vue index so queries return in under 200ms")
    assert "empty-clause" not in {f.rule for f in lint.lint(named, master)}


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


def test_rag_status_report_is_not_ai_work(master, model):
    model["sections"][0]["entries"][1]["bullets"][0] = "Led design system migration, 42 components, with a weekly RAG status report"
    assert "ai-era" not in {f.rule for f in lint.lint(model, master)}


@pytest.mark.parametrize("text", ["Ran quarterly performance evals for 6 teams", "Fine-tuned Storybook for 6 teams"])
def test_words_other_fields_use_are_not_ai_terms(master, model, text):
    model["sections"][0]["entries"][1]["bullets"][0] = text
    assert "ai-era" not in {f.rule for f in lint.lint(model, master)}


def test_ai_term_in_own_wording_warns(master):
    master["roles"][1]["bullets"][0]["claim"] = "Led design system migration w/ LLM codemods"
    findings = lint.lint(render.page_model(master), master)
    assert "ai-era" in rules(findings, lint.WARN) and "ai-era" not in rules(findings)


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


def test_every_rule_has_a_plain_reason_and_the_doc_carries_it():
    source = (cfg.APP / "resume" / "lint.py").read_text(encoding="utf-8")
    emitted = set(re.findall(r'(?:Finding\(\w+, |hit\(|\(\()"([a-z-]+)"', source))
    emitted |= set(re.findall(r'\("([a-z-]+)", [A-Z_]+\)', source))
    assert emitted and emitted <= lint.WHY.keys(), emitted - lint.WHY.keys()
    doc = (cfg.APP / "docs" / "resume" / "bullets.md").read_text(encoding="utf-8")
    assert all(f"| `{rule}` | {why} |" in doc for rule, why in lint.WHY.items())


TODAY = lint.date(2026, 9, 24)


def test_example_file_discloses_nothing_it_should_not(master):
    assert lint.master_findings(master, TODAY) == []


@pytest.mark.parametrize("location", ["12 Elm Street, Springfield, IL", "Springfield, IL 62701", "Springfield, IL, Apt 4"])
def test_street_address_warns(master, location):
    master["contact"]["location"] = location
    assert rules(lint.master_findings(master, TODAY), lint.WARN) == {"street-address"}


@pytest.mark.parametrize("text", ["Date of birth: 1990-04-02", "Marital status: single", "Nationality: Canadian", "Age: 34"])
def test_personal_details_warn(master, text):
    master["summary"] = text
    assert rules(lint.master_findings(master, TODAY), lint.WARN) == {"personal-details"}


def test_old_graduation_year_suggests_hiding_never_hides(master):
    master["education"][0]["end"] = "2008-05"
    findings = lint.master_findings(master, TODAY)
    assert rules(findings, lint.WARN) == {"old-graduation-year"} and "hide_year" in findings[0].detail
    assert "2008" in render.page_model(master)["sections"][-2]["entries"][0]["subline"]
    master["education"][0]["hide_year"] = True
    assert lint.master_findings(master, TODAY) == []


def test_shortened_school_name_warns(master):
    master["education"][0]["institution"] = "Lakeview CC"
    assert rules(lint.master_findings(master, TODAY), lint.WARN) == {"abbreviated-school"}
    master["education"][0]["institution"] = "Lakeview Community College"
    assert lint.master_findings(master, TODAY) == []


@pytest.mark.parametrize("line, warns", [
    ("Spanish (Fluent)", False), ("Mandarin Chinese (Professional working proficiency)", False),
    ("French (B2)", False), ("Spanish", True), ("English and Spanish - fluent", True),
    ("English, Spanish (Fluent)", True), ("English/Spanish (Native)", True),
])
def test_language_needs_its_own_level(master, line, warns):
    master["languages"] = [line]
    assert (rules(lint.master_findings(master, TODAY), lint.WARN) == {"language-level"}) is warns


def test_same_year_handover_is_not_an_overlap(master):
    master["roles"][0]["start"] = "2023"
    master["roles"][1]["end"] = "2023"
    assert "role-dates-overlap" not in rules(lint.lint(render.page_model(master), master), lint.WARN)
    master["roles"][1]["end"] = "2024"
    assert "role-dates-overlap" in rules(lint.lint(render.page_model(master), master), lint.WARN)


def test_career_break_is_not_an_unknown_entry(master):
    master["career_break"] = [{"reason": "Travel", "start": "2023-01", "end": "2023-01"}]
    master["roles"][1]["end"] = "2022-12"
    assert rules(lint.lint(render.page_model(master), master)) == set()


def own_bullet(master, text: str) -> dict:
    master["roles"][0]["bullets"][0]["claim"] = text
    return render.page_model(master)


def found(findings, rule: str) -> list:
    return [f for f in findings if f.rule == rule]


def test_british_spelling_warns_on_own_words_and_fails_on_generated(master, model):
    mine = copy.deepcopy(master)
    own = found(lint.lint(own_bullet(mine, "Shot 100 live theatre events in Vue"), mine), "spelling")
    assert [f.severity for f in own] == [lint.WARN] and "theatre -> theater" in own[0].detail
    generated = found(lint.lint(with_bullet(model, "Organised 12 Vue releases"), master), "spelling")
    assert [f.severity for f in generated] == [lint.FAIL] and "organised -> organized" in generated[0].detail


def test_typo_named_with_its_likely_word_and_field_terms_left_alone(master, model):
    typo = found(lint.lint(with_bullet(model, "Shipped managment reports in Vue"), master), "spelling")
    assert [f.severity for f in typo] == [lint.FAIL] and "did you mean management?" in typo[0].detail
    for fine in ("Precepted 6 nurses on a 32-bed med-surg unit in Epic",
                 "Advertised expertise across the enterprise in Vue",
                 "Won 2 sponsors: Rockin' Robin Diner, Globex",
                 "Helped onboard 3 engineers to Vue"):
        assert found(lint.lint(with_bullet(copy.deepcopy(model), fine), master), "spelling") == [], fine


def test_a_word_the_posting_uses_is_not_a_typo_in_generated_text(master, model):
    text = "Cut telemtry cost in Vue"
    assert found(lint.lint(with_bullet(copy.deepcopy(model), text), master), "spelling")
    assert not found(lint.lint(with_bullet(model, text), master, posting="telemtry"), "spelling")


@pytest.mark.parametrize("text, flagged", [
    ("Set up 12 live streaming channels on AWS", "live-streaming channels"),
    ("Full stack engineer on Vue", "Full-stack engineer"),
    ("Shipped features end to end in Vue", None),
    ("Wrote end-to-end tests in Vue", None),
])
def test_open_compound_before_a_noun_warns(master, model, text, flagged):
    hits = found(lint.lint(with_bullet(model, text), master), "compound-modifier")
    assert [f.severity for f in hits] == ([lint.WARN] if flagged else [])
    assert not flagged or flagged in hits[0].detail


def test_one_opening_word_on_four_bullets_warns_once(master, model):
    acme(model)["bullets"] = [f"Built {n} Vue screens for checkout" for n in range(3)]
    assert not found(lint.lint(copy.deepcopy(model), master), "overused-opening")
    acme(model)["bullets"].append("Built 9 Vue screens for search")
    assert [f.detail for f in found(lint.lint(model, master), "overused-opening")] == ["4 bullets open with 'built'"]


@pytest.mark.parametrize("text, words", [
    ("I successfully led our Vue migration", "I, our, successfully"),
    ("Triaged 30 patients a shift in a Level I trauma center", None),
    ("Cut lazy loading time in Vue 40%", None),
])
def test_filler_words_warn_and_level_i_is_not_a_pronoun(master, model, text, words):
    hits = found(lint.lint(with_bullet(model, text), master), "filler-word")
    assert [f.detail.split(":")[0] for f in hits] == ([words] if words else [])
