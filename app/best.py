"""Best to apply next: one score per open job the user hasn't acted on, from how well their resume
backs the posting's asks, how like their work the title is, how much it asks, pay, where, and how fresh it is. Orders the Today
page's "Best to apply next", the chat brief and the morning email - one order everywhere.

Weights: settings `rank.best_next`. Why each factor + its basis: app/docs/jobs/best-next.md.
An estimate for ordering, never a verdict: match is word overlap w/ the resume, not a reading of
it. Tailoring (job-tailor) judges each ask properly, with the user.
"""
import heapq
import html
import re
from bisect import bisect_left
from collections import deque
from datetime import date, datetime, timezone

import cfg
import rank
import store
from resume import knockout, schema, tailor

# seniority facet (row `seniority`, from enrichment) -> rung; career_level (setup answer) -> rung.
# "above yours" = 2+ rungs up: a mid-level applying to a senior post is ordinary, to a lead isn't
SENIORITY = {"intern": 0, "junior": 1, "middle": 2, "senior": 3, "lead": 4, "staff": 4, "principal": 5,
             "director": 5, "c_level": 6}
CAREER = {"entry": 1, "mid": 2, "senior": 3, "leader": 5}
# a required ask that hands over a team or a whole area: weighs as two asks
LEAD = re.compile(r"\b(?:lead|leads|leading|own|owns|ownership|manage|manages|managing|direct|directs|oversee|"
                  r"oversees|oversight|supervis\w*|head)\b", re.I)
# words every requirement uses: never what makes it this job's ask
FILLER = set("""a an and or the of in on for to with within at by from as is are be being been this that these those
your you our we their its it any all other such related relevant similar equivalent including include includes
experience experienced years year yrs plus minimum least ability able strong excellent good solid proven demonstrated
knowledge understanding familiarity familiar working work proficiency proficient skills skill required requirement
preferred must have has having must should will can using use used new etc e.g ie well highly advanced basic
environment fast paced team teams across multiple various""".split())
# the country is where the job is, never a skill: "US payroll regulatory requirements" was met by "US GAAP"
FILLER |= {"us", "usa", "unitedstates"}
STEM = 6
# languages a required ask can name ("Fluent in Spanish", "Bilingual English/Mandarin"): read
# apart from other words, since one shared word ("English") would back the whole ask
LANGUAGE = re.compile(r"\b(?:spanish|mandarin|cantonese|chinese|french|german|portuguese|italian|japanese|korean|"
                      r"arabic|hindi|urdu|bengali|punjabi|gujarati|tamil|telugu|russian|ukrainian|polish|vietnamese|"
                      r"tagalog|filipino|thai|indonesian|malay|turkish|farsi|persian|hebrew|greek|dutch|swedish|"
                      r"norwegian|danish|finnish|czech|romanian|hungarian|creole|swahili|amharic|somali|"
                      r"american sign language|asl|english)\b", re.I)
SAME_LANGUAGE = {"mandarin": "chinese", "cantonese": "chinese", "farsi": "persian", "filipino": "tagalog",
                 "asl": "american sign language"}
# levels setup offers: Native / Fluent / Professional / Conversational / Basic. Below working level
# backs no required ask ("Fluent Spanish required"); a line with no level counts (lint asks it)
LANGUAGE_BELOW_WORK = re.compile(r"\((?:[^)]*\W)?(?:conversational|basic|beginner|elementary|limited|learning)\b", re.I)


# names of several words whose words mean something else alone ("sound effects", "a final cut",
# "resolved", "AI-powered", a "30-bed unit" for "United"): one token, so "After Effects" is backed
# only by After Effects
PRODUCTS = re.compile(r"\b(?:after\s+effects|final\s+cut|media\s+composer|pro\s+tools|cinema\s+4d|davinci\s+resolve|"
                      r"power\s+bi|united\s+states)\b", re.I)
# a maker's or edition's name names no one tool. 2026-10-09, 3,828 video / editor / motion required lines:
# a resume w/ Adobe Photoshop + Final Cut Pro was "backed" on 60+ asks for Premiere Pro or After Effects
# ("Adobe", "Pro" shared). Alone in an ask ("the Adobe Creative Suite", "Microsoft Office") -> any of
# that maker's tools, or the suite by name, answers it (`suite`)
MAKERS = {"adobe", "microsoft", "google", "apple", "autodesk", "blackmagic", "maxon"}
EDITIONS = {"pro", "suite", "cloud", "creative", "cc", "office", "workspace"}


def root(word: str) -> str:
    """A word w/o its plural or -ed / -ing, so short roots meet: edit / edits / edited / editing,
    video / videos, shoot / shooting. Longer words already meet at 6 letters (managed, management)."""
    if word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        word = word[:-1]
    for end in ("ing", "ed"):
        if word.endswith(end) and len(word) - len(end) >= 4:
            return word[:-len(end)]
    return word


def forms(word: str) -> set[str]:
    return {word[:STEM], root(word)[:STEM]}


# "IT" in capitals is information technology, never the filler "it": "Sr. IT Compliance Analyst" read as a
# perfect title for an AML analyst (2026-10-12)
IT = re.compile(r"\bIT\b|\binformation technology\b", re.I)


# "React.js", "Node JS" = React, Node: before, "Node.js" was met by "Next.js" (the "js" they share)
JS = re.compile(r"(?i)\b([a-z][a-z0-9]*)\.js\b|\b(react|node|vue|next|angular|express|nest|nuxt|ember)\s?js\b")


