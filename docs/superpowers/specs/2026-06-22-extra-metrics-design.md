# wptemps — Mesures supplémentaires (détails CPU/GPU, swap, uptime, réseau)

**Date :** 2026-06-22
**Statut :** Validé (à relire)
**Suite de :** overlay infos machine + watts, déjà sur `main`.

## Objectif

Ajouter quatre groupes d'infos, chacun activable indépendamment depuis le menu 🌡 (tous
**désactivés par défaut** pour ne pas alourdir l'encadré tant qu'on n'active rien) :
1. **Détails CPU/GPU** : % d'utilisation GPU + fréquences CPU (P) et GPU.
2. **Swap** : mémoire d'échange utilisée / totale.
3. **Uptime** : depuis combien de temps le Mac est allumé.
4. **Réseau ↓/↑** : débit descendant / montant en temps réel.

Cible macOS Apple Silicon, sans `sudo`. Le wallpaper n'est jamais modifié.

## Rendu cible (tout activé)

```
macOS 15.6.1
MacBook Air · Apple M3
CPU 8c (4P+4E) · GPU 8c · 16 GB
Disk 24/228 GB free
────────────
CPU  54°C   8%   2.7W   3.4GHz
GPU  46°C   1%   0.1W   416MHz
RAM  9.4 / 16.0 GB
SWAP 0.7 / 2.0 GB
BAT  39%
UP   10d 2h
NET  ↓1.2 ↑0.3 MB/s
```

## Hors périmètre (YAGNI)

- Fréquence E-cluster séparée (on montre la P-cluster), historique/graphes, par-interface réseau.
- Débit disque, GPU RAM power, etc.

## Composants

### `metrics` — champs ajoutés (depuis macmon)
`Metrics` gagne : `gpu_load` (%), `cpu_freq_mhz`, `gpu_freq_mhz`, `swap_used_gb`,
`swap_total_gb`, `net_down_kbps`, `net_up_kbps`, `uptime_seconds` (tous `Optional`).
`metrics_from_macmon` remplit, depuis l'échantillon déjà lu :
- `gpu_load` = `gpu_usage[1] * 100`, `gpu_freq_mhz` = `gpu_usage[0]` ;
- `cpu_freq_mhz` = `pcpu_usage[0]` (cluster performance) ;
- `swap_used_gb`/`swap_total_gb` = `memory.swap_usage`/`swap_total` en Go.
(`net_*` et `uptime_seconds` ne viennent PAS de macmon — voir `extras.py`.)

### `extras.py` (nouveau) — uptime + débit réseau
- **Uptime** : `parse_boottime(s) -> Optional[int]` (parse `kern.boottime` → epoch secondes,
  pur) ; `uptime_seconds(boottime_reader=_read_boottime, now=time.time) -> Optional[float]`.
- **Réseau** :
  - `parse_net_counters(netstat_output) -> (in_bytes, out_bytes)` — somme des interfaces
    physiques (hors `lo`), pur.
  - `NetRateMeter` (objet **à état**) : `sample(in_bytes, out_bytes, now) -> (down_kbps,
    up_kbps)`. 1er appel → `(0.0, 0.0)` (pas de delta) ; ensuite débit = Δoctets / Δtemps / 1024.
    Pur (octets + temps injectés) ; l'état (compteurs précédents) est gardé par l'instance.
  - Lecteur réel `read_net_counters()` via `netstat -ib`.
- `apply_extras(m, net_meter, net_reader=read_net_counters, uptime_fn=uptime_seconds,
  now=time.time)` : remplit `m.net_down_kbps`/`net_up_kbps` (via `net_meter`) et
  `m.uptime_seconds`. Tolérant : toute erreur → champ laissé `None`.

### Formatage — fonctions pures (dans `metrics/base.py`)
- `format_lines(m, show_power=False, show_details=False)` :
  - `show_details` ajoute la fréquence CPU à la ligne CPU (`3.4GHz`), et `% GPU` + fréquence GPU
    à la ligne GPU (`1%  416MHz`).
- Helpers purs : `_freq(mhz)` (MHz→`416MHz` ou `3.4GHz` si ≥1000), `format_uptime(seconds)`
  (`10d 2h` / `2h 7m` / `5m`), `format_net(down_kbps, up_kbps)` (`↓1.2 ↑0.3 MB/s`, auto KB/MB),
  `format_swap(used_gb, total_gb)`.

### Composition — `compose_text(machine, metrics, cfg)`
On change la signature de `compose_text(machine, metrics, show_machine, show_power)` en
**`compose_text(machine, metrics, cfg)`** (lit `cfg.show_machine_info`, `show_power`,
`show_details`, `show_swap`, `show_uptime`, `show_net`). Il :
1. ajoute l'en-tête machine + séparateur si `show_machine_info` ;
2. `format_lines(metrics, show_power, show_details)` ;
3. insère une ligne `SWAP …` après RAM si `show_swap` et swap dispo ;
4. ajoute `UP …` si `show_uptime` et uptime dispo ;
5. ajoute `NET ↓…↑…` si `show_net` et débit dispo.
Tout champ `None` → ligne/segment omis.

### `settings.py` / `config.py`
Nouveaux champs (Settings ET Config), **défaut `False`** : `show_details`, `show_swap`,
`show_uptime`, `show_net`. Persistés ; absents d'un ancien fichier → `False`.
`config_from_settings` les mappe.

### `overlay.py`
- `OverlayController` détient un `NetRateMeter` (créé à l'init).
- `_update` : `m = read_metrics()` ; `apply_extras(m, self._net_meter)` ;
  `compose_text(self._machine, m, self.cfg)`.

### `app.py` — menu
4 cases à cocher (décochées par défaut) : **Détails CPU/GPU** (`toggleDetails:`), **Swap**
(`toggleSwap:`), **Uptime** (`toggleUptime:`), **Réseau** (`toggleNet:`). Chacune bascule son
réglage, ré-applique via `apply_style`, persiste, et reflète sa coche.

## Flux

à chaque tick : `read_metrics()` (macmon+pmset, + gpu/freq/swap) → `apply_extras` (réseau via
`NetRateMeter` à état + uptime) → `compose_text(machine, m, cfg)` → label. `machine_info()`
toujours lu une seule fois au démarrage.

## Gestion d'erreurs

- macmon sans `gpu_usage`/`pcpu_usage`/`swap` → champs `None`, segments omis.
- `netstat`/`kern.boottime` échouent → `net_*`/`uptime` `None`, lignes omises, pas de crash.
- 1er tick réseau → débit `(0,0)` (affiché `↓0.0 ↑0.0` si `show_net`).
- Anciens `settings.json` → nouveaux toggles `False`.

## Tests

- `metrics_from_macmon` : extrait `gpu_load`/`cpu_freq_mhz`/`gpu_freq_mhz`/swap.
- `extras` : `parse_boottime`, `parse_net_counters`, `NetRateMeter.sample` (1er appel = 0 ;
  delta correct ; Δtemps ≤ 0 → 0), `uptime_seconds` avec lecteurs factices ; `apply_extras`
  tolérant (lecteur qui lève → champs `None`).
- formats : `_freq`, `format_uptime`, `format_net`, `format_swap`.
- `format_lines(show_details=True)` : ajoute freq/usage GPU.
- `compose_text` : chaque toggle on/off ; omission des champs `None`.
- Settings/Config : round-trip + défauts `False` ; `config_from_settings`.
- Le câblage Cocoa (4 toggles) : exécution réelle.

## Dépendances

Aucune nouvelle (`netstat`/`sysctl` système ; macmon déjà là).
