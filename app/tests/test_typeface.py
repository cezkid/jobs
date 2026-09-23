import re
import shutil

import pymupdf
import pytest

import cfg
from resume import measure, render, schema, tailor, typeface

EXAMPLE = cfg.APP / "resume" / "master.example.yml"
SHIPPED = typeface.folder(typeface.DEFAULT)


@pytest.fixture
def master() -> dict:
    return schema.load(EXAMPLE)


def family_dir(tmp_path, name: str, keep=("Regular", "Bold")) -> None:
    """A font folder built out of the shipped family, so only the named face list is the variable."""
    (tmp_path / name).mkdir()
    for style in keep:
        shutil.copy(SHIPPED / f"{typeface.DEFAULT}-{style}.ttf", tmp_path / name / f"{name}-{style}.ttf")


def test_shipped_family_covers_the_weights_the_template_cannot_do_without():
    found = typeface.faces(typeface.DEFAULT)
    assert all(weight in found for weight in typeface.REQUIRED)
    assert typeface.check(typeface.DEFAULT) == []


def test_unknown_font_names_the_ones_installed():
    with pytest.raises(SystemExit, match=f"Installed: {typeface.DEFAULT}"):
        typeface.use("Helvetica Neue")


def test_a_family_without_600_still_renders_its_headings(master, tmp_path):
    # Caladea has no semibold; Typst answers weight 600 with the bold it does have
    assert typeface.SEMIBOLD not in typeface.faces(typeface.DEFAULT)
    _, results = render.render(render.page_model(master), tmp_path, budget=False, font=typeface.DEFAULT)
    assert not [name for name, ok, _ in results if not ok]


def test_missing_bold_is_reported_before_anything_renders(tmp_path, monkeypatch):
    monkeypatch.setattr(typeface, "DIR", tmp_path)
    family_dir(tmp_path, typeface.DEFAULT, keep=("Regular",))
    assert any("no bold face" in p for p in typeface.check(typeface.DEFAULT))


def test_folder_not_named_as_the_font_names_itself_is_reported(tmp_path, monkeypatch):
    # Typst finds a family by the name inside the file, so a mismatched folder renders nothing
    monkeypatch.setattr(typeface, "DIR", tmp_path)
    family_dir(tmp_path, "Helvetica")
    assert any(f"calls itself '{typeface.DEFAULT}" in p for p in typeface.check("Helvetica"))


def test_configured_font_is_the_one_embedded(master, tmp_path):
    path, results = render.render(render.page_model(master), tmp_path, budget=False, font=typeface.DEFAULT)
    with pymupdf.open(path) as doc:
        embedded = {f[3].split("+")[-1] for page in range(doc.page_count) for f in doc.get_page_fonts(page)}
    assert embedded and all(name.startswith(typeface.DEFAULT) for name in embedded)
    assert not [name for name, ok, _ in results if not ok]


def test_bullet_width_is_the_column_less_the_marker_it_renders(master, tmp_path):
    # the hanging indent is part em, part marker glyph: read it off the page, not off a constant
    model = render.page_model(master)
    path, _ = render.render(model, tmp_path, budget=False, font=typeface.DEFAULT)
    with pymupdf.open(path) as doc:
        words = doc[0].get_text("words")
    left = min(x0 for x0, *_ in words)
    markers = [(x0, b, l) for x0, _, _, _, w, b, l, n in words if w == "\u2022" and n == 0]
    assert markers, "no list marker on the page"
    _, block, line = markers[0]
    body = min(x0 for x0, _, _, _, _, b, l, n in words if (b, l) == (block, line) and n == 1)
    assert measure.bullet(typeface.DEFAULT) == pytest.approx(measure.COLUMN - (body - left), abs=0.05)


def test_char_guides_bracket_the_gap_that_makes_a_stub():
    one, (low, high) = tailor.char_guides(typeface.DEFAULT)
    assert one < low < high
    prose, avail = tailor.GUIDE_PROSE, measure.bullet(typeface.DEFAULT)
    assert measure.fit(typeface.DEFAULT, prose[:one], avail)[0] == 1
    lines, fill = measure.fit(typeface.DEFAULT, prose[:low], avail)
    # the low edge is where the window starts, so it has to be a length worth writing to, not
    # merely one the gate stops failing: at the old MIN_LINE_FILL edge it came out 48% empty
    assert lines == tailor.MAX_BULLET_LINES and fill >= tailor.TWO_LINE_FILL
    assert measure.fit(typeface.DEFAULT, prose[:high], avail)[0] == tailor.MAX_BULLET_LINES


def test_a_bullet_written_into_the_gap_is_sent_back():
    one, (low, _) = tailor.char_guides(typeface.DEFAULT)
    middle = tailor.GUIDE_PROSE[:(one + low) // 2]
    assert [v for v in tailor.bullet_shape(middle, "gap", typeface.DEFAULT) if "wraps to a line only" in v]


def test_two_line_window_stays_wide_enough_to_write_in():
    # a second line is capped by what two lines hold, so the window narrows as its low edge
    # rises - measured in Caladea: 49 characters at 40%, 28 at 60%, 4 at 85%, empty at 90%.
    # Anything that shrinks it past a few words leaves the writer no length to choose.
    _, (low, high) = tailor.char_guides(typeface.DEFAULT)
    assert high - low >= 20


def test_advice_to_fill_two_lines_lands_inside_the_two_line_window():
    """Following the advice has to end somewhere legal: filled, and still two lines."""
    prose, avail = tailor.GUIDE_PROSE, measure.bullet(typeface.DEFAULT)
    one, (low, _) = tailor.char_guides(typeface.DEFAULT)
    stubbed = prose[:(one + low) // 2]
    violation, = tailor.bullet_shape(stubbed, "gap", typeface.DEFAULT)
    add = int(re.search(r"add ~(\d+)", violation).group(1))
    lines, fill = measure.fit(typeface.DEFAULT, prose[:len(stubbed) + add], avail)
    assert lines == tailor.MAX_BULLET_LINES and fill >= tailor.TWO_LINE_FILL