def words_of(text: str) -> list[str]:
    text = IT.sub(lambda m: " infotech " if m.group(0) != "it" and m.group(0) != "It" else m.group(0), text)
    text = PRODUCTS.sub(lambda m: "".join(m.group(0).split()), text)
    text = JS.sub(lambda m: m.group(1) or m.group(2), text)
    for rx, short in SAME_WORDS:
        text = rx.sub(short, text)
    return [w for w in re.findall(r"[a-z][a-z0-9+#]*", text.lower()) if len(w) > 1 and w not in FILLER]


# one thing, two names: an ask in one backed by a resume in the other. HR asks: "HR" vs "human
# resources" both ways; "HRIS" backed by the HR system a resume names (Workday HCM, UKG ...) - 18 of
# 566 unbacked HR leader asks named HRIS against a resume that moved payroll to Workday (2026-10-09)
SAME_THING = ((re.compile(r"\bhuman resources?\b", re.I), "hr"), (re.compile(r"\bhr\b", re.I), "human resources"),
              (re.compile(r"\b(?:workday|ukg|ultipro|kronos|adp|dayforce|ceridian|successfactors|oracle hcm|peoplesoft|"
                          r"bamboohr|paylocity|paycom|paycor|rippling|namely|hibob|isolved)\b", re.I), "hris"),
              # security: the tool a resume names backs the kind it is (2026-10-09, a made-up director of cyber
              # defense - Splunk, CrowdStrike, Okta, CyberArk - on 12,351 senior security required lines)
              (re.compile(r"\b(?:okta|sailpoint|entra|azure ad|active directory|ping ?identity|forgerock|saviynt)\b", re.I), "iam"),
              (re.compile(r"\b(?:cyberark|beyondtrust|delinea|thycotic)\b", re.I), "pam"),
              (re.compile(r"\b(?:crowdstrike|sentinelone|carbon black|defender for endpoint|cortex xdr|cylance|tanium)\b", re.I),
               "edr"),
              (re.compile(r"\b(?:splunk|sentinel|qradar|arcsight|logrhythm|exabeam|chronicle|sumo logic|elastic security)\b",
                          re.I), "siem"),
              (re.compile(r"\b(?:xsoar|phantom|splunk soar|tines|swimlane)\b", re.I), "soar"),
              (re.compile(r"\b(?:tenable|nessus|qualys|rapid7|insightvm)\b", re.I), "vulnerability"))
# one name, its short form: folded to the short form on both sides before words are read, so "identity and
# access management" meets "IAM" without "identity", "access" or "management" backing anything else
# (short -> words put "information" + "event" from "SIEM" on the resume: a degree "in information
# systems" read as backed). 28 identity / endpoint / SIEM / pen-test asks were unbacked against a resume saying both
SAME_WORDS = ((re.compile(r"\bidentity (?:and|&) access management\b", re.I), "iam"),
              (re.compile(r"\bprivileged access management\b", re.I), "pam"),
              (re.compile(r"\bendpoint detection (?:and|&) response\b", re.I), "edr"),
              (re.compile(r"\bsecurity information (?:and|&) event management\b", re.I), "siem"),
              (re.compile(r"\bsecurity orchestration,? automation,? (?:and|&) response\b", re.I), "soar"),
              (re.compile(r"\bsecurity operations cent(?:er|re)s?\b", re.I), "soc"),
              (re.compile(r"\bgovernance,? risk,? (?:and|&) compliance\b", re.I), "grc"),
              (re.compile(r"\bdata loss prevention\b", re.I), "dlp"),
              (re.compile(r"\bapplication security\b", re.I), "appsec"),
              (re.compile(r"\bpen(?:etration)?[ -]?test(?:ing|s|er|ers)?\b", re.I), "pentest"),
              # one word, three spellings: "Front-End Engineer" on the resume, "Frontend Developer" in the
              # posting (2026-10-11: 9 of 74 front-end titles an AI judged same-field met no resume word)
              (re.compile(r"\bfront[- ]?end\b", re.I), "frontend"),
              (re.compile(r"\bback[- ]?end\b", re.I), "backend"),
              (re.compile(r"\bfull[- ]?stack\b", re.I), "fullstack"))


def stems(text: str) -> set[str]:
    """Content words cut to their first 6 letters, each also w/o its ending: "reconciliation" =
    "reconcile", "accountant" = "accounting", "edited" = "editing". Crude on purpose - an order, not
    a verdict."""
    text += "".join(f" {also}" for rx, also in SAME_THING if rx.search(text))
    return {f for w in words_of(text) for f in forms(w)}


def ask_words(text: str, leave: set[str] = frozenset()) -> list[set[str]]:
    """One set of forms per distinct content word of an ask, `leave` words left out."""
    return [forms(w) for w in dict.fromkeys(words_of(text)) if w not in leave]


# capitalised words in a row, "of" / "for" / "the" between them, are one name: "Uniform System of Accounts
# for the Lodging Industry". Read word by word, its "Accounts" backed the ask on any accounting resume
NAMED_RUN = re.compile(rf"{tailor.NAMED_TERM.pattern}(?:\s+(?:(?:of|for|the)\s+)*[A-Z][\w+#./-]*)*")


# "Excel-based", "data-driven": the tool is the first part
# also a name's kind-of-thing word ("HR Expertise", "NIST Framework", "Security Processes"): the name is the rest
NAME_SUFFIX = {"based", "driven", "oriented", "focused", "powered", "enabled", "degree", "expertise", "framework",
               "frameworks", "process", "processes", "methodology", "methodologies", "practices", "principles", "standards"}


