# wptemps Phase A — App barre de menus + overlay déplaçable (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire de wptemps une app pilotée par une icône de barre de menus, avec un overlay de températures déplaçable à la souris et dont la position est mémorisée.

**Architecture :** Réutilise le cœur existant (`metrics`, `format_lines`, `Config`). `overlay.py` évolue : la fenêtre devient une sous-classe déplaçable et la position est découplée du re-rendu (plus de « snap » au coin). Deux nouveaux modules : `settings.py` (persistance JSON) et `app.py` (barre de menus). Toute la logique non-Cocoa est isolée dans des fonctions/classes pures et testées ; le câblage Cocoa est vérifié par exécution réelle.

**Tech Stack :** Python 3.9, PyObjC (Cocoa + Quartz), pytest. macmon + pmset déjà en place.

## Global Constraints

- Cible **macOS Apple Silicon** uniquement.
- **Aucun `sudo`** (capteurs via macmon, déjà en place).
- Réglages/position persistés dans `~/Library/Application Support/wptemps/settings.json`.
- Fichier de settings absent/corrompu → **valeurs par défaut, jamais de crash**.
- Position sauvegardée hors écran → **clampée** dans l'écran courant.
- En mode source (non empaqueté), l'option « Lancer au démarrage » est **désactivée** (réservée au `.app`, Phase B).
- Le package reste `wptemps/` à la racine ; tests dans `tests/` ; `conftest.py` racine déjà présent.
- venv : `.venv` (déjà créé). Lancer pytest avec `.venv/bin/pytest`.

---

### Task 1: Persistance des réglages (`settings.py`)

**Files:**
- Create: `wptemps/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `wptemps.settings.Settings` — dataclass : `x: Optional[float]=None`, `y: Optional[float]=None`,
    `locked: bool=True`, `show: bool=True`, `font_size: int=28`, `opacity: int=190`,
    `color: tuple=(255,255,255)`.
  - `wptemps.settings.load(path=SETTINGS_PATH) -> Settings`
  - `wptemps.settings.save(s: Settings, path=SETTINGS_PATH) -> None`
  - `wptemps.settings.SETTINGS_PATH` (str).

- [ ] **Step 1: Écrire les tests qui échouent**

Create `tests/test_settings.py`:

```python
import json

from wptemps.settings import Settings, load, save


def test_save_then_load_roundtrip(tmp_path):
    p = str(tmp_path / "settings.json")
    s = Settings(x=100.0, y=200.0, locked=False, show=True,
                 font_size=30, opacity=180, color=(10, 20, 30))
    save(s, p)
    out = load(p)
    assert out == s


def test_load_missing_file_returns_defaults(tmp_path):
    out = load(str(tmp_path / "absent.json"))
    assert out == Settings()
    assert out.locked is True and out.x is None


def test_load_corrupt_file_returns_defaults(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("ceci n'est pas du json")
    assert load(str(p)) == Settings()


def test_load_ignores_unknown_keys_and_coerces_color(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"x": 5, "color": [1, 2, 3], "inconnu": 42}))
    out = load(str(p))
    assert out.x == 5
    assert out.color == (1, 2, 3)      # liste JSON -> tuple


def test_save_creates_directory(tmp_path):
    p = str(tmp_path / "sub" / "dir" / "settings.json")
    save(Settings(), p)
    assert load(p) == Settings()
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_settings.py -q`
Expected: FAIL (`ModuleNotFoundError: wptemps.settings`).

- [ ] **Step 3: Implémenter `settings.py`**

Create `wptemps/settings.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple

APP_SUPPORT = os.path.expanduser("~/Library/Application Support/wptemps")
SETTINGS_PATH = os.path.join(APP_SUPPORT, "settings.json")


@dataclass
class Settings:
    x: Optional[float] = None
    y: Optional[float] = None
    locked: bool = True
    show: bool = True
    font_size: int = 28
    opacity: int = 190
    color: Tuple[int, int, int] = (255, 255, 255)


def _from_dict(data) -> Settings:
    d = Settings()
    if not isinstance(data, dict):
        return d
    return Settings(
        x=data.get("x", d.x),
        y=data.get("y", d.y),
        locked=bool(data.get("locked", d.locked)),
        show=bool(data.get("show", d.show)),
        font_size=int(data.get("font_size", d.font_size)),
        opacity=int(data.get("opacity", d.opacity)),
        color=tuple(data.get("color", d.color)),
    )


