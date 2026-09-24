"""Application systems Job Finder can fill, picked by the posting link.

Each module here implements the same few names (contract checked by tests/test_apply_form.py):

    NAME                         shown to the user ("Ashby")
    matches(url) -> bool         this system's posting or application link
    application_url(url) -> str  the page the form is on
    questions(url) -> list       the form's questions, via apply.questions.question()
    READY                        CSS selector present once the form has loaded
    fill(page, q, resume_file)   type q["answer"] into the page -> "ok" | "ASK ..." | "FAIL ..."
    ids_on_page(page) -> list    question ids the page shows (finds ones the file lacks)

Add one: app/docs/apply-systems.md.
"""
from apply.systems import ashby

SYSTEMS = [ashby]
# filled another way: say so instead of "not supported"
ELSEWHERE = {"myworkdayjobs.com": "Workday - use `apply` + the Chrome extension (job-apply skill, Steps)",
             "myworkday.com": "Workday - use `apply` + the Chrome extension (job-apply skill, Steps)"}


def for_url(url: str):
    for system in SYSTEMS:
        if system.matches(url):
            return system
    return None


def elsewhere(url: str) -> str | None:
    return next((how for host, how in ELSEWHERE.items() if host in url), None)
