import copy
from datetime import date

import pytest

import cfg
from resume import jd, measure, render, report, schema, tailor, typeface

EXAMPLE = cfg.APP / "resume" / "master.example.yml"
JOB = {
    "public_slug": "senior-vue-acme-x1", "title": "Senior Vue Engineer, Search", "company": "Acme",
    "url": "https://jobs.ashbyhq.com/acme/1", "source": "ashby", "text": "Build search UI with Vue.",
    "requirements": [{"text": "5+ years Vue", "priority": "required"}, {"text": "GraphQL", "priority": "preferred"}],
    "enrichment": {}, "reality": {},
}


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


@pytest.fixture
def tailored() -> dict:
    return {
        "summary": "Senior Software Engineer shipping Vue search",
        "entries": [
            {"id": "acme", "title_mirror": "Senior Vue Engineer", "bullets": [
                {"text": "Cut checkout INP 410ms -> 170ms moving cart recalculation to Web Workers", "sources": ["acme-inp"]},
            ]},
            {"id": "globex", "title_mirror": None, "bullets": [
                {"text": "Led design system migration across product surfaces", "sources": ["globex-design-system"]},
            ]},
        ],
        "skills": [{"group": "Frontend", "items": ["Vue", "TypeScript"]}],
        "inferences": [],
        "coverage": [
            {"requirement": 0, "evidence": ["acme-inp"], "note": "Vue on page"},
            {"requirement": 1, "evidence": [], "note": "no GraphQL"},
        ],
    }


def test_page_model_applies_selection_mirror_and_skills(master, tailored):
    model = tailor.page_model(master, tailored)
    assert [s["title"] for s in model["sections"]] == ["Experience", "Skills", "Education", "Languages"]
    acme = model["sections"][0]["entries"][0]
    assert acme["heading"] == "Senior Software Engineer (Senior Vue Engineer)"
    assert acme["org"] == "Acme Inc."
    assert acme["bullets"] == [tailored["entries"][0]["bullets"][0]["text"]]
    assert model["sections"][1]["lines"] == [{"label": "Frontend", "text": "Vue, TypeScript"}]


def test_valid_selection_has_no_violations(master, tailored):
    assert tailor.check_selection(master, JOB, tailored) == []


def filler(lines: float) -> str:
    """Real words sized to a share of the bullet column - characters cannot express this."""
    words, out = "shipped ledger export tooling across regional payment teams".split(), []
    while measure.width(typeface.DEFAULT, " ".join(out)) < measure.bullet(typeface.DEFAULT) * lines:
        out.append(words[len(out) % len(words)])
    return " ".join(out[:-1])


@pytest.mark.parametrize("mutate, expected", [
    (lambda t: t["entries"].pop(), "role 'globex' dropped"),
    (lambda t: t["entries"].append({"id": "initech", "title_mirror": None, "bullets": []}), "'initech' not a master role"),
    (lambda t: t["entries"][1]["bullets"][0].update(sources=["acme-inp"]), "source 'acme-inp' belongs to 'acme'"),
    (lambda t: t["entries"][1]["bullets"][0].update(text="Led design system migration w/ Vite"), "['Vite'] in none of its sources"),
    (lambda t: t["entries"][0].update(title_mirror="Staff Engineer"), "not whole words of job title"),
    (lambda t: t["entries"][0].update(title_mirror="Vue Eng"), "not whole words of job title"),
    (lambda t: t["skills"][0]["items"].append("Kubernetes"), "'Kubernetes' not in the candidate's skills"),
    (lambda t: t["coverage"][1].update(evidence=["certifications[0]"]), "out of range: 0 certifications"),
    (lambda t: t["coverage"][1].update(evidence=["skills:GraphQL"]), "not a master skills item"),
    (lambda t: t["coverage"][1].update(evidence=["skills:Vite"]), "not on the page's skills"),
    (lambda t: t["entries"].append({"id": "evalkit", "title_mirror": "Search", "bullets": []}), "title_mirror on non-role"),
    (lambda t: t["coverage"].pop(), "requirement 1 missing"),
    (lambda t: t["coverage"][1].update(requirement=5), "requirement 5 out of range"),
    (lambda t: t["coverage"][1].update(evidence=["acme-rag-search"]), "'acme-rag-search' not a source of any on-page bullet"),
    (lambda t: t["entries"][0]["bullets"][0].update(text=filler(3.0)), "lines (max 2)"),
    (lambda t: t["entries"][0]["bullets"][0].update(text=filler(1.2)), "wraps to a line only"),
])
def test_selection_violations(master, tailored, mutate, expected):
    mutate(tailored)
    violations = tailor.check_selection(master, JOB, tailored)
    assert any(expected in v for v in violations), violations


@pytest.mark.parametrize("lines", [0.95, 1.6, 1.95])
def test_bullet_filling_one_line_or_two_passes(master, tailored, lines):
    tailored["entries"][0]["bullets"][0]["text"] = filler(lines)
    assert not [v for v in tailor.check_selection(master, JOB, tailored) if "line" in v]


