#!/bin/bash
# Construit dist/wptemps.app (app partageable, Apple Silicon).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v macmon >/dev/null 2>&1 && [ ! -x /opt/homebrew/bin/macmon ]; then
  echo "Erreur: macmon introuvable. Installe-le : brew install macmon" >&2
  exit 1
fi

rm -rf build dist
.venv/bin/python setup.py py2app

echo
echo "App construite : $ROOT/dist/wptemps.app"
echo "Partage : compresse dist/wptemps.app (zip). Au 1er lancement : clic-droit -> Ouvrir."
