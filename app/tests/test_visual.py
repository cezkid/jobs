"""Pixel snapshots of the resume + letter templates.

Runtime gates measure geometry; a change to indents, bold weight or date alignment in the Typst
templates passes them unnoticed. Each fixture renders to one PNG per page (72 ppi) and is compared
with app/tests/fixtures/visual/<fixture>-<page>.png: at most 0.2% of pixels may differ, and the
page count must match baselines.json.

No baselines yet -> the comparison tests skip. Operator step:
`UPDATE_VISUAL=1 uv run pytest -n 0 app/tests/test_visual.py` writes them; review the PNGs, then commit.
Windows stability is unverified: baselines come from one machine's Typst + bundled fonts.
"""
import copy
import json
import os
import re
import shutil
from datetime import date

import pymupdf
import pytest
import typst
import yaml

import cfg
from resume import letter, render, schema, typeface

DIR = cfg.APP / "tests" / "fixtures" / "visual"
FIXTURES = yaml.safe_load((DIR / "fixtures.yml").read_text(encoding="utf-8"))
BASELINES = DIR / "baselines.json"
BASES = {"example": cfg.APP / "resume" / "master.example.yml", "student": cfg.APP / "tests" / "fixtures" / "student.yml"}
TODAY = date(2026, 10, 1)
PPI = 72
MAX_DIFF = 0.002
UPDATE = bool(os.environ.get("UPDATE_VISUAL"))


def merged(base, patch):
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = dict(base)
    for k, v in patch.items():
        out[k] = merged(base[k], v) if k in base else copy.deepcopy(v)
    return out


def master_of(spec: dict) -> dict:
    # Patch the file as written, then load it: ids + derived fields come from schema.expand.
    raw = yaml.safe_load(BASES[spec["base"]].read_text(encoding="utf-8"))
    master = merged(raw, spec.get("patch", {}))
    if n := spec.get("repeat_roles"):
        roles = []
        for i in range(n):
            for r in master["roles"]:
                r = copy.deepcopy(r)
                if "id" in r:
                    r["id"] = f"{r['id']}-{i}"
                for b in r["bullets"]:
                    if isinstance(b, dict) and "id" in b:
                        b["id"] = f"{b['id']}-{i}"
                roles.append(r)
        master["roles"] = roles
    # No schema.validate: repeated roles break newest-first order, which the page doesn't need.
    return schema.expand(master)


def compile_png(template, model) -> list[bytes]:
    out = typst.compile(
        str(template), format="png", ppi=PPI,
        font_paths=[str(typeface.folder(typeface.use(typeface.DEFAULT)))], ignore_system_fonts=True,
        sys_inputs={"data": json.dumps(model, ensure_ascii=False)},
    )
    return list(out) if isinstance(out, (list, tuple)) else [out]


def pages_of(name: str) -> list[pymupdf.Pixmap]:
    spec = FIXTURES[name]
    master = master_of(spec)
    if spec["kind"] == "letter":
        model, template = letter.page(master, spec["paragraphs"], TODAY), letter.TEMPLATE
    else:
        model, template = render.page_model(master, TODAY), render.TEMPLATE
    return [pymupdf.Pixmap(png) for png in compile_png(template, render.with_page(model, typeface.DEFAULT))]


def differing(a: pymupdf.Pixmap, b: pymupdf.Pixmap) -> float:
    if (a.width, a.height, a.n) != (b.width, b.height, b.n):
        return 1.0
    x, y = a.samples, b.samples
    if x == y:
        return 0.0
    n = a.n
    bad = sum(1 for i in range(0, len(x), n) if x[i:i + n] != y[i:i + n])
    return bad / (a.width * a.height)


def need_baselines():
    if not BASELINES.exists():
        pytest.skip("no baselines yet - run the operator step: UPDATE_VISUAL=1 uv run pytest -n 0 app/tests/test_visual.py")


def write_baselines():
    counts = {}
    for name in FIXTURES:
        pages = pages_of(name)
        counts[name] = len(pages)
        for old in DIR.glob(f"{name}-*.png"):
            if re.fullmatch(re.escape(name) + r"-\d+\.png", old.name):
                old.unlink()
        for i, pix in enumerate(pages, 1):
            pix.save(str(DIR / f"{name}-{i}.png"))
    BASELINES.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.mark.parametrize("name", list(FIXTURES))
def test_matches_baseline(name):
    if UPDATE:
        write_baselines()
        return
    need_baselines()
    counts = json.loads(BASELINES.read_text(encoding="utf-8"))
    assert name in counts, f"{name} has no baseline - run the operator step"
    pages = pages_of(name)
    assert len(pages) == counts[name]
    for i, pix in enumerate(pages, 1):
        base = pymupdf.Pixmap((DIR / f"{name}-{i}.png").read_bytes())
        assert differing(pix, base) <= MAX_DIFF, f"{name} page {i} differs from its baseline"


@pytest.mark.parametrize("name", ["resume-example", "letter"])
def test_render_is_stable(name):
    first, second = pages_of(name), pages_of(name)
    assert len(first) == len(second)
    assert all(a.samples == b.samples for a, b in zip(first, second))


def test_margin_change_is_caught(tmp_path, monkeypatch):
    need_baselines()
    copy_dir = tmp_path / "templates"
    shutil.copytree(render.TEMPLATE.parent, copy_dir)
    tpl = copy_dir / render.TEMPLATE.name
    src = tpl.read_text(encoding="utf-8")
    changed = src.replace("d.page.margin_x_in * 1in", "(d.page.margin_x_in + 0.5) * 1in", 1)
    assert changed != src
    tpl.write_text(changed, encoding="utf-8")
    monkeypatch.setattr(render, "TEMPLATE", tpl)
    pages = pages_of("resume-example")
    base = pymupdf.Pixmap((DIR / "resume-example-1.png").read_bytes())
    assert differing(pages[0], base) > MAX_DIFF
