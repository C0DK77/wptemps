# wptemps — App barre de menus + overlay déplaçable + paquet .app

**Date :** 2026-06-22
**Statut :** Validé (à relire)
**Suite de :** Phase 1 (overlay macOS), déjà livrée sur `main`.

## Objectif

Transformer le script overlay en une **petite app macOS** :

1. pilotée par une **icône dans la barre de menus** (`NSStatusItem`) ;
2. dont l'affichage des températures se **déplace à la souris** (verrouiller/déverrouiller),
   avec **position mémorisée** entre les lancements ;
3. **empaquetable en `.app` partageable** (Python + PyObjC + `macmon` embarqués), pour la
   donner à d'autres sans qu'ils installent quoi que ce soit.

Cible : **macOS Apple Silicon** (M1/M2/M3/M4). Intel non supporté (`macmon` ne lit pas les
capteurs sur Intel).

## Hors périmètre (YAGNI)

- Signature/notarisation Apple officielle (compte développeur payant). L'app non signée
  s'ouvre via clic-droit → *Ouvrir* au 1er lancement.
- Support Intel et Windows (Phase 2 Windows = plan séparé ultérieur).
- Personnalisation avancée (thèmes, choix des métriques) au-delà des réglages existants.
- Réglages couleur/taille depuis le menu (peut venir plus tard).

## Approche & réutilisation

Le cœur métier ne change pas et est réutilisé tel quel :
- `wptemps.metrics.read_metrics()` (macmon + pmset),
- `wptemps.metrics.base.format_lines()`,
- `wptemps.config.Config` (étendu).

Ce qui évolue / est nouveau :
- `wptemps/overlay.py` (évolue) : la fenêtre devient **déplaçable** (état verrouillé/déverrouillé).
- `wptemps/app.py` (nouveau) : l'app — icône barre de menus, menu, cycle de vie, possède le
  contrôleur d'overlay. **Nouveau point d'entrée** (`python -m wptemps.app`).
- `wptemps/settings.py` (nouveau) : persistance JSON des réglages et de la position.

## Composants

### `settings.py` — persistance
- Emplacement : `~/Library/Application Support/wptemps/settings.json`.
- Contenu : `{"x": float|null, "y": float|null, "locked": bool, "show": bool,
  "font_size": int, "opacity": int, "color": [r,g,b]}`.
  `x`/`y` = origine (coords Cocoa, bas-gauche) de la fenêtre ; `null` = pas encore déplacé
  → on retombe sur le coin par défaut (`top-right`, marge config).
- Interface :
  - `load() -> Settings` (dataclass) — si fichier absent/corrompu → valeurs par défaut, sans crash.
  - `save(s: Settings) -> None` — crée le dossier si besoin, écrit le JSON.
- Pur et testable (round-trip, défauts sur fichier corrompu, création du dossier).

