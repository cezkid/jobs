import copy

import pytest

import cfg
from resume import report, schema, tailor

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


@pytest.mark.parametrize("mutate, expected", [
    (lambda t: t["entries"].pop(), "role 'globex' dropped"),
    (lambda t: t["entries"].append({"id": "initech", "title_mirror": None, "bullets": []}), "'initech' not a master role"),
    (lambda t: t["entries"][1]["bullets"][0].update(sources=["acme-inp"]), "source 'acme-inp' belongs to 'acme'"),
    (lambda t: t["entries"][1]["bullets"][0].update(text="Led design system migration w/ Vite"), "['Vite'] in none of its sources"),
    (lambda t: t["entries"][0].update(title_mirror="Staff Engineer"), "not part of job title"),
    (lambda t: t["entries"].append({"id": "evalkit", "title_mirror": "Search", "bullets": []}), "title_mirror on non-role"),
    (lambda t: t["coverage"].pop(), "requirement 1 missing"),
    (lambda t: t["coverage"][1].update(requirement=5), "requirement 5 out of range"),
    (lambda t: t["coverage"][1].update(evidence=["acme-rag-search"]), "'acme-rag-search' not a source of any on-page bullet"),
    (lambda t: t["entries"][0]["bullets"][0].update(text="x" * 181), "181 chars"),
])
def test_selection_violations(master, tailored, mutate, expected):
    mutate(tailored)
    violations = tailor.check_selection(master, JOB, tailored)
    assert any(expected in v for v in violations), violations


def test_moved_entity_resolves_through_inference(master, tailored):
    tailored["entries"][1]["bullets"][0]["text"] = "Led design system migration w/ Vite"
    tailored["inferences"] = [{"claim": "Vite build", "sources": ["globex-design-system"]}]
    assert tailor.check_selection(master, JOB, tailored) == []


def test_request_is_byte_identical_per_master_and_job(master):
    first = tailor.build_request(master, JOB)
    assert first == tailor.build_request(copy.deepcopy(master), copy.deepcopy(JOB))
    assert '"generated_words"' in first["prompt"]


def test_coverage_rows_drop_off_page_evidence(tailored):
    tailored["coverage"][0]["evidence"] = ["acme-rag-search"]
    rows = tailor.coverage_rows(JOB, tailored)
    assert [r["status"] for r in rows] == ["gap", "gap"]


def test_diff_marks_kept_rewritten_dropped_and_inferences(master, tailored):
    tailored["entries"][1]["bullets"][0]["text"] = master["roles"][1]["bullets"][0]["claim"]
    tailored["inferences"] = [{"claim": "Web Workers", "sources": ["acme-inp"]}]
    diff = report.diff_md(master, tailored, tailor.page_model(master, tailored))
    assert "- Web Workers\n  - from `acme-inp`" in diff
    assert "- title: Senior Software Engineer (Senior Vue Engineer)" in diff
    assert "- 1. rewritten: Cut checkout INP" in diff
    assert "- dropped `acme-rag-search`" in diff
    assert "- 1. kept `globex-design-system`" in diff
    assert "## evalkit\n\n- omitted" in diff
    assert "- dropped: Playwright, Retrieval-augmented generation (RAG), TanStack Query, Vite, eval harnesses" in diff


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
    assert (job_dir / tailor.CHECK_FILE).exists()
    assert list(job_dir.glob("*_Resume.pdf"))
