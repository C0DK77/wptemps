# wptemps — Personnalisation (police / couleur / alignement) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter au menu 🌡 le choix de la police (famille/taille/gras/italique via le sélecteur macOS), de la couleur (sélecteur macOS + opacité) et de l'alignement du texte (gauche/centre/droite), persistés et appliqués en direct.

**Architecture :** On étend `Settings` et `Config` avec des champs de style, on paramètre le rendu de `overlay.py` (police construite via `NSFontManager`, alignement via `align`), et `app.py` ouvre les panneaux natifs `NSFontPanel`/`NSColorPanel` (callbacks `changeFont:`/`changeColor:` câblés par cible/action — validé par spike) plus un sous-menu Alignement. Toute la logique non-Cocoa est isolée et testée.

**Tech Stack :** Python 3.9, PyObjC (AppKit), pytest. Aucune nouvelle dépendance.

## Global Constraints

- macOS Apple Silicon ; l'app ne modifie jamais le wallpaper.
- Nouveaux réglages persistés dans `~/Library/Application Support/wptemps/settings.json` ; `settings.json` ancien (sans les nouveaux champs) → valeurs par défaut, pas de crash.
- `align` ∈ {`left`,`center`,`right`} ; valeur invalide → `left`.
- Police enregistrée introuvable → repli police monospace système, pas de crash.
- Application **en direct** (re-rendu immédiat) + **sauvegarde** à chaque changement.
- Package `wptemps/` ; tests `tests/` ; venv `.venv` ; lancer pytest avec `.venv/bin/pytest`.

---

### Task 1: Champs de style dans `Settings` et `Config`

**Files:**
- Modify: `wptemps/settings.py`
- Modify: `wptemps/config.py`
- Modify: `wptemps/app.py` (`config_from_settings`)
- Test: `tests/test_settings.py` (ajouts), `tests/test_app.py` (ajouts)

**Interfaces:**
- Produces (ajouts) :
  - `Settings` : `font_name: str = "Menlo"`, `bold: bool = False`, `italic: bool = False`,
    `align: str = "left"`. `load()` normalise `align` invalide → `"left"`.
  - `Config` : mêmes champs `font_name`, `bold`, `italic`, `align`.
  - `config_from_settings(s)` mappe les 4 nouveaux champs.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_settings.py`:

```python
def test_new_style_fields_roundtrip(tmp_path):
    from wptemps.settings import Settings, load, save
    p = str(tmp_path / "s.json")
    s = Settings(font_name="Courier New", bold=True, italic=True, align="center")
    save(s, p)
    out = load(p)
    assert out.font_name == "Courier New"
    assert out.bold is True and out.italic is True
    assert out.align == "center"


def test_align_invalid_normalized_to_left(tmp_path):
    import json
    from wptemps.settings import load
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"align": "diagonal"}))
    assert load(str(p)).align == "left"


def test_old_settings_without_style_fields_uses_defaults(tmp_path):
    import json
    from wptemps.settings import Settings, load
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 10, "y": 20}))   # ancien fichier
    out = load(str(p))
    assert out.font_name == Settings().font_name
    assert out.bold is False and out.align == "left"
```

Add to `tests/test_app.py`:

```python
def test_config_from_settings_maps_style_fields():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(
        Settings(font_name="Courier New", bold=True, italic=True, align="right"))
    assert cfg.font_name == "Courier New"
    assert cfg.bold is True and cfg.italic is True
    assert cfg.align == "right"
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: FAIL (`AttributeError`/`TypeError` sur `font_name`/`align`).

- [ ] **Step 3: Étendre `Settings`**

In `wptemps/settings.py`, add the fields to the dataclass:

```python
@dataclass
class Settings:
    x: Optional[float] = None
    y: Optional[float] = None
    locked: bool = True
    show: bool = True
    font_size: int = 28
    opacity: int = 190
    color: Tuple[int, int, int] = (255, 255, 255)
    font_name: str = "Menlo"
    bold: bool = False
    italic: bool = False
    align: str = "left"
```

Update `_from_dict` to read + normalize the new fields (replace the function):

