# Wallpaper Temps — Design

**Date :** 2026-06-22
**Statut :** Validé (à relire)

## Objectif

Afficher en quasi-temps réel les mesures matérielles du PC (températures, charge, etc.)
**incrustées dans le fond d'écran** de l'utilisateur. Multi-plateforme : **macOS d'abord
(MacBook Air M3, Apple Silicon)**, puis **Windows (Asus)** en phase 2.

Le texte doit **se fondre** dans le wallpaper existant (pas de gros panneau encadré) — visuel
volontairement minimal pour cette première version.

## Approche retenue

**Image de fond régénérée** (et non un widget overlay natif). Un seul programme Python :

1. lit les mesures (~toutes les 5 s) ;
2. dessine une image = wallpaper d'origine + texte incrusté ;
3. définit cette image comme fond d'écran ;
4. recommence.

**Pourquoi :** le cœur (boucle, rendu, mise en page) est **commun à tous les OS**. Seuls deux
petits modules sont spécifiques à l'OS, derrière une interface claire. Un widget overlay natif
donnerait un rendu plus fluide mais exigerait du code natif distinct par OS (fenêtre niveau
bureau sur macOS, parentage `WorkerW` sur Windows) — beaucoup plus d'effort et de fragilité
pour un gain marginal sur des températures qui évoluent lentement.

**Compromis accepté :** rafraîchissement toutes les ~5 s (pas chaque seconde) ; léger flicker
possible sur certains systèmes au changement de wallpaper.

## Résultat de la validation capteurs M3 (réalisée le 2026-06-22)

Risque principal du projet = lire les températures sur Apple Silicon. **Validé sur la machine
cible.** L'outil **`macmon`** (`brew install macmon`) fournit, via `macmon pipe`, un JSON
**sans `sudo`** contenant tout le nécessaire. Mesures réelles relevées :

- `temp.cpu_temp_avg` → **55,4 °C**
- `temp.gpu_temp_avg` → **48,5 °C**
- `cpu_usage_pct` → charge CPU
- `memory.ram_usage` / `memory.ram_total` → RAM (11,2 / 17,2 Go)
- bonus : `cpu_power`, `gpu_power`, `ane_power` (Watts)

La **batterie** vient de `pmset -g batt` (ou `psutil`). Le **ventilateur** est absent sur le
Air M3 → champ `N/A`.

## Architecture & composants

```
main.py            # boucle, config, gestion d'erreurs, arrêt propre
config.py          # intervalle, position/alignement du texte, couleur, taille
metrics/
  __init__.py      # read_metrics() -> Metrics (sélectionne l'impl selon l'OS)
  base.py          # dataclass Metrics + valeurs N/A
  macos.py         # appelle `macmon pipe` (1 échantillon) + pmset ; parse JSON
  windows.py       # phase 2 (LibreHardwareMonitor + batterie)
render.py          # Metrics + wallpaper de base -> image finale (Pillow)
wallpaper.py       # get_current() / set(path) ; macOS via osascript, Windows phase 2
```

### Interface commune des mesures

`metrics.read_metrics()` renvoie une dataclass `Metrics` **normalisée**, identique sur tous
les OS :

```
Metrics(
  cpu_temp: float | None,   # °C
  gpu_temp: float | None,
  cpu_load: float | None,   # %
  ram_used: float | None,   # Go
  ram_total: float | None,
  battery_pct: float | None,
  fan_rpm: float | None,
)
```

Toute valeur indisponible = `None` → affichée `N/A`. Aucune mesure manquante ne fait planter
le programme.

### Rendu (`render.py`)

- Charge le **wallpaper d'origine** (capturé une fois au démarrage, jamais écrasé).
- Écrit les lignes de texte (police système, taille/couleur configurables) à une position
  configurable (coin par défaut).
- Pour « se fondre » : texte semi-transparent + fine ombre portée pour rester lisible sur fond
  clair comme sombre. Réglages basiques pour l'instant, on raffinera plus tard.
- Écrit l'image dans un fichier temporaire dédié (jamais le fichier wallpaper original).

### Application du fond d'écran (`wallpaper.py`)

- **macOS :** `osascript` (System Events) pour lire le wallpaper courant et le redéfinir.
- **Windows (phase 2) :** `SystemParametersInfoW (SPI_SETDESKWALLPAPER)`.

## Gestion d'erreurs & robustesse

- Capteur indisponible → `N/A`, jamais de crash.
- Wallpaper d'origine sauvegardé en mémoire au démarrage ; on n'écrase jamais le fichier source.
- Si `macmon` est absent → message clair invitant à `brew install macmon`.
- Arrêt propre (Ctrl-C) : on **restaure** le wallpaper d'origine.
- Boucle tolérante : une erreur ponctuelle est journalisée et la boucle continue.

## Phasage

- **Phase 1 — Mac (M3) :** squelette complet + `metrics/macos.py` + `render.py` +
  `wallpaper.py` macOS + boucle. Résultat fonctionnel sur le MacBook.
- **Phase 2 — Windows (Asus) :** `metrics/windows.py` (températures via LibreHardwareMonitor)
  + `wallpaper.py` Windows. Le reste est déjà commun.

## Dépendances

- `macmon` (Homebrew) — capteurs Apple Silicon, sans sudo. *(validé)*
- Python : `Pillow` (rendu image). `psutil` optionnel (batterie/charge de secours).
- Phase 2 Windows : LibreHardwareMonitor.

## Hors périmètre (YAGNI pour l'instant)

- Widget overlay natif / animations.
- Thèmes graphiques élaborés, graphiques historiques.
- Configuration GUI (config par fichier suffit).
- Linux.
