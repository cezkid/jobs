import httpx
import pytest

from ingest import probe

BASE = "https://api.test/v1"


def row(title: str, **enrichment) -> dict:
    return {"title": f" {title} ", "company": "Providence", "work_mode": None, "enrichment": enrichment}


def test_probe_counts_nulls_and_joins_list_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        rows = [row("RN - ICU", category="healthcare"), row("Physician", category="healthcare", seniority="senior")]
        return httpx.Response(200, json={"data": rows, "meta": {"total": 685}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        got = probe.probe(client, BASE, {"category": ["healthcare"], "cities": ["Springfield", "Springfield Gardens"]})
    assert seen["cities"] == "Springfield,Springfield Gardens"
    assert got["total"] == 685
    assert got["tallies"]["seniority"] == {None: 1, "senior": 1}
    assert got["tallies"]["work_mode"] == {None: 2}
    assert got["titles"][0] == "RN - ICU | Providence"


def test_city_values_from_geo_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/geo/cities" and request.url.params["q"] == "springfield"
        return httpx.Response(200, json={"data": [{"value": "Springfield", "country": "us"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert probe.city_values(client, BASE, "springfield") == ["Springfield (us)"]


def test_parse_params_splits_lists_and_rejects_bare_key():
    assert probe.parse_params(["category=healthcare", "cities=Springfield,Springfield Gardens"]) == {
        "category": "healthcare", "cities": ["Springfield", "Springfield Gardens"],
    }
    with pytest.raises(SystemExit):
        probe.parse_params(["category"])
