import argparse
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cfg
from resume import render, schema

FAIL = "fail"
WARN = "warn"

# PubMed 2010-2024 excess style words (delves 25.2x, showcasing 9.2x, underscores 9.1x) + ten-marker set + flowery cluster
STYLE_WORD_LIST = (
    "delve", "delves", "delved", "delving", "showcasing", "underscores", "across", "additionally", "comprehensive",
    "crucial", "enhancing", "exhibited", "insights", "notably", "particularly", "within", "meticulously", "intricate",
    "pivotal",
)
HEDGE_LIST = ("helped", "contributed to", "assisted with", "played a key role")
RESUME_VERB_LIST = ("leveraged", "spearheaded", "orchestrated", "synergized", "drove innovation")


def any_phrase(phrases: tuple[str, ...]) -> re.Pattern:
    return re.compile(rf"\b({'|'.join(map(re.escape, phrases))})\b", re.I)


STYLE_WORDS = any_phrase(STYLE_WORD_LIST)
EM_DASH = "\u2014"
MARKDOWN = re.compile(r"\*\*|__|^#+\s|##|`|\[[^\]]*\]\([^)]*\)", re.M)
INVISIBLE = re.compile("[\u00a0\u202f\u200b\u200c\u200d\u2060\ufeff]")
ROUND_PERCENT = re.compile(r"\b(10|15|20|25|30|40|50|100)%")
HEDGES = any_phrase(HEDGE_LIST)
RESUME_VERBS = any_phrase(RESUME_VERB_LIST)
NOT_ONLY = re.compile(r"\bnot only\b.*\bbut also\b", re.I)
TRIAD = re.compile(r"\b[\w-]+, [\w-]+,? and [\w-]+\b")
# pre-AI role (ai_era false) naming any of these = backdated AI claim
AI_TERMS = re.compile(
    r"\b(LLMs?|GPT[-\w.]*|ChatGPT|Claude|OpenAI|Anthropic|Gemini|LangChain|LlamaIndex|RAG|retrieval-augmented|"
    r"embeddings?|vector (search|database|store)|pgvector|Pinecone|AI agents?|LLM agents?|agentic|"
    r"prompt engineering|fine-tun\w+|Copilot|evals?|eval harness\w*)\b",
    re.I,
)
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
# number, or word w/ optional .js / C++ / C# tail
TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+(?:[.+#][^\W\d_]+|[+#]+)*")
SENTENCE_START = re.compile(r"(^|[.;:!?]\s+)$")
# craft floor, unmeasured (plan #AI-tell lint WARN ONLY): bullet lengths this uniform read templated
MIN_BULLET_LENGTH_CV = 0.15


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


def lint(model: dict, master: dict, inferences: list[dict] | None = None) -> list[Finding]:
    inferences = inferences or []
    findings: list[Finding] = []
    master_page = [norm(s) for s in render.page_strings(render.page_model(master))]
    verbatim = set(master_page) | {norm(s) for s in master_strings(master)}
    corpus = " ".join(master_strings(master))
    known = {t.casefold() for t in TOKEN.findall(corpus)}
    known_terms = {norm(s) for e in [*master["roles"], *master.get("projects", [])] for b in e["bullets"] for s in b.get("stack", [])}
    known_terms |= {norm(i) for g in master.get("skills", []) for i in g["items"]}
    entries = {e["id"]: e for e in [*master["roles"], *master.get("projects", [])]}
    bullet_ids = {b["id"] for e in entries.values() for b in e["bullets"]}

    for role in master["roles"]:
        if not schema.LEGAL_IDENTIFIER.search(role["company"].strip()):
            findings.append(Finding(WARN, "company-legal-id", f"roles/{role['id']}", f"{role['company']!r} lacks Inc./LLC/...; add if employer has one"))

    for i, inference in enumerate(inferences):
        unknown = [b for b in inference.get("from", []) if b not in bullet_ids]
        if not inference.get("from") or unknown:
            findings.append(Finding(FAIL, "inference-source", f"inferences[{i}]", f"from {inference.get('from')} - unknown ids {unknown}"))
        known |= {t.casefold() for t in TOKEN.findall(inference.get("claim", ""))}

    def hit(rule: str, where: str, text: str, detail: str, own_wording: bool) -> None:
        # candidate's own wording never hard-fails: target register, reported so selection can skip it
        findings.append(Finding(WARN if own_wording else FAIL, rule, where, f"{detail}: {text!r}"))

    for kind, where, text, entry_id in page_items(model):
        own = norm(text) in verbatim
        is_bullet = kind == "bullet"
        if words := sorted({m.group().lower() for m in STYLE_WORDS.finditer(text)}):
            hit("style-word", where, text, f"{', '.join(words)}", own)
        if EM_DASH in text:
            hit("em-dash", where, text, "U+2014", own)
        if MARKDOWN.search(text):
            hit("markdown", where, text, f"{MARKDOWN.search(text).group()!r}", own)
        if INVISIBLE.search(text):
            hit("invisible-unicode", where, text, f"U+{ord(INVISIBLE.search(text).group()):04X}", own)
        for m in ROUND_PERCENT.finditer(text):
            if m.group() not in corpus:
                hit("round-metric", where, text, f"{m.group()} absent from master", own)
        if is_bullet and not (re.search(r"\d", text) or any(c.isupper() for c in text[1:]) or AI_TERMS.search(text) or any(t in norm(text) for t in known_terms)):
            hit("specificity", where, text, "no product, stack item, number or proper noun", own)
        # heading may carry JD's title as mirror suffix => check_entry_identity owns it
        if not own and kind != "heading":
            unresolved = sorted({e for e in entities(text) if e.casefold() not in known})
            if unresolved:
                findings.append(Finding(FAIL, "unresolved-entity", where, f"{unresolved} in no master fact or inference: {text!r}"))

        for rule, pattern in (("hedge", HEDGES), ("resume-verb", RESUME_VERBS), ("not-only-but-also", NOT_ONLY), ("rule-of-three", TRIAD)):
            if kind in ("bullet", "summary") and (m := pattern.search(text)):
                findings.append(Finding(WARN, rule, where, f"{m.group()!r}: {text!r}"))
        if is_bullet and entry_id in entries:
            check_ai_era(entries[entry_id], where, text, findings)

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
    if len(lengths) >= 3:
        cv = statistics.pstdev(lengths) / statistics.mean(lengths)
        if cv < MIN_BULLET_LENGTH_CV:
            findings.append(Finding(WARN, "uniform-bullet-length", "page", f"word-count CV {cv:.2f} (floor {MIN_BULLET_LENGTH_CV})"))
    return findings


def check_ai_era(entry: dict, where: str, text: str, findings: list[Finding]) -> None:
    if not entry.get("ai_era") and (m := AI_TERMS.search(text)):
        findings.append(Finding(FAIL, "ai-era", where, f"{m.group()!r} inside entry with ai_era false: {text!r}"))
    if entry["end"] == schema.PRESENT:
        return
    for pattern, released in TOOL_RELEASED.items():
        if (m := pattern.search(text)) and entry["end"] < released:
            findings.append(Finding(FAIL, "ai-era", where, f"{m.group()!r} released {released}, entry ended {entry['end']}"))


def check_entry_identity(entry: dict, where: str, entries: dict, findings: list[Finding]) -> None:
    """Employer, title, dates = what verification catches; mirrored title allowed only as suffix."""
    source = entries.get(entry.get("id"))
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint untailored master page: AI-tell rules + honesty vs master")
    ap.add_argument("--master", type=Path, help="master yml (default config resume.master)")
    args = ap.parse_args()
    started = time.perf_counter()
    master = schema.load(args.master or cfg.resume_path(cfg.load(), "master"))
    findings = lint(render.page_model(master), master)
    for f in findings:
        print(f"  {f.severity}  {f.rule:22} {f.where:28} {f.detail}")
    fails = sum(f.severity == FAIL for f in findings)
    print(f"{fails} fail, {len(findings) - fails} warn in {time.perf_counter() - started:.2f}s")
    if fails:
        sys.exit("lint failed")


if __name__ == "__main__":
    main()
