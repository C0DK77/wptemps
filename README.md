# wptemps — overlay des températures et infos matériel (macOS)

Petite app **barre de menus** qui affiche, en surimpression sur le bureau, les
températures CPU/GPU, la charge, la RAM, et (en option) la conso en watts, les
fréquences, le swap, l'uptime, le débit réseau et les infos machine — sans
jamais modifier ton fond d'écran. **Apple Silicon uniquement.**

## Installation (utilisateur)

**Option A — télécharger l'app** : récupère `wptemps-x.y.z.dmg` dans les
[Releases](../../releases), glisse `wptemps.app` dans Applications, puis
**clic-droit → Ouvrir** au 1er lancement (app non signée).

**Option B — Homebrew** :
```bash
brew tap C0DK77/tap
brew trust c0dk77/tap              # requis par Homebrew pour un tap tiers
brew install --cask wptemps        # ajouter --no-quarantine pour eviter le clic-droit
```

L'app vit dans la **barre de menus** (icône 🌡) — pas d'icône Dock ni de fenêtre.
Clique l'icône pour afficher/masquer, déplacer, choisir l'apparence et les infos.

> Tu veux distribuer cette app ? Voir [DISTRIBUTION.md](DISTRIBUTION.md).

## Prérequis (développement)
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
cœurs / RAM / disque), **Conso (watts)** (puissance CPU/GPU), **Détails CPU/GPU**
(% GPU + fréquences), **Swap**, **Uptime** et **Réseau ↓/↑** (débit), et de quitter. Tous ces
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