def named(text: str) -> list[list[str]]:
    """Tools + products a requirement names (capitalised mid-sentence: Excel, SAP, SQL), each as its
    words: a name of several words is one entry; "Excel/Google Sheets" is two."""
    text = PRODUCTS.sub(lambda m: "".join(m.group(0).split()), text)
    return [w for run in NAMED_RUN.findall(text) for t in run.split("/")
            if (w := [x for x in words_of(t) if x not in NAME_SUFFIX])]


def languages(text: str) -> set[str]:
    return {SAME_LANGUAGE.get(n, n) for n in (m.lower() for m in LANGUAGE.findall(text))}


def resume_facts(config: dict, today: date) -> dict | None:
    """What the match reads off their resume details; none yet (or unreadable) => None."""
    path = cfg.resume_path(config, "master")
    try:
        master = schema.load(path)
    except (OSError, ValueError):
        return None
    parts = [master.get("summary") or "", master.get("headline") or ""]
    for group in ("roles", "projects"):
        for e in master.get(group) or []:
            parts += [e.get("title") or "", e.get("name") or "", e.get("blurb") or ""]
            parts += [b["claim"] if isinstance(b, dict) else str(b) for b in e.get("bullets") or []]
            parts += [s for b in e.get("bullets") or [] if isinstance(b, dict) for s in b.get("stack") or []]
    parts += [i for g in master.get("skills") or [] for i in g.get("items") or []]
    for e in master.get("education") or []:
        parts += [e.get("degree") or "", e.get("field") or "", e.get("details") or ""]
    parts += [c if isinstance(c, str) else " ".join(map(str, c.values())) for c in master.get("certifications") or []]
    # their own headings: awards, publications, credits. A clearance line is read by its level (knockout,
    # via credentials), never as words: the "CI" in "Active TS/SCI with CI polygraph" backed "CI/CD" asks
    parts += [x for o in master.get("other") or [] for x in [o.get("heading") or "", *(o.get("lines") or [])]
              if not knockout.clearance_held(x)[0] and not knockout.clearance_held(x)[2]]
    levels = [knockout.degree_held(e) for e in master.get("education") or []]
    held = max((knockout.LADDER.index(lv) for lv in levels if lv), default=None)
    spoken = " ".join(l.split("(")[0] for l in master.get("languages") or [] if not LANGUAGE_BELOW_WORK.search(l))
    own = " ".join([master.get("headline") or ""] + [r.get("title") or "" for r in master.get("roles") or []])
    return {"stems": stems(" ".join(parts)), "titles": stems(own), "lines": [p for p in parts if p.strip()], "years": knockout.dated_years(master, today),
            "credentials": knockout.credential_text(master), "portfolio": bool(knockout.portfolio_link(master)),
            "degree": held if None not in levels else "unknown", "languages": languages(spoken),
            "location": (master.get("contact") or {}).get("location") or ""}


CITIZEN = re.compile(r"(?i)\bcitizen(?:ship)?\b|\bU\.?S\.? persons?\b|\blawful permanent resident\b|\bITAR\b|\bexport[- ]control")
# asks no resume answers either way - each answered on the form, or by no one: a minimum age (12 of 143 forms
# we read ask 18+), a work permit (70 of 143, app/web/research/knockout-questions-2026-10.csv), lifting or
# standing, and age-coded wording ("recent graduate", "digital native"). Before this each counted against
# everyone, as citizenship did. A driver's licence or CDL is a credential, read as one (knockout)
_AGE = r"(?:1[4-9]|2[0-5])"
NOT_ON_RESUME = re.compile(
    rf"(?i)\b{_AGE}\s*\+?\s*(?:years?\s+)?(?:of age|years?[- ]old|or older|or over)\b|\bage(?:d| of)?\s+{_AGE}\b|"
    rf"\bat least {_AGE}(?=\s*(?:$|[.,;:)!]|or older|with\b))|\b(?:be|are|is)\s+{_AGE}\s*\+|\blegal (?:drinking |working )?age\b|"
    # work permit + sponsorship: never "authorized user of SAP", event "sponsorship sales"
    r"\b(?:authori[sz]ed|authori[sz]ation|eligib(?:le|ility)|permitted|right|legally able)\s+to\s+work\b|"
    r"\bwork (?:authori[sz]ation|permit|visa|eligibility)\b|\bemployment (?:authori[sz]ation|eligibility)\b|"
    r"\bwithout (?:[\w-]+\s+){0,4}?sponsorship\b|\b(?:visa|immigration|employment|h-?1b)\s+sponsorship\b|"
    r"\brequir\w* (?:(?:visa|employment|immigration|work)\s+)?sponsorship\b(?!\s+(?:sales|deals|packages|revenue))|"
    r"\bsponsorship\s+(?:now|in the future|for (?:employment|(?:an? )?(?:work )?visa))\b|"
    # lifting, standing: never "lift station maintenance"
    r"\b(?:able|ability) to (?:safely )?lift\b|\b(?:lift|carry|push|pull|mov)\w*\s+(?:[\w-]+\s+){0,4}?\d{2,3}\s*(?:pounds|lbs?|kg)\b|"
    r"\b(?:stand|sit|walk)(?:ing)?\s+for\s+(?:long|extended|prolonged|up to|several|most|\d)|\bable to stand\b|"
    # when + where they work, an employer's own statement: the form's or no one's ("Eastern Time hours",
    # "on-site in our New York City office", "Equal Opportunity Employer"); never "time management"
    r"\b(?:time zone|timezone|(?:eastern|pacific|central|mountain|[ECMP][SD]?T)\s+(?:time\s+)?(?:business\s+|working\s+)?hours)\b|"
    r"\bcore hours\b|\bon[- ]?call (?:basis|schedule|shifts?)\b|\bnon-work hours\b|\b(?:work|be|report)\s+(?:\w+\s+){0,2}on[- ]?site\b|\bcommut\w*|\brelocat\w*|"
    r"\bpreferred location\b|\b(?:early mornings|evenings|weekends|overnight)\b|\bequal (?:employment )?opportunity\b|"
    r"\bwithout regard to\b|\bE-?Verify\b|\b(?:be |reside |located |living )?(?:based|reside|located|living) in (?:the )?(?:US|U\.S\.|USA|United States|[A-Z][a-z]+)\b|"
    r"(?<!corporate )(?<!coordinate )(?<!coordinating )(?<!book )\btravel\b(?!\s*(?:and|&)\s*expenses?|\s*expenses?|\s*(?:industry|agenc\w+|tech|bookings?|insurance|nurse|nursing|arrangements|policy|policies|programs?|management|coordination|logistics|planning|reimbursements?))|\b\d+\s*(?:\+\s*)?hours? (?:a|per) (?:week|month)\b|"
    # age-coded: never "young children", "young adults" (a teacher's or counsellor's ask)
    r"\brecent (?:college |university |high school )?grad(?:uate)?s?\b|\bdigital natives?\b|\byouthful\b|"
    r"\byoung\b(?!\s+(?:children|child|kids|people|persons|adults?|learners|students|patients|audiences?|athletes|"
    r"women|men|readers|families|infants|toddlers|minds))|\b[1-6]\d\s*-?\s*years?[- ]old\b|"
    r"\bunder (?:the age of )?\d{2}(?:\s+years?(?:\s+(?:of age|old))?)?(?=\s*(?:$|[.,;:)!]))|\bunder the age of \d{2}\b")


