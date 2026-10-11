import json

import pytest

import cfg
from resume import confirmations, schema

EXAMPLE = cfg.APP / "resume" / "master.example.yml"
# same sources, same new term (Kubernetes), worded differently: one (b) repeat, no (a) repeat
FIRST = {"claim": "Shipped support search on Kubernetes", "sources": ["acme-rag-search"]}
REWORDED = {"claim": "Ran retrieval-augmented search on Kubernetes clusters", "sources": ["acme-rag-search"]}
OTHER = {"claim": "Cut checkout INP using Web Workers in Chrome", "sources": ["acme-inp"]}


def job(root, stage: str, folder: str, inferences: list[dict]):
    data = root / stage / folder / confirmations.JOB_DATA
    data.mkdir(parents=True)
    (data / "tailored.json").write_text(json.dumps({"entries": [], "inferences": inferences}), encoding="utf-8")
    (data / "jd.json").write_text(json.dumps({"title": folder.split(" - ")[-1]}), encoding="utf-8")


@pytest.fixture
def master() -> dict:
    return schema.load(EXAMPLE)


@pytest.fixture
def jobs_dir(tmp_path):
    # job 10 sorts after job 3 by number, not by name; stage folders never decide the order
    job(tmp_path, "2 Applied", "2 - Acme - Search Engineer", [FIRST])
    job(tmp_path, "1 To apply", "3 - Globex - Frontend Engineer", [OTHER])
    job(tmp_path, "1 To apply", "10 - Initech - Platform Engineer", [REWORDED])
    return tmp_path


def test_reworded_inference_on_same_sources_and_term_repeats_by_substance_only(jobs_dir, master):
    result = confirmations.measure(jobs_dir, master)
    assert (result["jobs"], result["inferences"], result["later_inferences"]) == (3, 3, 2)
    assert (result["repeat_a"], result["repeat_b"]) == (0, 1)
    assert [r["job"] for r in result["per_job"]] == [2, 3, 10]
    assert result["per_job"][2]["repeat_b"] == 1
    assert result["repeats"][0]["same_substance_as"] == 2
    assert result["top_terms"] == [("Kubernetes", 1)]
    assert result["share_b"] == 0.5
    assert not result["build_reuse"]  # 3 jobs, under the 8 the threshold needs


def test_same_wording_repeats_by_both_keys(tmp_path, master):
    job(tmp_path, "1 To apply", "1 - Acme - A", [FIRST])
    job(tmp_path, "1 To apply", "2 - Acme - B", [{**FIRST, "claim": "  shipped SUPPORT search\non Kubernetes "}])
    result = confirmations.measure(tmp_path, master)
    assert (result["repeat_a"], result["repeat_b"]) == (1, 1)


def test_repeat_inside_one_job_is_not_a_re_ask(tmp_path, master):
    job(tmp_path, "1 To apply", "1 - Acme - A", [FIRST, REWORDED])
    result = confirmations.measure(tmp_path, master)
    assert (result["repeat_a"], result["repeat_b"]) == (0, 0)


def test_different_new_term_or_sources_is_a_new_ask(tmp_path, master):
    job(tmp_path, "1 To apply", "1 - Acme - A", [FIRST])
    job(tmp_path, "1 To apply", "2 - Acme - B", [{**FIRST, "claim": "Shipped support search on OpenSearch"}])
    job(tmp_path, "1 To apply", "3 - Acme - C", [{**FIRST, "sources": ["acme-rag-search", "acme-inp"]}])
    assert confirmations.measure(tmp_path, master)["repeat_b"] == 0


def test_term_a_source_fact_carries_is_no_new_term(master):
    # Vue sits in the source's stack: only Kubernetes is the stretch to confirm
    claim = "Shipped Vue search on Kubernetes"
    assert set(confirmations.new_terms(claim, [confirmations.master_bullets(master)["acme-rag-search"]])) == {"kubernetes"}


def test_threshold_builds_reuse_from_eight_jobs_at_twenty_percent(tmp_path, master):
    for n in range(1, 9):
        job(tmp_path, "1 To apply", f"{n} - Acme - Job {n}", [FIRST, {**OTHER, "claim": f"Cut checkout INP {n}00ms"}])
    result = confirmations.measure(tmp_path, master)
    assert result["jobs"] == 8 and result["share_b"] == 0.5
    assert result["build_reuse"]


def test_without_show_no_claim_text_or_term_is_printed(jobs_dir, capsys):
    confirmations.main(["measure", str(jobs_dir), "--master", str(EXAMPLE)])
    out = capsys.readouterr().out
    assert "1 by sources + terms (b)" in out and "0 by wording (a)" in out
    for text in (FIRST["claim"], REWORDED["claim"], OTHER["claim"], "Kubernetes", "Chrome"):
        assert text not in out


def test_show_prints_repeated_claims_and_terms(jobs_dir, capsys):
    confirmations.main(["measure", str(jobs_dir), "--master", str(EXAMPLE), "--show"])
    out = capsys.readouterr().out
    assert REWORDED["claim"] in out and "Kubernetes x1" in out
    assert OTHER["claim"] not in out  # only repeats are named
