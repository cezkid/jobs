import re

import cfg
import workspace
from window import brand

CSS = cfg.ROOT / workspace.PAGES_CSS
WHITE = {"#ffffff", "#fff", "#f2f2f2"}


def css_block(selector: str) -> dict:
    body = re.search(re.escape(selector) + r"\s*\{(.*?)\}", CSS.read_text(encoding="utf-8"), flags=re.S).group(1)
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", body))


def test_window_wears_brand_colors_in_light_and_dark():
    # stock code-editor theme => the window reads as a developer tool, not Job Finder
    settings = workspace.settings("claude")
    colors = settings["workbench.colorCustomizations"]
    assert set(colors) == {"[Light Modern]", "[Dark Modern]"}
    assert colors["[Light Modern]"]["editor.background"] == brand.PAPER
    assert colors["[Dark Modern]"]["editor.background"] == brand.DESK
    # light by default, dark only when the computer is dark
    assert settings["window.autoDetectColorScheme"] is True
    assert settings["workbench.preferredLightColorTheme"] == "Light Modern"
    assert settings["workbench.preferredDarkColorTheme"] == "Dark Modern"
    assert workspace.settings("copilot")["workbench.colorCustomizations"] == colors


def test_every_window_text_color_readable():
    # grey-on-grey labels a job seeker can't read; WCAG AA 4.5:1
    for theme, colors in brand.THEMES.items():
        found = brand.pairs(colors)
        assert len(found) > 20
        for fg, bg in found:
            ratio = brand.contrast(colors[fg][:7], colors[bg][:7])
            assert ratio >= 4.5, f"{theme}: {fg} on {bg} = {ratio:.2f}"


def test_highlighter_always_carries_ink():
    # white on #ffe433 is 1.3:1 - unreadable badge or selected row
    for theme, colors in brand.THEMES.items():
        for key, value in colors.items():
            if value.lower() == brand.MARK and re.search(r"[Bb]ackground$", key):
                fg = re.sub(r"([Bb])ackground$", lambda m: "Foreground" if m.group(1) == "B" else "foreground", key)
                assert colors.get(fg) == brand.INK, f"{theme}: {key} is highlighter, {fg} = {colors.get(fg)}"
    for selector in ("body.vscode-light", "body.vscode-dark"):
        tokens = css_block(selector)
        assert tokens["mark-text"] == brand.INK and tokens["mark-text"] not in WHITE


def test_page_text_readable_light_and_dark():
    # Today's lines + say chips on paper and on the dark desk
    for selector in ("body.vscode-light", "body.vscode-dark"):
        t = css_block(selector)
        for fg, bg in (("text", "desk"), ("text-2", "desk"), ("text", "card"), ("text-2", "card"), ("mark-text", "mark")):
            ratio = brand.contrast(t[fg], t[bg])
            assert ratio >= 4.5, f"{selector}: {fg} on {bg} = {ratio:.2f}"


def test_page_stylesheet_uses_only_brand_colors():
    # a stray hex drifts the pages away from the window + site
    used = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", CSS.read_text(encoding="utf-8"))}
    assert used and used <= set(brand.TOKENS.values())


def test_page_stylesheet_exists_and_loads_nothing_remote():
    # missing file => VS Code warns "Could not load 'markdown.styles'" on every page;
    # a remote font would tell a third party each time a page opens
    assert workspace.settings("claude")["markdown.styles"] == [workspace.PAGES_CSS]
    assert CSS.is_file()
    text = CSS.read_text(encoding="utf-8")
    assert not re.search(r"https?:|//[a-z]", text.replace("/*", "").replace("*/", ""), flags=re.I)
    assert "@import" not in text
    for url in re.findall(r'url\("([^"]+)"\)', text):
        assert (CSS.parent / url).resolve().is_file(), url
