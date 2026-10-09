"""`pytest --changed` picks the tests a change can reach - and stays off the browser fillers for one
it can't (affected.py)."""
import affected


def picked(*files, depth=affected.DEPTH):
    return affected.select(list(files), depth)[0]


def test_a_module_change_runs_its_tests_and_its_users_tests_not_the_browser_fillers():
    tests = picked("app/rank.py")
    assert {"test_rank.py", "test_best.py", "test_today.py", "test_alert.py"} <= tests
    assert "test_apply_in_window.py" not in tests and "test_pages.py" not in tests
    # widened on request, the fillers come back (filler -> questions -> tailor -> report -> rank)
    assert "test_apply_lever.py" in picked("app/rank.py", depth=99)


def test_a_command_a_test_runs_through_jobs_py_counts():
    # test_ai runs argv ["jobs.py", "ai"]; a bare "email" in a form test is no command run
    assert "test_ai.py" in picked("app/ai.py")
    assert "test_apply_in_window.py" not in picked("app/alert.py")


def test_data_files_docs_and_test_setup():
    assert "test_rank.py" in picked("app/profiles/example.yml")
    assert "test_docs.py" in picked("app/skills/job-setup.md")
    assert picked("app/tests/conftest.py") is None and picked("pyproject.toml") is None
    assert picked("app/tests/test_rank.py") == {"test_rank.py"}


def test_a_site_change_runs_every_site_test():
    # SITE_TESTS named two files that never existed and left test_pages out (2026-10-09)
    assert all((affected.TESTS / t).exists() for t in affected.SITE_TESTS)
    assert set(affected.SITE_TESTS) <= picked("docs/index.html")


def test_parts_split_the_suite_site_vs_app_claims_in_both():
    assert affected.parts(["app/rank.py", "AGENTS.md"]) == {"app"}
    assert affected.parts(["docs/index.html", "app/web/pages.py"]) == {"site"}
    assert affected.parts(["docs/index.html", "app/rank.py"]) == affected.parts([]) == {"app", "site"}
    site, app = "app/tests/test_pages.py::test_x", "app/tests/test_rank.py::test_y[a]"
    assert affected.in_part(site, "site") and not affected.in_part(site, "app")
    assert affected.in_part(app, "app") and not affected.in_part(app, "site")
    claims = "app/tests/test_site.py::test_site_claims_still_match_the_app"
    assert affected.in_part(claims, "app") and affected.in_part(claims, "site")
