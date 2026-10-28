"""Gem (jobs.gem.com): questions from the job board's own public read, answers typed into its React form.

Measured facts and why each rule exists: app/docs/apply/gem.md.
"""
import re

import httpx

from apply import dom
from apply.questions import key_from_title, left_on_page, question, signs

NAME = "Gem"
# the page's own read (gem.md "Where the form comes from"): a query, the board + posting id only
GRAPHQL = "https://jobs.gem.com/api/public/graphql"
QUERY = """
fragment Q on PublicOatsQuestion { extId answerType displayType text isRequired options { extId value } }
fragment D on PublicOatsDemographicSurveyQuestion { extId answerType displayType text options { extId value } }
query ExternalJobPosting($boardId: String!, $extId: String!) {
  oatsExternalJobPosting(boardId: $boardId, extId: $extId) { title isApplicationFormHidden }
  oatsJobPostFieldsAndQuestions(jobBoardVanityPath: $boardId, jobPostExtId: $extId) {
    fields { fieldType isRequired } questions { ...Q }
    demographicSurvey { surveyType questions { ...D } } } }"""
# board, posting id ("jobpost:..." in base64, so it starts am9icG9zdD); freehire's links add ?utm_source=freehire.me
POSTING_URL = re.compile(r"https?://jobs\.gem\.com/([\w-]+)/(am9icG9zdD[\w-]+)/?(?:[?#].*)?$")
SOURCES = ("gem",)
EXAMPLES = ("https://jobs.gem.com/acme/am9icG9zdDqcyLhlgwyA4nm6KGEaTGtc",
            "https://jobs.gem.com/acme/am9icG9zdDqcyLhlgwyA4nm6KGEaTGtc?utm_source=freehire.me")
# questions() is one plain POST of the page's own read, no browser: the live test runs it
QUESTIONS_OVER_HTTP = True
# the first name box: on the page once the form has drawn (after the reads come back); the file boxes
# are hidden under their drop areas, never "visible"
READY = "input[type=text]"
# Gem's own boxes, by its field type: (label on the page, kind, key) - gem.md "Boxes"
FIELDS = {"FIRST_NAME": ("First name", "text", "first_name"), "LAST_NAME": ("Last name", "text", "last_name"),
          "EMAIL": ("Email", "email", "email"), "LINKEDIN_URL": ("LinkedIn URL", "url", "linkedin"),
          "PHONE": ("Phone number", "phone", "phone"), "LOCATION": ("Location", "text", "location"),
          "COMPANY": ("Current company", "text", None), "JOB_TITLE": ("Current title", "text", None),
          "RESUME": ("Resume", "file", "resume"), "COVER_LETTER": ("Cover letter", "file", "cover_letter")}
# question answerType -> shared kind; NUMERIC_RATING (a row of numbers) is asked as a number, filled by hand
KIND = {"SHORT_TEXT": "text", "LONG_TEXT": "longtext", "SINGLE_SELECT": "choice", "MULTI_SELECT": "multichoice",
        "NUMERIC_RATING": "number", "FILE": "file"}
# the voluntary survey Gem draws by its type, labels + options its own (gem.md "Voluntary survey", 1 form
# opened 2026-10-26); the disability part of EEOC is on no open form yet: left to ids_on_page to name
SURVEY = {"Gender": ["Male", "Female", "Decline to self-identify"],
          "Race": ["Hispanic or Latino", "White (Not Hispanic or Latino)",
                   "Black or African American (Not Hispanic or Latino)",
                   "Native Hawaiian or Other Pacific Islander (Not Hispanic or Latino)",
                   "Asian (Not Hispanic or Latino)",
                   "American Indian or Alaskan Native (Not Hispanic or Latino)",
                   "Two or more races (Not Hispanic or Latino)", "Decline to self-identify"],
          "Veteran status": ["I identify as one or more of the classifications of a protected veteran listed above",
                             "I am not a protected veteran",
                             "I decline to self-identify for protected veteran status"]}
SURVEY_PARTS = {"EEO": ("Gender", "Race"), "EEOV": ("Gender", "Race", "Veteran status"),
                "EEOC": ("Gender", "Race", "Veteran status")}
# a dropdown's open list: questions show role=option, the voluntary survey role=menuitem (gem.md "Widgets")
MENU = "#floating-ui-portal [role=option], #floating-ui-portal [role=menuitem]"
# Gem's LinkedIn check (gem.md "LinkedIn URL"): anything before linkedin.com must end in a dot
LINKEDIN = re.compile(r"^(.+\.)?linkedin\.com/in/[^/?#]{3,}", re.I)
# the page marks the box it is about to fill with this attribute, so a locator can find it again
MARK = "data-jf"


def matches(url: str) -> bool:
    return bool(POSTING_URL.match(url.strip()))


def parse_url(url: str) -> tuple[str, str]:
    """(board, posting id)."""
    m = POSTING_URL.match(url.strip())
    if not m:
        raise ValueError(f"not a jobs.gem.com posting link: {url}")
    return m.group(1), m.group(2)


