"""Does this wording fit? - asked before writing, not after rendering a whole page.

`bullet_shape` has always known the answer, but only `tailor check` ever asked it, so anyone
editing a bullet in the master details had one way to find out: render the PDF and read the
line-fill gate. That is a 2s round trip reporting on a page, when the question is about one
sentence - and it cannot be asked at all about a sentence not yet written into the file.

So this prints the two target sizes first. A bullet fits one line or fills two, and the gap
between them wraps to a stub wasting a row; knowing both edges before writing is what stops
the write-measure-rewrite loop, since a candidate aimed at an edge lands on it.
"""
import argparse
import sys
import time
from pathlib import Path

import cfg
from resume import measure, render, schema, tailor


def sizing(font: str, text: str, avail: float) -> str:
    """Cut to one line, or add to fill two - the two edges, in characters of this text."""
    cut = measure.chars_for(font, text, measure.width(font, text) - avail)
    tail = measure.wrap(font, text, avail)[-1]
    add = measure.chars_for(font, text, render.TARGET_LINE_FILL * avail - measure.width(font, tail))
    return f"cut {cut} to fit one line" + (f", or add ~{add} to fill two" if add > 0 else "")


def report(font: str, text: str, where: str, avail: float) -> tuple[str, str]:
    """How it renders, then what to do about it - judged at the target, not at the FAIL floor.

    `bullet_shape` speaks for the page: under `MIN_LINE_FILL` a row is wasted badly enough to
    stop the render. It is not the number to write at. A second line 45% full clears that gate
    and still throws away half a row, so a tool that answers "should I write this?" with the
    gate's threshold hands back an `ok` on the exact shape `app/docs/bullets.md` was written to
    stamp out. `thin` is that band: allowed on the page, not what to aim at.
    """
    lines, fill = measure.fit(font, text, avail)
    if shape := tailor.bullet_shape(text, where, font):
        return "fail", shape[0].split(": ", 1)[1].rsplit(": ", 1)[0]
    if lines > 1 and fill < tailor.TWO_LINE_FILL:
        return "thin", f"passes the page, wastes most of a row - {sizing(font, text, avail)}"
    return "ok", "ok"


def line(font: str, text: str, where: str, avail: float) -> str:
    status, advice = report(font, text, where, avail)
    lines, fill = measure.fit(font, text, avail)
    return (f"  {status:4} {lines} line(s), last {fill:.0%} full, {len(text)} chars - {advice}"
            f"\n       {text!r}")


def candidates(font: str, texts: list[str]) -> list[str]:
    avail = measure.bullet(font)
    return [line(font, t, f"candidate {n}", avail) for n, t in enumerate(texts, 1)]


def master_bullets(font: str, master: dict) -> list[str]:
    """Every bullet already on the page, so a badly sized one is named without a render."""
    avail, out = measure.bullet(font), []
    for group in ("roles", "projects"):
        for entry in master.get(group) or []:
            label = entry.get("company") or entry.get("name") or entry.get("title")
            for n, bullet in enumerate(entry.get("bullets") or [], 1):
                text = bullet["claim"] if isinstance(bullet, dict) else bullet
                where = f"{label} bullet {n}"
                if report(font, text, where, avail)[0] != "ok":
                    out.append(line(font, text, where, avail).replace("\n       ", f"\n       [{where}] ", 1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure candidate bullet wordings against the page, without rendering")
    ap.add_argument("text", nargs="*", help="candidate wordings, or - to read them a line at a time from stdin; none checks the master bullets")
    ap.add_argument("--master", type=Path, help="master yml (default config resume.master)")
    args = ap.parse_args()
    started = time.perf_counter()
    config = cfg.load()
    font = cfg.resume_font(config)
    one, (low, high) = tailor.char_guides(font)
    print(f"{font}: one line is about {one} chars or fewer; two full lines are {low}-{high}. "
          f"Between them wraps to a stub - aim at an edge.")

    texts = ([l.strip() for l in sys.stdin if l.strip()]
             if args.text == ["-"] else args.text)
    if texts:
        lines = candidates(font, texts)
    else:
        master = schema.load(args.master or cfg.resume_path(config, "master"))
        lines = master_bullets(font, master) or ["  ok   every bullet on the page fits one line or fills two"]
    print("\n".join(lines))
    print(f"{len(texts) or 'all'} checked in {time.perf_counter() - started:.2f}s")


if __name__ == "__main__":
    main()
