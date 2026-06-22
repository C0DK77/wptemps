#!/bin/bash
# Installe l'app wptemps (barre de menus) comme LaunchAgent (lancement a l'ouverture de session).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
LABEL="com.wptemps.overlay"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -x "$PY" ]; then
  echo "Erreur: venv introuvable ($PY). Lance d'abord l'installation (voir README)." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>-m</string>
        <string>wptemps.app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <!-- PATH explicite : launchd n'inclut pas /opt/homebrew/bin, requis pour macmon -->
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/wptemps_overlay.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/wptemps_overlay.err</string>
</dict>
</plist>
EOF

# (re)charge l'agent
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "OK : LaunchAgent installe et lance -> $PLIST"
echo "Pour l'arreter/desinstaller : scripts/uninstall-login-item.sh"
