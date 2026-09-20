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


FACETS = {"category": {"finance": 16032, "healthcare": 30032, "sales": 84609},
          "work_mode": {"remote": 5871, "hybrid": 900}}


def facet_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs/facets"
        assert request.url.params["countries"] == "us"
        return httpx.Response(200, json={"data": {"total": 754737, "facets": FACETS}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_facet_values_sorts_every_facet_by_count():
    with facet_client() as client:
        got = probe.facet_values(client, BASE, {"countries": "us"})
    assert list(got) == ["category", "work_mode"]
    assert got["category"] == [("sales", 84609), ("healthcare", 30032), ("finance", 16032)]


def test_facet_values_narrows_to_one_facet():
    with facet_client() as client:
        got = probe.facet_values(client, BASE, {"countries": "us"}, "work_mode")
    assert got == {"work_mode": [("remote", 5871), ("hybrid", 900)]}


def test_facet_values_rejects_unknown_facet_instead_of_answering_empty():
    with facet_client() as client:
        with pytest.raises(SystemExit, match="category, work_mode"):
            probe.facet_values(client, BASE, {"countries": "us"}, "seniority")


def test_facets_flag_does_not_swallow_a_filter_param(monkeypatch, capsys):
    real_client = httpx.Client
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        return httpx.Response(200, json={"data": {"total": 754737, "facets": FACETS}})

    monkeypatch.setattr("sys.argv", ["probe", "--facets", "countries=us"])
    monkeypatch.setattr(probe.cfg, "defaults", lambda: {"api": {"base": BASE, "timeout_s": 5}})
    monkeypatch.setattr(probe.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    probe.main()
    # countries=us reached the request as a filter, not as the facet name
    assert seen == {"countries": "us"}
    out = capsys.readouterr().out
    assert out.startswith("category: sales 84609")
    assert "work_mode: remote 5871" in out