def backed(text: str, facts: dict, years_read: bool = False) -> bool | None:
    """Does the resume back one required ask? None = can't tell from words (a trait everyone
    claims: tailoring shows it w/ a line, bullets.md) => not counted either way."""
    # a licence or certification is held or not: before this, "Active CAMS certification" counted as
    # backed by any certificate ("certification" = half its words) and Series 63 backed Series 24
    missing = knockout.credentials_missing(text, facts["credentials"]) if "credentials" in facts else None
    if missing:
        return False
    years = None if years_read else knockout.years_asked(text)
    if years is not None:
        if facts["years"] is None or facts["years"] < years:
            return None if facts["years"] is None else False
        # the years are there; what they are years of must be too. Before this "3+ years managing
        # OneTrust" was met by any 3 years of work (2026-10-12, held-out fields: compliance, security)
        return backed(knockout.YEARS.sub(" ", text, count=1), facts, years_read=True) is not False
    degree = knockout.degree_asked(text)
    if degree:
        held = facts["degree"]
        return None if held == "unknown" else held is not None and held >= knockout.LADDER.index(degree)
    # every language it names, at working level on their Languages line; English alone can't tell
    # (the resume is written in it). Before this, "Fluent in Spanish" never matched a native speaker
    if asked := languages(text) - {"english"}:
        return asked <= facts.get("languages", set())
    if languages(text):
        return None
    if missing == []:
        return True
    # a clearance held or not, at its level: before this a Secret holder "backed" "Active TS/SCI with polygraph"
    if knockout.clearance_asked(text):
        return knockout.clearance_short(text, facts["credentials"]) is None if "credentials" in facts else None
    # citizenship is the work-permit answer, never in a resume: 73 of 12,351 senior security asks counted
    # against everyone ("Must be a U.S. citizen")
    if CITIZEN.search(text) and not knockout.SECURITY_CLEARANCE.search(text):
        return None
    # age, work permit, lifting, age-coded wording: the form's, never the resume's (years + degree read first:
    # "authorized to work in the US; 3+ years of SQL" still asks the years)
    if NOT_ON_RESUME.search(text):
        return None
    # a portfolio or reel: answered by a link to their work, never by words. Before this, 217 of 551
    # video postings' asks to see work counted against everyone, link or not
    if knockout.portfolio_asked(text):
        return facts.get("portfolio")
    if tailor.is_trait(text):
        return None
    tools = named(text)
    generic = {t for name in tools for t in name if root(t) in MAKERS | EDITIONS}
    own = [[forms(t) for t in name if t not in generic] for name in tools]
    if any(name and sum(bool(f & facts["stems"]) for f in name) * 2 >= len(name) + (len(name) == 2) for name in own):
        # "SQL, Python, R, or other tools": one named tool they have answers the ask - half the words of a
        # name of several, as any ask (never "Uniform System of Accounts for the Lodging Industry" <- accounts);
        # a name of two needs both: "NIST SP 800-53" was met by NIST CSF, "Full Stack Developer" by any
        # developer (2026-10-12, 540 lines labelled by an AI: 0.741 => 0.765 agreement; 43 untuned lines
        # it changes: right on 37)
        return True
    if generic and not any(own) and any(forms(g) & facts["stems"] for g in generic if root(g) in MAKERS | {"office", "workspace"}):
        # a suite by name: "the Adobe Creative Suite" <- Photoshop; "Microsoft Office" <- MS Office
        return True
    words = ask_words(text, generic)
    if not words:
        # "5+ years of experience": nothing past the years
        return years_read
    return sum(bool(f & facts["stems"]) for f in words) * 2 >= len(words)

