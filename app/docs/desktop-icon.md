# Desktop icon

What the user double-clicks to open Job Finder. Art = `app/install/icon.svg` (master, 64 px up)
+ `icon-32.svg`, `icon-16.svg` (hand-tuned on whole pixels: master blurs there).

- Route B "Page on ink" (owner pick 2026-10-03, routes shown at 256-16 px + in a Dock): white page,
  yellow highlight running off its edge, dark tile w/ depth. Chrome, Figma, VS Code sit on light
  tiles on macOS 26 (measured) => dark tile found at a glance; old flat black mark read cheap.
- Killed: Swipe (Notes look-alike small), Morning (reads weather / calendar), Marked J (one letter
  says little; Microsoft advises no letters), Marker (highlighter pen = PDF-highlighting apps).
- Site favicon (`docs/icon.svg`) unchanged - separate owner decision.
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
