#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
APP="$OUT/DjVuBook AudioLab.app"
mkdir -p "$APP/Contents/MacOS" "$OUT"
MODULE_CACHE="${TMPDIR:-/tmp}/DjVuBookAudioLabSwiftModuleCache"
mkdir -p "$MODULE_CACHE"
swiftc -module-cache-path "$MODULE_CACHE" -framework AppKit -framework CryptoKit "$ROOT/AudioLabApp.swift" -o "$APP/Contents/MacOS/DjVuBook"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>DjVuBook</string>
<key>CFBundleIdentifier</key><string>local.djvubook.audiolab</string>
<key>CFBundleName</key><string>DjVuBook AudioLab</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.12.0</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST
cp "$ROOT"/*.py "$OUT/"
printf 'Created %s\n' "$APP"
