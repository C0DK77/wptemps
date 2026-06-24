# wptemps — Cases « Contour » et « Fond » du bloc

**Date :** 2026-06-24
**Statut :** Validé (à relire)
**Suite de :** personnalisation police/couleur (déjà livrée sur `main`).

## Objectif

Permettre à l'utilisateur d'**encadrer** le bloc overlay de façon permanente, via deux options
indépendantes du menu 🌡 → **Apparence** :

- **Fond** : le fond noir semi-transparent (25 %) à coins arrondis — exactement celui affiché
  aujourd'hui en mode déplacement — rendu **permanent** (visible même verrouillé).
- **Contour** : un trait de cadre autour du bloc — noir 25 %, 1px, coins arrondis 6px.

Les deux cases sont **indépendantes** (l'une, l'autre, les deux, ou aucune). L'apparence choisie
est **persistée** (rechargée au lancement) et reste **visible partout, y compris une fois le bloc
verrouillé** (état final). Cible : macOS Apple Silicon (inchangé).

## Hors périmètre (YAGNI)

- Choix de couleur / épaisseur / rayon du contour ou du fond (valeurs fixes, calées sur le repère
  de déplacement existant).
- Plusieurs blocs / styles par métrique (il n'y a qu'une seule fenêtre overlay).
- Ombre, dégradé, marges internes réglables.

## Rappel de l'existant

Le repère affiché quand on déplace le bloc avant verrouillage n'est **pas** une bordure : c'est un
**fond noir 25 % à coins arrondis 6px** posé sur le calque de `contentView` (`overlay.py`
`_UNLOCKED_BG_ALPHA = 0.25`, `lock_params(...)["bg_alpha"]`, `set_locked` lignes 291-300). En
verrouillé, `bg_alpha = 0.0` et `cornerRadius = 0.0` → bloc « nu ». Aucun trait de contour n'existe.

## Approche

On **dissocie** l'apparence du calque de l'état verrouillé. L'apparence devient fonction de trois
entrées : `locked`, `show_box`, `show_frame`. Une fonction pure `box_style(...)` calcule
fond / contour / arrondi ; le contrôleur l'applique au calque. Les décorations transitent par un
chemin dédié (`set_decorations`), distinct de `set_config` (qui ne gère que le texte) — séparation
nette « comment encadrer » vs « quoi afficher ».

### Règles d'apparence

| État | Fond | Contour | Coins |
|------|------|---------|-------|
| **Déplacement** (déverrouillé) | 25 % (toujours — repère de saisie) | 25 % 1px si `show_frame` | 6px |
| **Verrouillé / final** | 25 % si `show_box`, sinon 0 | 25 % 1px si `show_frame` | 6px si `show_box` OU `show_frame`, sinon 0 |

En déplacement, le fond reste toujours à 25 % pour garder le repère de saisie actuel inchangé, quel
que soit `show_box`. Le contour, lui, s'affiche dès que `show_frame` est coché, dans les deux états.

**Cumul assumé :** quand les deux cases sont cochées, le contour 25 % se superpose au fond 25 % et
paraît légèrement plus foncé aux bords. Validé tel quel par l'utilisateur.

## Composants

### `settings.py` — champs ajoutés
`Settings` gagne `show_box: bool = False` et `show_frame: bool = False`. `load()`/`_from_dict`
tolèrent leur absence (défaut `False`) ; `save()`/`_to_dict` les persistent. Les champs existants
sont conservés.

### `overlay.py` — apparence paramétrable
- Nouvelle fonction pure `box_style(locked, show_box, show_frame)` → dict
  `{"bg_alpha": float, "border_alpha": float, "border_width": float, "corner_radius": float}`,
  suivant les règles ci-dessus (constante `_UNLOCKED_BG_ALPHA = 0.25` réutilisée ; contour
  `border_width = 1.0`, `border_alpha = 0.25`).
- `lock_params(...)` **n'expose plus `bg_alpha`** ; il ne garde que `level` / `ignores_mouse` /
  `draggable`. L'apparence du calque sort de `lock_params` vers `box_style`.
- État ajouté dans `OverlayController.__init__` : `self._show_box = False`,
  `self._show_frame = False`.
- Nouvelle méthode `set_decorations(show_box, show_frame)` : stocke les deux drapeaux puis appelle
  `_apply_box_style()`.
- Nouvelle méthode privée `_apply_box_style()` : lit `self._locked`, `self._show_box`,
  `self._show_frame`, calcule via `box_style(...)`, applique au calque
  `contentView().layer()` : `setBackgroundColor_` (noir × `bg_alpha`), `setBorderColor_`
  (noir × `border_alpha`), `setBorderWidth_`, `setCornerRadius_`.
- `set_locked(...)` appelle `_apply_box_style()` pour la partie calque (au lieu d'écrire
  directement `bg_alpha`/`cornerRadius`).

### `app.py` — menu et bascules
- Deux entrées **cochables** ajoutées dans le sous-menu **Apparence** (après Alignement) :
  **« Contour »** → `toggleFrame:`, **« Fond »** → `toggleBox:`. Références gardées
  (`self.item_frame`, `self.item_box`).
- Handlers `toggleFrame_` / `toggleBox_` : inversent `Settings.show_frame` / `show_box`, appellent
  `self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)`,
  `save(self.settings)`, puis `_refresh_checks()`.
- `setup()` : après `set_locked(...)`, appelle
  `self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)` pour appliquer
  l'état rechargé au lancement.
- `_refresh_checks()` : coche `item_frame` / `item_box` selon `settings.show_frame` / `show_box`.

`config.py` est **inchangé** (les décorations ne passent pas par `Config`).

## Flux

clic « Contour »/« Fond » → mise à jour `Settings.show_frame`/`show_box` →
`controller.set_decorations(...)` → `_apply_box_style()` (re-style immédiat du calque) →
`save(settings)`. Au lancement : `load()` → `set_locked(...)` → `set_decorations(...)`.

## Gestion d'erreurs

- `settings.json` ancien (sans `show_box`/`show_frame`) → défauts `False`, bloc nu comme avant.
- Valeurs non booléennes → `bool(...)` à la lecture.
- Aucune dépendance nouvelle (`CALayer.borderColor`/`borderWidth`/`cornerRadius` font partie de
  Quartz/AppKit déjà présents).

## Tests

- `settings.py` : round-trip de `show_box`/`show_frame` ; défaut `False` si absents.
- `overlay.py` : `box_style(...)` testée pure pour les 4 combinaisons clés —
  - verrouillé + rien → `bg_alpha == 0`, `border_width == 0`, `corner_radius == 0` ;
  - verrouillé + fond → `bg_alpha == 0.25`, `corner_radius == 6` ;
  - verrouillé + contour → `border_width == 1`, `border_alpha == 0.25`, `corner_radius == 6` ;
  - déverrouillé → `bg_alpha == 0.25` quel que soit `show_box`.
- `lock_params(...)` : les assertions `bg_alpha` des tests existants
  (`test_lock_params_locked`/`_unlocked`) **migrent** vers les tests `box_style` ; `lock_params`
  ne vérifie plus que `level`/`ignores_mouse`/`draggable`.
- Le câblage menu/calque (cocher, application réelle au calque) est vérifié en exécution réelle.
