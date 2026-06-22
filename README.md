# wptemps — températures du Mac sur le fond d'écran

Affiche les températures CPU/GPU, la charge CPU, la RAM et la batterie,
incrustées dans le fond d'écran macOS, rafraîchies toutes les 5 s.

## Prérequis
- macOS Apple Silicon
- `brew install macmon`
- Python 3.9+

## Installation
```bash
/usr/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Lancer
```bash
.venv/bin/python -m wptemps.main
```
Ctrl-C arrête le programme et restaure le fond d'écran d'origine.

## Configuration
Réglages dans `wptemps/config.py` : intervalle, position, couleur, opacité,
taille de police, ombre.

Si le texte est peu lisible sur un fond clair, augmenter le contraste
(`color=(0, 0, 0)` ou `opacity=230`). Le fond d'écran ne change que parce que
le chemin de l'image alterne entre `wp_a.png` et `wp_b.png` (macOS ignore une
re-définition vers le même chemin).

## Tests
```bash
.venv/bin/pytest -q
```

## Phase 2 (à venir)
Support Windows (Asus) : lecture des températures via LibreHardwareMonitor
et application du wallpaper via l'API Windows.
