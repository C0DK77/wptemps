# wptemps — températures du Mac sur le fond d'écran

Affiche les températures CPU/GPU, la charge CPU, la RAM et la batterie
par-dessus le fond d'écran macOS, rafraîchies toutes les 5 s.

## Prérequis
- macOS Apple Silicon
- `brew install macmon`
- Python 3.9+

## Installation
```bash
/usr/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Lancer (mode recommandé : overlay)
```bash
.venv/bin/python -m wptemps.overlay
```
Affiche le texte dans une fenêtre transparente épinglée **au niveau du bureau**
(derrière les icônes et les fenêtres). Ton fond d'écran n'est **pas modifié**
et reste dynamique. Pour quitter : Ctrl-C (ou tuer le process) — rien à restaurer.

## Mode alternatif : image de fond régénérée
```bash
.venv/bin/python -m wptemps.main
```
Remplace le fond d'écran par une image (wallpaper + texte incrusté), rafraîchie
en boucle. Ctrl-C restaure le fond d'origine. Limite : le fond devient une image
fixe à la résolution de la source ; préférer le mode overlay.

## Configuration
Réglages dans `wptemps/config.py` : intervalle, position (`top-right`,
`top-left`, `bottom-left`, `bottom-right`), couleur, opacité, taille de police.
Si le texte est peu lisible sur un fond clair, augmenter le contraste
(`color=(0, 0, 0)` ou `opacity=230`).

## Tests
```bash
.venv/bin/pytest -q
```

## Phase 2 (à venir)
Support Windows (Asus) : lecture des températures via LibreHardwareMonitor
et application du wallpaper via l'API Windows.
