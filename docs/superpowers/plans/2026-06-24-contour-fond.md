# Cases « Contour » et « Fond » du bloc — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter deux options indépendantes au menu 🌡 → Apparence — « Fond » (fond noir 25 % arrondi permanent) et « Contour » (trait de cadre noir 25 % 1px) — persistées et visibles même bloc verrouillé.

**Architecture:** L'apparence du calque de l'overlay devient fonction de `(locked, show_box, show_frame)` via une fonction pure `box_style(...)`. Les décorations transitent par une méthode dédiée `set_decorations(...)` du contrôleur (distincte de `set_config` qui ne gère que le texte). Deux booléens persistés dans `Settings`, deux entrées de menu cochables qui les basculent.

**Tech Stack:** Python, PyObjC (AppKit / Quartz / CALayer), pytest.

## Global Constraints

- Cible macOS Apple Silicon (inchangé). Aucune dépendance nouvelle (CALayer fait déjà partie de Quartz/AppKit).
- Le wallpaper n'est jamais modifié (garantie inchangée).
- Constantes fixes : fond `_UNLOCKED_BG_ALPHA = 0.25` (réutilisée), contour `border_width = 1.0`, `border_alpha = 0.25`, coins `6.0`.
- Défaut des nouveaux réglages : `False` (bloc nu, comportement identique à aujourd'hui).
- `config.py` reste inchangé : les décorations ne passent PAS par `Config`.
- Messages de commit terminés par : `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Persistance des réglages `show_box` / `show_frame`

**Files:**
- Modify: `wptemps/settings.py` (dataclass `Settings`, `_from_dict`, `_to_dict`)
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: rien (premier task).
- Produces: `Settings.show_box: bool = False`, `Settings.show_frame: bool = False`, persistés dans le JSON sous les clés `"show_box"` / `"show_frame"`.

- [ ] **Step 1: Write the failing test**

Ajouter dans `tests/test_settings.py` :

```python
def test_box_frame_roundtrip(tmp_path):
    from wptemps.settings import Settings, load, save
    p = tmp_path / "settings.json"
    save(Settings(show_box=True, show_frame=True), str(p))
    s = load(str(p))
    assert s.show_box is True
    assert s.show_frame is True


def test_box_frame_default_false_when_absent(tmp_path):
    import json
    from wptemps.settings import load
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"locked": True}))   # ancien fichier, sans les nouveaux champs
    s = load(str(p))
    assert s.show_box is False
    assert s.show_frame is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings.py::test_box_frame_roundtrip tests/test_settings.py::test_box_frame_default_false_when_absent -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'show_box'`.

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/settings.py`, ajouter les deux champs à la dataclass `Settings` (après `show_battery`) :

```python
    show_battery: bool = True
    show_box: bool = False
    show_frame: bool = False
```

Dans `_from_dict(...)`, ajouter au constructeur `Settings(...)` final :

```python
        show_box=bool(data.get("show_box", d.show_box)),
        show_frame=bool(data.get("show_frame", d.show_frame)),
```

Dans `_to_dict(s)`, ajouter au dict retourné :

```python
        "show_box": s.show_box, "show_frame": s.show_frame,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings.py -v`
Expected: PASS (tous les tests settings, anciens inclus).

- [ ] **Step 5: Commit**

```bash
git add wptemps/settings.py tests/test_settings.py
git commit -m "feat(settings): persiste show_box et show_frame

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Fonction pure `box_style` et application au calque

**Files:**
- Modify: `wptemps/overlay.py` (`lock_params`, nouvelle `box_style`, `OverlayController.__init__`, `set_locked`, nouvelles méthodes `set_decorations` / `_apply_box_style`)
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `Settings.show_box` / `Settings.show_frame` (Task 1, via les appelants).
- Produces:
  - `box_style(locked: bool, show_box: bool, show_frame: bool) -> dict` avec les clés
    `"bg_alpha": float`, `"border_alpha": float`, `"border_width": float`, `"corner_radius": float`.
  - `OverlayController.set_decorations(show_box: bool, show_frame: bool) -> None`.
  - `lock_params(...)` n'expose PLUS la clé `"bg_alpha"` (uniquement `level`/`ignores_mouse`/`draggable`).

- [ ] **Step 1: Write the failing test**

Dans `tests/test_overlay.py`, mettre à jour l'import et **remplacer** les deux tests `test_lock_params_locked` / `test_lock_params_unlocked` (qui asseyaient sur `bg_alpha`) par les versions sans `bg_alpha`, et ajouter les tests `box_style`.

Import en tête (ajouter `box_style`) :

```python
from wptemps.overlay import box_style, compute_origin, lock_params, place_top_left
```

Remplacer les deux tests existants par :

```python
def test_lock_params_locked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(True, desktop)
    assert p["level"] == desktop + 1
    assert p["ignores_mouse"] is True
    assert p["draggable"] is False
    assert "bg_alpha" not in p