def application_url(url: str) -> str:
    board, posting = parse_url(url)
    return f"https://jobs.gem.com/{board}/{posting}"


def plain(text: str) -> str:
    """A title as the page shows it to a reader: Gem prints an employer's **bold** marks as typed."""
    return " ".join(text.replace("*", " ").split())


def from_read(data: dict) -> list[dict]:
    """The shared questions, in page order: Gem's own boxes, the employer's questions, the survey."""
    posting, form = data.get("oatsExternalJobPosting"), data.get("oatsJobPostFieldsAndQuestions")
    if not posting or not form:
        raise ValueError("posting not found - it may have closed")
    if posting.get("isApplicationFormHidden"):
        raise ValueError("the posting shows no application form - the employer takes applications elsewhere")
    out = []
    for f in form.get("fields") or []:
        title, kind, key = FIELDS.get(f["fieldType"], (f["fieldType"].replace("_", " ").capitalize(), "text", None))
        out.append(question(f"field:{f['fieldType']}", title, kind, bool(f.get("isRequired")), key=key,
                            native=f"field:{f['fieldType']}"))
    for q in form.get("questions") or []:
        if q["answerType"] == "DISPLAY_ONLY":  # words on the form, no box
            continue
        kind, options = KIND.get(q["answerType"], "text"), [o["value"].strip() for o in q.get("options") or []]
        if kind == "choice" and sorted(options) == ["No", "Yes"]:
            kind = "yesno"
        title = plain(q["text"])
        out.append(question(q["extId"], title, kind, bool(q.get("isRequired")), options, key_from_title(title, kind),
                            f"{q['answerType']}:{q.get('displayType')}"))
    survey = form.get("demographicSurvey") or {}
    for title in SURVEY_PARTS.get(survey.get("surveyType"), ()):
        out.append(question(f"survey:{title}", title, "choice", False, SURVEY[title], native="survey"))
    for q in survey.get("questions") or []:  # an employer's own survey questions: none on open forms yet
        out.append(question(q["extId"], plain(q["text"]), "choice", False,
                            [o["value"].strip() for o in q.get("options") or []], native="survey:own"))
    return out


def form_read(url: str) -> dict:
    board, posting = parse_url(url)
    r = httpx.post(GRAPHQL, timeout=30, json={"operationName": "ExternalJobPosting", "query": QUERY,
                                              "variables": {"boardId": board, "extId": posting}})
    r.raise_for_status()
    return r.json().get("data") or {}


def questions(url: str) -> list[dict]:
    return from_read(form_read(url))


def closed(url: str) -> str | None:
    """Why the form isn't there (form.closed): None = Gem still has the posting."""
    try:
        data = form_read(url)
    except httpx.HTTPError as e:
        return f"can't tell if the posting is open - Gem didn't answer ({type(e).__name__})"
    return None if data.get("oatsExternalJobPosting") else "the posting is no longer on the employer's Gem board - it may have closed"


# every label the form shows over a box, as plain words (Gem's question blocks carry no ids of their own:
# a label span, then the box under it - gem.md "Widgets")
# Gem's question blocks carry no ids of their own: a label, then the box beside it - its next sibling, or
# its parent's when the label sits in a header with help words under it (gem.md "Widgets")
SCRIPT = """
  const plain = s => s.replace(/\\*/g, ' ').replace(/\\s+/g, ' ').trim();
  const own = e => plain([...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' '));
  const boxes = 'input:not([type=hidden]), textarea:not([name$="captcha-response"]), button[type=button]';
  const beside = e => [e.nextElementSibling, e.parentElement && e === e.parentElement.firstElementChild
                       ? e.parentElement.nextElementSibling : null].find(s => s && (s.matches(boxes) || s.querySelector(boxes)));
  const labels = () => [...document.querySelectorAll('span, div')]
    .filter(e => !e.closest('#floating-ui-portal') && own(e) && beside(e));
"""
# every label over a box, as plain words: help words above a block (the survey's) are no label - the box
# beside a label holds no words of its own outside its options, button and upload area
LABELS = "() => {" + SCRIPT + """
  const words = s => [...s.querySelectorAll('span, div')].some(x => own(x) && !x.closest('label, button, [role=presentation]'));
  // a chosen file's name shows over its drop area like a label: no question
  return labels().filter(e => !words(beside(e)) && !/\\.(pdf|docx?)$/i.test(own(e))).map(own);
}"""
# mark the block under the label `title` (label + box) so a locator finds it again
FIND = "([title, mark]) => {" + SCRIPT + """
  document.querySelectorAll(`[${mark}]`).forEach(e => e.removeAttribute(mark));
  const label = labels().find(e => own(e) === title);
  if (!label) return false;
  let block = label.parentElement;
  while (!block.contains(beside(label))) block = block.parentElement;
  block.setAttribute(mark, title);
  return true;
}"""


def ids_on_page(page) -> list[str]:
    """Question ids the page shows: each label matched to the posting's questions (read again - the page
    gives no ids); a label the read lacks kept as `label:<words>`, so fill names it."""
    try:
        by_title = {q["title"]: q["id"] for q in questions(page.url)}
    except (ValueError, httpx.HTTPError):
        by_title = {}
    return [by_title.get(t, f"label:{t}") for t in dict.fromkeys(page.evaluate(LABELS))]


