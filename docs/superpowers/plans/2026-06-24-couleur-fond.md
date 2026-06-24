# Couleur du fond du bloc — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre de choisir la couleur et l'opacité du Fond du bloc overlay via le sélecteur de couleur natif macOS, persisté, défaut noir 25 %.

**Architecture:** `box_style(...)` renvoie un `fill_mode` (`grab`/`custom`/`none`) au lieu d'un `bg_alpha` fixe ; `_apply_box_style()` traduit le mode en couleur réelle (noir 25 % pour le repère de déplacement, `box_color`/`box_opacity` pour le fond verrouillé). Le `NSColorPanel` unique est partagé entre texte et fond via un drapeau `_color_target`. La couleur du fond transite par `set_decorations(...)` (chemin décoration), pas par `Config`.

**Tech Stack:** Python, PyObjC (AppKit / Quartz / CALayer / NSColorPanel), pytest.

## Global Constraints

- Test interpreter (le seul avec PyObjC) : `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest …`, exécuté depuis la racine `/Users/corentindesjars/code/wptemps`.
- Défauts = rendu actuel : `box_color = (0, 0, 0)`, `box_opacity = 64` (≈ 25 % de 255). Rétrocompat : ancien `settings.json` sans ces clés → noir 25 %.
- Contour et repère de déplacement restent **noir 25 %** (inchangés). Seul le fond verrouillé prend la couleur choisie.
- `config.py` reste **inchangé** : la couleur du fond ne passe pas par `Config`.
- Constante existante réutilisée : `_UNLOCKED_BG_ALPHA = 0.25` (overlay.py:20).
- Messages de commit terminés par : `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Persistance `box_color` / `box_opacity`

**Files:**
- Modify: `wptemps/settings.py` (dataclass `Settings`, `_from_dict`, `_to_dict`)
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: rien.
- Produces: `Settings.box_color: Tuple[int, int, int] = (0, 0, 0)`, `Settings.box_opacity: int = 64`, persistés sous les clés JSON `"box_color"` (liste) / `"box_opacity"` (int).

- [ ] **Step 1: Write the failing test**

Ajouter dans `tests/test_settings.py` :

```python
def test_box_color_opacity_roundtrip(tmp_path):
    from wptemps.settings import Settings, load, save
    p = tmp_path / "settings.json"
    save(Settings(box_color=(10, 20, 30), box_opacity=128), str(p))
    s = load(str(p))
    assert s.box_color == (10, 20, 30)
    assert s.box_opacity == 128


def test_box_color_defaults_when_absent(tmp_path):
    import json
    from wptemps.settings import load
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"locked": True}))   # ancien fichier
    s = load(str(p))
    assert s.box_color == (0, 0, 0)
    assert s.box_opacity == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_settings.py::test_box_color_opacity_roundtrip tests/test_settings.py::test_box_color_defaults_when_absent -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'box_color'`.

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/settings.py`, ajouter les deux champs à la dataclass `Settings` (après `show_frame`) :

```python
    show_frame: bool = False
    box_color: Tuple[int, int, int] = (0, 0, 0)
    box_opacity: int = 64
```

Dans `_from_dict(...)`, ajouter au constructeur `Settings(...)` final :

```python
        box_color=tuple(data.get("box_color", d.box_color)),
        box_opacity=int(data.get("box_opacity", d.box_opacity)),
```

Dans `_to_dict(s)`, ajouter au dict retourné :

```python
        "box_color": list(s.box_color), "box_opacity": s.box_opacity,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_settings.py -v`
Expected: PASS (anciens tests inclus).

- [ ] **Step 5: Commit**

