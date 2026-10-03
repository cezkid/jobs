# App window

VS Code window the Desktop icon opens (`app/launch.py`, `app/workspace.py`): look, pages, layout.
Measure in a scratch VS Code only (`JOBS_VSCODE_DIR`, [README](README.md)), never
the owner's own.

## Measured

- Look (`app/window/brand.py`, one token set): `workbench.colorCustomizations` per theme
  (`[Light Modern]`, `[Dark Modern]`) + `window.autoDetectColorScheme` => light by default, dark
  follows the computer; user's own theme elsewhere untouched. Highlighter only on marks (selected
  row, badge, say chip), always under ink. Contrast >= 4.5:1 per pair, tested.
- Pages: `markdown.styles: ["app/window/pages.css"]` - relative path joined to the first workspace
  folder (1.140 bundle read). Content sits in `.markdown-body`; body carries `vscode-light` /
  `vscode-dark` / `vscode-high-contrast`. Caladea via relative `url()` from `app/resume/fonts`
  loads (preview CSP font-src = webview source); seen live, scratch window, 2026-10-03.
- Scratch dir path must stay short: VS Code's IPC socket `<data>/1.14-main.sock` over 103 chars
  => window never opens, launch still exits 0. Use `mktemp -d /tmp/jfv.XXXX`.

## Rejected
