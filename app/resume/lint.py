import argparse
import functools
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import cfg
from resume import render, schema

FAIL = "fail"
WARN = "warn"

# PubMed 2010-2024 excess style words (delves 25.2x, showcasing 9.2x, underscores 9.1x) + ten-marker set + flowery cluster.
# "across" and "within" left 2026-09-24: they carry scope ("across 6 teams"), which is evidence (docs/bullets.md)
STYLE_WORD_LIST = (
    "delve", "delves", "delved", "delving", "showcasing", "underscores", "additionally", "comprehensive",
    "crucial", "enhancing", "exhibited", "insights", "notably", "particularly", "meticulously", "intricate",
    "pivotal",
)
HEDGE_LIST = ("helped", "contributed to", "assisted with", "played a key role")
RESUME_VERB_LIST = ("leveraged", "spearheaded", "orchestrated", "synergized", "drove innovation")
# a grade the reader cannot check carries no information; the fact that earned it does (docs/bullets.md)
GRADE_LIST = (
    "advanced", "best-in-class", "world-class", "cutting-edge", "state-of-the-art", "industry-leading",
    "best-of-breed", "top-tier", "seamless", "robust",
)


def any_phrase(phrases: tuple[str, ...]) -> re.Pattern:
    return re.compile(rf"\b({'|'.join(map(re.escape, phrases))})\b", re.I)


STYLE_WORDS = any_phrase(STYLE_WORD_LIST)
EM_DASH = "\u2014"
MARKDOWN = re.compile(r"\*\*|__|^#+\s|##|`|\[[^\]]*\]\([^)]*\)", re.M)
INVISIBLE = re.compile("[\u00a0\u202f\u200b\u200c\u200d\u2060\ufeff]")
ROUND_PERCENT = re.compile(r"\b(10|15|20|25|30|40|50|100)%")
HEDGES = any_phrase(HEDGE_LIST)
RESUME_VERBS = any_phrase(RESUME_VERB_LIST)
GRADES = any_phrase(GRADE_LIST)
# a purpose clause naming nothing specific is usually the definition of the thing just named
EMPTY_CLAUSE = re.compile(
    r",?\s+\b(so that|so|allowing|enabling|letting|helping|ensuring|giving|making|thereby|which)\b", re.I)