```bash
git add wptemps/settings.py tests/test_settings.py
git commit -m "feat(settings): persiste box_color et box_opacity

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `box_style` → `fill_mode` et fond coloré dans l'overlay

**Files:**
- Modify: `wptemps/overlay.py` (`box_style`, `OverlayController.initWithConfig_`, `set_decorations`, `_apply_box_style`, nouveau `_fill_color`)
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: rien de Task 1 directement (les valeurs arrivent par paramètres de `set_decorations`).
- Produces:
  - `box_style(locked, show_box, show_frame) -> dict` avec clés `"fill_mode"` (str ∈ `{"grab","custom","none"}`), `"border_alpha"` (float), `"border_width"` (float), `"corner_radius"` (float). **Plus de clé `"bg_alpha"`.**
  - `OverlayController.set_decorations(show_box, show_frame, box_color=(0, 0, 0), box_opacity=64) -> None` (paramètres couleur **optionnels avec défauts** pour ne pas casser les appelants existants à 2 arguments).

- [ ] **Step 1: Write the failing test**

Dans `tests/test_overlay.py`, **remplacer** les 4 tests `box_style` existants (qui asseyent sur `bg_alpha`) par les versions ci-dessous, et ajouter le test de stockage couleur. Les deux tests `lock_params` (`assert "bg_alpha" not in p`) restent inchangés.

```python
def test_box_style_locked_bare():
    s = box_style(locked=True, show_box=False, show_frame=False)
    assert s["fill_mode"] == "none"
    assert s["border_width"] == 0.0
    assert s["corner_radius"] == 0.0


def test_box_style_locked_box_only():
    s = box_style(locked=True, show_box=True, show_frame=False)
    assert s["fill_mode"] == "custom"
    assert s["border_width"] == 0.0
    assert s["corner_radius"] == 6.0


def test_box_style_locked_frame_only():
    s = box_style(locked=True, show_box=False, show_frame=True)
    assert s["fill_mode"] == "none"
    assert s["border_width"] == 1.0
    assert s["border_alpha"] == 0.25
    assert s["corner_radius"] == 6.0


def test_box_style_unlocked_is_grab():
    off = box_style(locked=False, show_box=False, show_frame=False)
    on = box_style(locked=False, show_box=True, show_frame=False)
    assert off["fill_mode"] == "grab"
    assert on["fill_mode"] == "grab"
    assert off["corner_radius"] == 6.0


def test_set_decorations_stores_box_color():
    import AppKit
    import wptemps.overlay as ov
    from wptemps.config import Config
    AppKit.NSApplication.sharedApplication()
    c = ov.OverlayController.alloc().initWithConfig_(Config())
    c.set_decorations(True, False, (10, 20, 30), 128)
    assert c._box_color == (10, 20, 30)
    assert c._box_opacity == 128
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_overlay.py -k "box_style or set_decorations_stores" -v`
Expected: FAIL — assertions `fill_mode` échouent (`KeyError`/mismatch) et `_box_color` absent.

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/overlay.py` :

(a) Remplacer la fonction `box_style` (actuellement lignes ~130-142) par :

```python
def box_style(locked, show_box, show_frame):
    """Apparence du calque. fill_mode: 'grab' (repere de deplacement, noir 25%),
    'custom' (fond colore choisi, verrouille + show_box), 'none' (pas de fond)."""
    if not locked:
        fill_mode = "grab"
    elif show_box:
        fill_mode = "custom"
    else:
        fill_mode = "none"
    border_width = 1.0 if show_frame else 0.0
    rounded = fill_mode != "none" or show_frame
    return {
        "fill_mode": fill_mode,
        "border_alpha": _UNLOCKED_BG_ALPHA,
        "border_width": border_width,
        "corner_radius": 6.0 if rounded else 0.0,
    }
```

(b) Dans `initWithConfig_`, après `self._show_frame = False` (ligne ~228) et avant `self._build_window()` :

```python
        self._box_color = (0, 0, 0)
        self._box_opacity = 64
```

(c) Remplacer `set_decorations` (lignes ~316-319) par :

```python
    def set_decorations(self, show_box, show_frame, box_color=(0, 0, 0), box_opacity=64):
        self._show_box = bool(show_box)
        self._show_frame = bool(show_frame)
        self._box_color = tuple(box_color)
        self._box_opacity = int(box_opacity)
        self._apply_box_style()
```

(d) Remplacer `_apply_box_style` (lignes ~321-329) et ajouter `_fill_color` :

