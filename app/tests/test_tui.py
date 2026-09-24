import asyncio

import pytest
from textual.widgets import DataTable, SelectionList

import cfg
import store
import tui
from conftest import make_job

CONFIG = cfg.load(cfg.PROFILES / "example.yml")


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "jobs.db"
    conn = store.connect(path)
    with conn:
        store.upsert(conn, [
            make_job("senior-a", seniority="senior"),
            make_job("staff-b", seniority="staff", collections=["fortune500"]),
            make_job("principal-c", seniority="principal", tier="local"),
            make_job("closed-d", seniority="senior", closed_at="2026-09-15T00:00:00Z"),
            make_job("blocked-e", seniority="lead", company_slug="jobgether"),
        ], store.utc_now())
    conn.close()
    return path


def table_slugs(app) -> list[str]:
    table = app.query_one("#table", DataTable)
    return [table.coordinate_to_cell_key((r, 0)).row_key.value for r in range(table.row_count)]


def test_launch_filter_senior_plus_and_open(db_path, monkeypatch):
    opened = []
    monkeypatch.setattr(tui.webbrowser, "open", opened.append)

    async def scenario():
        app = tui.JobsApp(db_path, CONFIG)
        async with app.run_test() as pilot:
            assert table_slugs(app) == ["staff-b", "senior-a", "principal-c"]
            app.query_one("#seniority", SelectionList).deselect("senior")
            await pilot.pause()
            assert table_slugs(app) == ["staff-b", "principal-c"]
            app.query_one("#table", DataTable).focus()
            await pilot.press("o")
            assert opened == ["https://boards.greenhouse.io/acme/jobs/staff-b"]

    asyncio.run(scenario())


def test_null_seniority_rows_visible_as_unspecified(tmp_path):
    path = tmp_path / "jobs.db"
    conn = store.connect(path)
    with conn:
        store.upsert(conn, [make_job("rn-a", seniority=None), make_job("senior-b")], store.utc_now())
    conn.close()

    async def scenario():
        app = tui.JobsApp(path, CONFIG)
        async with app.run_test() as pilot:
            assert sorted(table_slugs(app)) == ["rn-a", "senior-b"]
            app.query_one("#seniority", SelectionList).deselect(tui.UNSPECIFIED_LEVEL)
            await pilot.pause()
            assert table_slugs(app) == ["senior-b"]

    asyncio.run(scenario())
