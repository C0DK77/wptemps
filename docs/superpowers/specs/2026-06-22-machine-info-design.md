# wptemps — Infos machine + consommation (watts)

**Date :** 2026-06-22
**Statut :** Validé (à relire)
**Suite de :** app barre de menus personnalisable, déjà sur `main`.

## Objectif

Enrichir l'encadré avec :
1. un **en-tête machine statique** : OS, modèle, puce, cœurs CPU/GPU, RAM totale, disque
   (total / libre) ;
2. la **consommation en watts** (CPU / GPU) ajoutée aux lignes live.

Chaque bloc est activable/désactivable depuis le menu 🌡 et persisté. Cible : macOS Apple
Silicon, sans `sudo`. Le wallpaper n'est jamais modifié.

## Rendu cible

```
macOS 15.6.1
MacBook Air · Apple M3
CPU 8c (4P+4E) · GPU 8c · 16 Go
Disk 24/228 Go libres
────────────
CPU  56°C   3%   4.2W
GPU  48°C   0%   0.1W
RAM  11.1 / 16.0 Go
BAT  87%
```

L'en-tête machine (4 premières lignes) est masquable ; les watts sur CPU/GPU sont masquables.

## Hors périmètre (YAGNI)

- Rafraîchissement live du disque (lu une fois au démarrage ; l'espace libre bouge lentement).
- Fréquences CPU/GPU, ANE, swap, réseau (possible plus tard).
- Per-ligne styling.

## Composants

### `sysinfo.py` (nouveau) — infos machine, lues une fois
- `machine_info() -> MachineInfo` (dataclass), **mis en cache** (lecture unique) :
  `os_version` (str), `model_name` (str), `chip` (str), `cpu_cores` (int), `cpu_p` (int),
  `cpu_e` (int), `gpu_cores` (int), `ram_gb` (int|None), `disk_total_gb` (float|None),
  `disk_free_gb` (float|None). Tout champ indisponible → `None`/valeur vide.
- Sources :
  - OS : `sw_vers -productVersion`.
  - puce / cœurs P+E / GPU / RAM : `macmon pipe -s 1 --soc-info` → champ `soc`
    (`chip_name`, `pcpu_cores`, `ecpu_cores`, `gpu_cores`, `memory_gb`).
  - modèle lisible : `system_profiler SPHardwareDataType` → « Model Name » (repli : `mac_model`
    du `soc`, ex. `Mac15,12`).
  - disque : `shutil.disk_usage("/")`.
- Fonctions de parsing **pures** (sur des chaînes/dicts déjà obtenus) pour la testabilité ;
  les appels système sont isolés derrière des lecteurs injectables.

### `metrics` — watts
- `Metrics` gagne `cpu_power: float|None`, `gpu_power: float|None` (en watts).
- `metrics_from_macmon` lit `sample["cpu_power"]` / `sample["gpu_power"]` (déjà présents dans le
  JSON `macmon` qu'on échantillonne).

### Composition du texte
- Fonction **pure** `compose_text(machine, metrics, show_machine, show_power) -> str` :
  - si `show_machine` : lignes d'en-tête depuis `machine` (on omet les champs `None`) + un
    séparateur ;
  - lignes live via `format_lines(metrics)`, avec watts ajoutés aux lignes CPU/GPU si
    `show_power` et watts disponibles.
- `format_lines` est étendu pour accepter `show_power` (défaut `False` → comportement actuel
  inchangé) et ajouter `4.2W` aux lignes CPU/GPU quand demandé et disponible.
- L'overlay utilise `compose_text(...)` au lieu de `overlay_text(metrics)` seul.

### `settings.py` / `config.py`
- Nouveaux champs (Settings ET Config) : `show_machine_info: bool = True`,
  `show_power: bool = True`. Persistés ; absents d'un ancien fichier → défauts.
  `config_from_settings` les mappe (comme les autres champs de style).

### `overlay.py`
- `OverlayController` reçoit `MachineInfo` une fois (paramètre d'init, ex.
  `initWithConfig_machine_`) et le garde.
- `_update` compose via `compose_text(self._machine, read_metrics(), self.cfg.show_machine_info,
  self.cfg.show_power)`. `set_config(cfg)` (déjà présent) suffit donc à ré-appliquer un
  changement de toggle.

### `app.py` — menu
- Deux cases à cocher dans le menu 🌡 (cochées par défaut) : **« Infos machine »**
  (`toggleMachine:`) et **« Conso (watts) »** (`togglePower:`). Un clic bascule le réglage
  (`settings.show_machine_info` / `settings.show_power`), ré-applique via `apply_style`
  (`set_config` + `save`) et met à jour les coches.

## Flux

démarrage : `machine_info()` (cache) → l'overlay le garde. À chaque tick / changement de menu :
`compose_text(machine, read_metrics(), show_machine, show_power)` → mise à jour du label.

## Gestion d'erreurs

- `macmon --soc-info` indisponible → en-tête machine réduit aux champs obtenus (OS, disque) ou
  vide ; jamais de crash.
- `system_profiler` lent/échoue → repli sur `mac_model` brut.
- Champs `None` → lignes/segments omis.
- Watts absents → simplement non affichés.

## Tests

- `sysinfo` : parsing pur de `soc` (chip/cœurs/RAM), de la sortie `sw_vers`, du « Model Name » ;
  composition d'un `MachineInfo` à partir de lecteurs factices ; champs manquants → `None`.
- `metrics` : `metrics_from_macmon` extrait `cpu_power`/`gpu_power`.
- `format_lines(show_power=True)` ajoute les watts ; `show_power=False` inchangé.
- `compose_text` : en-tête on/off, watts on/off, omission des champs `None`.
- Le câblage menu/Cocoa : vérifié en exécution réelle.

## Dépendances

Aucune nouvelle (`shutil` stdlib ; `macmon`/`sw_vers`/`system_profiler` déjà là).