def test_moved_entity_resolves_through_inference(master, tailored):
    tailored["entries"][1]["bullets"][0]["text"] = "Led design system migration w/ Vite"
    tailored["inferences"] = [{"claim": "Vite build", "sources": ["globex-design-system"]}]
    assert tailor.check_selection(master, JOB, tailored) == []


def test_request_is_byte_identical_per_master_and_job(master):
    first = tailor.build_request(master, JOB)
    assert first == tailor.build_request(copy.deepcopy(master), copy.deepcopy(JOB))
    assert '"generated_words"' in first["prompt"]


def test_coverage_rows_drop_off_page_evidence(master, tailored):
    tailored["coverage"][0]["evidence"] = ["acme-rag-search"]
    rows = tailor.coverage_rows(JOB, tailored, master)
    assert [r["status"] for r in rows] == ["gap", "gap"]


def with_certification(master: dict) -> dict:
    master["certifications"] = [{"name": "Basic Life Support (BLS)", "issuer": "Acme Heart Association"}]
    return master


BLS_JOB = {**JOB, "requirements": [{"text": "Current BLS certification", "priority": "required"},
                                   {"text": "GraphQL", "priority": "preferred"}]}


def test_held_certification_counts_as_coverage(master, tailored):
    with_certification(master)
    tailored["coverage"][0]["evidence"] = ["certifications[0]"]
    tailored["coverage"][1]["evidence"] = ["skills:TypeScript"]
    assert tailor.check_selection(master, BLS_JOB, tailored) == []
    rows = tailor.coverage_rows(BLS_JOB, tailored, master)
    assert [r["status"] for r in rows] == ["met", "met"]
    assert rows[0]["shown"] == ["Basic Life Support (BLS)"]


def test_certifications_move_under_summary_when_the_posting_requires_one(master, tailored):
    with_certification(master)
    titles = lambda job: [s["title"] for s in tailor.page_model(master, tailored, job)["sections"]]
    assert titles(BLS_JOB)[0] == "Certifications"
    assert titles(JOB)[-2:] == ["Certifications", "Languages"]
    spelled = {**JOB, "requirements": [{"text": "basic life support", "priority": "required"}]}
    assert titles(spelled)[0] == "Certifications"


def old_roles(master: dict) -> dict:
    """Two more roles below the example's, both ended 20 years before TODAY."""
    master["roles"] += [
        {**master["roles"][1], "id": "initech", "company": "Initech LLC", "start": "2003-01", "end": "2006-01", "bullets": []},
        {**master["roles"][1], "id": "hooli", "company": "Hooli LLC", "start": "2000-01", "end": "2002-12", "bullets": []},
    ]
    return master


TODAY = date(2026, 9, 24)


def test_trailing_old_roles_may_be_dropped_a_middle_one_may_not(master, tailored):
    old_roles(master)
    tailored["entries"].append({"id": "initech", "title_mirror": None, "bullets": []})
    assert tailor.check_selection(master, JOB, tailored, today=TODAY) == []  # hooli, the oldest, dropped
    tailored["entries"][-1]["id"] = "hooli"  # initech dropped with an older role still below it
    assert any("role 'initech' dropped" in v for v in tailor.check_selection(master, JOB, tailored, today=TODAY))
    recent = copy.deepcopy(tailored)
    recent["entries"].pop(1)  # globex ended 2023: never droppable
    assert any("role 'globex' dropped" in v for v in tailor.check_selection(master, JOB, recent, today=TODAY))


def test_mirror_claiming_a_level_the_candidate_lacks_fails(master, tailored):
    master["roles"][0]["title"] = "Staff Nurse"
    tailored["entries"][0]["title_mirror"] = "Nurse Manager"
    job = {**JOB, "title": "Nurse Manager, ICU"}
    violations = tailor.check_selection(master, job, tailored)
    assert any("claims manager" in v for v in violations), violations


def test_report_speaks_plain_words_and_gives_reasons(master, tailored):
    tailored["entries"][1]["bullets"][0]["text"] = master["roles"][1]["bullets"][0]["claim"]
    tailored["inferences"] = [{"claim": "Web Workers", "sources": ["acme-inp"]}]
    tailored["reasons"] = [{"id": "acme-rag-search", "reason": "this job does not ask for AI search"},
                           {"id": "Playwright", "reason": "testing is not in the posting"}]
    diff = report.diff_md(master, tailored, tailor.page_model(master, tailored))
    assert "Job title shown as \"Senior Software Engineer (Senior Vue Engineer)\"" in diff
    assert "- Web Workers\n  - based on: Cut checkout INP by moving cart recalculation off main thread (acme-inp)" in diff
    assert "- Reworded: Cut checkout INP" in diff
    assert "- Left out: Built retrieval-augmented search over support docs, eval harness scoring answer grounding - why: this job does not ask for AI search" in diff
    assert "- Kept as written: Led design system migration" in diff
    assert "## evalkit\n\n- Left off this version" in diff
    assert "- Left out: Playwright - why: testing is not in the posting" in diff
    assert "master" not in diff and "`" not in diff


