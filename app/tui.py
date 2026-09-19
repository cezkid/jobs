import argparse
import webbrowser
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Label, Select, SelectionList, Static, Switch

import cfg
import rank
import store
from text import html_to_text

# facet null on most non-tech rows (measured 2026-09-19: 93 of 100 healthcare)
UNSPECIFIED_LEVEL = "unspecified"


def level(job: dict) -> str:
    return job["seniority"] or UNSPECIFIED_LEVEL


def salary_label(job: dict) -> str:
    salary = rank.annual_usd_min(job)
    return f"${salary // 1000}k" if salary else ""


class JobsApp(App):
    TITLE = "jobs"
    CSS = """
    #filters { width: 32; padding: 0 1; }
    #filters Label { margin-top: 1; }
    #table { height: 1fr; }
    #detail { height: 45%; border-top: solid $accent; padding: 0 1; }
    """
    BINDINGS = [
        ("o", "open_url", "Open in browser"),
        ("r", "reload", "Reload"),
        ("slash", "focus_search", "Search"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: Path | str, config: dict):
        super().__init__()
        self.db_path = db_path
        self.config = config
        self.jobs: dict[str, dict] = {}
        self.title = config["profile"]["name"]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="filters"):
                yield Label("Title search")
                yield Input(id="search", placeholder="words in title")
                yield Label("Tier")
                tiers = [(p["label"], p["tier"]) for p in self.config["passes"]]
                yield Select(tiers, id="tier", prompt="All tiers")
                yield Label("Seniority")
                yield SelectionList[str](id="seniority")
                yield Label("Top companies only")
                yield Switch(id="top")
                yield Label("Include closed")
                yield Switch(id="closed")
            with Vertical():
                yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
                with VerticalScroll(id="detail"):
                    yield Static(id="detail-body", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#table", DataTable).add_columns("Tier", "Title", "Company", "Level", "Salary", "Top", "Posted", "Alerted")
        self.action_reload()

    def action_reload(self) -> None:
        conn = store.connect(self.db_path)
        try:
            ranked = rank.rank(store.all_jobs(conn, include_closed=True), self.config)
        finally:
            conn.close()
        self.jobs = {j["public_slug"]: j for j in ranked}
        levels = sorted({level(j) for j in ranked})
        seniority = self.query_one("#seniority", SelectionList)
        keep = set(seniority.selected) if seniority.option_count else set(levels)
        seniority.clear_options()
        seniority.add_options([(level, level, level in keep) for level in levels])
        self.apply_filters()

    def visible_jobs(self) -> list[dict]:
        search = self.query_one("#search", Input).value.strip().lower()
        tier = self.query_one("#tier", Select).value
        levels = set(self.query_one("#seniority", SelectionList).selected)
        top_only = self.query_one("#top", Switch).value
        include_closed = self.query_one("#closed", Switch).value
        boost = self.config["rank"]["boost_collections"]
        return [
            j for j in self.jobs.values()
            if (include_closed or not j["closed_at"])
            and (tier is Select.NULL or j["tier"] == tier)
            and level(j) in levels
            and (not top_only or rank.collections_hit(j, boost))
            and search in j["title"].lower()
        ]

    def apply_filters(self) -> None:
        table = self.query_one("#table", DataTable)
        table.clear()
        boost = self.config["rank"]["boost_collections"]
        visible = self.visible_jobs()
        for j in visible:
            top = ",".join(c for c in j["collections"] if c in boost)
            table.add_row(
                j["tier"], j["title"], j["company"], j["seniority"] or "", salary_label(j), top,
                (j["posted_at"] or "")[:10], (j["alerted_at"] or "")[:10], key=j["public_slug"],
            )
        self.sub_title = f"{len(visible)} of {len(self.jobs)}"
        self.show_detail(self.current_job())

    def current_job(self) -> dict | None:
        table = self.query_one("#table", DataTable)
        if not table.row_count:
            return None
        return self.jobs[table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value]

    def show_detail(self, job: dict | None) -> None:
        body = self.query_one("#detail-body", Static)
        if job is None:
            body.update("")
            return
        head = f"{job['title']}\n{job['company']} | {job['location'] or ''} | {job['work_mode']} | {salary_label(job)}\n{job['url']}\ntailor.py {job['public_slug']}\n\n"
        body.update(Text(head + html_to_text(job["description"])))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.show_detail(self.jobs.get(event.row_key.value))

    def on_input_changed(self, _: Input.Changed) -> None:
        self.apply_filters()

    def on_select_changed(self, _: Select.Changed) -> None:
        self.apply_filters()

    def on_selection_list_selected_changed(self, _: SelectionList.SelectedChanged) -> None:
        self.apply_filters()

    def on_switch_changed(self, _: Switch.Changed) -> None:
        self.apply_filters()

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_open_url(self) -> None:
        job = self.current_job()
        if job:
            webbrowser.open(job["url"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Browse ranked jobs")
    ap.add_argument("--db", help="override config db path")
    args = ap.parse_args()
    config = cfg.load()
    JobsApp(args.db or cfg.db_path(config), config).run()


if __name__ == "__main__":
    main()