NOT_ONLY = re.compile(r"\bnot only\b.*\bbut also\b", re.I)
TRIAD = re.compile(r"\b[\w-]+, [\w-]+,? and [\w-]+\b")
# pre-AI role (ai_era false) naming any of these = backdated AI claim. Words other fields use
# for other things stay out: evals (clinical, performance), embeddings (maths), fine-tuning (any tuning)
AI_TERMS = re.compile(
    r"\b(LLMs?|GPT[-\w.]*|ChatGPT|Claude|OpenAI|Anthropic|Gemini|LangChain|LlamaIndex|retrieval-augmented|"
    r"vector (search|database|store)|pgvector|Pinecone|AI agents?|LLM agents?|agentic|"
    r"prompt engineering|Copilot|eval harness\w*)\b",
    re.I,
)
# capitals only, and never the red-amber-green status every project manager reports in
AI_ACRONYM = re.compile(r"\bRAG\b(?![- ](status|rating|report|dashboard|chart)s?\b)")
# first public release; role ending before it cannot have used it
TOOL_RELEASED = {
    re.compile(r"\bCopilot\b", re.I): "2021-06",
    re.compile(r"\bLangChain\b", re.I): "2022-10",
    re.compile(r"\bLlamaIndex\b", re.I): "2022-11",
    re.compile(r"\bChatGPT\b", re.I): "2022-11",
    re.compile(r"\bGPT-4", re.I): "2023-03",
    re.compile(r"\bClaude\b", re.I): "2023-03",
}
NUMBER = re.compile(r"\d")
PERCENT_WORDS = r"\s*(%|percent\b|per cent\b)"
# tech names w/ exactly one correct spelling - drift between bullets reads as carelessness
CANONICAL = {re.compile(rf"\b{p}\b", re.I): c for p, c in (
    (r"nginx", "NGINX"), (r"jquery", "jQuery"), (r"angular\.?js", "AngularJS"),
    (r"node\.?js", "Node.js"), (r"github", "GitHub"), (r"gitlab", "GitLab"),
    (r"javascript", "JavaScript"), (r"typescript", "TypeScript"), (r"mysql", "MySQL"),
    (r"mariadb", "MariaDB"), (r"mongodb", "MongoDB"), (r"graphql", "GraphQL"),
    (r"kubernetes", "Kubernetes"), (r"eslint", "ESLint"), (r"webpack", "Webpack"),
)}
# a domain or handle is lowercase by convention - github.com is not a misspelling of GitHub
URL_OR_HANDLE = re.compile(r"\b(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.\w+|\b[\w-]+\.(?:com|net|org|io|dev|me|co|ai)\b", re.I)
# number, or word w/ optional .js / C++ / C# tail
TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+(?:[.+#][^\W\d_]+|[+#]+)*")
SENTENCE_START = re.compile(r"(^|[.;:!?]\s+)$")
# craft floor, unmeasured (plan #AI-tell lint WARN ONLY): bullet lengths this uniform read templated
MIN_BULLET_LENGTH_CV = 0.15
# one opening word leading this many bullets anywhere on the page. VMock (2026-09-24) marked
# "Built" x8 as overused; 4 is the user's own threshold, decided that day, not a measured one
MAX_SAME_OPENING = 4
# VMock's filler list, trimmed to the words that are filler wherever they appear: "the", "that",
# "which", "their" are on its list too, and are ordinary English. "lazy" was its own false
# positive - "lazy loading" is a technique - so no word here is ever matched inside a compound
FILLER_LIST = ("successfully", "actively")
FILLER = any_phrase(FILLER_LIST)
# first person, lower case only: "US" and "UK" are places. "I" only opening a sentence, where it
# is the pronoun - "Level I trauma center" is a rating
PRONOUN = re.compile(r"\b(me|my|we|our|ours|myself|ourselves)\b|(?:^|[.;:!?]\s+)(I)\b(?!\.)")
# two-word modifiers that take a hyphen before the noun they describe (Chicago 7.89, AP):
# "live-streaming channels", "full-stack engineer". Flagged only when a word follows that is not a
# preposition or conjunction, so "shipped features end to end" and "streaming live" stay unflagged
COMPOUND_LIST = (
    "live streaming", "end to end", "full stack", "real time", "open source", "front end", "back end",
    "cross functional", "high traffic", "long term", "short term", "large scale", "high quality",
    "data driven", "user facing", "customer facing", "client facing", "mission critical", "day to day",
    "hands on", "in house", "third party", "cross platform", "fast paced", "high volume", "low latency",
    "multi tenant", "patient centered", "evidence based", "detail oriented", "full time", "part time",
)
COMPOUND = re.compile(rf"\b({'|'.join(' '.join(map(re.escape, p.split())) for p in COMPOUND_LIST)}) ([a-z]\w*(?:\.\w+)*)", re.I)
NOT_A_NOUN = {"and", "or", "to", "for", "in", "on", "at", "with", "of", "by", "from", "as", "the", "a", "an",
              "across", "into", "than", "that", "which", "while", "since", "so", "but", "via", "per", "is", "was"}
# British forms a US screener reads as misspellings: VMock marked "theatre" as a spelling error
# 2026-09-24, and a spelling error costs its whole language score. Word -> US form, explicit forms
# only: "advertise", "expertise", "enterprise" and "analyses" are US English and must never match
US_FORMS = {
    **{uk + end: us + end for uk, us in (
        ("colour", "color"), ("behaviour", "behavior"), ("favour", "favor"), ("honour", "honor"),
        ("labour", "labor"), ("neighbour", "neighbor"), ("flavour", "flavor"), ("humour", "humor"),
        ("endeavour", "endeavor"), ("harbour", "harbor"), ("rumour", "rumor"), ("vapour", "vapor"))
       for end in ("", "s", "ed", "ing", "ful", "ite", "ites", "able", "al", "ally", "hood", "er", "ers")},
    **{uk + end: us + end for uk, us in (
        ("theatre", "theater"), ("centre", "center"), ("metre", "meter"), ("fibre", "fiber"),
        ("litre", "liter"), ("calibre", "caliber"), ("spectre", "specter"), ("sombre", "somber"))
       for end in ("", "s")},
    **{stem + "is" + end: stem + "iz" + end for stem in (
        "organ", "real", "recogn", "priorit", "optim", "standard", "custom", "util", "modern", "minim",
        "maxim", "special", "visual", "summar", "final", "central", "digit", "monet", "local", "initial",
        "synchron", "categor", "author", "emphas", "character", "mobil", "normal", "sanit", "stabil",
        "capital", "container", "parameter", "token", "serial", "virtual", "personal", "operational",
        "commercial", "industrial", "global", "hospital", "apolog", "critic", "familiar", "memor",
        "publiс", "revolution", "scrutin", "symbol", "systemat", "harmon", "internation", "rational",
        "decentral", "democrat", "energ", "incentiv", "institutional", "item", "legal", "neutral",
        "penal", "revital", "subsid", "util", "vocal", "author")
       for end in ("e", "es", "ed", "ing", "ation", "ations", "er", "ers", "able")},
    **{"analys" + end: "analyz" + end for end in ("e", "ed", "ing", "er", "ers")},
    **{"paralys" + end: "paralyz" + end for end in ("e", "ed", "ing")},
    "centred": "centered", "centring": "centering", "modelling": "modeling", "modelled": "modeled",
    "modeller": "modeler", "travelled": "traveled", "travelling": "traveling", "traveller": "traveler",
    "travellers": "travelers", "labelled": "labeled", "labelling": "labeling", "cancelled": "canceled",
    "cancelling": "canceling", "levelled": "leveled", "signalling": "signaling", "fuelled": "fueled",
    "counselling": "counseling", "counsellor": "counselor", "counsellors": "counselors",
    "channelled": "channeled", "licence": "license", "licences": "licenses", "licenced": "licensed",
    "defence": "defense", "offence": "offense", "practise": "practice", "practised": "practiced",
    "practising": "practicing", "grey": "gray", "enrol": "enroll", "enrolment": "enrollment",
    "enrolments": "enrollments", "fulfil": "fulfill", "fulfilment": "fulfillment", "judgement": "judgment",
    "programme": "program", "programmes": "programs", "catalogue": "catalog", "catalogues": "catalogs",
    "catalogued": "cataloged", "analogue": "analog", "aluminium": "aluminum", "cheque": "check",
    "cheques": "checks", "tyre": "tire", "tyres": "tires", "mould": "mold", "manoeuvre": "maneuver",
    "paediatric": "pediatric", "paediatrics": "pediatrics", "orthopaedic": "orthopedic",
    "orthopaedics": "orthopedics", "anaesthesia": "anesthesia", "anaesthetic": "anesthetic",
    "anaesthetist": "anesthetist", "haemoglobin": "hemoglobin", "oestrogen": "estrogen",
    "gynaecology": "gynecology", "encyclopaedia": "encyclopedia", "ageing": "aging",
    "sceptical": "skeptical", "storey": "story", "storeys": "stories", "draught": "draft",
    "plough": "plow", "kerb": "curb", "jewellery": "jewelry", "pyjamas": "pajamas", "towards": "toward",
}
# work words a general dictionary lacks. pyspellchecker's English list is a word-frequency list
# from subtitles and misses "workflow", "dataset", "analytics", "telehealth" - so a word here is
# one a hiring manager reads as ordinary, not one it has checked. Add to it; never shorten it to
# make a resume flag
WORK_WORDS = frozenset("""
agentic analytics api apis app apps backend backends chatbot chatbots cli codebase codebases config
configs dataset datasets devops dropdown dropdowns ecommerce edtech fintech frontend frontends fullstack
healthtech iframe iframes kanban linter linters linting livestream livestreaming livestreams login logins
logout metadata microservice microservices middleware monorepo monorepos namespace namespaces offboarding
offboard offboards offsite onboard onboards onboarded onboarding onsite podcast podcasts polyfill polyfills prefetch prefetching refactor
refactored refactoring refactors repo repos rerender rerenders roadmap roadmaps runtime runtimes sdk sdks
serverless signin signup signups standup standups telehealth telemedicine theming timestamp timestamps
toolchain toolchains transpile transpiled triaged triaging ui unmount upsell upsells url urls ux webinar
webinars webpage webpages wireframe wireframes wireframing workflow workflows preop postop med meds ehr emr
surg dev devs diff diffs diffing hackathon hackathons enablement precept precepted preceptor readmission
readmissions jan feb mar apr jun jul aug sep sept oct nov dec
""".split())
WORD_CHUNK = re.compile(r"\S+")
EDGE_PUNCT = "()[]{}\"'“”‘’,.;:!?"

# rule -> one plain sentence a non-technical user reads in "Check before sending.md", and the
# chat can say when asked why. Mirrored in docs/bullets.md #Why each rule - keep the two in step
WHY = {
    "title-changed": "Your job title must match what your employer's records say.",
    "employer-changed": "The employer's name must match what their records say.",
    "dates-changed": "Job dates must match what your employer's records say.",
    "unknown-entry": "Every job on the page has to come from your resume.",
    "inference-source": "New wording has to point back to something your resume already says.",
    "unresolved-entity": "A number, tool or name appears that your resume never mentions.",
    "ai-era": "AI wording on a job that ended before those tools existed reads as backdated.",
    "role-dates-overlap": "Two jobs overlap in dates - fine if both were real, but a checker will ask.",
    "company-legal-id": "Employer names are often written with Inc. or LLC in official records.",
    "round-metric": "A round percentage your resume never states looks made up.",
    "unmeasurable-grade": "Words like 'world-class' can't be checked; the fact behind them says more.",
    "empty-clause": "Part of this line may explain something the reader already knows.",
    "specificity": "This line names nothing a reader can picture: no number, tool or name.",
    "style-word": "This word shows up far more in AI-written text than in people's writing.",
    "hedge": "'Helped' or 'assisted' is fine when it is true; just check it describes your part.",
    "resume-verb": "Words like 'spearheaded' read as filler when every line uses one.",
    "rule-of-three": "Lists of three in a row are a pattern readers link with AI writing.",
    "not-only-but-also": "'Not only ... but also' is a pattern readers link with AI writing.",
    "same-verb-opening": "Two lines in a row start with the same word.",
    "uniform-bullet-length": "Every line is about the same length, which reads as templated.",
    "lead-bullet-weak": "The first line under this job has no number, but a later one does.",
    "bullet-taper": "An older job has more lines than a newer one.",
    "canonical-casing": "A tool name is spelled differently from its official spelling.",
    "em-dash": "Long dashes are a common sign of AI-written text.",
    "markdown": "Formatting symbols would show up as stray characters.",
    "invisible-unicode": "An invisible character could trip up job-site software.",
    "street-address": "City and state is enough; a street address adds nothing and exposes you.",
    "personal-details": "US employers don't expect these; they invite bias.",
    "abbreviated-school": "Application forms match your school against a list of full names, so a short form like \"CC\" matches nothing.",
    "language-level": "Resume readers store each language with its own level, so write one per line with the level in brackets, like Spanish (Fluent).",
    "old-graduation-year": "A graduation year from 15+ years ago can invite age bias; you may leave the year off.",
    "spelling": "Resume scanners count a spelling mistake against the whole page, and US employers read British spellings as mistakes.",
    "compound-modifier": "Two words describing the next one take a hyphen - live-streaming channels, full-stack engineer.",
    "overused-opening": "One word starts many of your lines; a different true verb here and there reads less repetitive.",
    "filler-word": "Words like 'successfully' or 'my' take room and add nothing the line does not already say.",
}
# contact location: a house number, apartment or suite, or a ZIP code is more than a city and state
STREET = re.compile(r"^\s*\d+\s+\w|\b(apt|apartment|suite|ste|unit)\b\.?|#\s*\d|\b\d{5}(-\d{4})?\b", re.I)
# asked for on some CVs abroad; on a US resume they only give a screener grounds it may not use
PERSONAL = re.compile(
    r"\b(date of birth|D\.?O\.?B\b|place of birth|born (on |in )?\d|age:?\s*\d{2}\b|\d{2}\s*(years|yrs)\s*old|"
    r"marital status|married|divorced|widowed|nationality|religion:|gender:)", re.I)
# forms match the school against a list of full names ("Do not use abbreviations"): "Lakeview CC" matches nothing
ABBREVIATED_SCHOOL = re.compile(r"\b(CC|CCC|Univ|Coll|Inst)\b\.?|\bU\.? of\b")
# one language, then its level in brackets: parsers store language + level as a pair
# (Textkernel LanguageCompetencies), so "English and Spanish - fluent" gives one or neither a level
LANGUAGE_LINE = re.compile(r"[^\W\d_][\w .'-]*?\s*\([^()]+\)")
SEVERAL_LANGUAGES = re.compile(r",|/|&|\band\b", re.I)
# Indeed/AARP: past this a graduation year dates the candidate more than it informs
OLD_GRADUATION_YEARS = 15


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    where: str
    detail: str


def norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def master_strings(master) -> list[str]:
    if isinstance(master, str):
        return [master]
    if isinstance(master, dict):
        return [s for v in master.values() for s in master_strings(v)]
    if isinstance(master, list):
        return [s for v in master for s in master_strings(v)]
    return []


def page_items(model: dict):
    """(kind, where, text, entry id or None) for every string on page."""
    yield "contact", "contact", model["contact"]["name"], None
    yield "contact", "contact", render.SEP.join(model["contact"]["parts"]), None
    if model.get("headline"):
        yield "headline", "headline", model["headline"], None
    if model.get("summary"):
        yield "summary", "summary", model["summary"], None
    for section in model["sections"]:
        for entry in section.get("entries", []):
            where = entry_where(section["title"], entry)
            for kind in ("heading", "org", "subline"):
                if entry.get(kind):
                    yield kind, where, entry[kind], entry.get("id")
            for i, bullet in enumerate(entry["bullets"]):
                yield "bullet", f"{where} bullet {i + 1}", bullet, entry.get("id")
        for line in section.get("lines", []):
            yield "line", section["title"], f"{line['label']}: {line['text']}" if line.get("label") else line["text"], None


def entry_where(section_title: str, entry: dict) -> str:
    return f"{section_title}/{entry.get('id', entry['heading'])}"


def ai_term(text: str) -> re.Match | None:
    return AI_TERMS.search(text) or AI_ACRONYM.search(text)


def entity_key(token: str) -> str:
    """Compare form: "1,000" and "1000" are one number."""
    return (token.replace(",", "") if token[:1].isdigit() else token).casefold()


def vouched(word: str, text: str, facts: list[str], posting: str) -> bool:
    """Word the posting uses, or another of the candidate's facts: a term of the field, not a grade added."""
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.I)
    return bool(pattern.search(posting)) or any(pattern.search(s) for s in facts if norm(s) != norm(text))


def entities(text: str) -> list[str]:
    """Numbers + capitalized tokens, minus sentence-initial capital on plain word."""
    found = []
    for m in TOKEN.finditer(text):
        tok = m.group()
        plain_initial_cap = tok[:1].isupper() and tok[1:].islower()
        if tok[0].isdigit() or any(c.isupper() for c in tok):
            if plain_initial_cap and SENTENCE_START.search(text[:m.start()]):
                continue
            found.append(tok)
    return found


@functools.cache
def dictionary():
    """English word list, loaded once: 160k words, ~0.3s."""
    from spellchecker import SpellChecker
    return SpellChecker(language="en", distance=1)


def plain_words(text: str) -> list[str]:
    """Lower-case words a dictionary can judge: names, acronyms, versions and tool names left out.

    A capital anywhere but a sentence's first letter marks a name ("React", "Ohio", "AWS"); a
    digit, dot, slash-joined or + # @ token is a version, file, handle or tool ("i18next",
    "Node.js", "C#"). Hyphenated words are judged part by part."""
    out, start = [], True
    for chunk in WORD_CHUNK.findall(URL_OR_HANDLE.sub(" ", text)):
        word = chunk.strip(EDGE_PUNCT)
        # after a colon or semicolon a capital is a name ("sponsors: Rockin' Robin Diner"), not a new sentence
        opens, start = start, chunk.rstrip(")\"'”’").endswith((".", "!", "?"))
        if not word or re.search(r"[\d.+#@_&/\\]", word):
            continue
        word = re.sub(r"['’]s$", "", word)
        if word[1:] != word[1:].lower() or (word[0].isupper() and not opens):
            continue
        out += [part.lower() for part in word.split("-") if part.isalpha()]
    return out


def misspelled(text: str, allowed: set[str]) -> list[str]:
    """Unknown words one letter away from a known one - the shape of a typo ("managment",
    "recieved"). A word with no near neighbour is a field's own term far more often than a slip
    ("readmissions", "precepted"), so it is left alone. British forms are british()'s."""
    words = [w for w in plain_words(text) if w not in allowed and w not in WORK_WORDS and w not in US_FORMS]
    found = []
    for word in sorted(set(dictionary().unknown(words))):
        if near := dictionary().candidates(word):
            found.append(f"{word} (did you mean {dictionary().correction(word) or sorted(near)[0]}?)")
    return found


def british(text: str) -> list[str]:
    return sorted({f"{w} -> {US_FORMS[w]}" for w in plain_words(text) if w in US_FORMS})


def open_compounds(text: str) -> list[str]:
    return [f"{m.group(1)} {m.group(2)} -> {m.group(1).replace(' ', '-')} {m.group(2)}"
            for m in COMPOUND.finditer(text) if m.group(2).lower() not in NOT_A_NOUN]


def lint(model: dict, master: dict, inferences: list[dict] | None = None, posting: str = "") -> list[Finding]:
    """`posting` = the job's own text: a style or grade word it uses is its term, not the writer's."""
    inferences = inferences or []
    findings: list[Finding] = []
    master_page = [norm(s) for s in render.page_strings(render.page_model(master))]
    facts = master_strings(master)
    verbatim = set(master_page) | {norm(s) for s in facts}
    corpus = " ".join(facts)
    known = {entity_key(t) for t in TOKEN.findall(corpus)}
    known_terms = {norm(s) for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"] for s in b.get("stack", [])}
    known_terms |= {norm(i) for g in master.get("skills", []) for i in g["items"]}
    entries = {e["id"]: e for e in [*master["roles"], *master.get("projects", [])]}
    bullet_ids = {b["id"] for e in entries.values() for b in e["bullets"]}
    # a tool or item the user lists is a word they use; generated text may also use any word
    # the user's facts or the posting do - a typo there is the user's, flagged on their own line
    listed = {w for t in known_terms for w in plain_words(t)}
    vouched_words = listed | set(plain_words(corpus)) | set(plain_words(posting))

    for role in master["roles"]:
        if not schema.LEGAL_IDENTIFIER.search(role["company"].strip()):
            findings.append(Finding(WARN, "company-legal-id", f"roles/{role['id']}", f"{role['company']!r} lacks Inc./LLC/...; add if employer has one"))

    # dates are verified w/ HR; roles are newest-first, so an end past the next start is a claim to check
    today = date.today()
    for newer, older in zip(master["roles"], master["roles"][1:]):
        if older["end"] == schema.PRESENT or not overlaps(older["end"], newer["start"], today):
            continue
        detail = f"ends {older['end']}, but {newer['company']} starts {newer['start']}"
        if older["company"].strip().casefold() == newer["company"].strip().casefold():
            detail += " - SAME employer, so a promotion here reads as an error, not concurrent work"
        findings.append(Finding(WARN, "role-dates-overlap", f"roles/{older['id']}", detail))

    for i, inference in enumerate(inferences):
        unknown = [b for b in inference.get("from", []) if b not in bullet_ids]
        if not inference.get("from") or unknown:
            findings.append(Finding(FAIL, "inference-source", f"inferences[{i}]", f"from {inference.get('from')} - unknown ids {unknown}"))
        known |= {entity_key(t) for t in TOKEN.findall(inference.get("claim", ""))}

    def hit(rule: str, where: str, text: str, detail: str, own_wording: bool) -> None:
        # candidate's own wording never hard-fails: target register, reported so selection can skip it
        findings.append(Finding(WARN if own_wording else FAIL, rule, where, f"{detail}: {text!r}"))

    def unvouched(pattern: re.Pattern, text: str) -> list[str]:
        return sorted({w for m in pattern.finditer(text) if not vouched(w := m.group().lower(), text, facts, posting)})

    for kind, where, text, entry_id in page_items(model):
        own = norm(text) in verbatim
        is_bullet = kind == "bullet"
        if words := unvouched(STYLE_WORDS, text):
            hit("style-word", where, text, f"{', '.join(words)}", own)
        scrubbed = URL_OR_HANDLE.sub(" ", text)
        for pattern, canon in CANONICAL.items():
            for m in pattern.finditer(scrubbed):
                if m.group() != canon:
                    findings.append(Finding(WARN, "canonical-casing", where, f"{m.group()!r} -> {canon!r}: {text!r}"))
        if EM_DASH in text:
            hit("em-dash", where, text, "U+2014", own)
        if MARKDOWN.search(text):
            hit("markdown", where, text, f"{MARKDOWN.search(text).group()!r}", own)
        if INVISIBLE.search(text):
            hit("invisible-unicode", where, text, f"U+{ord(INVISIBLE.search(text).group()):04X}", own)
        for m in ROUND_PERCENT.finditer(text):
            if not re.search(rf"\b{m.group(1)}{PERCENT_WORDS}", corpus, re.I):
                hit("round-metric", where, text, f"{m.group()} absent from master", own)
        # report only, always: it detects "names nothing specific", which is not the same as
        # "adds nothing" (1 false positive in 8 constructed clauses, docs/bullets.md)
        if is_bullet and (clause := EMPTY_CLAUSE.search(text)):
            tail = text[clause.end():]
            if not (NUMBER.search(tail) or any(c.isupper() for c in tail) or any(t in norm(tail) for t in known_terms)):
                findings.append(Finding(WARN, "empty-clause", where, f"{clause.group(1)!r} clause names nothing specific: {text!r}"))
        # employer names and section headings are not claims about quality: claim kinds only
        if kind in ("bullet", "summary") and (graded := unvouched(GRADES, text)):
            hit("unmeasurable-grade", where, text, f"{', '.join(graded)} - grade the reader cannot check", own)
        if is_bullet and not (re.search(r"\d", text) or any(c.isupper() for c in text[1:]) or ai_term(text) or any(t in norm(text) for t in known_terms)):
            hit("specificity", where, text, "no product, stack item, number or proper noun", own)
        # heading may carry JD's title as mirror suffix => check_entry_identity owns it
        if not own and kind != "heading":
            unresolved = sorted({e for e in entities(text) if entity_key(e) not in known})
            if unresolved:
                findings.append(Finding(FAIL, "unresolved-entity", where, f"{unresolved} in no master fact or inference: {text!r}"))

        # a hedge or verb the facts already use is the candidate's own account of their part
        for rule, pattern in (("hedge", HEDGES), ("resume-verb", RESUME_VERBS)):
            if kind in ("bullet", "summary") and (words := unvouched(pattern, text)):
                findings.append(Finding(WARN, rule, where, f"{words[0]!r}: {text!r}"))
        for rule, pattern in (("not-only-but-also", NOT_ONLY), ("rule-of-three", TRIAD)):
            if kind in ("bullet", "summary") and (m := pattern.search(text)):
                findings.append(Finding(WARN, rule, where, f"{m.group()!r}: {text!r}"))
        if is_bullet and entry_id in entries:
            check_ai_era(entries[entry_id], where, text, findings, own)
        if kind in ("bullet", "summary", "headline", "line", "subline"):
            if typos := misspelled(text, listed if own else vouched_words):
                hit("spelling", where, text, f"possible typo: {', '.join(typos)}", own)
            if uk := british(text):
                hit("spelling", where, text, f"British spelling: {', '.join(uk)}", own)
            for fix in open_compounds(text):
                findings.append(Finding(WARN, "compound-modifier", where, f"{fix}: {text!r}"))
        if kind in ("bullet", "summary", "headline"):
            filler = sorted({m.group().lower() for m in FILLER.finditer(text)} |
                            {m.group(1) or m.group(2) for m in PRONOUN.finditer(text)})
            if filler:
                findings.append(Finding(WARN, "filler-word", where, f"{', '.join(filler)}: {text!r}"))

    role_ids = {r["id"] for r in master["roles"]}
    for section in model["sections"]:
        # newest role first: an older entry given more space than a newer one buries current work
        counts = [(entry_where(section["title"], e), len(e["bullets"])) for e in section.get("entries", []) if e.get("id") in role_ids]
        for (_, newer), (where, older) in zip(counts, counts[1:]):
            if older > newer:
                findings.append(Finding(WARN, "bullet-taper", where, f"{older} bullets under an older role, more than the {newer} above it"))

    lengths = []
    for section in model["sections"]:
        for entry in section.get("entries", []):
            where = entry_where(section["title"], entry)
            check_entry_identity(entry, where, entries, findings)
            firsts = [b.split()[0].casefold() for b in entry["bullets"] if b.split()]
            for a, b in zip(firsts, firsts[1:]):
                if a == b:
                    findings.append(Finding(WARN, "same-verb-opening", where, f"consecutive bullets open {a!r}"))
            bullets = entry["bullets"]
            # opening bullet is the one always read; a measured claim there outranks a vague one
            if len(bullets) > 1 and not NUMBER.search(bullets[0]) and any(NUMBER.search(b) for b in bullets[1:]):
                findings.append(Finding(WARN, "lead-bullet-weak", where, "opening bullet carries no number, a later one does"))
            lengths += [len(b.split()) for b in entry["bullets"]]
    openings: dict[str, int] = {}
    for section in model["sections"]:
        for entry in section.get("entries", []):
            for bullet in entry["bullets"]:
                if bullet.split():
                    first = bullet.split()[0].strip(EDGE_PUNCT).casefold()
                    openings[first] = openings.get(first, 0) + 1
    for word, count in sorted(openings.items(), key=lambda kv: -kv[1]):
        if count >= MAX_SAME_OPENING:
            findings.append(Finding(WARN, "overused-opening", "page", f"{count} bullets open with {word!r}"))
    if len(lengths) >= 3:
        cv = statistics.pstdev(lengths) / statistics.mean(lengths)
        if cv < MIN_BULLET_LENGTH_CV:
            findings.append(Finding(WARN, "uniform-bullet-length", "page", f"word-count CV {cv:.2f} (floor {MIN_BULLET_LENGTH_CV})"))
    return findings


def overlaps(end: str, start: str, today: date) -> bool:
    """Same month = overlap; same year, when either says only a year, is a handover, not an overlap."""
    order = schema.compare(end, start, today)
    return order > 0 or (order == 0 and not (schema.year_only(end) or schema.year_only(start)))


def check_ai_era(entry: dict, where: str, text: str, findings: list[Finding], own: bool = False) -> None:
    # the candidate's own sentence is theirs to explain (a date typo, a word their field uses
    # otherwise): reported. Tailoring adding the same word is a backdated claim: failed.
    severity = WARN if own else FAIL
    if not entry.get("ai_era") and (m := ai_term(text)):
        findings.append(Finding(severity, "ai-era", where, f"{m.group()!r} inside entry with ai_era false: {text!r}"))
    if entry["end"] == schema.PRESENT:
        return
    for pattern, released in TOOL_RELEASED.items():
        if (m := pattern.search(text)) and schema.compare(entry["end"], released, date.today()) < 0:
            findings.append(Finding(severity, "ai-era", where, f"{m.group()!r} released {released}, entry ended {entry['end']}"))


def check_entry_identity(entry: dict, where: str, entries: dict, findings: list[Finding]) -> None:
    """Employer, title, dates = what verification catches; mirrored title allowed only as suffix."""
    if "id" not in entry:  # career break or school: straight from the user's facts, never tailored
        return
    source = entries.get(entry["id"])
    if source is None:
        findings.append(Finding(FAIL, "unknown-entry", where, f"id {entry.get('id')!r} not in master roles/projects"))
        return
    name = source.get("title", source.get("name"))
    if not entry["heading"].startswith(name):
        findings.append(Finding(FAIL, "title-changed", where, f"{entry['heading']!r} does not start with master {name!r}"))
    if source.get("company") and entry.get("org") != source["company"]:
        findings.append(Finding(FAIL, "employer-changed", where, f"{entry.get('org')!r} != master {source['company']!r}"))
    span = render.span_label(source)
    if span and span not in (entry.get("subline") or ""):
        findings.append(Finding(FAIL, "dates-changed", where, f"subline {entry.get('subline')!r} lacks {span!r}"))


def master_findings(master: dict, today: date) -> list[Finding]:
    """Checks on the user's own file, not any one page: what it discloses, never what it claims."""
    findings = []
    location = master["contact"]["location"]
    if m := STREET.search(location):
        findings.append(Finding(WARN, "street-address", "contact", f"{m.group().strip()!r} in {location!r}"))
    for text in master_strings(master):
        if m := PERSONAL.search(text):
            findings.append(Finding(WARN, "personal-details", "resume", f"{m.group()!r}: {text!r}"))
    for i, school in enumerate(master.get("education") or []):
        if m := ABBREVIATED_SCHOOL.search(school["institution"]):
            findings.append(Finding(WARN, "abbreviated-school", f"education[{i}]",
                                    f"{m.group()!r} in {school['institution']!r}: write the school's full name"))
        end = school.get("end")
        if end and not school.get("hide_year") and today.year - int(end[:4]) >= OLD_GRADUATION_YEARS:
            findings.append(Finding(WARN, "old-graduation-year", f"education[{i}]",
                                    f"{school['degree']} ended {end[:4]}; hide_year: true leaves the year off"))
    for i, line in enumerate(master.get("languages") or []):
        name = line.split("(")[0]
        if not LANGUAGE_LINE.fullmatch(line.strip()) or SEVERAL_LANGUAGES.search(name):
            findings.append(Finding(WARN, "language-level", f"languages[{i}]",
                                    f"{line!r}: one language per line, level in brackets - Spanish (Fluent)"))
    return findings


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint untailored master page: AI-tell rules + honesty vs master")
    ap.add_argument("--master", type=Path, help="master yml (default config resume.master)")
    args = ap.parse_args()
    started = time.perf_counter()
    master = schema.load(args.master or cfg.resume_path(cfg.load(), "master"))
    findings = lint(render.page_model(master), master) + master_findings(master, date.today())
    for f in findings:
        print(f"  {f.severity}  {f.rule:22} {f.where:28} {f.detail}")
    fails = sum(f.severity == FAIL for f in findings)
    print(f"{fails} fail, {len(findings) - fails} warn in {time.perf_counter() - started:.2f}s")
    if fails:
        sys.exit("lint failed")


if __name__ == "__main__":
    main()