```python
_ALIGNS = ("left", "center", "right")


def _from_dict(data) -> Settings:
    d = Settings()
    if not isinstance(data, dict):
        return d
    align = data.get("align", d.align)
    if align not in _ALIGNS:
        align = "left"
    return Settings(
        x=data.get("x", d.x),
        y=data.get("y", d.y),
        locked=bool(data.get("locked", d.locked)),
        show=bool(data.get("show", d.show)),
        font_size=int(data.get("font_size", d.font_size)),
        opacity=int(data.get("opacity", d.opacity)),
        color=tuple(data.get("color", d.color)),
        font_name=str(data.get("font_name", d.font_name)),
        bold=bool(data.get("bold", d.bold)),
        italic=bool(data.get("italic", d.italic)),
        align=align,
    )
```

Update `_to_dict` to include them (replace the function):

```python
def _to_dict(s: Settings) -> dict:
    return {
        "x": s.x, "y": s.y, "locked": s.locked, "show": s.show,
        "font_size": s.font_size, "opacity": s.opacity, "color": list(s.color),
        "font_name": s.font_name, "bold": s.bold, "italic": s.italic, "align": s.align,
    }
```

- [ ] **Step 4: Étendre `Config`**

In `wptemps/config.py`, add the fields to the dataclass (after `line_spacing`):

```python
    line_spacing: int = 10
    font_name: str = "Menlo"
    bold: bool = False
    italic: bool = False
    align: str = "left"
```

- [ ] **Step 5: Étendre `config_from_settings`**

In `wptemps/app.py`, replace `config_from_settings`:

```python
def config_from_settings(s: Settings) -> Config:
    return Config(
        font_size=s.font_size, opacity=s.opacity, color=tuple(s.color),
        font_name=s.font_name, bold=s.bold, italic=s.italic, align=s.align,
    )
```

- [ ] **Step 6: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: PASS (anciens + nouveaux tests).

- [ ] **Step 7: Commit**

```bash
git add wptemps/settings.py wptemps/config.py wptemps/app.py tests/test_settings.py tests/test_app.py
git commit -m "feat: champs de style (font_name/bold/italic/align) dans Settings et Config"
```

---

### Task 2: Rendu paramétrable + `set_config` (`overlay.py`)

**Files:**
- Modify: `wptemps/overlay.py`
- Test: `tests/test_overlay.py` (ajouts)

**Interfaces:**
- Consumes: `Config` (avec `font_name`/`bold`/`italic`/`align`).
- Produces :
  - `wptemps.overlay._alignment_constant(align) -> int` (NSTextAlignment ; défaut left).
  - `wptemps.overlay.build_font(name, size, bold, italic) -> NSFont` (repli système si famille
    introuvable).
  - `OverlayController.set_config(cfg)` : remplace la config et re-rend immédiatement.
  - `_attributes()` utilise `build_font` + `_alignment_constant(cfg.align)`.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_overlay.py`:

```python
def test_alignment_constant_maps_values():
    from wptemps.overlay import _alignment_constant
    assert _alignment_constant("left") == AppKit.NSTextAlignmentLeft
    assert _alignment_constant("center") == AppKit.NSTextAlignmentCenter
    assert _alignment_constant("right") == AppKit.NSTextAlignmentRight
    assert _alignment_constant("nope") == AppKit.NSTextAlignmentLeft


def test_build_font_applies_traits():
    from wptemps.overlay import build_font
    fm = AppKit.NSFontManager.sharedFontManager()
    f = build_font("Menlo", 20, bold=True, italic=False)
    assert bool(fm.traitsOfFont_(f) & AppKit.NSBoldFontMask)
    assert round(f.pointSize()) == 20


def test_build_font_falls_back_for_unknown_family():
    from wptemps.overlay import build_font
    f = build_font("NoSuchFontFamily__xyz", 18, bold=False, italic=False)
    assert f is not None
    assert round(f.pointSize()) == 18
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: FAIL (`ImportError: cannot import name '_alignment_constant'`).

- [ ] **Step 3: Ajouter `_alignment_constant` et `build_font`**

In `wptemps/overlay.py`, add these two functions just before `_make_paragraph_style`:

```python
def _alignment_constant(align):
    return {
        "left": AppKit.NSTextAlignmentLeft,
        "center": AppKit.NSTextAlignmentCenter,
        "right": AppKit.NSTextAlignmentRight,
    }.get(align, AppKit.NSTextAlignmentLeft)


def build_font(name, size, bold, italic):
    fm = AppKit.NSFontManager.sharedFontManager()
    font = (AppKit.NSFont.fontWithName_size_(name, size)
            or AppKit.NSFont.monospacedSystemFontOfSize_weight_(
                size, AppKit.NSFontWeightRegular))
    if bold:
        font = fm.convertFont_toHaveTrait_(font, AppKit.NSBoldFontMask)
    if italic:
        font = fm.convertFont_toHaveTrait_(font, AppKit.NSItalicFontMask)
    return font
```