def test_lock_params_unlocked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(False, desktop)
    assert p["level"] == AppKit.NSFloatingWindowLevel
    assert p["ignores_mouse"] is False
    assert p["draggable"] is True
    assert "bg_alpha" not in p
```

Ajouter les nouveaux tests :

```python
def test_box_style_locked_bare():
    s = box_style(locked=True, show_box=False, show_frame=False)
    assert s["bg_alpha"] == 0.0
    assert s["border_width"] == 0.0
    assert s["corner_radius"] == 0.0


def test_box_style_locked_box_only():
    s = box_style(locked=True, show_box=True, show_frame=False)
    assert s["bg_alpha"] == 0.25
    assert s["border_width"] == 0.0
    assert s["corner_radius"] == 6.0


def test_box_style_locked_frame_only():
    s = box_style(locked=True, show_box=False, show_frame=True)
    assert s["bg_alpha"] == 0.0
    assert s["border_width"] == 1.0
    assert s["border_alpha"] == 0.25
    assert s["corner_radius"] == 6.0


def test_box_style_unlocked_always_has_grab_fill():
    # en deplacement le fond reste a 25% quel que soit show_box (repere de saisie)
    off = box_style(locked=False, show_box=False, show_frame=False)
    on = box_style(locked=False, show_box=True, show_frame=False)
    assert off["bg_alpha"] == 0.25
    assert on["bg_alpha"] == 0.25
    assert off["corner_radius"] == 6.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_overlay.py -k "box_style or lock_params" -v`
Expected: FAIL — `ImportError: cannot import name 'box_style'`.

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/overlay.py` :

(a) Retirer `bg_alpha` de `lock_params` :

```python
def lock_params(locked, desktop_level):
    if locked:
        return {"level": desktop_level + 1, "ignores_mouse": True,
                "draggable": False}
    return {"level": AppKit.NSFloatingWindowLevel, "ignores_mouse": False,
            "draggable": True}
```

(b) Ajouter la fonction pure juste après `lock_params` :

```python
def box_style(locked, show_box, show_frame):
    """Apparence du calque selon l'etat verrouille et les decorations choisies.
    En deplacement, le fond reste a 25% (repere de saisie) quel que soit show_box."""
    fill = (not locked) or show_box
    bg_alpha = _UNLOCKED_BG_ALPHA if fill else 0.0
    border_width = 1.0 if show_frame else 0.0
    rounded = fill or show_frame
    return {
        "bg_alpha": bg_alpha,
        "border_alpha": _UNLOCKED_BG_ALPHA,
        "border_width": border_width,
        "corner_radius": 6.0 if rounded else 0.0,
    }
```

(c) Dans `OverlayController.initWithConfig_`, ajouter l'état avant `self._build_window()` :

```python
        self._show_box = False
        self._show_frame = False
```

(d) Ajouter les deux méthodes (par ex. juste après `set_locked`) :

```python
    def set_decorations(self, show_box, show_frame):
        self._show_box = bool(show_box)
        self._show_frame = bool(show_frame)
        self._apply_box_style()

    def _apply_box_style(self):
        s = box_style(self._locked, self._show_box, self._show_frame)
        layer = self.window.contentView().layer()
        layer.setBackgroundColor_(
            AppKit.NSColor.blackColor().colorWithAlphaComponent_(s["bg_alpha"]).CGColor())
        layer.setBorderColor_(
            AppKit.NSColor.blackColor().colorWithAlphaComponent_(s["border_alpha"]).CGColor())
        layer.setBorderWidth_(s["border_width"])
        layer.setCornerRadius_(s["corner_radius"])
```

(e) Remplacer la fin de `set_locked` (les lignes qui écrivaient `bg_alpha`/`cornerRadius`) par un appel à `_apply_box_style` :

```python
    def set_locked(self, locked):
        self._locked = bool(locked)
        p = lock_params(self._locked, self._desktop_level)
        self.window.setLevel_(p["level"])
        self.window.setIgnoresMouseEvents_(p["ignores_mouse"])
        self.window.setDraggable_(p["draggable"])
        self._apply_box_style()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_overlay.py -v`
Expected: PASS (tous les tests overlay).

- [ ] **Step 5: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat(overlay): box_style + set_decorations pour fond/contour

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Menu « Contour » / « Fond » et câblage