```python
    def _apply_box_style(self):
        s = box_style(self._locked, self._show_box, self._show_frame)
        layer = self.window.contentView().layer()
        layer.setBackgroundColor_(self._fill_color(s["fill_mode"]).CGColor())
        layer.setBorderColor_(
            AppKit.NSColor.blackColor().colorWithAlphaComponent_(s["border_alpha"]).CGColor())
        layer.setBorderWidth_(s["border_width"])
        layer.setCornerRadius_(s["corner_radius"])

    def _fill_color(self, fill_mode):
        if fill_mode == "grab":
            return AppKit.NSColor.blackColor().colorWithAlphaComponent_(_UNLOCKED_BG_ALPHA)
        if fill_mode == "custom":
            r, g, b = self._box_color
            return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
                r / 255.0, g / 255.0, b / 255.0, self._box_opacity / 255.0)
        return AppKit.NSColor.clearColor()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_overlay.py -v`
Expected: PASS (tous les tests overlay).

- [ ] **Step 5: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat(overlay): fond colore via fill_mode + box_color/box_opacity

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Menu « Couleur du fond… » et routage du panneau

**Files:**
- Modify: `wptemps/app.py` (`setup`, `_build_status_item`, `openColor_`, `changeColor_`, nouveaux `openBoxColor_` / `_apply_decorations`, mise à jour des appels `set_decorations`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Settings.box_color`/`box_opacity` (Task 1) ; `OverlayController.set_decorations(show_box, show_frame, box_color, box_opacity)` (Task 2).
- Produces: menu « Couleur du fond… » (`openBoxColor:`) ; `changeColor_` routé par `self._color_target` (`"text"`/`"box"`) ; helper `_apply_decorations()`.

- [ ] **Step 1: Write the failing test**

Le fichier `tests/test_app.py` teste surtout de la logique pure ; pour les handlers Cocoa on instancie `MenuBarApp.alloc().init()` et on injecte des doubles (même approche que le test `toggleBox_` déjà présent). Ajouter :

```python
def test_change_color_routes_to_box_target():
    import AppKit
    import wptemps.app as appmod
    from wptemps.settings import Settings

    AppKit.NSApplication.sharedApplication()
    calls = []

    class FakeController:
        def set_decorations(self, show_box, show_frame, box_color, box_opacity):
            calls.append((show_box, show_frame, box_color, box_opacity))
        def set_config(self, cfg):
            calls.append(("config", cfg))

    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings(show_box=True, show_frame=False)
    app.controller = FakeController()
    app._color_target = "box"

    # le panneau partage : on lui fixe une couleur connue, changeColor_ la relit
    cp = AppKit.NSColorPanel.sharedColorPanel()
    cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(1.0, 0.0, 0.0, 0.5))

    import types
    original_save = appmod.save
    appmod.save = lambda s: None
    app._refresh_checks = types.MethodType(lambda self: None, app)
    try:
        app.changeColor_(None)
    finally:
        appmod.save = original_save

    assert app.settings.box_color == (255, 0, 0)
    assert app.settings.box_opacity == 128          # round(0.5*255)
    # routé vers set_decorations avec la nouvelle couleur, pas set_config
    assert calls[-1] == (True, False, (255, 0, 0), 128)
    assert all(c[0] != "config" for c in calls)


def test_change_color_text_target_unchanged():
    import AppKit
    import wptemps.app as appmod
    from wptemps.settings import Settings

    AppKit.NSApplication.sharedApplication()
    applied = []

    class FakeController:
        def set_config(self, cfg):
            applied.append(cfg)
        def set_decorations(self, *a):
            applied.append(("deco", a))

    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings()
    app.controller = FakeController()
    app._color_target = "text"

    cp = AppKit.NSColorPanel.sharedColorPanel()
    cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.0, 1.0, 0.0, 1.0))

    import types
    original_save = appmod.save
    appmod.save = lambda s: None
    app._refresh_checks = types.MethodType(lambda self: None, app)
    try:
        app.changeColor_(None)
    finally:
        appmod.save = original_save

    assert app.settings.color == (0, 255, 0)
    assert app.settings.opacity == 255
    assert applied and not isinstance(applied[-1], tuple)   # set_config appelé (chemin texte)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_app.py::test_change_color_routes_to_box_target -v`
