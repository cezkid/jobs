#!/bin/bash
# Desktop icon = small app, not a .command => no Terminal window left open once VS Code is up.
# Optional arg: where the app goes (tests pass a tmp path, never the real Desktop).
# Dock still shows VS Code's own icon once it runs (Microsoft-signed app, can't change).
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
app="${1:-$HOME/Desktop/CEZ Job Finder.app}"
script="$app/Contents/Resources/Scripts/main.scpt"
# edited in place when it already opens this folder: rm + recreate moves the icon on the Desktop
if ! osadecompile "$script" 2>/dev/null | grep -qF "set d to \"$DIR\""; then
  rm -rf "${app:?}"
  osacompile -o "$app" -e "set d to \"$DIR\"" \
    -e 'do shell script "bash " & quoted form of (d & "/app/install/start-mac.sh") & " >/dev/null 2>&1 &"'
fi
# brand icon: applet.icns only counts once the asset catalog + its plist key are gone;
# re-signed or codesign calls the Info.plist invalid (measured 2026-10-03)
res="$app/Contents/Resources"
cp "$DIR/app/install/icon.icns" "$res/applet.icns"
rm -f "$res/Assets.car"
/usr/libexec/PlistBuddy -c 'Delete :CFBundleIconName' "$app/Contents/Info.plist" 2>/dev/null
codesign --force --deep -s - "$app" 2>/dev/null
touch "$app"  # Finder redraws the icon
rm -f "${app%.app}.command"  # icon from installs before the app
