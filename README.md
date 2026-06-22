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

## Lancer (app barre de menus)
```bash
.venv/bin/python -m wptemps.app
```
Une icône 🌡 apparaît dans la barre de menus. Le menu permet d'afficher/masquer,
de **déverrouiller pour déplacer** l'affichage (puis le reverrouiller), de choisir
**Police…** (police, taille, gras/italique), **Couleur…** (couleur + opacité) et
**Alignement** (gauche/centre/droite), **Infos machine** (en-tête OS / modèle / puce /
cœurs / RAM / disque) et **Conso (watts)** (puissance CPU/GPU), et de quitter. Tous ces
réglages — et la position — sont mémorisés dans `~/Library/Application Support/wptemps/settings.json`.
Ton fond d'écran n'est **jamais modifié**.

Mode overlay seul (sans menu) : `.venv/bin/python -m wptemps.overlay`.

> « Lancer au démarrage » depuis le menu n'est actif que pour l'app empaquetée
> (voir « Construire l'app partageable » plus bas). En mode source, utilise
> `scripts/install-login-item.sh`.

## Lancer automatiquement à l'ouverture de session
```bash
scripts/install-login-item.sh     # installe + démarre l'app barre de menus (LaunchAgent)
scripts/uninstall-login-item.sh   # la retire du démarrage et l'arrête
```
Le LaunchAgent force un `PATH` incluant `/opt/homebrew/bin` (requis pour trouver
`macmon`). Logs : `/tmp/wptemps_overlay.log` et `/tmp/wptemps_overlay.err`.
`KeepAlive` est activé : l'overlay est relancé automatiquement s'il s'arrête
(utilise le script de désinstallation pour l'arrêter pour de bon).

## Configuration
Réglages dans `wptemps/config.py` : intervalle, position (`top-right`,
`top-left`, `bottom-left`, `bottom-right`), couleur, opacité, taille de police.
Si le texte est peu lisible sur un fond clair, augmenter le contraste
(`color=(0, 0, 0)` ou `opacity=230`).

## Construire l'app partageable (.app)
```bash
bash build.sh
```
Produit `dist/wptemps.app` : Python, PyObjC et `macmon` sont **embarqués** — le
destinataire n'installe rien. Cible **Apple Silicon**.

Partage : compresser `dist/wptemps.app` en `.zip` et l'envoyer (ou le déposer sur
GitHub Releases). L'app n'étant pas signée par un compte développeur Apple, le 1er
lancement se fait par **clic-droit → Ouvrir** (ensuite, double-clic normal). Une fois
ouverte, le menu 🌡 propose « Lancer au démarrage ».

Licences tierces : voir `THIRD_PARTY_NOTICES.md` (macmon, MIT).

## Tests
```bash
.venv/bin/pytest -q
```

## Phase 2 (à venir)
Support Windows (Asus) : lecture des températures via LibreHardwareMonitor
et application du wallpaper via l'API Windows.
