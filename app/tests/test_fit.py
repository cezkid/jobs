from resume import fit, measure, render, tailor, typeface

FONT = typeface.DEFAULT
AVAIL = measure.bullet(FONT)


def status(text: str) -> str:
    return fit.report(FONT, text, "candidate", AVAIL)[0]


def test_one_line_and_filled_two_lines_both_pass():
    one, (low, _) = tailor.char_guides(FONT)
    assert status(tailor.GUIDE_PROSE[:one]) == "ok"
    assert status(tailor.GUIDE_PROSE[:low]) == "ok"


def test_a_bullet_the_page_refuses_is_reported_as_fail():
    one, (low, _) = tailor.char_guides(FONT)
    assert status(tailor.GUIDE_PROSE[:(one + low) // 2]) == "fail"


def test_a_second_line_under_the_writing_target_is_thin_not_ok():
    """The band between the FAIL floor and the target: legal on the page, still a wasted row.

    Reporting these as `ok` is the failure the command exists to prevent - the gate answers
    "does this stop the render", never "is this worth writing".
    """
    prose = tailor.GUIDE_PROSE
    thin = [n for n in range(len(prose))
            if (f := measure.fit(FONT, prose[:n], AVAIL))[0] > 1
            and render.MIN_LINE_FILL <= f[1] < tailor.TWO_LINE_FILL]
    assert thin, "no length lands between the floor and the target"
    assert status(prose[:thin[0]]) == "thin"
    assert not tailor.bullet_shape(prose[:thin[0]], "candidate", FONT)


def test_thin_advice_lands_on_an_edge():
    """Following what `thin` says has to end somewhere worth writing, not merely somewhere legal."""
    prose = tailor.GUIDE_PROSE
    thin = next(n for n in range(len(prose))
                if (f := measure.fit(FONT, prose[:n], AVAIL))[0] > 1
                and render.MIN_LINE_FILL <= f[1] < tailor.TWO_LINE_FILL)
    advice = fit.sizing(FONT, prose[:thin], AVAIL)
    add = int(advice.split("add ~")[1].split(" ")[0])
    lines, filled = measure.fit(FONT, prose[:thin + add], AVAIL)
    assert lines == tailor.MAX_BULLET_LINES and filled >= tailor.TWO_LINE_FILL