- [ ] **Step 4: Utiliser l'alignement paramétrable**

In `wptemps/overlay.py`, replace `_make_paragraph_style` (it currently takes `position`):

```python
def _make_paragraph_style(align, line_spacing):
    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(_alignment_constant(align))
    para.setLineSpacing_(line_spacing)
    return para
```

- [ ] **Step 5: Construire les attributs depuis la config**

In `wptemps/overlay.py`, replace the body of `_attributes` (the font line and the paragraph
style line):

```python
    def _attributes(self):
        font = build_font(self.cfg.font_name, self.cfg.font_size,
                          self.cfg.bold, self.cfg.italic)
        shadow = AppKit.NSShadow.alloc().init()
        shadow.setShadowColor_(AppKit.NSColor.blackColor().colorWithAlphaComponent_(0.6))
        shadow.setShadowBlurRadius_(2.0)
        shadow.setShadowOffset_(AppKit.NSMakeSize(1, -1))
        return {
            AppKit.NSFontAttributeName: font,
            AppKit.NSForegroundColorAttributeName: self._color(),
            AppKit.NSShadowAttributeName: shadow,
            AppKit.NSParagraphStyleAttributeName: _make_paragraph_style(
                self.cfg.align, self.cfg.line_spacing),
        }
```

- [ ] **Step 6: Ajouter `set_config`**

In `wptemps/overlay.py`, add this method to `OverlayController` (e.g. just after
`set_position`):

```python
    def set_config(self, cfg):
        self.cfg = cfg
        self._update()
```

- [ ] **Step 7: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: PASS (tous, anciens + 3 nouveaux).

- [ ] **Step 8: Vérification réelle (re-rendu avec un style différent)**

Run:

```bash
.venv/bin/python - <<'PY'
import AppKit
from wptemps.config import Config
from wptemps.overlay import OverlayController
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
c = OverlayController.alloc().initWithConfig_(Config())
c.start(); c.set_visible(True)
c.set_config(Config(font_name="Courier New", bold=True, align="center", color=(255,0,0)))
print("set_config applique sans erreur")
PY
```

Expected : "set_config applique sans erreur" (pas d'exception ; le rendu se reconstruit avec la
nouvelle police/couleur/alignement).

- [ ] **Step 9: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat: rendu overlay parametrable (police/traits/alignement) + set_config"
```

---

### Task 3: Menu police / couleur / alignement (`app.py`)

**Files:**
- Modify: `wptemps/app.py`
- Test: `tests/test_app.py` (ajouts)

**Interfaces:**
- Consumes: `Settings`, `config_from_settings`, `OverlayController.set_config`, `build_font`.
- Produces :
  - `wptemps.app.font_to_fields(font) -> dict` — `{font_name, font_size, bold, italic}`.
  - `wptemps.app.color_to_fields(color) -> dict` — `{color: (r,g,b), opacity: int}` (0-255).
  - `wptemps.app.apply_style(settings, set_config_fn, save_fn) -> None`.
  - `MenuBarApp` : items « Police… » (`openFont:`), « Couleur… » (`openColor:`), sous-menu
    Alignement (`setAlign:`) ; callbacks `changeFont:` / `changeColor:`.

- [ ] **Step 1: Écrire les tests purs qui échouent**

Add to `tests/test_app.py`:

```python
def test_font_to_fields_extracts_family_size_traits():
    import AppKit
    from wptemps.app import font_to_fields
    from wptemps.overlay import build_font
    fields = font_to_fields(build_font("Menlo", 24, bold=True, italic=False))
    assert fields["font_name"] == "Menlo"
    assert fields["font_size"] == 24
    assert fields["bold"] is True
    assert fields["italic"] is False


def test_color_to_fields_extracts_rgb_and_opacity():
    import AppKit
    from wptemps.app import color_to_fields
    col = AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(1.0, 0.0, 0.0, 0.5)
    f = color_to_fields(col)
    assert f["color"] == (255, 0, 0)
    assert f["opacity"] == 128   # round(0.5*255)