def backing(text: str, facts: dict) -> str | None:
    """The resume line that backs one required ask: the line sharing the most of its words, when `backed`
    says True. None = not backed, can't tell, or no lines read (facts w/o "lines"). Their own words, as written."""
    if backed(text, facts) is not True:
        return None
    words = ask_words(text, {t for name in named(text) for t in name if root(t) in MAKERS | EDITIONS})
    if not words:
        return None
    best_line, best_hits = None, 0
    for line in facts.get("lines") or []:
        have = stems(line)
        hits = sum(bool(f & have) for f in words)
        if hits > best_hits:
            best_line, best_hits = line, hits
    return " ".join(best_line.split()) if best_line and best_hits * 2 >= len(words) else None


# a wish inside a line the job search tagged required: "is a plus", "preferred", "ideally" (2026-10-11,
# 1,200 live rows: about 1 in 20 required lines carry one; finance 1 in 8). Never "5 plus years",
# "competitive advantage"
WISH = re.compile(r"(?i)\bpreferred\b|\bpreferabl[ey]\b|\b(?:is|are|a|big|huge|definite)\s+plus\b|\bnice[- ]to[- ]have\b|"
                  r"\bbonus\b|\bdesirable\b|\bdesired\b|\bideally\b|\b(?:is|are|an|be)\s+(?:an?\s+)?advantage\b|\badvantageous\b")
MUST = re.compile(r"(?i)\b(?:required|must|mandatory)\b")
WISH_BRACKET = re.compile(r"\(([^()]*)\)")
# where a wish clause starts: a semicolon, a sentence, ", with" / ", ideally" / " - "
WISH_SPLIT = re.compile(r"(?i);|\.\s+(?=[A-Z])|,\s*(?=(?:with|ideally|preferably|especially|and ideally)\b)|\s+[-–—]\s+")


def asked(text: str) -> str:
    """A required line w/o its wishes: "6+ years of payroll (Mexico experience a plus)" asks the years;
    "Bachelor's in Accounting or related preferred" asks nothing. A part that also says required stays."""
    if not WISH.search(text):
        return text
    text = WISH_BRACKET.sub(lambda m: "" if WISH.search(m.group(1)) and not MUST.search(m.group(1)) else m.group(0), text)
    return " ".join(q.strip() for q in WISH_SPLIT.split(text)
                    if q.strip() and (not WISH.search(q) or MUST.search(q))).strip(" ;.,-")


def required(job: dict) -> list[str]:
    """The posting's required lines, wishes cut out; a line that was all wish is gone."""
    return [t for r in (job.get("enrichment") or {}).get("requirements") or []
            if r.get("priority") == "required" and (t := asked(r["text"]))]


def years_tag(job: dict, facts: dict | None, asks: list[str]) -> int | None:
    """The job search's years tag (experience_years_min) when it counts as an ask: no line said years, their
    dated years known, not an early-career title (rank.EARLY_CAREER: the tag read 10 on "New Grad")."""
    years = (job.get("enrichment") or {}).get("experience_years_min")
    if years and facts and facts["years"] is not None and not rank.early_career(job) \
            and not any(knockout.years_asked(t) is not None for t in asks):
        return years
    return None


def years_only(job: dict, facts: dict | None, counted: tuple[int, int] | None) -> tuple[int, int] | None:
    """(years asked, theirs) when the one ask counted is the years tag - said as years, never "Matches 1 of 1"."""
    if counted and counted[1] == 1 and (years := years_tag(job, facts, required(job))):
        return years, facts["years"]
    return None


def match(job: dict, facts: dict | None, prior: float = 0) -> tuple[float, tuple[int, int] | None]:
    """Share of required asks the resume backs; years asked (experience_years_min) one more ask
    when no line said it - never on an early-career title, where that tag misreads (rank.EARLY_CAREER).
    `prior` asks read as half-backed join the count: a share off few asks stays near the middle
    (1 of 1 = 0.67 at 2, 8 of 8 = 0.9). No resume or no asks => neutral 0.5."""
    if facts is None:
        return 0.5, None
    asks = required(job)
    verdicts = [backed(t, facts) for t in asks]
    if years := years_tag(job, facts, asks):
        verdicts.append(facts["years"] >= years)
    counted = [v for v in verdicts if v is not None]
    if not counted:
        return 0.5, None
    return (sum(counted) + prior / 2) / (len(counted) + prior), (sum(counted), len(counted))


# words naming a level, a schedule or a place, not the kind of work: "Senior", "Manager", "II", "Remote"
TITLE_LEVEL = set("""senior sr junior jr lead principal staff head chief director manager vp vice president associate
assistant intern internship ii iii iv remote hybrid onsite contract contractor temporary temp part time full us
level entry mid""".split())


# their own past titles (+ headline) weigh half of title fit, the whole resume the rest: "analyst" met
# "variance analysis" (6-letter stems), so "Financial Analyst" read as a senior accountant's own title
# (2026-10-12, 1,007 live rows rated by an AI, 4 fields: top-10 nDCG 0.644 => 0.654, finance 0.44 => 0.48;
# titles alone 0.645)
TITLE_OWN = 0.5


def title_fit(job: dict, facts: dict | None) -> float:
    """Share of the title's words for the kind of work found anywhere in their resume: "Tableau
    Developer" against an HR director's, "Payroll Tax Analyst" against a brokerage analyst's. Level
    words and the bracketed part left out. No resume, or a title of level words only => 0.5."""
    if facts is None:
        return 0.5
    words = ask_words(re.sub(r"\(.*?\)", " ", job.get("title") or ""), TITLE_LEVEL)
    if not words:
        return 0.5
    share = lambda own: sum(bool(f & own) for f in words) / len(words)
    whole = share(facts["stems"])
    return whole if "titles" not in facts else TITLE_OWN * share(facts["titles"]) + (1 - TITLE_OWN) * whole


