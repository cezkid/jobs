"""Application systems Job Finder can fill, picked by the posting link.

Each module here implements the same few names (contract checked by tests/test_apply_form.py):

    NAME                         shown to the user ("Ashby")
    matches(url) -> bool         this system's posting or application link
    application_url(url) -> str  the page the form is on
    questions(url) -> list       the form's questions, via apply.questions.question()
    READY                        CSS selector present once the form has loaded
    fill(page, q, resume_file)   type q["answer"] into the page -> "ok" | "ASK ..." | "FAIL ..."
    ids_on_page(page) -> list    question ids the page shows (finds ones the file lacks)
    SOURCES                      freehire `source` slugs whose links land here (test_systems_live.py)
    EXAMPLES                     a few anonymised link shapes (acme): each matches this system only

Optional, for forms spread over pages (start box, then the form; "Step 1 of 5"):

    PER_PAGE = True              fill works on the tab the user has open, never a fresh page 1
    fill(...) -> "LATER ..."     box on another page (questions.LATER); single-page systems FAIL
    page=                        on each question(): section / step it is on (questions.question)
    read(page) -> list           questions off the page the user is on; prepare merges them into
                                 the answers file page by page (questions.merge)
    on_tab(url, tab_url) -> bool this application's tab; default below

Optional, what leaves when:

    FILE_ON_CHOICE = True        a chosen file goes to the employer's site at once, before Submit
                                 (measured): prepare tells the AI to say so in the upload yes

Optional, for the live test:

    QUESTIONS_OVER_HTTP = True   questions(url) is a plain HTTP read (no browser): the live test runs it

Every module in this package is a system - a new one is one new file, no list to edit (five
systems were added side by side in 2026-10; a shared list was the file every branch touched).
Add one: app/docs/apply/apply-systems.md.
"""
import importlib
import pkgutil
from urllib.parse import urlsplit


def discover() -> list:
    """Every module here, by name: the contract test checks each keeps the contract."""
    return [importlib.import_module(f"{__name__}.{m.name}")
            for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name)]


SYSTEMS = discover()
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


def on_tab(system, url: str, tab_url: str) -> bool:
    """A tab already open on this application: same host + the posting id (last part parse_url
    gives), else the application page's path. Another employer's form, or another job on the same
    board (UKG keeps the job in the query, its path is the same for all), never matches."""
    app, tab = urlsplit(system.application_url(url)), urlsplit(tab_url)
    if app.hostname != tab.hostname:
        return False
    if hasattr(system, "parse_url"):
        return system.parse_url(url)[-1] in tab_url
    return len(app.path) > 1 and tab.path.startswith(app.path)


def tab_match(system, url: str):
    """match for browser.page_at: the system's own on_tab, else the default."""
    if hasattr(system, "on_tab"):
        return lambda tab_url: system.on_tab(url, tab_url)
    return lambda tab_url: on_tab(system, url, tab_url)
