import copy

import pymupdf
import pytest
import yaml

from resume import letter, schema
from test_tailor import EXAMPLE, JOB

WHY = "I use Acme's search every week and want to make it faster for everyone else."
TAILORED = {"summary": "", "skills": [], "inferences": [], "entries": [{"id": "acme", "title_mirror": None, "bullets": [
    {"text": "Cut checkout INP 410ms -> 170ms moving cart recalculation to Web Workers", "sources": ["acme-inp"]}]}],
    "coverage": [{"requirement": 0, "evidence": ["acme-inp"], "note": "Vue on page"},
                 {"requirement": 1, "evidence": [], "note": "no GraphQL"}]}


@pytest.fixture
def master() -> dict:
    return copy.deepcopy(schema.load(EXAMPLE))


def answer(*paragraphs) -> dict:
    return {"paragraphs": [{"text": t, "sources": s} for t, s in paragraphs]}


GOOD = answer(
    (f"I'm applying for the Senior Vue Engineer, Search role at Acme. {WHY}", []),
    ("At Acme I built retrieval-augmented search over support docs, with an eval harness scoring answer grounding, "
     "so I know what makes search answers trustworthy and how to measure it before shipping.", ["acme-rag-search"]),
    ("I also led a design system migration across product surfaces at Globex, which taught me to move a whole "
     "product without stopping the teams building on it.", ["globex-design-system"]),
    ("I would welcome the chance to talk about the search work ahead.", []),
)


def found(master, ans, why=WHY):
    return [(s, r) for s, r, _ in letter.check(master, JOB, TAILORED, why, ans)]


def test_task_carries_no_contact_block_and_names_what_the_resume_never_shows(master):
    data = yaml.safe_load(letter.payload(master, JOB, TAILORED, WHY))
    assert "contact" not in data["master"] and data["your_words"] == WHY
    assert "graphql" in data["words_resume_never_shows"]
    assert [r["on_resume"] for r in data["job"]["requirements"]] == [True, False]


def test_a_draft_resting_on_cited_facts_passes(master):
    assert [f for f in found(master, GOOD) if f[0] == letter.FAIL] == []


def test_letter_overstatement_report_only(master):
    master["roles"][1]["bullets"][0]["claim"] = "Assisted with design system migration across product surfaces"
    ans = copy.deepcopy(GOOD)
    ans["paragraphs"][2]["text"] = ("Led design system migration across product surfaces at Globex, a "
                                    "company-wide effort, which taught me to move a product while other teams kept shipping.")
    got = found(master, ans)
    assert (letter.WARN, "hedge-upgrade") in got and (letter.WARN, "reach-claim") in got
    assert [f for f in got if f[0] == letter.FAIL] == []


def test_users_sentence_verbatim_exactly_once(master):
    reworded = copy.deepcopy(GOOD)
    reworded["paragraphs"][0]["text"] = "I'm applying for the role at Acme because I love its search."
    assert (letter.FAIL, "your-words") in found(master, reworded)


def test_a_name_or_number_outside_the_cited_facts_fails(master):
    padded = copy.deepcopy(GOOD)
    padded["paragraphs"][1]["text"] += " It served 2 million users on Kubernetes."
    assert (letter.FAIL, "unresolved-entity") in found(master, padded)


def test_facts_capped_at_five(master):
    master["roles"][0]["bullets"] += [{"id": f"acme-extra-{i}", "claim": f"Shipped release {i}"} for i in range(4)]
    many = copy.deepcopy(GOOD)
    many["paragraphs"][1]["sources"] = ["acme-rag-search", "acme-inp", "acme-extra-0", "acme-extra-1", "acme-extra-2"]
    assert (letter.FAIL, "too-many-facts") in found(master, many)


def test_filler_fails_the_ai_warns_on_the_users_own(master):
    filler = copy.deepcopy(GOOD)
    filler["paragraphs"][3]["text"] = "I am passionate about this role and would welcome a talk."
    assert (letter.FAIL, "letter-filler") in found(master, filler)
    keen = "I'm excited to apply because Acme's search is the one I use every week."
    mine = copy.deepcopy(GOOD)
    mine["paragraphs"][0]["text"] = f"I'm applying for the role at Acme. {keen}"
    assert (letter.WARN, "letter-filler") in found(master, mine, keen)


def test_over_400_words_fails_short_is_only_said(master):
    assert (letter.INFO, "letter-length") in found(master, GOOD)
    long = copy.deepcopy(GOOD)
    long["paragraphs"][3]["text"] = "I would welcome the chance to talk. " * 60
    assert (letter.FAIL, "letter-length") in found(master, long)


def test_pdf_one_page_same_typeface_black_whole_words(master, tmp_path):
    paragraphs = [p["text"] for p in GOOD["paragraphs"]]
    path = tmp_path / letter.file_name(master)
    path.write_bytes(letter.compile_letter(letter.page(master, paragraphs, letter.date(2026, 10, 1)), "Caladea"))
    assert path.name.endswith("_Cover_Letter.pdf")
    assert [n for n, ok, _ in letter.gates(path, "Caladea") if not ok] == []
    with pymupdf.open(path) as doc:
        text = doc[0].get_text()
    assert "Dear Hiring Team," in text and "October 1, 2026" in text and master["contact"]["name"] in text


def test_paste_text_has_no_contact_block(master):
    text = letter.paste_text(master, [p["text"] for p in GOOD["paragraphs"]])
    assert text.startswith("Dear Hiring Team,") and master["contact"]["email"] not in text
    assert text.rstrip().endswith(master["contact"]["name"])


def test_a_word_the_resume_says_in_another_form_is_no_gap(master):
    master["roles"][0]["bullets"][0]["claim"] = "Edit short-form video and caption every clip"
    job = {**JOB, "requirements": [{"text": "Edits with captions, never seen GraphQL", "priority": "required"}]}
    never = letter.never_shows(job, master)
    assert "edits" not in never and "captions" not in never and "graphql" in never


def test_a_text_box_letter_points_to_the_reel_the_posting_asks_for(master):
    master["contact"]["links"] = ["linkedin.com/in/jane", "vimeo.com/janedoe"]
    paragraphs = [p["text"] for p in GOOD["paragraphs"]]
    reel = {**JOB, "requirements": [{"text": "Please include a link to your reel", "priority": "required"}]}
    text = letter.paste_text(master, paragraphs, reel)
    assert "\n\nReel: vimeo.com/janedoe\n\nSincerely," in text
    folio = {**JOB, "requirements": [{"text": "Portfolio required", "priority": "required"}]}
    assert "Portfolio: vimeo.com/janedoe" in letter.paste_text(master, paragraphs, folio)
    # no ask, or only LinkedIn: nothing added
    assert "vimeo" not in letter.paste_text(master, paragraphs, JOB)
    master["contact"]["links"] = ["linkedin.com/in/jane"]
    assert "linkedin" not in letter.paste_text(master, paragraphs, reel)


def test_never_mention_quoted_term_fails_letter(master, monkeypatch):
    monkeypatch.setattr("about.load", lambda: {"never_mention": [{"said": 'never "design system"'}]})
    got = found(master, GOOD)
    assert (letter.FAIL, "never-mention") in got


def test_never_mention_warn_only_cases_letter(master, monkeypatch):
    monkeypatch.setattr("about.load", lambda: {"never_mention": [{"said": 'never "Globex"'}]})
    got = found(master, GOOD)
    assert (letter.WARN, "never-mention") in got and (letter.FAIL, "never-mention") not in got