def above_level(job: dict, config: dict, facts: dict | None = None) -> bool:
    level = CAREER.get(config["rank"].get("career_level") or "")
    rung = SENIORITY.get(job.get("seniority") or "")
    return level is not None and rung is not None and rung >= level + 2


def asks(job: dict, config: dict, bn: dict, facts: dict | None = None) -> tuple[float, int, int]:
    """1 = light, 0 = heavy: required asks + lead/manage duties (each counts twice) between
    asks_light and asks_heavy; a level 2+ rungs above theirs halves it. No asks listed => 0.5.
    A leader (career_level) leads for a living: their lead duties count once, like any ask. 2026-10-09,
    680 US director / VP / chief postings w/ required asks (HR-titled + chief searches): median 7 asks,
    1 to lead; counted twice, 49 read heavy (16+), counted once 22."""
    texts = required(job)
    lead = 0 if config["rank"].get("career_level") == "leader" else sum(bool(LEAD.search(t)) for t in texts)
    if not texts:
        score = 0.5
    else:
        load = len(texts) + lead
        score = min(1.0, max(0.0, (bn["asks_heavy"] - load) / (bn["asks_heavy"] - bn["asks_light"])))
    return (score / 2 if above_level(job, config, facts) else score), len(texts), lead


def pay(job: dict, ladder: list[float], floor: float) -> float:
    """Place among the listed pay of the jobs scored (`ladder`, sorted; 0 lowest, 1 highest); under their floor
    halves it. Not listed => 0.25: unknown, below a listed middle."""
    annual = rank.annual_usd(job)
    if annual is None:
        return 0.25
    place = 1.0 if len(ladder) < 2 else bisect_left(ladder, annual) / (len(ladder) - 1)
    return place / 2 if floor and not rank.meets_floor(job, floor) else place


def where(job: dict, tiers: list[str]) -> float:
    """Their own where-first order (search settings passes): first tier 1, last 0."""
    if job.get("tier") not in tiers:
        return 0.0
    return 1.0 if len(tiers) < 2 else 1 - tiers.index(job["tier"]) / (len(tiers) - 1)


# Today's two lists (owner 2026-10-23): remote jobs + jobs near them, each in its own order. Inside one
# list the tier order says nothing, so `where` reads as `place` there: a remote job open to where they
# live, a nearby job whose office is in their area. 2026-10-23, 826 live front-end rows (remote US +
# 19 North Jersey / NYC cities), two resumes, every job rated by an AI for fit + "can they work it
# from home": app/docs/jobs/best-next.md #Two lists
LISTS = ("remote", "nearby")
# a place outside the US named in a location: "Remote Canada", "Toronto, ON", "Lisbon" (2026-10-23, 548
# live remote front-end rows: 36 the AI called not open to a New Jersey resident read open, 21 abroad)
ABROAD = re.compile(r"(?i)\b(?:canada|mexico|ciudad de|brazil|brasil|argentina|colombia|chile|peru|latam|latin america|"
                    r"india|china|japan|korea|singapore|philippines|indonesia|vietnam|pakistan|bangladesh|australia|"
                    r"new zealand|united kingdom|uk|england|ireland|scotland|germany|france|spain|portugal|italy|"
                    r"netherlands|poland|romania|ukraine|europe|emea|apac|israel|egypt|nigeria|kenya|south africa|turkey|"
                    r"toronto|vancouver|montreal|ontario|quebec|alberta|british columbia|london|berlin|dublin|bengaluru|"
                    r"bangalore|hyderabad|pune|lahore|manila|warsaw|lisbon|madrid|paris|amsterdam|bucharest)\b")
IN_US = re.compile(r"(?i)\b(?:united states|usa|u\.s\.|us)\b")
# remote anywhere in the US, whatever office it also names: "Santa Clara, CA or Remote", "Remote, US"
ANY_US = re.compile(r"(?i)\bor remote\b|remote (?:within|in|across|anywhere in) (?:the )?(?:us|u\.s|united states)\b|"
                    r"remote,? (?:us|u\.s|united states)\b|\b(?:us|united states) remote\b(?! -)|\banywhere\b|nationwide")
HOME_WORK = re.compile(r"(?i)remote|work from home|wfh")


def home_states(config: dict, facts: dict | None) -> set[str]:
    """Where they live, as state codes: their resume's own location, else every city tier's `states`."""
    own = rank.states_named((facts or {}).get("location"))
    return own | {s.upper() for p in config["passes"] for s in p.get("states") or []}


def list_of(job: dict) -> str:
    """Which of Today's two lists: a remote job, else one near them (hybrid, on-site, not tagged)."""
    return "remote" if job.get("work_mode") == "remote" else "nearby"


def open_to(job: dict, home: set[str]) -> float:
    """A remote job open to where they live: 1 = US-wide or names their state, 0 = only abroad or
    remote in another state ("Remote - Texas", "US Remote - Arizona"), 0.5 = an office in another
    state, or a city alone - can't tell. Home unknown => a state named can't be told either."""
    loc = job.get("location") or ""
    countries = job.get("countries") or []
    if countries and "us" not in countries or ABROAD.search(loc) and not IN_US.search(loc) \
            or re.search(r"(?i)west coast", loc) and not ANY_US.search(loc):
        return 0.0
    if named := rank.states_named(loc):
        if not home or named & home or ANY_US.search(loc):
            return 1.0
        return 0.0 if HOME_WORK.search(loc) else 0.5
    return 1.0 if not loc.strip() or IN_US.search(loc) or HOME_WORK.search(loc) else 0.5


