"""Kinds of software work - front-end, back-end, mobile ... - read off a job's title, or, for a plain
"Software Engineer" title, off its skill tags. Software engineering is many jobs under one name:
the job search files a title naming its kind under that kind's category (1,000 of 1,000 newest
`frontend` rows titled front-end, 2026-10-09), but 58% of `software_engineering` rows are titled
plainly ("Senior Software Engineer") and their kind shows only in the stack they list.

rank.software_kinds = kinds the user does: a title naming only other kinds - or a plain title whose
skill tags list another kind's stack and none of theirs - sorts lower, never hidden.
blocklist.software_kinds = kinds hidden outright, by title only (tags are weaker evidence).
Measured + why: app/docs/jobs/freehire.md #Software engineering kinds.
"""
import re

# kind -> (plain label, role words, stack words, skill tags in the job search's own spellings,
# categories it files that kind's titles under). Title words match whole words, case-insensitive.
# Role words decide when a title has any: "Senior Backend Engineer (TypeScript)" is back-end work in
# a front-end language (19 of 1,000 newest `backend` rows read front-end on the language, 2026-10-09)
KINDS = {
    "frontend": ("front-end",
                 r"front[- ]?end|ui|ux|user interface|web (?:developer|engineer|application|app)s?|design systems?|"
                 r"data visuali[sz]ation",
                 r"react(?![ .-]?native)(?:\.?js)?|angular(?:js)?|vue(?:\.?js)?|javascript|typescript|css|html",
                 {"react", "typescript", "javascript", "css", "html", "angular", "vue", "nextjs", "redux", "svelte",
                  "tailwind", "wcag"},
                 ("frontend",)),
    "fullstack": ("full-stack", r"full[- ]?stack", None, set(), ("fullstack",)),
    "backend": ("back-end", r"back[- ]?end|apis?|server[- ]side|platform|microservices?|distributed systems?",
                r"java(?!script)|golang|\.net|c#|ruby|rails|scala|php|node(?:\.?js)?|python|django",
                {"java", "go", "spring", "kafka", "grpc", "microservices", "distributed-systems", "dotnet", "csharp",
                 "ruby", "rails", "scala", "nodejs", "php", "django", "fastapi", "flask"},
                ("backend",)),
    "mobile": ("mobile app", r"mobile|ios|android", r"swift(?:ui)?|kotlin|flutter|react[ .-]?native|xamarin",
               {"ios", "android", "swift", "kotlin", "flutter", "react-native", "swiftui", "objective-c"},
               ("mobile",)),
    "systems": ("systems / embedded",
                r"embedded|firmware|kernel|drivers?|fpga|rtos|compilers?|gpu|low[- ]level|systems?",
                r"c\+\+|rust|linux",
                {"cpp", "c", "rust", "linux", "firmware", "rtos", "fpga"},
                ("embedded", "hardware")),
    "infra": ("DevOps / cloud",
              r"devops|devsecops|sre|site reliability|infrastructure|cloud|kubernetes|release|build|"
              r"network(?:ing)?|security|reliability",
              None,
              {"kubernetes", "terraform", "devops", "infrastructure-as-code"},
              ("devops", "sre", "network_engineering", "security")),
    "data": ("data / AI",
             r"data|machine learning|ml|ai|llm|deep learning|computer vision|nlp|analytics|scientist|mlops|research",
             None,
             {"spark", "machine-learning", "pytorch", "tensorflow", "data-pipelines"},
             ("data_engineering", "ml_ai", "ai_engineering", "data_science")),
    "qa": ("testing", r"qa|sdet|test|testing|quality (?:assurance|engineer(?:ing)?)|automation engineer", None, set(),
           ("qa",)),
}
# full-stack work is front-end work plus a back end: a plain title listing only back-end tags isn't it
STACK = {k: (KINDS["frontend"][3] if k == "fullstack" else v[3]) for k, v in KINDS.items()}


def _whole(words: str | None) -> re.Pattern | None:
    return re.compile(rf"(?<!\w)(?:{words})(?!\w)", re.I) if words else None


ROLE = {k: _whole(v[1]) for k, v in KINDS.items()}
LANGUAGE = {k: rx for k, v in KINDS.items() if (rx := _whole(v[2]))}
# a plain title the skill tags are read for: software work, not a designer or manager tagged java
SOFTWARE_TITLE = re.compile(r"(?<!\w)(?:engineer|engineering|developer|programmer|swe|sde|software|coder)(?!\w)", re.I)


def unknown(kinds: list[str] | None) -> list[str]:
    return [k for k in kinds or [] if k not in KINDS]


def named(title: str) -> list[str]:
    """Kinds the title names by role, else by language, in the order they first appear in it."""
    title = (title or "").replace("_", " ")
    for words in (ROLE, LANGUAGE):
        if hits := [(m.start(), k) for k, rx in words.items() if (m := rx.search(title))]:
            return [k for _, k in sorted(hits)]
    return []


def label(kind: str) -> str:
    return KINDS[kind][0]


def hidden(job: dict, hide: list[str] | None) -> bool:
    """Title names kinds and every one is hidden: "Java Full Stack" stays when only back-end is."""
    kinds = named(job.get("title") or "")
    return bool(hide) and bool(kinds) and set(kinds) <= set(hide)


def mismatch(job: dict, wanted: list[str] | None) -> list[str]:
    """One plain reason when the job is clearly another kind of software work than theirs, else []."""
    if not wanted:
        return []
    title = job.get("title") or ""
    kinds = named(title)
    if kinds:
        return [] if set(kinds) & set(wanted) else [f"title says {label(kinds[0])}"]
    if not SOFTWARE_TITLE.search(title):
        return []
    tags = [s.lower() for s in job.get("skills") or []]
    if set(tags) & set().union(*(STACK[k] for k in wanted)):
        return []
    for kind in KINDS:
        if kind not in wanted and (theirs := [t for t in tags if t in STACK[kind]]):
            return [f"skills listed are {label(kind)} ({', '.join(theirs[:2])})"]
    return []
