#!/bin/bash
# Construit dist/wptemps.app puis l'empaquette dans un .dmg partageable
# (avec un raccourci vers /Applications pour l'installation par glisser-deposer).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-1.0.0}"
APP="dist/wptemps.app"
DMG="dist/wptemps-${VERSION}.dmg"
STAGE="dist/dmg-stage"

# 1) construire l'app
bash build.sh

# 2) preparer le contenu du dmg
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

# 3) creer le dmg compresse
hdiutil create -volname "wptemps" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

SHA=$(shasum -a 256 "$DMG" | awk '{print $1}')
echo
echo "DMG cree : $ROOT/$DMG"
echo "sha256   : $SHA"
echo
echo "-> Televerse ce .dmg dans une Release GitHub, puis mets a jour"
echo "   l'URL et le sha256 dans Casks/wptemps.rb."