Expected: FAIL — `changeColor_` ne consulte pas `_color_target` (écrit `color`/`opacity`, n'appelle pas `set_decorations`).

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/app.py` :

(a) Dans `setup()`, là où le panneau couleur est configuré (après `cp.setShowsAlpha_(True)`), initialiser la cible :

```python
        self._color_target = "text"
```

(b) Dans `_build_status_item`, après la ligne `_make_item(apparence_menu, self, "Couleur…", b"openColor:")`, ajouter :

```python
        _make_item(apparence_menu, self, "Couleur du fond…", b"openBoxColor:")
```

(c) Ajouter le helper `_apply_decorations` (par ex. juste avant `toggleBox_`) :

```python
    def _apply_decorations(self):
        self.controller.set_decorations(
            self.settings.show_box, self.settings.show_frame,
            self.settings.box_color, self.settings.box_opacity)
```

(d) Remplacer le corps de `toggleBox_` et `toggleFrame_` pour passer par le helper :

```python
    def toggleBox_(self, sender):
        self.settings.show_box = not self.settings.show_box
        self._apply_decorations()
        save(self.settings)
        self._refresh_checks()

    def toggleFrame_(self, sender):
        self.settings.show_frame = not self.settings.show_frame
        self._apply_decorations()
        save(self.settings)
        self._refresh_checks()
```

(e) Dans `setup()`, remplacer l'appel existant
`self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)`
par :

```python
        self._apply_decorations()
```

(f) Au début de `openColor_`, poser la cible texte :

```python
    def openColor_(self, sender):
        self._color_target = "text"
        AppKit.NSApp.activateIgnoringOtherApps_(True)
```

(g) Ajouter `openBoxColor_` (après `changeColor_`) :

```python
    def openBoxColor_(self, sender):
        self._color_target = "box"
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        cp = AppKit.NSColorPanel.sharedColorPanel()
        r, g, b = self.settings.box_color
        cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.settings.box_opacity / 255.0))
        cp.orderFront_(self)
```

(h) Remplacer `changeColor_` pour router selon la cible :

```python
    def changeColor_(self, sender):
        f = color_to_fields(AppKit.NSColorPanel.sharedColorPanel().color())
        if getattr(self, "_color_target", "text") == "box":
            self.settings.box_color = f["color"]
            self.settings.box_opacity = f["opacity"]
            self._apply_decorations()
            save(self.settings)
            self._refresh_checks()
        else:
            self.settings.color = f["color"]
            self.settings.opacity = f["opacity"]
            self._apply()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest tests/test_app.py -v`
Expected: PASS (le test `toggleBox_` existant passe toujours — son `FakeController.set_decorations` doit accepter les 4 arguments ; s'il n'a que 2 paramètres, le mettre à jour avec `box_color`/`box_opacity` ou `*args`).

> Note : si le test existant `test_toggle_box_frame_updates_controller_and_saves` utilise un `FakeController.set_decorations(self, show_box, show_frame)`, élargir sa signature à `set_decorations(self, show_box, show_frame, box_color=None, box_opacity=None)` pour qu'il accepte le nouvel appel à 4 arguments, et ajuster son assertion si elle compare le tuple d'appel.

- [ ] **Step 5: Commit**

```bash
git add wptemps/app.py tests/test_app.py
git commit -m "feat(app): menu Couleur du fond + routage du panneau couleur

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Vérification de bout en bout

**Files:** aucun changement de code ; vérification finale.

**Interfaces:**
- Consumes: tout le travail précédent.
- Produces: confirmation que la suite passe + checklist manuelle.

- [ ] **Step 1: Run the full test suite**

Run: `/Users/corentindesjars/code/pc/.venv/bin/python -m pytest -q`
Expected: PASS (aucune régression ; nouveaux tests inclus).

- [ ] **Step 2: Vérification manuelle (macOS)**

Lancer l'app et vérifier :
- Apparence → cocher **Fond** : fond noir 25 % par défaut (inchangé).
- Apparence → **Couleur du fond…** : choisir une couleur (et bouger le curseur d'opacité) → le fond du bloc verrouillé prend la couleur/opacité choisies, en direct.
- **Couleur…** (texte) puis **Couleur du fond…** alternés : chacun modifie bien sa cible, sans interférence.
- Déverrouiller pour déplacer : le repère reste **noir 25 %** (la couleur de fond ne s'y applique pas).
- Quitter / relancer : la couleur de fond est rechargée (persistée).

- [ ] **Step 3: Commit (si ajustements)**

Aucun commit si tout passe sans modification.