def test_apply_style_applies_and_saves():
    from wptemps.app import apply_style
    from wptemps.settings import Settings
    applied, saved = [], []
    s = Settings(font_name="Courier New", align="center")
    apply_style(s, set_config_fn=lambda cfg: applied.append(cfg),
                save_fn=lambda x: saved.append(x))
    assert applied and applied[0].font_name == "Courier New"
    assert applied[0].align == "center"
    assert saved == [s]
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_app.py -q`
Expected: FAIL (`ImportError: cannot import name 'font_to_fields'`).

- [ ] **Step 3: Ajouter les helpers purs**

In `wptemps/app.py`, add (near `config_from_settings`):

```python
def font_to_fields(font) -> dict:
    fm = AppKit.NSFontManager.sharedFontManager()
    tr = fm.traitsOfFont_(font)
    return {
        "font_name": font.familyName(),
        "font_size": int(round(font.pointSize())),
        "bold": bool(tr & AppKit.NSBoldFontMask),
        "italic": bool(tr & AppKit.NSItalicFontMask),
    }


def color_to_fields(color) -> dict:
    c = color.colorUsingColorSpace_(AppKit.NSColorSpace.sRGBColorSpace()) or color
    return {
        "color": (int(round(c.redComponent() * 255)),
                  int(round(c.greenComponent() * 255)),
                  int(round(c.blueComponent() * 255))),
        "opacity": int(round(c.alphaComponent() * 255)),
    }


def apply_style(settings, set_config_fn, save_fn) -> None:
    set_config_fn(config_from_settings(settings))
    save_fn(settings)
```

- [ ] **Step 4: Lancer pour vérifier le succès des tests purs**

Run: `.venv/bin/pytest tests/test_app.py -q`
Expected: PASS.

- [ ] **Step 5: Ajouter les éléments de menu et les callbacks**

In `wptemps/app.py`, inside `_build_status_item`, add the new items just before the separator
that precedes « Quitter » (i.e. after the login item block):

```python
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        _make_item(menu, self, "Police…", b"openFont:")
        _make_item(menu, self, "Couleur…", b"openColor:")
        align_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Alignement", None, "")
        align_menu = AppKit.NSMenu.alloc().init()
        self.align_items = {}
        for key, label in (("left", "Gauche"), ("center", "Centre"), ("right", "Droite")):
            it = _make_item(align_menu, self, label, b"setAlign:")
            it.setRepresentedObject_(key)
            self.align_items[key] = it
        align_item.setSubmenu_(align_menu)
        menu.addItem_(align_item)
```

Then, in `setup` (after the overlay controller is created), wire the panels' target/action:

```python
        AppKit.NSFontManager.sharedFontManager().setTarget_(self)
        AppKit.NSFontManager.sharedFontManager().setAction_(b"changeFont:")
        cp = AppKit.NSColorPanel.sharedColorPanel()
        cp.setTarget_(self)
        cp.setAction_(b"changeColor:")
        cp.setShowsAlpha_(True)
```

Add the action methods and callbacks to `MenuBarApp`:

```python
    def _apply(self):
        apply_style(self.settings,
                    set_config_fn=self.controller.set_config,
                    save_fn=save)
        self._refresh_checks()

    def openFont_(self, sender):
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        fm = AppKit.NSFontManager.sharedFontManager()
        cur = build_font(self.settings.font_name, self.settings.font_size,
                         self.settings.bold, self.settings.italic)
        fm.setSelectedFont_isMultiple_(cur, False)
        fm.orderFrontFontPanel_(self)

    def changeFont_(self, sender):
        fm = AppKit.NSFontManager.sharedFontManager()
        cur = build_font(self.settings.font_name, self.settings.font_size,
                         self.settings.bold, self.settings.italic)
        new = fm.convertFont_(cur)
        f = font_to_fields(new)
        self.settings.font_name = f["font_name"]
        self.settings.font_size = f["font_size"]
        self.settings.bold = f["bold"]
        self.settings.italic = f["italic"]
        self._apply()

    def openColor_(self, sender):
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        cp = AppKit.NSColorPanel.sharedColorPanel()
        r, g, b = self.settings.color
        cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.settings.opacity / 255.0))
        cp.orderFront_(self)

    def changeColor_(self, sender):
        f = color_to_fields(AppKit.NSColorPanel.sharedColorPanel().color())
        self.settings.color = f["color"]
        self.settings.opacity = f["opacity"]
        self._apply()

    def setAlign_(self, sender):
        self.settings.align = sender.representedObject()
        self._apply()
```

Add to `_refresh_checks` (so the current alignment is checked), append after the existing
lines:

```python
        if hasattr(self, "align_items"):
            for key, item in self.align_items.items():
                item.setState_(
                    AppKit.NSControlStateValueOn if self.settings.align == key
                    else AppKit.NSControlStateValueOff)
