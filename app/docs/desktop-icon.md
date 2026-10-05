# Desktop icon

What the user double-clicks to open Job Finder. Art = `app/install/icon.svg` (master, 64 px up)
+ `icon-32.svg`, `icon-16.svg` (hand-tuned on whole pixels: master blurs there).

- "Blackbird on ink" (owner pick 2026-10-04: bird picked from 8 site concepts, tile kept from
  route B for findability): blackbird, "the first one up" - ink body, highlighter-yellow beak; on
  the tile the pale cut (#f2f2f2). Dark tile w/ depth, Apple 1024 grid. Chrome, Figma, VS Code sit
  on light tiles on macOS 26 (measured) => dark tile found at a glance.
- Crop system, one mark everywhere (owner 2026-10-04): Desktop = bird on the dark tile; site =
  bare bird beside the name, no tile (header, browser tab, share cards); dark page: bird in the
  page's text tone (#f2f2f2), yellow beak. Site side: `site.md`.
- Bare bird: `app/install/mark.svg` (master, 256 grid) + `mark-32.svg` (small cut, whole pixels
  at 32 + 16 px). One home w/ the tile art => `icon-sync.json` guards both.
- Art contract (generators read it; each file's `<desc>` repeats its part):
  - `mark-32.svg`: `viewBox="0 0 32 32"`; shapes (`path`, `circle`, `rect`, `ellipse` or
    `polygon`) direct children of the `<svg>`, one a line, each w/ `class` first - `ink`, `beak`,
    `eye`, all three used - + its `fill` as an attribute, lowercase: ink `#000000`, beak + eye
    `#ffe433`; no id, style, transform, defs, group. `assets.mark_shapes()` fails otherwise.
    Dark cut never drawn: derived (ink => text tone, eye => page colour, beak stays) => same
    outline both schemes.
  - `mark.svg`: `viewBox="0 0 256 256"`, same classes (+ `pupil`), used as is (share cards, light).
  - `icon.svg`: 1024 grid, tile 824 at 100; bird in one `<g id="bird">` (assets.py measures it:
    farthest point <= 0.40 of the side from centre at 1024 / 824, else the maskable icon fails).
  - `icon-32.svg`, `icon-16.svg`: `<rect id="tile" .../>` on one line (`icons.py` regrows it for
    Windows), bird on whole pixels - 16 px redrawn by hand (head 3 px, legs 1 px, beak 2 x 1 px,
    no eye): the small cut scaled to 8 px = grey blob, no yellow left (measured). Test holds a
    full-yellow beak pixel in both small favicon frames.
- Was (2026-10-03): route B "Page on ink" - white page, yellow highlight off its edge, same tile.
  Killed 2026-10-04, owner: disliked as the site's logo - a generic file icon in an app tile.
  Before it: flat black mark, read cheap.
- Killed: Swipe (Notes look-alike small), Morning (reads weather / calendar), Marked J (one letter
  says little; Microsoft advises no letters), Marker (highlighter pen = PDF-highlighting apps).
- Files: `app/install/icon.icns` (Mac), `app/install/icon.ico` (Windows) by `uv run --with pillow
  python app/install/icons.py` - headless Chrome renders, Pillow packs. Dev step, output
  committed, neither a runtime dependency. Art changed => rerun, commit both.
  `ICON_PREVIEW=<png>` also writes a light + dark preview sheet.
- Mac: `make-icon-mac.sh [path]` - osacompile applet, `applet.icns` swapped in, `Assets.car` +
  `CFBundleIconName` removed (else the asset catalog's generic script picture wins), ad-hoc
  re-signed (else `codesign -v` calls the Info.plist invalid). Measured 2026-10-03.
- Existing app edited in place (rm + recreate moves the icon on the Desktop); recreated only when
  missing or opening another folder.
- Launch (`ensure_mac_icon`): old `.command` icon or applet w/ a different `applet.icns` => maker
  runs once.
- Dock + app switcher show VS Code's own icon once it's open: Microsoft-signed app, its icon
  can't be changed by us. Only the Desktop icon carries the brand.
- Mac margin: body 824 of 1024 px (macOS 11+ grid) => same size as other Desktop apps. Windows:
  master cropped to `viewBox 70 70 884 884` (tile ~93%), small rungs' tile 1 px from the edge -
  a Mac margin makes the shortcut look smaller than its neighbours.
- Windows: installer's Desktop shortcut -> `start-windows.bat` (kept: Smart App Control work hooks
  it; uvw/pythonw fail silently when SAC blocks Python), `IconLocation` = `app\install\icon.ico`,
  `WindowStyle` 7 = console minimized to the taskbar during update + launch, never over the screen.
- Launch (`ensure_windows_icon`): shortcuts made before 2026-10-03 (VS Code's icon, console in
  front) re-pointed once by hidden powershell, only when the shortcut's target is this install's
  `start-windows.bat`; missing shortcut never recreated. Done => `.data/desktop-icon-refreshed`;
  failed run retried next launch.
- Taskbar + running window show VS Code's icon (its AppUserModelID `Microsoft.VisualStudioCode`):
  only the Desktop shortcut carries the brand, as on Mac.
- Morning notification (Windows): toast names + pictures the app whose AppUserModelID it carries.
  Launch (`ensure_start_shortcut`) writes Start Menu `CEZ Job Finder.lnk` (-> `start-windows.bat`,
  brand icon, `System.AppUserModel.ID` = `CEZ.JobFinder`) as bytes from Python (`app/shortcut.py`,
  [MS-SHLLINK] + [MS-PROPSTORE]): WScript.Shell can't set the id, IPropertyStore needs Add-Type C#
  (unsigned temp DLL - Smart App Control / Constrained Language Mode). Rewritten when bytes differ
  (install moved). `notify` uses `CEZ.JobFinder` only while that shortcut exists, and falls back
  to PowerShell's id inside the script if Windows refuses ours - never no toast. Click still goes
  through `jobfinder:`. owner: pending - live Windows check (plan-ejf.12.3 child).