def box_of(page, q: dict):
    """The question's block, found by its label (try reads how each shows its answer)."""
    page.evaluate(FIND, [q["title"], MARK])
    return page.locator(f'[{MARK}="{q["title"]}"]').first


def norm(s: str) -> str:
    return " ".join(str(s).split())


def wanted(q: dict) -> list[str]:
    value = q["answer"]
    if isinstance(value, list):
        return [norm(v) for v in value]
    return [("Yes" if dom.yes(value) else "No") if q["kind"] == "yesno" else norm(value)]


def ticks(box) -> tuple[list, list[str]]:
    """A radio or tick set: the inputs (id = the option's own id) and each one's label words."""
    members = box.locator("input[type=radio], input[type=checkbox]").all()
    names = [norm(m.evaluate("e => e.labels && e.labels[0] ? e.labels[0].innerText : ''")) for m in members]
    return members, names


def put_menu(page, box, want: str) -> str:
    """Gem's dropdown: a button opens a list in the page's floating layer; the option that is the
    answer is clicked - never the first offered. The button then shows the pick."""
    button = box.locator("button[type=button]").first
    button.scroll_into_view_if_needed()
    button.click()
    options = page.locator(MENU)
    try:
        options.first.wait_for(timeout=5000)
    except Exception:
        return "FAIL the list didn't open - pick it on the page"
    texts = [norm(t) for t in options.all_inner_texts()]
    if want not in texts:
        page.keyboard.press("Escape")
        return f"ASK no option '{want}'; offered: {', '.join(texts)[:200]}"
    options.nth(texts.index(want)).click()
    page.wait_for_timeout(200)
    got = norm(button.inner_text())
    return "ok" if got == want else f"FAIL shows '{got}'"


def put_file(box, path: str) -> str:
    """The box shows the chosen file's name above it (gem.md "Resume box"); Gem keeps the file in the
    page until Apply - nothing is sent when it is chosen (read in its script, 2026-10-26)."""
    box.locator("input[type=file]").first.set_input_files(path)
    name = path.rsplit("/", 1)[-1]
    try:
        box.get_by_text(name).first.wait_for(timeout=5000)
    except Exception:
        return "ASK upload not confirmed on page - check the resume box"
    return "ok"


def put_text(box, value: str, kind: str) -> str:
    field = box.locator("textarea:not([name$='captcha-response']), input[type=text], input:not([type])").first
    field.scroll_into_view_if_needed()
    return dom.put_text(field, value, kind, editable=False)


def holds(page, q: dict) -> bool:
    """The answer still shows, read off the page as a person sees it (form.recheck): a dropdown by its
    button's words, a tick by each option's checked state, a file by its name, a box by its value."""
    box = box_of(page, q)
    if not box.count():
        return False
    kind, value = q["kind"], q["answer"]
    if kind == "file":  # the chosen file's name shows over the box
        return value is not True or bool(re.search(r"\.(pdf|docx?)\b", box.inner_text(), re.I))
    members, names = ticks(box)
    if kind in ("choice", "multichoice", "yesno") and members:
        want = wanted(q)
        return all((n in want) == m.evaluate("e => e.checked") for m, n in zip(members, names))
    if kind in ("choice", "yesno"):
        return norm(box.locator("button[type=button]").first.inner_text()) == wanted(q)[0]
    field = box.locator("textarea:not([name$='captcha-response']), input[type=text], input:not([type])")
    if not field.count():
        return False
    got = field.first.input_value()
    return dom.digits(got) == dom.digits(str(value)) if kind == "phone" else got == str(value)


def fill(page, q: dict, resume_file: str | None) -> str:
    kind, value = q["kind"], q["answer"]
    if signs(q["title"]):
        return left_on_page(q)
    box = box_of(page, q)
    if not box.count():
        return "FAIL question not on page"
    if kind == "file":
        if q.get("key") not in ("resume", "cover_letter"):
            return f"ASK not the resume box ({q['title']}) - the user uploads their own file there"
        if q.get("key") == "cover_letter" and not resume_file:
            return "ASK cover letter box - no letter made for this job (letter prepare), or the user uploads their own"
        return put_file(box, resume_file) if value is True and resume_file else "skipped - upload not approved"
    if (q.get("native") or "").startswith("NUMERIC_RATING"):
        return f"ASK a row of numbers to click ({value}) - pick it on the page"
    if q.get("key") == "linkedin" and not LINKEDIN.match(str(value)):
        return f"ASK Gem refuses '{value}' as a LinkedIn link - it takes linkedin.com/in/... or https://www.linkedin.com/in/..."
    if kind in ("choice", "multichoice", "yesno"):
        members, names = ticks(box)
        if members:
            return dom.put_ticks(members, names, wanted(q), role=False, single=kind != "multichoice")
        return put_menu(page, box, wanted(q)[0])
    return put_text(box, value, kind)