```

Ensure the module imports `build_font`:

```python
from .overlay import OverlayController, build_font
```

- [ ] **Step 6: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (tous verts).

- [ ] **Step 7: Vérification réelle (l'app se lance, callbacks programmatiques)**

Run:

```bash
.venv/bin/python - <<'PY'
import AppKit
from wptemps.app import MenuBarApp
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
d = MenuBarApp.alloc().init().setup()
# simuler un changement de couleur via le callback
cp = AppKit.NSColorPanel.sharedColorPanel()
cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.0, 1.0, 0.0, 0.8))
d.changeColor_(cp)
print("apres changeColor: color=", d.settings.color, "opacity=", d.settings.opacity)
d.settings.align = "left"; d.setAlign_(type("S",(),{"representedObject":lambda s:"center"})())
print("apres setAlign: align=", d.settings.align)
assert d.settings.color == (0, 255, 0)
assert d.settings.align == "center"
print("OK callbacks reels")
PY
```

Expected : la couleur devient `(0,255,0)`, opacité ~204, alignement `center`, sans erreur.

- [ ] **Step 8: Commit**

```bash
git add wptemps/app.py tests/test_app.py
git commit -m "feat: menu Police/Couleur/Alignement (panneaux natifs + callbacks)"
```

---

### Task 4: Vérification de bout en bout + README

**Files:**
- Modify: `README.md`
- Test: vérification manuelle réelle

- [ ] **Step 1: Lancer l'app et vérifier les nouveaux menus**

Run: `.venv/bin/python -m wptemps.app`
Vérifier : le menu 🌡 contient « Police… », « Couleur… » et le sous-menu « Alignement »
(Gauche/Centre/Droite, coché sur l'actuel). « Police… » ouvre le sélecteur de police, le choix
modifie l'overlay en direct ; « Couleur… » ouvre le sélecteur de couleur (avec opacité) ;
changer l'alignement re-aligne le texte. Quitter via le menu.

- [ ] **Step 2: Vérifier la persistance**

Relancer l'app : la police, la couleur et l'alignement choisis doivent être conservés.

```bash
cat ~/Library/Application\ Support/wptemps/settings.json
```

Expected : `font_name`, `bold`, `italic`, `align`, `color`, `opacity` reflètent les choix.

- [ ] **Step 3: Mettre à jour le README**

In `README.md`, in the `## Lancer (app barre de menus)` section, add to the menu description
that the menu also offers « Police… » (police, taille, gras/italique), « Couleur… » (couleur +
opacité) et « Alignement » (gauche/centre/droite), tous mémorisés.

Concretely, replace the sentence listing the menu actions with:

```markdown
Une icône 🌡 apparaît dans la barre de menus. Le menu permet d'afficher/masquer,
de **déverrouiller pour déplacer** l'affichage (puis le reverrouiller), de choisir
**Police…** (police, taille, gras/italique), **Couleur…** (couleur + opacité) et
**Alignement** (gauche/centre/droite), et de quitter. Tous ces réglages — et la
position — sont mémorisés dans `~/Library/Application Support/wptemps/settings.json`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README — personnalisation police/couleur/alignement"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec :**
- Police/taille/gras/italique via panneau natif → Task 3 (`openFont_`/`changeFont_`,
  `font_to_fields`) + Task 2 (`build_font`). ✓
- Couleur + opacité via panneau natif → Task 3 (`openColor_`/`changeColor_`, `color_to_fields`). ✓
- Alignement gauche/centre/droite → Task 1 (`align`), Task 2 (`_alignment_constant`,
  paragraphe), Task 3 (sous-menu `setAlign_`). ✓
- Persistance + défauts + `align` invalide → `left` → Task 1 (tests). ✓
- Application en direct (`set_config`) → Task 2 + `apply_style` Task 3. ✓
- Police introuvable → repli système → Task 2 (`build_font`, test). ✓
- Pas de modification du wallpaper → aucune dépendance wallpaper. ✓

**Placeholders :** aucun ; tout le code est fourni.

**Cohérence des types :** `Settings`/`Config` nouveaux champs identiques ;
`config_from_settings` les mappe ; `build_font(name,size,bold,italic)` utilisé par overlay et
app ; `font_to_fields`/`color_to_fields`/`apply_style`/`set_config` cohérents entre tâches ;
`_alignment_constant`/`_make_paragraph_style(align, …)` cohérents.
