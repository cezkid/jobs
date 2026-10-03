# Desktop icon

What the user double-clicks to open Job Finder. Brand mark = `docs/icon.svg`.

- Files: `app/install/icon.icns` (Mac), `app/install/icon.ico` (Windows), drawn from the svg
  geometry by `uv run --with pillow python app/install/icons.py` - dev step, output committed,
  Pillow never a runtime dependency. Mark changed => rerun, commit both.
- Mac: `make-icon-mac.sh [path]` - osacompile applet, `applet.icns` swapped in, `Assets.car` +
  `CFBundleIconName` removed (else the asset catalog's generic script picture wins), ad-hoc
  re-signed (else `codesign -v` calls the Info.plist invalid). Measured 2026-10-03.
- Existing app edited in place (rm + recreate moves the icon on the Desktop); recreated only when
  missing or opening another folder.
- Launch (`ensure_mac_icon`): old `.command` icon or applet w/ a different `applet.icns` => maker
  runs once.
- Dock + app switcher show VS Code's own icon once it's open: Microsoft-signed app, its icon
  can't be changed by us. Only the Desktop icon carries the brand.
- Mac margin: body 824 of 1024 px (macOS 11+ grid) => same size as other Desktop apps. Windows
  icon edge to edge.
- Windows: installer's Desktop shortcut -> `start-windows.bat` (kept: Smart App Control work hooks
  it; uvw/pythonw fail silently when SAC blocks Python), `IconLocation` = `app\install\icon.ico`,
  `WindowStyle` 7 = console minimized to the taskbar during update + launch, never over the screen.
- Launch (`ensure_windows_icon`): shortcuts made before 2026-10-03 (VS Code's icon, console in
  front) re-pointed once by hidden powershell, only when the shortcut's target is this install's
  `start-windows.bat`; missing shortcut never recreated. Done => `.data/desktop-icon-refreshed`;
  failed run retried next launch.
- Taskbar + running window show VS Code's icon (its AppUserModelID `Microsoft.VisualStudioCode`):
  only the Desktop shortcut carries the brand, as on Mac.