### `overlay.py` — fenêtre déplaçable
- `OverlayController` gère la fenêtre, la vue texte, le timer (déjà existant), **plus** :
  - `set_locked(locked: bool)` :
    - **verrouillé** : `setLevel_(bureau+1)`, `setIgnoresMouseEvents_(True)`, pas de cadre →
      discret, clic-traversant, derrière icônes/fenêtres (comportement actuel).
    - **déverrouillé** : `setLevel_(NSFloatingWindowLevel)`, `setIgnoresMouseEvents_(False)`,
      léger fond/cadre semi-transparent visible → saisissable au premier plan.
  - La fenêtre est une sous-classe `DraggableWindow(NSWindow)` qui implémente
    `mouseDown:`/`mouseDragged:` pour se déplacer quand déverrouillée, et `mouseUp:` →
    appelle un callback `on_moved(x, y)` pour persister la position.
  - `apply_position(x, y)` : si `x/y` non nuls, place la fenêtre à cette origine (clampée à
    l'écran) ; sinon coin par défaut via `compute_origin` (déjà existant).
- Le rendu du texte (police, couleur, opacité, ombre) reste comme aujourd'hui.

### `app.py` — barre de menus
- `NSApplication` en `Accessory` (pas d'icône Dock).
- `NSStatusItem` avec icône SF Symbol `thermometer` (fallback texte « 🌡 »).
- Menu :
  - « Afficher les températures » (case à cocher, lié à `show`),
  - « Déverrouiller pour déplacer » ↔ « Verrouiller la position » (bascule `locked`),
  - « Lancer au démarrage » (case à cocher),
  - séparateur,
  - « Quitter ».
- Possède le `OverlayController`. Au démarrage : charge `settings`, applique position +
  show + locked. Tout changement via le menu met à jour `settings` et appelle `save()`.

### Lancer au démarrage
- Via **`SMAppService.mainAppService`** (ServiceManagement, macOS 13+) : `register()` /
  `unregister()` pour l'app empaquetée. État reflété par la case à cocher du menu.
- Si l'API échoue (ex. lancé depuis les sources, non empaqueté) : la case est désactivée et
  un message indique que l'option n'est disponible que pour le `.app`. Les anciens scripts
  `scripts/install-login-item.sh` restent utilisables pour le mode source.

### Empaquetage `.app` (Phase B)
- **py2app**. `Info.plist` : `LSUIElement = 1` (pas d'icône Dock), nom `wptemps`.
- Le binaire **`macmon`** est copié dans `Contents/Resources/` de l'app (`resources` py2app).
  Licence MIT de macmon respectée : inclure sa licence/attribution dans le bundle.
- `metrics/macos.py` évolue : `_macmon_path()` retourne le `macmon` **embarqué** si présent
  (résolu via le chemin du bundle), sinon `"macmon"` (PATH système, mode source).
- `build.sh` : (re)génère `dist/wptemps.app`.

## Flux de données

timer (toutes les `interval_sec`) → `read_metrics()` (via macmon embarqué ou système) →
`format_lines()` → mise à jour du label. Drag (déverrouillé) → déplacement fenêtre →
`mouseUp` → `on_moved` → `settings.save()`.

## Gestion d'erreurs

- `settings.json` absent/corrompu → défauts, pas de crash.
- `macmon` introuvable/illisible → métriques `N/A` (déjà géré dans `read_metrics`).
- Position sauvegardée hors écran (changement de moniteur) → clampée dans l'écran courant.
- `SMAppService` indisponible → option « Lancer au démarrage » désactivée proprement.

## Phasage

- **Phase A — app fonctionnelle depuis les sources** : `settings.py`, `overlay.py` déplaçable,
  `app.py` (barre de menus + menu + drag + persistance + lancement au démarrage). Utilisable
  via `python -m wptemps.app`. **Livrable testable autonome.**
- **Phase B — empaquetage `.app`** : validation préalable d'un build py2app minimal (spike),
  puis `macmon` embarqué + `_macmon_path()` + `build.sh` + attribution licence macmon.
  **Livrable : `wptemps.app` partageable.**

Chaque phase aura son propre plan d'implémentation.

## Tests

- `settings.py` : round-trip charge/sauve, défauts sur JSON corrompu, création du dossier.
- `metrics/macos.py` : `_macmon_path()` renvoie le chemin embarqué quand le fichier existe,
  sinon `"macmon"`.
- `overlay.py` : `apply_position` clampe une position hors écran ; `compute_origin` (déjà testé).
- Le câblage Cocoa (menu, NSStatusItem, drag réel) : vérifié par exécution réelle + Quartz,
  pas de test unitaire UI.

## Dépendances

- Existant : `pyobjc-framework-Cocoa`, `pyobjc-framework-Quartz`, `pytest`.
- Phase A : `pyobjc-framework-ServiceManagement` (pour `SMAppService`). En mode source
  l'option « Lancer au démarrage » reste désactivée ; elle ne prend effet que pour le `.app`
  (Phase B). Le mode source garde les scripts `scripts/(un)install-login-item.sh`.
- Phase B : `py2app` (outil de build), binaire `macmon` (déjà installé via brew, à copier
  dans le bundle, attribution licence MIT incluse).
