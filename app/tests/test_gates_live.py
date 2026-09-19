import asyncio
import httpx
import pytest
from textual.widgets import DataTable, SelectionList

import cfg
import rank
import store
import tui
from ingest import freehire
from resume import jd
from text import html_to_text

SENIOR_PLUS = {"senior", "staff", "lead", "principal"}


@pytest.fixture(scope="module")
def polled(tmp_path_factory):
    config = cfg.load(cfg.PROFILES / "example.yml")
    conn = store.connect(tmp_path_factory.mktemp("db") / "jobs.db")
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        summary = freehire.run(config, conn, client)
    return config, conn, summary


def test_poller_returns_rows(polled):
    _, _, summary = polled
    assert summary["remote"]["fetched"] > 0
    assert summary["local"]["fetched"] > 0


def test_city_tier_rows_inside_listed_cities(polled):
    config, conn, _ = polled
    wanted = {c.casefold() for c in next(p for p in config["passes"] if p["tier"] == "local")["params"]["cities"]}
    local = [j for j in store.all_jobs(conn) if j["tier"] == "local"]
    assert local
    for j in local:
        assert wanted & {c.casefold() for c in j["cities"]}, (j["public_slug"], j["cities"])


def test_remote_rows_match_settled_filter(polled):
    _, conn, _ = polled
    remote = [j for j in store.all_jobs(conn) if j["tier"] == "remote"]
    assert remote
    for j in remote:
        assert j["work_mode"] == "remote", j["public_slug"]
        assert "us" in j["countries"], j["public_slug"]


def test_blocklisted_reposter_never_ranked(polled):
    config, conn, _ = polled
    ranked = rank.rank(store.all_jobs(conn), config)
    assert ranked
    assert [j["company_slug"] for j in ranked if j["company_slug"] == "jobgether"] == []


def test_tui_launches_and_filters_senior_plus(polled):
    config, conn, _ = polled
    db_file = conn.execute("PRAGMA database_list").fetchone()["file"]

    async def scenario():
        app = tui.JobsApp(db_file, config)
        async with app.run_test(size=(160, 50)) as pilot:
            levels = app.query_one("#seniority", SelectionList)
            levels.deselect_all()
            for i in range(levels.option_count):
                if levels.get_option_at_index(i).value in SENIOR_PLUS:
                    levels.select(levels.get_option_at_index(i).value)
            await pilot.pause()
            visible = app.visible_jobs()
            assert visible
            assert all(j["seniority"] in SENIOR_PLUS for j in visible)
            assert app.query_one("#table", DataTable).row_count == len(visible)

    asyncio.run(scenario())


def test_detail_jd_beats_stored_truncation(polled):
    config, conn, _ = polled
    job = next(j for j in rank.rank(store.all_jobs(conn), config) if j["tier"] == "remote" and j["description"])
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        full = jd.fetch(client, config["api"]["base"], job["public_slug"])
    assert len(full["text"]) > len(html_to_text(job["description"]))
    assert full["requirements"]


def test_second_poll_closes_nothing_new(polled):
    config, conn, _ = polled
    with httpx.Client(timeout=config["api"]["timeout_s"]) as client:
        again = freehire.run(config, conn, client)
    assert again["remote"]["closed"] == 0