def _to_dict(s: Settings) -> dict:
    return {
        "x": s.x, "y": s.y, "locked": s.locked, "show": s.show,
        "font_size": s.font_size, "opacity": s.opacity, "color": list(s.color),
    }


def load(path: str = SETTINGS_PATH) -> Settings:
    try:
        with open(path, "r") as f:
            return _from_dict(json.load(f))
    except Exception:
        return Settings()


def save(s: Settings, path: str = SETTINGS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(_to_dict(s), f, indent=2)
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_settings.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add wptemps/settings.py tests/test_settings.py
git commit -m "feat: persistance des reglages (settings.py)"
```

---

### Task 2: Overlay déplaçable + position découplée du rendu (`overlay.py`)

**Files:**
- Modify: `wptemps/overlay.py` (réécriture complète — voir Step 3)
- Test: `tests/test_overlay.py` (ajouts)

**Interfaces:**
- Consumes: `Config`, `read_metrics`, `format_lines`, `Metrics`.
- Produces (en plus de `overlay_text`, `compute_origin` déjà existants) :
  - `wptemps.overlay.place_top_left(left, top, w, h, screen_w, screen_h) -> (int, int)`
    — origine bas-gauche clampée, pour une fenêtre dont le coin haut-gauche est `(left, top)`.
  - `wptemps.overlay.lock_params(locked: bool, desktop_level: int) -> dict`
    — clés : `level`, `ignores_mouse`, `draggable`, `bg_alpha`.
  - `wptemps.overlay.DraggableWindow(NSWindow)` — `setDraggable_`, `setOnMoved_`.
  - `OverlayController` enrichi : `setOnMoved_(cb)`, `set_position(left, top)`,
    `set_visible(bool)`, `set_locked(bool)`.

- [ ] **Step 1: Écrire les tests purs qui échouent**

Add to `tests/test_overlay.py` (garder l'existant, ajouter ces tests) :

```python
import AppKit
import Quartz

from wptemps.overlay import place_top_left, lock_params


def test_place_top_left_in_bounds():
    # fenetre 200x100, coin haut-gauche (300, 700) sur ecran 1000x800
    x, y = place_top_left(300, 700, 200, 100, 1000, 800)
    assert x == 300
    assert y == 600          # origine bas-gauche = top - h


def test_place_top_left_clamps_offscreen():
    x, y = place_top_left(5000, 5000, 200, 100, 1000, 800)
    assert x == 800          # 1000 - 200
    assert y == 700          # 800 - 100


def test_place_top_left_clamps_negative():
    x, y = place_top_left(-50, 10, 200, 100, 1000, 800)
    assert x == 0
    assert y == 0


def test_lock_params_locked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(True, desktop)
    assert p["level"] == desktop + 1
    assert p["ignores_mouse"] is True
    assert p["draggable"] is False
    assert p["bg_alpha"] == 0.0


def test_lock_params_unlocked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(False, desktop)
    assert p["level"] == AppKit.NSFloatingWindowLevel
    assert p["ignores_mouse"] is False
    assert p["draggable"] is True
    assert p["bg_alpha"] > 0.0
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: FAIL (`ImportError: cannot import name 'place_top_left'`).

- [ ] **Step 3: Réécrire `wptemps/overlay.py`**

Replace the entire content of `wptemps/overlay.py` with:

```python
"""Overlay macOS : fenetre transparente affichant les temperatures, deplacable.
Verrouille (defaut) : niveau bureau, clic-traversant. Deverrouille : saisissable
au premier plan pour etre deplacee. La fenetre ne modifie jamais le wallpaper."""
from __future__ import annotations

import math

import AppKit
import objc
import Quartz

from .config import Config
from .metrics import read_metrics
from .metrics.base import Metrics, format_lines

_PAD = 8
_UNLOCKED_BG_ALPHA = 0.25


def overlay_text(m: Metrics) -> str:
    return "\n".join(format_lines(m))


def compute_origin(screen_w, screen_h, win_w, win_h, position, margin):
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else screen_w - win_w - margin
    y = screen_h - win_h - margin if top else margin
    return max(0, int(x)), max(0, int(y))


def place_top_left(left, top, w, h, screen_w, screen_h):
    """Origine bas-gauche (coords Cocoa) d'une fenetre w x h dont le coin
    haut-gauche est (left, top), clampee pour rester entierement a l'ecran."""
    x = max(0, min(int(left), int(screen_w - w)))
    y = max(0, min(int(top - h), int(screen_h - h)))
    return x, y


def lock_params(locked, desktop_level):
    if locked:
        return {"level": desktop_level + 1, "ignores_mouse": True,
                "draggable": False, "bg_alpha": 0.0}
    return {"level": AppKit.NSFloatingWindowLevel, "ignores_mouse": False,
            "draggable": True, "bg_alpha": _UNLOCKED_BG_ALPHA}


def _make_paragraph_style(position, line_spacing):
    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(AppKit.NSTextAlignmentRight if position.endswith("right")
                       else AppKit.NSTextAlignmentLeft)
    para.setLineSpacing_(line_spacing)
    return para


class DraggableWindow(AppKit.NSWindow):
    def initWithContentRect_styleMask_backing_defer_(self, rect, style, backing, defer):
        self = objc.super(DraggableWindow, self).initWithContentRect_styleMask_backing_defer_(
            rect, style, backing, defer)
        if self is None:
            return None
        self._draggable = False
        self._on_moved = None
        self._drag_offset = None
        return self

    def setDraggable_(self, flag):
        self._draggable = bool(flag)

    def setOnMoved_(self, callback):
        self._on_moved = callback

    def canBecomeKeyWindow(self):
        return True

    def mouseDown_(self, event):
        if self._draggable:
            self._drag_offset = event.locationInWindow()

    def mouseDragged_(self, event):
        if self._draggable and self._drag_offset is not None:
            p = AppKit.NSEvent.mouseLocation()
            self.setFrameOrigin_(AppKit.NSMakePoint(
                p.x - self._drag_offset.x, p.y - self._drag_offset.y))

    def mouseUp_(self, event):
        if self._draggable and self._on_moved is not None:
            o = self.frame().origin
            self._on_moved(o.x, o.y)
        self._drag_offset = None


class OverlayController(AppKit.NSObject):
    def initWithConfig_(self, cfg):
        self = objc.super(OverlayController, self).init()
        if self is None:
            return None
        self.cfg = cfg
        self._top_left = None       # (left, top) coords Cocoa ; None => coin par defaut
        self._locked = True
        self._on_moved_cb = None
        self._desktop_level = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
        self._build_window()
        self.set_locked(True)
        return self

    def _color(self):
        r, g, b = self.cfg.color
        return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.cfg.opacity / 255.0)

    def _attributes(self):
        font = (AppKit.NSFont.fontWithName_size_("Menlo", self.cfg.font_size)
                or AppKit.NSFont.monospacedSystemFontOfSize_weight_(
                    self.cfg.font_size, AppKit.NSFontWeightRegular))
        shadow = AppKit.NSShadow.alloc().init()
        shadow.setShadowColor_(AppKit.NSColor.blackColor().colorWithAlphaComponent_(0.6))
        shadow.setShadowBlurRadius_(2.0)
        shadow.setShadowOffset_(AppKit.NSMakeSize(1, -1))
        return {
            AppKit.NSFontAttributeName: font,
            AppKit.NSForegroundColorAttributeName: self._color(),
            AppKit.NSShadowAttributeName: shadow,
            AppKit.NSParagraphStyleAttributeName: _make_paragraph_style(
                self.cfg.position, self.cfg.line_spacing),
        }

    def _build_window(self):
        rect = AppKit.NSMakeRect(0, 0, 320, 160)
        win = DraggableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, AppKit.NSWindowStyleMaskBorderless, AppKit.NSBackingStoreBuffered, False)
        win.setOpaque_(False)
        win.setBackgroundColor_(AppKit.NSColor.clearColor())
        win.setHasShadow_(False)
        win.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary)
        win.setOnMoved_(self._handle_moved)
        view = win.contentView()
        view.setWantsLayer_(True)
        label = AppKit.NSTextField.alloc().initWithFrame_(rect)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.cell().setWraps_(False)
        view.addSubview_(label)
        win.orderFront_(None)
        self.window = win
        self.label = label

    def setOnMoved_(self, cb):
        self._on_moved_cb = cb

    def _handle_moved(self, origin_x, origin_y):
        h = self.window.frame().size.height
        self._top_left = (origin_x, origin_y + h)
        if self._on_moved_cb is not None:
            self._on_moved_cb(self._top_left[0], self._top_left[1])

    def set_position(self, left, top):
        self._top_left = None if (left is None or top is None) else (left, top)
        self._update()

    def set_visible(self, visible):
        if visible:
            self.window.orderFront_(None)
        else:
            self.window.orderOut_(None)

    def set_locked(self, locked):
        self._locked = bool(locked)
        p = lock_params(self._locked, self._desktop_level)
        self.window.setLevel_(p["level"])
        self.window.setIgnoresMouseEvents_(p["ignores_mouse"])
        self.window.setDraggable_(p["draggable"])
        layer = self.window.contentView().layer()
        layer.setBackgroundColor_(
            AppKit.NSColor.blackColor().colorWithAlphaComponent_(p["bg_alpha"]).CGColor())
        layer.setCornerRadius_(0.0 if self._locked else 6.0)

    def _update(self):
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            overlay_text(read_metrics()), self._attributes())
        size = astr.size()
        w = int(math.ceil(size.width)) + 2 * _PAD
        h = int(math.ceil(size.height)) + 2 * _PAD
        screen = AppKit.NSScreen.mainScreen().frame()
        if self._top_left is None:
            x, y = compute_origin(screen.size.width, screen.size.height, w, h,
                                  self.cfg.position, self.cfg.margin)
            self._top_left = (x, y + h)
        x, y = place_top_left(self._top_left[0], self._top_left[1], w, h,
                              screen.size.width, screen.size.height)
        self.window.setFrame_display_(AppKit.NSMakeRect(x, y, w, h), True)
        self.label.setFrame_(AppKit.NSMakeRect(_PAD, _PAD, w - 2 * _PAD, h - 2 * _PAD))
        self.label.setAttributedStringValue_(astr)

    def tick_(self, timer):
        self._update()

    def start(self):
        self._update()
        self.timer = (
            AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                self.cfg.interval_sec, self, b"tick:", None, True))


def main() -> None:
    cfg = Config()
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    controller = OverlayController.alloc().initWithConfig_(cfg)
    controller.start()
    print("[wptemps] overlay demarre (mode autonome).")
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer les tests purs pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: PASS (les 4 tests existants + 5 nouveaux = 9).

- [ ] **Step 5: Vérification réelle de l'overlay autonome**

Run:

```bash
.venv/bin/python -m wptemps.overlay &
OPID=$!
# laisser s'ouvrir, inspecter le niveau via Quartz, puis arreter
.venv/bin/python - "$OPID" <<'PY'
import sys, Quartz
pid = int(sys.argv[1])
desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
infos = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
mine = [w for w in infos if w.get("kCGWindowOwnerPID") == pid]
print("fenetres:", len(mine), "| layer attendu (bureau+1):", desktop + 1)
for w in mine:
    print("  layer:", w.get("kCGWindowLayer"))
PY
kill -9 "$OPID" 2>/dev/null
```

Expected : 1 fenêtre, `layer == bureau+1` (mode verrouillé par défaut). Pas d'erreur.

- [ ] **Step 6: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat: overlay deplacable (DraggableWindow, lock/unlock, position persistante)"
```

---

### Task 3: App barre de menus (`app.py`)

**Files:**
- Create: `wptemps/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Settings`, `load`, `save`, `Config`, `OverlayController`.
- Produces:
  - `wptemps.app.AppState(settings, save_fn, apply_locked, apply_visible)` — logique pure des
    bascules : `toggle_locked() -> bool`, `toggle_show() -> bool`, `record_move(left, top)`.
  - `wptemps.app.config_from_settings(s: Settings) -> Config`.
  - `wptemps.app.login_supported() -> bool` (False en mode source).
  - `wptemps.app.MenuBarApp(NSObject)` + `wptemps.app.main()`.

- [ ] **Step 1: Écrire les tests purs qui échouent**

Create `tests/test_app.py`:

```python
from wptemps.app import AppState, config_from_settings, login_supported
from wptemps.settings import Settings


def _state(settings):
    saved, applied = [], []
    st = AppState(
        settings,
        save_fn=lambda s: saved.append((s.locked, s.show, s.x, s.y)),
        apply_locked=lambda locked: applied.append(("locked", locked)),
        apply_visible=lambda show: applied.append(("show", show)),
    )
    return st, saved, applied


def test_toggle_locked_flips_persists_and_applies():
    st, saved, applied = _state(Settings(locked=True))
    result = st.toggle_locked()
    assert result is False
    assert st.settings.locked is False
    assert ("locked", False) in applied
    assert saved and saved[-1][0] is False


def test_toggle_show_flips_persists_and_applies():
    st, saved, applied = _state(Settings(show=True))
    assert st.toggle_show() is False
    assert ("show", False) in applied
    assert saved[-1][1] is False


def test_record_move_persists_position():
    st, saved, applied = _state(Settings())
    st.record_move(123.0, 456.0)
    assert st.settings.x == 123.0 and st.settings.y == 456.0
    assert saved[-1][2:] == (123.0, 456.0)


def test_config_from_settings_maps_fields():
    cfg = config_from_settings(Settings(font_size=33, opacity=170, color=(1, 2, 3)))
    assert cfg.font_size == 33
    assert cfg.opacity == 170
    assert cfg.color == (1, 2, 3)


def test_login_supported_is_false_from_source():
    # lance depuis les sources (non empaquete) -> non supporte
    assert login_supported() is False
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_app.py -q`
Expected: FAIL (`ModuleNotFoundError: wptemps.app`).

- [ ] **Step 3: Implémenter `wptemps/app.py`**

Create `wptemps/app.py`:

```python
"""App wptemps : icone de barre de menus pilotant l'overlay deplacable."""
from __future__ import annotations

import sys

import AppKit
import objc

from .config import Config
from .overlay import OverlayController
from .settings import Settings, load, save


class AppState:
    """Logique pure des bascules du menu (testable sans Cocoa)."""

    def __init__(self, settings, save_fn, apply_locked, apply_visible):
        self.settings = settings
        self._save = save_fn
        self._apply_locked = apply_locked
        self._apply_visible = apply_visible

    def toggle_locked(self):
        self.settings.locked = not self.settings.locked
        self._apply_locked(self.settings.locked)
        self._save(self.settings)
        return self.settings.locked

    def toggle_show(self):
        self.settings.show = not self.settings.show
        self._apply_visible(self.settings.show)
        self._save(self.settings)
        return self.settings.show

    def record_move(self, left, top):
        self.settings.x = left
        self.settings.y = top
        self._save(self.settings)


def config_from_settings(s: Settings) -> Config:
    return Config(font_size=s.font_size, opacity=s.opacity, color=tuple(s.color))


def login_supported() -> bool:
    # Le lancement au demarrage via SMAppService ne s'applique qu'a l'app empaquetee.
    return bool(getattr(sys, "frozen", False))


class MenuBarApp(AppKit.NSObject):
    def setup(self):
        self.settings = load()
        cfg = config_from_settings(self.settings)
        self.controller = OverlayController.alloc().initWithConfig_(cfg)

        self.state = AppState(
            self.settings, save_fn=save,
            apply_locked=self.controller.set_locked,
            apply_visible=self.controller.set_visible,
        )
        self.controller.setOnMoved_(self.state.record_move)

        if self.settings.x is not None and self.settings.y is not None:
            self.controller.set_position(self.settings.x, self.settings.y)
        self.controller.set_locked(self.settings.locked)
        self.controller.set_visible(self.settings.show)
        self.controller.start()

        self._build_status_item()
        return self

    def _build_status_item(self):
        bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        button = self.status_item.button()
        img = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "thermometer", None)
        if img is not None:
            button.setImage_(img)
        else:
            button.setTitle_("\U0001F321")

        menu = AppKit.NSMenu.alloc().init()
        self.item_show = self._add(menu, "Afficher les temperatures", b"toggleShow:")
        self.item_lock = self._add(menu, "", b"toggleLock:")
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.item_login = self._add(menu, "Lancer au demarrage", b"toggleLogin:")
        if not login_supported():
            self.item_login.setEnabled_(False)
            self.item_login.setToolTip_("Disponible uniquement dans l'app empaquetee (.app)")
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self._add(menu, "Quitter", b"quit:")
        self.status_item.setMenu_(menu)
        self._refresh_checks()

    def _add(self, menu, title, selector):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, selector, "")
        item.setTarget_(self)
        menu.addItem_(item)
        return item

    def _refresh_checks(self):
        self.item_show.setState_(
            AppKit.NSControlStateValueOn if self.settings.show
            else AppKit.NSControlStateValueOff)
        self.item_lock.setTitle_(
            "Verrouiller la position" if not self.settings.locked
            else "Deverrouiller pour deplacer")

    def toggleShow_(self, sender):
        self.state.toggle_show()
        self._refresh_checks()

    def toggleLock_(self, sender):
        self.state.toggle_locked()
        self._refresh_checks()

    def toggleLogin_(self, sender):
        pass  # active en Phase B (app empaquetee)

    def quit_(self, sender):
        AppKit.NSApp.terminate_(self)


def main() -> None:
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    delegate = MenuBarApp.alloc().init().setup()
    app.setDelegate_(delegate)  # retient la reference
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer les tests purs pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_app.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (tous verts).

- [ ] **Step 6: Commit**

```bash
git add wptemps/app.py tests/test_app.py
git commit -m "feat: app barre de menus (NSStatusItem) pilotant l'overlay"
```

---

### Task 4: Vérification de bout en bout + README

**Files:**
- Modify: `README.md`
- Test: vérification manuelle réelle

**Interfaces:**
- Consumes: tout le package.
- Produces: app lançable via `python -m wptemps.app` + doc.

- [ ] **Step 1: Lancer l'app réelle et vérifier l'icône + l'overlay**

Run:

```bash
.venv/bin/python -m wptemps.app &
APID=$!
.venv/bin/python - "$APID" <<'PY'
import sys, Quartz
pid = int(sys.argv[1])
desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
infos = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
mine = [w for w in infos if w.get("kCGWindowOwnerPID") == pid]
print("fenetres on-screen du process:", len(mine))
for w in mine:
    print("  layer:", w.get("kCGWindowLayer"), "(bureau+1 =", desktop + 1, ")")
PY
echo "Verifier visuellement : icone thermometre dans la barre de menus + temperatures sur le bureau."
kill -9 "$APID" 2>/dev/null
```

Expected : l'overlay s'affiche (layer bureau+1), une icône apparaît dans la barre de menus. Pas d'erreur au lancement.

- [ ] **Step 2: Vérifier manuellement le déplacement et la persistance**

Procédure (manuelle, à faire une fois) :
1. Lancer `.venv/bin/python -m wptemps.app`.
2. Menu → « Deverrouiller pour deplacer », glisser l'overlay ailleurs, menu → « Verrouiller la position ».
3. Quitter via le menu, relancer : l'overlay doit réapparaître à la **nouvelle** position.
4. Vérifier que `~/Library/Application Support/wptemps/settings.json` contient des `x`/`y` non nuls :

```bash
cat ~/Library/Application\ Support/wptemps/settings.json
```

Expected : le fichier existe et `x`/`y` reflètent la position choisie ; l'overlay réapparaît au bon endroit.

- [ ] **Step 3: Mettre à jour le README**

Replace the `## Lancer` section of `README.md` with:

```markdown
## Lancer (app barre de menus)
```bash
.venv/bin/python -m wptemps.app
```
Une icône 🌡 apparaît dans la barre de menus. Le menu permet d'afficher/masquer,
de **déverrouiller pour déplacer** l'affichage (puis le reverrouiller), et de quitter.
La position est mémorisée dans `~/Library/Application Support/wptemps/settings.json`.
Ton fond d'écran n'est **jamais modifié**.

Mode overlay seul (sans menu) : `.venv/bin/python -m wptemps.overlay`.

> « Lancer au démarrage » depuis le menu n'est actif que pour l'app empaquetée
> (`.app`, à venir). En mode source, utilise `scripts/install-login-item.sh`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README app barre de menus + verification end-to-end Phase A"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec :**
- Icône barre de menus + menu (afficher/masquer, lock/unlock, login, quitter) → Task 3. ✓
- Overlay déplaçable (verrouillé/déverrouillé, drag) → Task 2. ✓
- Position mémorisée + réapparition au même endroit → Tasks 1 (settings) + 2 (`_handle_moved`, `set_position`) + 3 (wiring). ✓
- Persistance `~/Library/Application Support/wptemps/settings.json` → Task 1. ✓
- Settings absent/corrompu → défauts → Task 1 (tests). ✓
- Position hors écran → clampée → Task 2 (`place_top_left`, testé). ✓
- « Lancer au démarrage » désactivé en mode source → Task 3 (`login_supported`, item désactivé). ✓
- Réutilise `metrics`/`format_lines`/`Config` → Tasks 2-3. ✓
- Pas de modification du wallpaper → aucune dépendance wallpaper dans overlay/app. ✓

**Placeholders :** aucun TODO/TBD ; `toggleLogin_` est volontairement un no-op documenté
(activé en Phase B), pas un placeholder de code manquant pour cette phase.

**Cohérence des types :** `Settings`, `load/save`, `OverlayController.set_locked/set_visible/
set_position/setOnMoved_`, `AppState.toggle_locked/toggle_show/record_move`,
`config_from_settings`, `login_supported` — noms et signatures identiques entre tâches.
