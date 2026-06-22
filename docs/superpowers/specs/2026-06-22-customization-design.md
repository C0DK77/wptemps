# wptemps — Personnalisation police / couleur / alignement

**Date :** 2026-06-22
**Statut :** Validé (à relire)
**Suite de :** app barre de menus (Phase A/B), déjà livrée sur `main`.

## Objectif

Permettre à l'utilisateur de personnaliser l'affichage des températures depuis le menu 🌡 :
- **police** (famille), **taille**, **gras / italique** — via le sélecteur de police macOS ;
- **couleur** (et opacité) — via le sélecteur de couleur macOS ;
- **alignement du texte** des lignes dans le bloc : gauche / centre / droite.

Tout est **persisté** (rechargé au lancement) et **appliqué en direct**. Cible : macOS Apple
Silicon (inchangé). Le wallpaper n'est jamais modifié (garantie inchangée).

## Hors périmètre (YAGNI)

- Listes de polices/couleurs prédéfinies (on utilise les panneaux natifs, choix complet).
- Réglage de la taille / position du bloc via ces nouveaux menus (la taille vient du panneau
  de police ; la position reste le glisser-déposer existant).
- Per-métrique styling (couleur différente par ligne), animations, thèmes.

## Approche

On réutilise les **panneaux natifs macOS** :
- `NSFontPanel` (via `NSFontManager`) pour police + taille + gras/italique ;
- `NSColorPanel` pour la couleur + opacité (alpha).

Le menu 🌡 ouvre ces panneaux ; les callbacks `changeFont:` / `changeColor:` mettent à jour les
réglages, ré-appliquent à l'overlay et sauvegardent. L'alignement est un sous-menu à 3 choix.

## Composants

### `settings.py` — champs ajoutés
`Settings` gagne : `font_name: str = "Menlo"`, `bold: bool = False`, `italic: bool = False`,
`align: str = "left"` (valeurs `left` | `center` | `right`). Les champs existants
(`font_size`, `opacity`, `color`, position, etc.) sont conservés. `load()` tolère l'absence des
nouveaux champs (valeurs par défaut) ; `align` inconnu est normalisé à `left`.

### `config.py` — champs ajoutés
`Config` gagne les mêmes champs de style : `font_name`, `bold`, `italic`, `align`. Le champ
`position` reste pour le coin par défaut au tout premier lancement ; **l'alignement du texte ne
dépend plus de `position`** mais de `align`.

### `overlay.py` — rendu paramétrable
- `_attributes()` construit la police depuis `cfg.font_name` + `cfg.font_size`, puis applique
  les traits gras/italique via `NSFontManager` (`convertFont:toHaveTrait:`) ; repli sur une
  police monospace système si la famille est introuvable.
- L'alignement du paragraphe vient de `cfg.align` (et non plus de `position`).
- Nouvelle méthode `set_config(cfg)` : remplace `self.cfg` et déclenche un re-rendu immédiat.

### `app.py` — menu et panneaux
Nouveaux éléments de menu (avant « Quitter ») :
- **« Police… »** → `NSFontManager` : préselectionne la police courante puis
  `orderFrontFontPanel:`. Callback `changeFont:` → lit la police convertie, en extrait famille
  / taille / gras / italique, met à jour `Settings`, ré-applique, sauvegarde.
- **« Couleur… »** → configure `NSColorPanel` (cible/action `changeColor:`, alpha activé),
  préselectionne la couleur courante, l'affiche. Callback `changeColor:` → lit la couleur
  (RGB + alpha → `color` + `opacity`), met à jour `Settings`, ré-applique, sauvegarde.
- **Sous-menu « Alignement »** : Gauche / Centre / Droite, coche l'actuel ; un clic met à jour
  `Settings.align`, ré-applique, sauvegarde.

Helper pur `apply_style(settings, controller, save_fn)` (ou équivalent) : reconstruit la config
via `config_from_settings`, appelle `controller.set_config(...)`, persiste — pour factoriser la
logique commune aux trois actions et la rendre testable.

## Flux

clic menu (police/couleur/alignement) → mise à jour `Settings` → `config_from_settings` →
`controller.set_config(cfg)` (re-rendu immédiat) → `save(settings)`.

## Gestion d'erreurs

- Police enregistrée introuvable au chargement → repli police monospace système, pas de crash.
- `align` invalide → `left`.
- `settings.json` ancien (sans les nouveaux champs) → valeurs par défaut.
- Panneaux indisponibles / callback inattendu → capturé, pas de crash (l'overlay garde son style
  courant).

## Point à valider d'abord (spike)

Brancher `changeFont:` / `changeColor:` sur une app **sans fenêtre** (barre de menus) : valider
que les callbacks arrivent bien via cible/action (`NSFontManager.setTarget:`/`setAction:`,
`NSColorPanel.setTarget:/setAction:`) et que l'app accessoire peut afficher les panneaux. Mini
test avant de construire le reste.

## Tests

- `settings.py` : round-trip des nouveaux champs ; défauts si absents ; `align` invalide → `left`.
- `config_from_settings` : mappe `font_name`/`bold`/`italic`/`align`.
- `overlay.py` : une fonction pure de normalisation d'alignement (`align` → constante
  `NSTextAlignment`) testée ; le reste (panneaux, traits de police) vérifié en exécution réelle.

## Dépendances

Aucune nouvelle dépendance : `NSFontManager`/`NSFontPanel`/`NSColorPanel` font partie d'AppKit
(déjà présent).
