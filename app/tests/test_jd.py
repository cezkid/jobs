import httpx
import pytest

from resume import jd

BASE = "https://api.test/v1"


def raw_job(**over) -> dict:
    job = {
        "public_slug": "senior-vue-acme-x1",
        "title": " Senior Vue Engineer ",
        "company": "Acme",
        "url": "https://jobs.ashbyhq.com/acme/1",
        "source": "ashby",
        "description": "<p>Build UI&nbsp;with Vue�Node</p>",
        "enrichment": {
            "requirements": [
                {"text": "5+ years Vue", "priority": "required"},
                {"text": "GraphQL &amp; Apollo", "priority": "preferred"},
            ]
        },
        "reality": {"class": "fresh"},
    }
    job.update(over)
    return job


def client_for(status: int, body: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs/senior-vue-acme-x1"
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_unwraps_data_and_cleans_text():
    got = jd.fetch(client_for(200, {"data": raw_job()}), BASE, "senior-vue-acme-x1")
    assert got["title"] == "Senior Vue Engineer"
    assert "<p>" not in got["text"] and "�" not in got["text"]
    assert got["requirements"][1] == {"text": "GraphQL & Apollo", "priority": "preferred"}


def test_unknown_slug_raises():
    with pytest.raises(httpx.HTTPStatusError):
        jd.fetch(client_for(404), BASE, "senior-vue-acme-x1")


def test_missing_requirements_rejected():
    with pytest.raises(ValueError, match="requirements empty"):
        jd.parse(raw_job(enrichment={}))


def test_unknown_priority_rejected():
    raw = raw_job(enrichment={"requirements": [{"text": "Vue", "priority": "nice"}]})
    with pytest.raises(ValueError, match="unknown requirement priorities"):
        jd.parse(raw)


def extracted(**over) -> dict:
    got = {
        "title": " Staff Software Engineer, Core Products ",
        "company": " Gusto ",
        "requirements": [{"text": "10+ years software development", "priority": "required"}],
    }
    got.update(over)
    return got


def test_from_text_shape():
    got = jd.from_text("  Staff Software Engineer\nRuby on Rails, Vue  ", "https://gusto.com/job/1", extracted())
    assert got["public_slug"] == "gusto-staff-software-engineer-core-products"
    assert (got["title"], got["company"], got["source"]) == ("Staff Software Engineer, Core Products", "Gusto", "pasted")
    assert got["text"].startswith("Staff") and got["text"].endswith("Vue")
    assert got["enrichment"] == {} and got["reality"] == {}


def test_from_text_empty_requirements_rejected():
    with pytest.raises(ValueError, match="extracted requirements empty"):
        jd.from_text("posting", "", extracted(requirements=[]))


def test_from_text_unknown_priority_rejected():
    with pytest.raises(ValueError, match="unknown requirement priorities"):
        jd.from_text("posting", "", extracted(requirements=[{"text": "Vue", "priority": "nice"}]))
