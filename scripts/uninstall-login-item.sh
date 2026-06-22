#!/bin/bash
# Desinstalle l'overlay wptemps du lancement a l'ouverture de session.
set -euo pipefail

LABEL="com.wptemps.overlay"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "OK : LaunchAgent desinstalle (l'overlay ne se lancera plus a l'ouverture de session)."
