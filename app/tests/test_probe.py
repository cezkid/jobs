import httpx
import pytest

from ingest import probe

BASE = "https://api.test/v1"


def row(title: str, **enrichment) -> dict:
    return {"title": f" {title} ", "company": "Acme Health", "work_mode": None, "enrichment": enrichment}


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
    assert got["titles"][0] == "RN - ICU | Acme Health"


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


def test_probe_and_facets_stop_on_a_filter_the_search_ignores():
    def handler(request: httpx.Request) -> httpx.Response:
        meta = {"total": 798143, "ignored_params": [{"param": "bogus_param"}]}
        if request.url.path.endswith("/facets"):
            return httpx.Response(200, json={"data": {"facets": FACETS}, "meta": meta})
        return httpx.Response(200, json={"data": [row("Anything")], "meta": meta})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SystemExit, match="bogus_param"):
            probe.probe(client, BASE, {"bogus_param": "1"})
        with pytest.raises(SystemExit, match="bogus_param"):
            probe.facet_values(client, BASE, {"bogus_param": "1"})


def test_title_counts_per_form_open_and_last_30_days():
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        asked.append(params)
        totals = {('"registered nurse"', None): 50, ('"registered nurse"', "30"): 11,
                  ('"RN"', None): 19827, ('"RN"', "30"): 6400}
        return httpx.Response(200, json={"data": [], "meta": {"total": totals[params["q"], params.get("posted_within_days")]}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        got = probe.title_counts(client, BASE, {"countries": ["us"]}, ["registered nurse", "RN"])
    assert got == [("registered nurse", 50, 11), ("RN", 19827, 6400)]
    assert all(a["q_fields"] == "title" and a["countries"] == "us" and a["limit"] == "1" for a in asked)


# /jobs/facets ignores q_fields (meta.ignored_params, 2026-10-09): a title search's facets came back
# as an error, and without q_fields they count the words anywhere in a posting. Tallied off the rows
def test_title_search_facets_are_tallied_off_its_rows_never_the_facets_endpoint():
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs/search"
        assert request.url.params["q"] == '"compliance"' and request.url.params["q_fields"] == "title"
        pages.append(int(request.url.params["offset"]))
        rows = [dict(row("Compliance Analyst", category="legal"), work_mode="remote", requires_clearance=True),
                row("Trade Compliance Manager", category="management"),
                row("Compliance Officer", category="legal")]
        return httpx.Response(200, json={"data": rows if pages[-1] == 0 else [], "meta": {"total": 3}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        got = probe.facet_values(client, BASE, {"q": "compliance", "q_fields": "title", "countries": "us"})
        assert got["category"] == [("legal", 2), ("management", 1)]
        assert got["work_mode"] == [("-", 2), ("remote", 1)]
        assert got["requires_clearance"] == [("-", 2), ("true", 1)]
        assert pages == [0], "3 of 3 read: no second page"
        assert probe.facet_values(client, BASE, {"q": "compliance", "q_fields": "title"}, "category") == {
            "category": [("legal", 2), ("management", 1)]}