def near(job: dict, config: dict, home: set[str]) -> float:
    """A nearby job's office in their area: 1 = its location names one of their tier's cities or
    states, 0 = it names only a place elsewhere ("Toronto, ON" filed under New York City - the job
    search's city list is loose, freehire.md), else the share of its cities that are theirs."""
    loc = (job.get("location") or "").lower()
    theirs = {c for p in config["passes"] if p["tier"] == job.get("tier") for c in (p["params"].get("cities") or [])}
    states = {s.upper() for p in config["passes"] if p["tier"] == job.get("tier") for s in p.get("states") or []} or home
    if rank.states_named(job.get("location")) & states or any(c.lower() in loc for c in theirs):
        return 1.0
    cities = job.get("cities") or []
    if any(c.lower() in loc for c in cities if c not in theirs) or ABROAD.search(loc):
        return 0.0
    return 0.5 if not cities or not theirs else sum(c in theirs for c in cities) / len(cities)


def place(job: dict, config: dict, home: set[str]) -> float:
    return open_to(job, home) if list_of(job) == "remote" else near(job, config, home)


def posted_days(job: dict, now: datetime) -> int | None:
    """Days since the posting went up (freehire's first sighting, rank.age), else since it
    reached their list."""
    days = rank.age(job, now)
    if days is None and job.get("first_fetched_at"):
        days = (now - datetime.strptime(job["first_fetched_at"], store.ISO).replace(tzinfo=timezone.utc)).days
    return None if days is None else max(0, days)


def fresh(job: dict, now: datetime, fresh_days: int) -> float:
    """Newer is better, linear to 0 at fresh_days. Unknown => 0.5."""
    days = posted_days(job, now)
    return 0.5 if days is None else max(0.0, 1 - days / fresh_days)


def windows(jobs: list[dict], now: datetime, steps: list[int], enough: int) -> dict[str, int]:
    """Freshest first (owner 2026-10-08: "start with 1 day and if not keep expanding"): jobs
    posted within steps[0] days are one group; fewer than `enough` there => the window widens
    to the next step until it holds enough, then the next group starts. Slug -> group number;
    age unknown => last group."""
    ages = {j["public_slug"]: posted_days(j, now) for j in jobs}
    group, size, out = 0, 0, {}
    for step in steps:
        for slug, days in ages.items():
            if slug not in out and days is not None and days <= step:
                out[slug], size = group, size + 1
        if size >= enough:
            group, size = group + 1, 0
    return {slug: out.get(slug, group) for slug in ages}


TAG = re.compile(r"<[^>]*>")


def posting_keys(job: dict) -> list[tuple]:
    """Same posting under another company name (an aggregator's copy, a brand + its parent:
    PlayStation Global / Sony Interactive Entertainment): title + the description's opening, or
    title + the same required asks word for word (copies whose company intro differs). Markup
    left out: the two Sony copies differed only in it."""
    title = " ".join(job["title"].lower().split())
    text = " ".join(html.unescape(TAG.sub(" ", job.get("description") or "")).split()).lower()[:300]
    asks = tuple(sorted(" ".join(t.lower().split()) for t in required(job)))
    return [k for k, ok in ((("text", title, text), text), (("asks", title, asks), len(asks) >= 3)) if ok]


def spread(jobs: list[dict], repeat: float, twin: float, seen: dict | None = None) -> list[dict]:
    """Best first, less `repeat` per job from the same employer already placed above and `twin`
    per copy of the same posting above (one employer filled 2-4 of the top 10, the same posting
    sat twice under two names - 2026-10-11, 1,200 live rows). `seen` = counts from jobs placed
    before these, updated. Order only: `best` stays as scored."""
    seen = {} if seen is None else seen
    # one queue per employer, best first: the employer's cut is the same for all its jobs, so only
    # each queue's head competes (1,400 rows from one employer: 1 s => 0.3 s for the Today page)
    queues = {}
    for j in sorted(jobs, key=lambda j: (-j["best"], j["public_slug"])):
        queues.setdefault(j["company_slug"], deque()).append((j, posting_keys(j)))

    def entry(employer):
        j, postings = queues[employer][0]
        return (-(j["best"] - repeat * seen.get(employer, 0) - twin * any(k in seen for k in postings)),
                j["public_slug"], employer)

    heap = [entry(e) for e in queues]
    heapq.heapify(heap)
    placed = []
    while heap:
        top = heapq.heappop(heap)
        if (fresh := entry(top[2])) != top:
            # a copy of it was placed since: the cut grew
            heapq.heappush(heap, fresh)
            continue
        j, postings = queues[top[2]].popleft()
        placed.append(j)
        for k in (top[2], *postings):
            seen[k] = seen.get(k, 0) + 1
        if queues[top[2]]:
            heapq.heappush(heap, entry(top[2]))
    return placed