**Files:**
- Modify: `wptemps/app.py` (`MenuBarApp.setup`, `_build_status_item`, `_refresh_checks`, nouveaux handlers)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Settings.show_box` / `show_frame` (Task 1), `OverlayController.set_decorations(...)` (Task 2).
- Produces: deux entrées de menu cochables et leurs handlers `toggleBox_` / `toggleFrame_` ; appel de `set_decorations` au lancement.

- [ ] **Step 1: Write the failing test**

Regarder d'abord `tests/test_app.py` pour réutiliser ses fakes existants (l'`AppState` y est testé sans Cocoa via des doubles). Ajouter un test au niveau logique des handlers : un faux contrôleur enregistre les appels `set_decorations`, et on vérifie que basculer met à jour `settings`, appelle `set_decorations(show_box, show_frame)` et sauvegarde.

```python
def test_toggle_box_frame_updates_controller_and_saves():
    import wptemps.app as appmod
    from wptemps.settings import Settings

    saved = {}
    calls = []

    class FakeController:
        def set_decorations(self, show_box, show_frame):
            calls.append((show_box, show_frame))

    # MenuBarApp est une NSObject ; on teste la logique des handlers en
    # instanciant via alloc().init() et en injectant les attributs minimaux.
    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings()
    app.controller = FakeController()
    app._save_for_test = lambda s: saved.update({"show_box": s.show_box,
                                                 "show_frame": s.show_frame})

    # monkeypatch du save module-level et de _refresh_checks (UI Cocoa absente)
    import types
    appmod.save = lambda s: app._save_for_test(s)
    app._refresh_checks = types.MethodType(lambda self: None, app)

    app.toggleBox_(None)
    assert app.settings.show_box is True
    assert calls[-1] == (True, False)

    app.toggleFrame_(None)
    assert app.settings.show_frame is True
    assert calls[-1] == (True, True)
    assert saved == {"show_box": True, "show_frame": True}
```

> Si le pattern de `tests/test_app.py` diffère (p. ex. il teste `AppState` plutôt que `MenuBarApp` directement), aligne ce test sur le style déjà présent dans le fichier — l'essentiel à vérifier : `toggleBox_`/`toggleFrame_` mutent `settings`, appellent `controller.set_decorations(settings.show_box, settings.show_frame)`, et `save(settings)`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app.py::test_toggle_box_frame_updates_controller_and_saves -v`
Expected: FAIL — `AttributeError: 'MenuBarApp' object has no attribute 'toggleBox_'`.

- [ ] **Step 3: Write minimal implementation**

Dans `wptemps/app.py` :

(a) Dans `_build_status_item`, sous-menu **Apparence**, après l'ajout de `align_item` au menu (`apparence_menu.addItem_(align_item)`), ajouter les deux entrées cochables :

```python
        self.item_frame = _make_item(apparence_menu, self, "Contour", b"toggleFrame:")
        self.item_box = _make_item(apparence_menu, self, "Fond", b"toggleBox:")
```

(b) Dans `setup()`, juste après `self.controller.set_locked(self.settings.locked)`, appliquer les décorations rechargées :

```python
        self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)
```

(c) Ajouter les deux handlers (près des autres `toggle*_`) :

```python
    def toggleBox_(self, sender):
        self.settings.show_box = not self.settings.show_box
        self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)
        save(self.settings)
        self._refresh_checks()

    def toggleFrame_(self, sender):
        self.settings.show_frame = not self.settings.show_frame
        self.controller.set_decorations(self.settings.show_box, self.settings.show_frame)
        save(self.settings)
        self._refresh_checks()
```

(d) Dans `_refresh_checks`, ajouter la coche des deux items (sous une garde `hasattr`, comme les autres) :

```python
        if hasattr(self, "item_box"):
            self.item_box.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_box
                else AppKit.NSControlStateValueOff)
            self.item_frame.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_frame
                else AppKit.NSControlStateValueOff)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add wptemps/app.py tests/test_app.py
git commit -m "feat(app): menu Contour/Fond + application au lancement

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Vérification de bout en bout (suite complète)

**Files:**
- Aucun changement de code ; vérification finale.

**Interfaces:**
- Consumes: tout le travail précédent.
- Produces: confirmation que la suite passe.

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`
Expected: PASS (aucune régression ; nouveaux tests inclus).

- [ ] **Step 2: Vérification manuelle rapide (réelle, macOS)**

Lancer l'app (`python -m wptemps` ou la commande de lancement habituelle du projet) et vérifier :
- Apparence → cocher **Fond** : le bloc verrouillé affiche le fond noir 25 % arrondi.
- Apparence → cocher **Contour** : un trait de cadre fin apparaît ; les deux cumulés → bords un peu plus foncés (attendu).
- Décocher les deux → bloc nu comme avant. Déverrouiller : le repère de déplacement 25 % est inchangé.
- Quitter / relancer : l'état des cases est rechargé (persisté).

- [ ] **Step 3: Commit (si ajustements)**

Aucun commit si tout passe sans modification.
