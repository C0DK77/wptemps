# wptemps — Couleur du fond du bloc

**Date :** 2026-06-24
**Statut :** Validé (à relire)
**Suite de :** cases « Contour » et « Fond » (`2026-06-24-contour-fond-design.md`, livrée sur `main`).

## Objectif

Permettre de **choisir la couleur (et l'opacité) du Fond** du bloc overlay, au lieu du noir 25 %
fixe. Le choix se fait via le **sélecteur de couleur natif macOS** (le même que pour le texte),
est **persisté**, et s'applique au fond permanent quand la case **Fond** est cochée.

Par défaut : **noir à 25 %** (rendu identique à aujourd'hui). Cible : macOS Apple Silicon.

## Hors périmètre (YAGNI)

- Couleur du **Contour** : reste noir 25 % 1px (l'utilisateur n'a demandé que le fond).
- Couleur du **repère de déplacement** : reste noir 25 % (garantit qu'on voit toujours le bloc à
  déplacer, même si la couleur de fond choisie est très transparente).
- Dégradés, motifs, plusieurs fonds.

## Rappel de l'existant

- `Settings` porte déjà `show_box` / `show_frame` (booléens) et, pour le texte, `color` /
  `opacity`. L'app expose **un seul** `NSColorPanel` partagé (`app.py` `openColor_` /
  `changeColor_`, cible/action posées dans `setup()`).
- Le fond est appliqué par `overlay.py` : `box_style(locked, show_box, show_frame)` renvoie
  aujourd'hui un `bg_alpha` (0 ou 0.25) ; `_apply_box_style()` peint le calque en **noir** ×
  `bg_alpha`. Le contour est noir × `border_alpha` (0.25), largeur `border_width`.

## Approche

On rend la couleur du fond **paramétrable** et on **partage le panneau de couleur** via un drapeau
de cible.

### Sélecteur partagé (drapeau de cible)

`MenuBarApp` gagne `self._color_target` (str, défaut `"text"`). Deux entrées de menu :
- **« Couleur… »** (existante) → `openColor_` pose `_color_target = "text"`, pré-sélectionne la
  couleur du texte, ouvre le panneau (inchangé par ailleurs).
- **« Couleur du fond… »** (nouvelle) → `openBoxColor_` pose `_color_target = "box"`,
  pré-sélectionne `box_color`/`box_opacity`, ouvre le panneau.

Le callback unique `changeColor_` lit `_color_target` : `"text"` → écrit `color`/`opacity` et
ré-applique via le chemin texte (`_apply` / `set_config`) ; `"box"` → écrit `box_color`/
`box_opacity` et ré-applique via le chemin décoration (`set_decorations`).

### Rendu : mode de remplissage

`box_style(...)` ne renvoie plus `bg_alpha` mais un **`fill_mode`** :

| État | `fill_mode` |
|------|-------------|
| Déverrouillé (déplacement) | `"grab"` |
| Verrouillé + `show_box` | `"custom"` |
| Verrouillé + non `show_box` | `"none"` |

`_apply_box_style()` traduit le mode en couleur du calque :
- `"grab"` → noir × `_UNLOCKED_BG_ALPHA` (0.25) — repère de déplacement, inchangé ;
- `"custom"` → `box_color` × (`box_opacity` / 255) ;
- `"none"` → transparent (alpha 0).

Coins arrondis : `6.0` si `fill_mode != "none"` **ou** `show_frame`, sinon `0.0` (règle
inchangée). Contour : noir × 0.25, `border_width` 1px si `show_frame` (inchangé).

## Composants

### `settings.py` — champs ajoutés
`Settings` gagne `box_color: Tuple[int, int, int] = (0, 0, 0)` et `box_opacity: int = 64`.
`_from_dict` les lit avec défauts (tuple/int) ; `_to_dict` les persiste (`box_color` en liste).
Rétrocompat : ancien `settings.json` sans ces clés → noir 25 %.

### `overlay.py` — fond paramétrable
- `box_style(locked, show_box, show_frame)` renvoie un dict
  `{"fill_mode": str, "border_alpha": float, "border_width": float, "corner_radius": float}`
  (plus de clé `bg_alpha`). `fill_mode ∈ {"grab", "custom", "none"}`.
- `OverlayController` stocke `self._box_color = (0, 0, 0)` et `self._box_opacity = 64` (init avant
  `_build_window`/`set_locked`).
- `set_decorations(show_box, show_frame, box_color, box_opacity)` : stocke les quatre valeurs puis
  appelle `_apply_box_style()`.
- `_apply_box_style()` : calcule `box_style(...)`, choisit la couleur de fond selon `fill_mode`
  (`"grab"` → noir 0.25 ; `"custom"` → `_box_color` × `_box_opacity`/255 ; `"none"` → clear),
  applique fond + bordure + arrondi au calque.

### `app.py` — menu et callbacks
- `self._color_target = "text"` initialisé dans `setup()`.
- `_build_status_item` : ajoute **« Couleur du fond… »** (`b"openBoxColor:"`) dans le sous-menu
  **Apparence**, près de « Couleur… ».
- `openColor_` : pose `_color_target = "text"` (reste sinon identique).
- `openBoxColor_` : pose `_color_target = "box"`, pré-sélectionne le panneau avec `box_color`/
  `box_opacity` (sRGB + alpha), `orderFront_`.
- `changeColor_` : si `_color_target == "box"` → `box_color`/`box_opacity` depuis
  `color_to_fields(...)`, `controller.set_decorations(show_box, show_frame, box_color,
  box_opacity)`, `save` ; sinon comportement texte actuel.
- Les appels existants à `set_decorations` (handlers `toggleBox_`/`toggleFrame_` et `setup()`)
  passent désormais aussi `box_color`/`box_opacity`.

`config.py` reste **inchangé** (la couleur du fond ne passe pas par `Config`).

## Flux

« Couleur du fond… » → `_color_target = "box"` → panneau → `changeColor_` (branche box) →
maj `Settings.box_color`/`box_opacity` → `controller.set_decorations(show_box, show_frame,
box_color, box_opacity)` → re-style du calque → `save(settings)`.

## Gestion d'erreurs

- `settings.json` ancien (sans `box_color`/`box_opacity`) → défauts noir 25 %.
- Valeurs invalides → coercition (`tuple(...)`, `int(...)`) comme pour `color`/`opacity`.
- `_color_target` inattendu → traité comme `"text"` (défaut sûr).
- Aucune dépendance nouvelle.

## Tests

- `settings.py` : round-trip de `box_color`/`box_opacity` ; défauts `(0,0,0)`/`64` si absents.
- `overlay.py` : `box_style(...)` renvoie le bon `fill_mode` pour les 3 cas
  (déverrouillé → `"grab"` ; verrouillé+box → `"custom"` ; verrouillé sans box → `"none"`) ;
  `corner_radius` correct (6 si fill ou frame, sinon 0). Les tests existants asseyant sur
  `bg_alpha` migrent vers `fill_mode`.
- `app.py` : un test logique du routage couleur — avec `_color_target = "box"`, `changeColor_`
  écrit `box_color`/`box_opacity` et appelle `set_decorations(...)` avec ces valeurs (pas
  `set_config`) ; avec `"text"`, écrit `color`/`opacity`. Le câblage panneau/calque réel est
  vérifié en exécution (macOS).