def score(jobs: list[dict], config: dict, now: datetime, facts: dict | None, by_place: bool = False) -> list[dict]:
    """Each job + `best` (0-1 weighted mean less demerits) + `best_parts`, freshest window first
    (`windows`), best first inside it, employers spread (`spread`). Ties: slug order, so the same
    list always reads the same. by_place = one of Today's two lists (`lists`): `where` read as
    `place`, weighed by `place`."""
    bn = config["rank"]["best_next"]
    weights = {k: bn.get(k, 0) for k in ("match", "title", "asks", "pay", "where", "fresh")}
    if by_place:
        weights["where"] = bn.get("place", 0)
    tiers, floor = cfg.tier_order(config), config["rank"]["salary_floor_usd"]
    home = home_states(config, facts)
    ladder = sorted(a for j in jobs if (a := rank.annual_usd(j)) is not None)
    out = []
    for j in jobs:
        m, counted = match(j, facts, bn.get("match_prior", 0))
        a, n_asks, lead = asks(j, config, bn, facts)
        parts = {"match": m, "title": title_fit(j, facts), "asks": a, "pay": pay(j, ladder, floor),
                 "where": place(j, config, home) if by_place else where(j, tiers),
                 "fresh": fresh(j, now, bn["fresh_days"])}
        total = sum(weights[k] * parts[k] for k in weights) / (sum(weights.values()) or 1)
        total -= bn["demerit"] * rank.demerits(j, config)
        out.append(dict(j, best=round(total, 6), best_parts=parts,
                        best_facts={"matched": counted, "asks": n_asks, "lead": lead, "above": above_level(j, config, facts),
                                    "years_only": years_only(j, facts, counted)}))
    group = windows(out, now, bn["fresh_windows"], bn["fresh_enough"])
    out.sort(key=lambda j: (group[j["public_slug"]], -j["best"], j["public_slug"]))
    repeat, twin = bn.get("repeat", 0), bn.get("twin", 0)
    if lead := bn.get("fresh_first"):
        # the first picks come from the freshest window, the rest by score at any age (2026-10-12): with
        # every job in window order, a 5-day-old perfect fit sat at #152 below 60 weaker last-day posts
        seen = {}
        first = spread([j for j in out if group[j["public_slug"]] == 0], repeat, twin, seen)[:lead]
        taken = {j["public_slug"] for j in first}
        return first + spread([j for j in out if j["public_slug"] not in taken], repeat, twin, seen)
    # spread inside each freshness group, counting employers placed in groups above
    placed, seen = [], {}
    for g in dict.fromkeys(group[j["public_slug"]] for j in out):
        placed += spread([j for j in out if group[j["public_slug"]] == g], repeat, twin, seen)
    return placed


def candidates(conn, config: dict, now: datetime, ranked: list[dict] | None = None) -> list[dict]:
    """Open jobs on their list they haven't acted on: no job folder, not applied, not closed,
    not blocked (rank hides those), not stale (likely filled). ranked = rank.rank of every row,
    when the caller already made it."""
    acting = {v for r in conn.execute("SELECT public_slug, link_key(url) FROM applications") for v in r if v}
    return [j for j in (rank.rank(store.all_jobs(conn), config, now) if ranked is None else ranked)
            if not j["stale"] and not ({j["public_slug"], *j["duplicates"], store.link_key(j["url"])} & acting)]


def lists(jobs: list[dict], config: dict, now: datetime, facts: dict | None) -> dict[str, list[dict]]:
    """Today's two lists, each scored on its own (pay ladder, freshness windows, employer spread inside
    it), in their where-first order: remote first when their first tier searches remote. Empty ones left out."""
    first = next(iter(config["passes"]), {})
    keys = LISTS if (first.get("params") or {}).get("work_mode") in ("remote", ["remote"]) else LISTS[::-1]
    out = {k: score([j for j in jobs if list_of(j) == k], config, now, facts, by_place=True) for k in keys}
    return {k: v for k, v in out.items() if v}


def ordered(conn, config: dict, now: datetime, which: str | None = None) -> list[dict]:
    """rank --best: one order of every job, or one of Today's two lists (which = remote | nearby)."""
    facts = resume_facts(config, now.date())
    if which:
        return lists(candidates(conn, config, now), config, now, facts).get(which, [])
    return score(candidates(conn, config, now), config, now, facts)


def ago(days: int | None) -> str:
    if days is None:
        return ""
    return "posted today" if days < 1 else "posted 1 day ago" if days == 1 else f"posted {days} days ago"


def reasons(job: dict, config: dict, now: datetime) -> str:
    """The score in plain words, the order it weighs: match, a title far from theirs, a heavy ask, pay, where, age, then
    anything that pulled it down."""
    rc, f = config["rank"], job["best_facts"]
    if f.get("years_only"):
        # 4 in 10 postings list no requirements: their one ask is the job search's years tag
        asked, have = f["years_only"]
        parts = [f"Asks {asked}+ years, you have them" if have >= asked else f"Asks {asked}+ years, you have {have}"]
    else:
        parts = [f"Matches {f['matched'][0]} of {f['matched'][1]} asks" if f["matched"] else ""]
    if job["best_parts"].get("title", 1) == 0:
        # only when no word meets: a share in between ("Regional HR Business Partner" for an HR director,
        # 1 of 3) is the same work worded otherwise as often as not - the score weighs it, the line doesn't say it
        parts.append("title unlike your past work")
    if job["best_parts"]["asks"] < 0.5 and f["asks"]:
        heavy = f"Asks a lot: {f['asks']} requirements"
        parts.append(heavy + (f", {f['lead']} to lead or manage" if f["lead"] >= 2 else ""))
    if f["above"]:
        parts.append(f"{job['seniority'].replace('_', '-')} level, above yours")
    place = "remote" if job.get("work_mode") == "remote" else next(iter(job.get("cities") or []), job.get("location") or "")
    parts += [rank.pay_words(job, rc), place, ago(posted_days(job, now))]
    parts += rank.flags(job, config)
    return " · ".join(p for p in parts if p)
