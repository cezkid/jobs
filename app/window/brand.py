"""Job Finder's look in the VS Code window: the install site's highlighter-on-paper (docs/index.html).

One set of tokens => window colors (workspace.py), page stylesheet (pages.css) and contrast test all
read the same values. Yellow background only where a click does something (buttons, Today's "Open
the posting"; owner 2026-10-03), never body text, and always carries ink: white on #ffe433 is 1.3:1.
"""

PAPER = "#ffffff"
INK = "#000000"
INK_2 = "#3a3a3a"
RULE = "#c8c8c8"
MARK = "#ffe433"
# pressed / hover on a yellow button: one step deeper, ink text still
MARK_2 = "#f2cf00"
# dark desk = site's dark mode
DESK = "#1c1c1e"
TEXT_DARK = "#f2f2f2"
TEXT_DARK_2 = "#bdbdbd"
LINE = "#48484a"
# quiet tints between paper and rule (hover, inactive selection, sunk inputs); not on the site
WASH = "#f3f3f1"
DESK_2 = "#2c2c2e"

TOKENS = {"paper": PAPER, "ink": INK, "ink-2": INK_2, "rule": RULE, "mark": MARK, "mark-2": MARK_2, "desk": DESK,
          "text-dark": TEXT_DARK, "text-dark-2": TEXT_DARK_2, "line": LINE, "wash": WASH, "desk-2": DESK_2}


def chrome(bg: str, fg: str, fg_2: str, line: str, tint: str, button_bg: str, button_fg: str, ring: str) -> dict:
    """VS Code color ids for one theme; light + dark differ only in the values passed."""
    return {
        "foreground": fg,
        "descriptionForeground": fg_2,
        "focusBorder": ring,
        "widget.border": line,
        "titleBar.activeBackground": bg,
        "titleBar.activeForeground": fg,
        "titleBar.inactiveBackground": bg,
        "titleBar.inactiveForeground": fg_2,
        "titleBar.border": line,
        "activityBar.background": bg,
        "activityBar.foreground": fg,
        "activityBar.inactiveForeground": fg_2,
        "activityBar.activeBorder": ring,
        "activityBar.border": line,
        "activityBarTop.foreground": fg,
        "activityBarTop.inactiveForeground": fg_2,
        "activityBarTop.activeBorder": ring,
        "activityBarBadge.background": button_bg,
        "activityBarBadge.foreground": button_fg,
        "badge.background": button_bg,
        "badge.foreground": button_fg,
        "sideBar.background": bg,
        "sideBar.foreground": fg,
        "sideBar.border": line,
        "sideBarTitle.foreground": fg,
        "sideBarSectionHeader.background": bg,
        "sideBarSectionHeader.foreground": fg,
        "sideBarSectionHeader.border": line,
        "editor.background": bg,
        "editor.foreground": fg,
        "editorGroup.border": line,
        "editorGroupHeader.tabsBackground": bg,
        "editorGroupHeader.tabsBorder": line,
        "tab.activeBackground": bg,
        "tab.activeForeground": fg,
        "tab.activeBorderTop": ring,
        "tab.inactiveBackground": bg,
        "tab.inactiveForeground": fg_2,
        "tab.hoverBackground": tint,
        "tab.border": line,
        "statusBar.background": bg,
        "statusBar.foreground": fg_2,
        "statusBar.border": line,
        "statusBar.noFolderBackground": bg,
        "statusBar.noFolderForeground": fg_2,
        "statusBarItem.hoverBackground": tint,
        "statusBarItem.hoverForeground": fg,
        "statusBarItem.remoteBackground": bg,
        "statusBarItem.remoteForeground": fg,
        "panel.background": bg,
        "panel.border": line,
        "panelTitle.activeForeground": fg,
        "panelTitle.inactiveForeground": fg_2,
        "panelTitle.activeBorder": ring,
        # yellow background only where a click does something (owner rule 2026-10-03)
        "button.background": MARK,
        "button.foreground": INK,
        "button.hoverBackground": MARK_2,
        "button.secondaryBackground": tint,
        "button.secondaryForeground": fg,
        "list.activeSelectionBackground": tint,
        "list.activeSelectionForeground": fg,
        "list.activeSelectionIconForeground": fg,
        "list.inactiveSelectionBackground": tint,
        "list.inactiveSelectionForeground": fg,
        "list.hoverBackground": tint,
        "list.hoverForeground": fg,
        "list.focusOutline": ring,
        "list.highlightForeground": fg,
        "input.background": bg,
        "input.foreground": fg,
        "input.border": line,
        "input.placeholderForeground": fg_2,
        "dropdown.background": bg,
        "dropdown.foreground": fg,
        "dropdown.border": line,
        "scrollbarSlider.background": line + "80",
        "scrollbarSlider.hoverBackground": line + "c0",
        "scrollbarSlider.activeBackground": fg_2,
        "textLink.foreground": fg,
        "textLink.activeForeground": fg,
    }


# focus ring + active-tab line: ink on paper (yellow on white is invisible), highlighter on the dark desk
LIGHT = {
    **chrome(PAPER, INK, INK_2, RULE, WASH, button_bg=INK, button_fg=PAPER, ring=INK),
    # selected words in a resume file: quiet grey under ink (yellow means a button)
    "editor.selectionBackground": RULE,
    "editor.selectionForeground": INK,
}
DARK = {
    **chrome(DESK, TEXT_DARK, TEXT_DARK_2, LINE, DESK_2, button_bg=TEXT_DARK, button_fg=INK, ring=MARK),
    # dark editor text is near-white => highlighter would carry white text; a quiet grey instead
    "editor.selectionBackground": LINE,
}

THEMES = {"Light Modern": LIGHT, "Dark Modern": DARK}


def color_customizations() -> dict:
    """Per-theme blocks: the user's own theme choice elsewhere stays theirs."""
    return {f"[{theme}]": colors for theme, colors in THEMES.items()}


def pairs(colors: dict) -> list[tuple[str, str]]:
    """Every text color with the background it sits on, as VS Code color ids."""
    fg_bg = [("foreground", "sideBar.background"), ("descriptionForeground", "sideBar.background"),
             ("descriptionForeground", "editor.background"), ("textLink.foreground", "editor.background"),
             ("list.highlightForeground", "sideBar.background"), ("input.placeholderForeground", "input.background"),
             ("statusBarItem.hoverForeground", "statusBarItem.hoverBackground"),
             ("button.foreground", "button.hoverBackground"), ("list.hoverForeground", "list.hoverBackground")]
    for key in colors:
        for fg_word, bg_word in (("Foreground", "Background"), ("foreground", "background")):
            if key.endswith(fg_word):
                bg = key[: -len(fg_word)] + bg_word
                if bg in colors:
                    fg_bg.append((key, bg))
    return [(f, b) for f, b in dict.fromkeys(fg_bg) if f in colors and b in colors]


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    """WCAG ratio, 1..21."""
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)