def test_folder_name_readable_and_filesystem_safe():
    job = {**JOB, "company": 'Acme: "Health"', "title": "RN / ICU?  Nights."}
    assert tailor.folder_name(job) == "Acme Health - RN ICU Nights"


def test_long_folder_name_cut_at_word():
    job = {**JOB, "company": "Weights & Biases", "title": "Senior Software Engineer, ML Model Training UI - Weights & Biases"}
    name = tailor.folder_name(job)
    assert len(name) <= tailor.MAX_FOLDER_CHARS
    assert name.split()[-1] in job["title"].split()


def test_job_dir_reused_for_same_job_suffixed_for_other(tmp_path):
    first = tailor.job_dir_for(tmp_path, JOB)
    assert first.name == "Acme - Senior Vue Engineer, Search"
    (first / tailor.JOB_DATA).mkdir(parents=True)
    tailor.write_json(first / tailor.JOB_DATA / "jd.json", JOB)
    assert tailor.job_dir_for(tmp_path, JOB) == first
    other = tailor.job_dir_for(tmp_path, {**JOB, "public_slug": "senior-vue-acme-x2"})
    assert other.name == "Acme - Senior Vue Engineer, Search (2)"


def test_prepare_on_a_posting_without_requirements_explains_instead_of_crashing(tmp_path, monkeypatch):
    """The user-facing half of jd.NoRequirements: a plain way out, never a traceback."""
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    config = cfg.defaults()
    master_path = cfg.resume_path(config, "master")
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    def no_requirements(*_args):
        raise jd.NoRequirements("senior-payroll-analyst: enrichment.requirements empty")

    monkeypatch.setattr(jd, "fetch", no_requirements)
    with pytest.raises(SystemExit) as exited:
        tailor.prepare(config, "senior-payroll-analyst", None, "")
    said = str(exited.value)
    assert "no requirements" in said and "tailor posting" in said
    assert "Traceback" not in said


def test_prepare_then_check_fills_job_folder(tmp_path, monkeypatch, master, tailored):
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    monkeypatch.setattr(tailor, "POSTING_ANSWER", tmp_path / "posting.json")
    config = cfg.defaults()
    master_path = cfg.resume_path(config, "master")
    master_path.parent.mkdir(parents=True)
    master_path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    posting = tmp_path / "posting.txt"
    posting.write_text(JOB["text"], encoding="utf-8")
    tailor.write_json(tailor.POSTING_ANSWER, {k: JOB[k] for k in ("title", "company", "requirements")})

    tailor.prepare(config, None, posting, JOB["url"])
    job_dir = tmp_path / "My Jobs" / "Acme - Senior Vue Engineer, Search"
    assert "5+ years Vue" in (job_dir / tailor.POSTING_FILE).read_text(encoding="utf-8")
    assert (job_dir / tailor.JOB_DATA / "task.md").exists()

    tailor.write_json(job_dir / tailor.JOB_DATA / "tailored.json", tailored)
    tailor.check(config, "acme-senior-vue-engineer-search")
    checked = (job_dir / tailor.CHECK_FILE).read_text(encoding="utf-8")
    assert "## Ready to send?" in checked and "| Need | Shown? |" in checked
    assert list(job_dir.glob("*_Resume.pdf"))


def test_career_break_and_other_sections_stay_on_the_tailored_page(master, tailored):
    master["roles"][1]["end"] = "2021-01"
    master["career_break"] = [{"reason": "Caring for a family member", "start": "2021-02", "end": "2023-01"}]
    master["other"] = [{"heading": "Awards", "lines": ["Employee of the Year, 2022"]}]
    model = tailor.page_model(master, tailored)
    headings = [e["heading"] for e in model["sections"][0]["entries"]]
    assert headings[1] == "Career break - Caring for a family member"
    assert {"title": "Awards", "lines": [{"text": "Employee of the Year, 2022"}]} in model["sections"]


def test_year_only_end_is_old_only_once_the_whole_year_is(master):
    master["roles"][1].update(start="2008", end="2011")
    assert tailor.droppable(master, date(2026, 12, 1)) == {"globex"}
    assert tailor.droppable(master, date(2026, 9, 1)) == set()


def test_summary_may_run_four_lines_not_five(master, tailored):
    job = {"title": "Senior Vue Engineer", "requirements": []}
    words = "Senior Software Engineer shipping Vue and TypeScript product UI with LLM search".split()
    for count, ok in ((45, True), (57, False)):
        tailored["summary"] = " ".join((words * 8)[:count])
        problems = [v for v in tailor.check_selection(master, job, tailored) if v.startswith("summary")]
        assert (problems == []) is ok, (count, problems)
    assert f"{render.MAX_SUMMARY_LINES} lines" in tailor.system("Caladea")
