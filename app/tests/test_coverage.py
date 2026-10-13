import httpx
import pytest

from ingest import coverage

BASE = "https://api.test/v1"


@pytest.mark.parametrize("link, system, board_link", [
    ("https://jobs.ashbyhq.com/candidhealth/f770bdc1-6704-44c6-9417-b98c1a4c75c4?src=x", "ashby",
     "https://jobs.ashbyhq.com/candidhealth"),
    ("https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers/job/Remote/Software-Engineer_2019448", "workday",
     "https://cisco.wd5.myworkdayjobs.com/Cisco_Careers"),
    ("https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/89355", "oracle",
     "https://edmn.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1"),
    ("https://careers-lmi.icims.com/jobs/14588/full-stack-developer/job", "icims", "https://careers-lmi.icims.com"),
    ("https://careers.veeco.com/job/Somerset-Software-Engineer-NJ-08873/1436013200/", "successfactors (likely)",
     "https://careers.veeco.com/"),
    ("https://jobs.siemens.com/en_US/externaljobs/JobDetail/524931", "unknown", "https://jobs.siemens.com/"),
])
def test_board_names_system_and_link_to_submit(link, system, board_link):
    got = coverage.board(link)
    assert (got["system"], got["link"]) == (system, board_link)


def test_greenhouse_hosts_share_one_board():
    assert coverage.board("https://boards.greenhouse.io/doordashusa/jobs/8212984")["key"] == \
        coverage.board("https://job-boards.greenhouse.io/doordashusa/jobs/1?utm_source=freehire.me")["key"]


@pytest.mark.parametrize("link, pid", [
    ("https://jobs.ashbyhq.com/credal/9e2c7a06-4be8-47e8-884e-5978fc38c122", "9e2c7a06-4be8-47e8-884e-5978fc38c122"),
    ("https://usaa.wd1.myworkdayjobs.com/USAAJOBSWD/job/Software-Engineer-I_R0120279-1", "r0120279-1"),
    ("https://careers-lmi.icims.com/jobs/14588/full-stack-developer/job", "14588"),
    ("https://careers.veeco.com/job/Somerset-Software-Engineer-NJ-08873/1436013200/", "1436013200"),
    ("https://mlp.eightfold.ai/careers/job", None),
])
def test_posting_id(link, pid):
    assert coverage.posting_id(link) == pid


def test_company_guess_from_board_name():
    assert coverage.company_guess("https://jobs.lever.co/dutch/ef1c88fa") == "dutch"
    assert coverage.company_guess("https://careers-lmi.icims.com/jobs/1/x/job") == "lmi"
    assert coverage.company_guess("https://jobs.siemens.com/x/524931") is None


def client_for(rows: list[dict], *, search_rows: list[dict] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if "q" in params:
            return httpx.Response(200, json={"data": search_rows if search_rows is not None else rows})
        offset = int(params["offset"])
        return httpx.Response(200, json={"data": rows[offset:offset + coverage.PAGE]})

    return httpx.Client(transport=httpx.MockTransport(handler))


def row(url: str, title: str = "Software Engineer") -> dict:
    return {"company": "Acme Corp", "company_slug": "acme", "url": url, "title": f" {title} ", "source": "ashby"}


LINK = "https://jobs.ashbyhq.com/acme/11111111-2222-3333-4444-555555555555"


def test_found_by_posting_id_inside_stored_url():
    rows = [row("https://jobs.ashbyhq.com/acme/99999999-2222-3333-4444-555555555555"),
            row(LINK + "?utm_source=freehire.me", "Staff Engineer, Data")]
    with client_for(rows) as client:
        got = coverage.check(client, BASE, LINK, "Acme")
    assert (got["verdict"], got["title"]) == ("found", "Staff Engineer, Data")


def test_board_read_but_posting_missing():
    rows = [row("https://jobs.ashbyhq.com/acme/99999999-2222-3333-4444-555555555555")]
    with client_for(rows) as client:
        assert coverage.check(client, BASE, LINK, "Acme")["verdict"] == "posting_missing"


def test_company_known_from_another_site_means_board_missing():
    rows = [row("https://boards.greenhouse.io/acme/jobs/123")]
    with client_for(rows) as client:
        assert coverage.check(client, BASE, LINK, "Acme")["verdict"] == "board_missing"


def test_company_not_in_freehire_and_no_company():
    other = [{"company": "Zeta", "company_slug": "zeta", "url": "https://x.test/1", "title": "x"}]
    with client_for([], search_rows=other) as client:
        assert coverage.check(client, BASE, LINK, "Acme")["verdict"] == "company_missing"
        assert coverage.check(client, BASE, "https://jobs.siemens.com/x/524931")["verdict"] == "no_company"


def test_pages_through_company_rows():
    rows = [row(f"https://jobs.ashbyhq.com/acme/{i}") for i in range(coverage.PAGE + 5)]
    rows.append(row(LINK))
    with client_for(rows) as client:
        got = coverage.check(client, BASE, LINK, "Acme")
    assert got["verdict"] == "found" and got["rows"] == coverage.PAGE + 6


def test_read_lines(tmp_path):
    f = tmp_path / "links.txt"
    f.write_text("# header\n\nhttps://a.test/1 | Acme Corp\nhttps://b.test/2\n")
    assert coverage.read_lines(str(f)) == [("https://a.test/1", "Acme Corp"), ("https://b.test/2", None)]
