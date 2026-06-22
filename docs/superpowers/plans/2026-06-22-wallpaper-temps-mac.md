# Wallpaper Temps — Phase 1 (Mac M3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher les températures/charge du Mac M3 incrustées dans le fond d'écran, mises à jour en boucle.

**Architecture :** Un programme Python à boucle. Le cœur (modèle de mesures, rendu image, boucle) est commun ; deux modules sont spécifiques macOS : lecture capteurs (`macmon` + `pmset`) et application du wallpaper (`osascript`). Les fonctions impures (subprocess) sont isolées derrière des callables injectables pour rester testables.

**Tech Stack :** Python 3.9 (système), Pillow (rendu), pytest (tests), `macmon` (Homebrew, déjà installé), outils macOS `osascript`/`sips`/`pmset`.

## Global Constraints

- Cible Phase 1 : **macOS Apple Silicon uniquement** (Windows = plan séparé Phase 2).
- **Aucun `sudo`** : capteurs lus via `macmon pipe` (validé sans sudo).
- Toute mesure indisponible → `None`, affichée `N/A`, **jamais de crash**.
- Ne **jamais écraser** le fichier wallpaper d'origine ; écrire dans des fichiers de sortie dédiés.
- Visuel **minimal** : texte fondu (semi-transparent + ombre), police monospace `/System/Library/Fonts/Menlo.ttc`.
- Refresh par défaut : **5 s** (configurable).
- Package Python : `wptemps/` à la racine du repo ; tests dans `tests/` ; un `conftest.py` vide à la racine garantit l'import.

---

### Task 1: Scaffold projet + modèle de mesures

**Files:**
- Create: `requirements.txt`
- Create: `conftest.py`
- Create: `wptemps/__init__.py`
- Create: `wptemps/metrics/__init__.py`
- Create: `wptemps/metrics/base.py`
- Test: `tests/test_base.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `wptemps.metrics.base.Metrics` — dataclass, tous champs `Optional[float]` défaut `None` :
    `cpu_temp, gpu_temp, cpu_load, ram_used_gb, ram_total_gb, battery_pct, fan_rpm`.
  - `wptemps.metrics.base.format_lines(m: Metrics) -> list[str]`.

- [ ] **Step 1: Créer l'environnement et les dépendances**

Create `requirements.txt`:

```
Pillow==10.4.0
pytest==8.3.2
```

Run:

```bash
/usr/bin/python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
```

Expected: installation sans erreur.

- [ ] **Step 2: Créer les fichiers de package vides**

Create `conftest.py` (vide — met la racine du repo sur `sys.path`):

```python
```

Create `wptemps/__init__.py`:

```python
```

Create `wptemps/metrics/__init__.py`:

```python
```

- [ ] **Step 3: Écrire le test qui échoue**

Create `tests/test_base.py`:

```python
from wptemps.metrics.base import Metrics, format_lines


def test_format_lines_all_values():
    m = Metrics(
        cpu_temp=55.4, gpu_temp=48.5, cpu_load=12.0,
        ram_used_gb=11.2, ram_total_gb=17.2, battery_pct=87.0, fan_rpm=None,
    )
    lines = format_lines(m)
    assert lines[0] == "CPU  55°C  12%"
    assert lines[1] == "GPU  48°C"
    assert lines[2] == "RAM  11.2 / 17.2 GB"
    assert lines[3] == "BAT  87%"
    assert all("FAN" not in l for l in lines)  # pas de ventilo -> ligne omise


def test_format_lines_handles_missing():
    lines = format_lines(Metrics())
    assert lines[0] == "CPU  N/A  N/A"
    assert lines[1] == "GPU  N/A"
    assert lines[2] == "RAM  N/A"
    assert lines[3] == "BAT  N/A"


def test_format_lines_includes_fan_when_present():
    lines = format_lines(Metrics(fan_rpm=2400.0))
    assert any(l == "FAN  2400 rpm" for l in lines)
```

- [ ] **Step 4: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_base.py -v`
Expected: FAIL (`ImportError`/`ModuleNotFoundError: wptemps.metrics.base`).

- [ ] **Step 5: Implémenter le modèle**

Create `wptemps/metrics/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Metrics:
    cpu_temp: Optional[float] = None
    gpu_temp: Optional[float] = None
    cpu_load: Optional[float] = None       # pourcentage 0-100
    ram_used_gb: Optional[float] = None
    ram_total_gb: Optional[float] = None
    battery_pct: Optional[float] = None
    fan_rpm: Optional[float] = None


def _temp(v: Optional[float]) -> str:
    return f"{v:.0f}°C" if v is not None else "N/A"


def _pct(v: Optional[float]) -> str:
    return f"{v:.0f}%" if v is not None else "N/A"


def format_lines(m: Metrics) -> list:
    lines = [
        f"CPU  {_temp(m.cpu_temp)}  {_pct(m.cpu_load)}",
        f"GPU  {_temp(m.gpu_temp)}",
    ]
    if m.ram_used_gb is not None and m.ram_total_gb is not None:
        lines.append(f"RAM  {m.ram_used_gb:.1f} / {m.ram_total_gb:.1f} GB")
    else:
        lines.append("RAM  N/A")
    lines.append(f"BAT  {_pct(m.battery_pct)}")
    if m.fan_rpm is not None:
        lines.append(f"FAN  {m.fan_rpm:.0f} rpm")
    return lines
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_base.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt conftest.py wptemps tests/test_base.py
git commit -m "feat: scaffold projet + modele Metrics et format_lines"
```

---

### Task 2: Parseurs capteurs macOS (purs)

**Files:**
- Create: `wptemps/metrics/macos.py`
- Test: `tests/test_macos_parsers.py`

**Interfaces:**
- Consumes: rien (fonctions pures sur des données déjà extraites).
- Produces :
  - `metrics_from_macmon(sample: dict) -> dict` — clés sous-ensemble des champs `Metrics`.
  - `parse_battery_pct(pmset_output: str) -> Optional[float]`.

- [ ] **Step 1: Écrire le test qui échoue**

Create `tests/test_macos_parsers.py` (le `SAMPLE` est un vrai échantillon `macmon pipe` capté sur la machine cible) :

```python
from wptemps.metrics.macos import metrics_from_macmon, parse_battery_pct

SAMPLE = {
    "cpu_usage_pct": 0.03833765536546707,
    "memory": {"ram_total": 17179869184, "ram_usage": 11243503616,
               "swap_total": 2147483648, "swap_usage": 1085931520},
    "temp": {"cpu_temp_avg": 55.41343688964844, "gpu_temp_avg": 48.45880126953125},
}


def test_metrics_from_macmon_extracts_fields():
    d = metrics_from_macmon(SAMPLE)
    assert d["cpu_temp"] == 55.41343688964844
    assert d["gpu_temp"] == 48.45880126953125
    assert d["cpu_load"] == 3.8          # fraction -> pourcentage, arrondi 1 decimale
    assert d["ram_total_gb"] == 16.0     # 17179869184 / 1024^3
    assert d["ram_used_gb"] == 10.5      # 11243503616 / 1024^3, arrondi


def test_metrics_from_macmon_tolerates_missing_keys():
    d = metrics_from_macmon({})
    assert d["cpu_temp"] is None
    assert d["ram_total_gb"] is None
    assert d["cpu_load"] is None


def test_parse_battery_pct():
    out = (" -InternalBattery-0 (id=12345)\t87%; discharging; 4:32 remaining present: true")
    assert parse_battery_pct(out) == 87.0


def test_parse_battery_pct_absent():
    assert parse_battery_pct("Now drawing from 'AC Power'") is None
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_macos_parsers.py -v`
Expected: FAIL (`ModuleNotFoundError: wptemps.metrics.macos`).

- [ ] **Step 3: Implémenter les parseurs**

Create `wptemps/metrics/macos.py`:

```python
from __future__ import annotations

import re
from typing import Optional

_GB = 1024 ** 3


def _bytes_to_gb(v: Optional[float]) -> Optional[float]:
    return round(v / _GB, 1) if v is not None else None


def _frac_to_pct(v: Optional[float]) -> Optional[float]:
    return round(v * 100, 1) if v is not None else None


def metrics_from_macmon(sample: dict) -> dict:
    temp = sample.get("temp") or {}
    mem = sample.get("memory") or {}
    return {
        "cpu_temp": temp.get("cpu_temp_avg"),
        "gpu_temp": temp.get("gpu_temp_avg"),
        "cpu_load": _frac_to_pct(sample.get("cpu_usage_pct")),
        "ram_used_gb": _bytes_to_gb(mem.get("ram_usage")),
        "ram_total_gb": _bytes_to_gb(mem.get("ram_total")),
    }


def parse_battery_pct(pmset_output: str) -> Optional[float]:
    m = re.search(r"(\d+)%", pmset_output)
    return float(m.group(1)) if m else None
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_macos_parsers.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add wptemps/metrics/macos.py tests/test_macos_parsers.py
git commit -m "feat: parseurs purs macmon + batterie pmset"
```

---

### Task 3: Lecture des mesures (intégration subprocess + dispatcher)

**Files:**
- Modify: `wptemps/metrics/macos.py`
- Modify: `wptemps/metrics/__init__.py`
- Test: `tests/test_read_metrics.py`

**Interfaces:**
- Consumes: `Metrics`, `metrics_from_macmon`, `parse_battery_pct`.
- Produces :
  - `wptemps.metrics.macos.read_metrics(sampler=..., battery_reader=...) -> Metrics`
    — `sampler() -> str` (JSON brut), `battery_reader() -> str` (sortie `pmset`).
    Toute exception d'un lecteur → champs laissés à `None`.
  - `wptemps.metrics.read_metrics() -> Metrics` — ré-export depuis `metrics.macos`.

- [ ] **Step 1: Écrire le test qui échoue**

Create `tests/test_read_metrics.py`:

```python
import json

from wptemps.metrics.macos import read_metrics

SAMPLE_JSON = json.dumps({
    "cpu_usage_pct": 0.05,
    "memory": {"ram_total": 17179869184, "ram_usage": 8589934592},
    "temp": {"cpu_temp_avg": 60.0, "gpu_temp_avg": 50.0},
})
BATT = " -InternalBattery-0 (id=1)\t91%; discharging; 3:00 remaining"


def test_read_metrics_combines_sources():
    m = read_metrics(sampler=lambda: SAMPLE_JSON, battery_reader=lambda: BATT)
    assert m.cpu_temp == 60.0
    assert m.gpu_temp == 50.0
    assert m.cpu_load == 5.0
    assert m.ram_total_gb == 16.0
    assert m.battery_pct == 91.0


def test_read_metrics_survives_sampler_failure():
    def boom():
        raise RuntimeError("macmon absent")
    m = read_metrics(sampler=boom, battery_reader=lambda: BATT)
    assert m.cpu_temp is None          # macmon a echoue -> None
    assert m.battery_pct == 91.0       # batterie toujours lue


def test_read_metrics_survives_battery_failure():
    def boom():
        raise RuntimeError("pmset absent")
    m = read_metrics(sampler=lambda: SAMPLE_JSON, battery_reader=boom)
    assert m.cpu_temp == 60.0
    assert m.battery_pct is None
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_read_metrics.py -v`
Expected: FAIL (`ImportError: cannot import name 'read_metrics'`).

- [ ] **Step 3: Implémenter sampler réel + read_metrics**

Append to `wptemps/metrics/macos.py`:

```python
import json
import subprocess


def _macmon_one_sample() -> str:
    out = subprocess.run(
        ["macmon", "pipe", "-s", "1", "-i", "200"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return out.stdout.strip().splitlines()[-1]


def _pmset_battery() -> str:
    out = subprocess.run(
        ["pmset", "-g", "batt"],
        capture_output=True, text=True, timeout=5, check=True,
    )
    return out.stdout


def read_metrics(sampler=_macmon_one_sample, battery_reader=_pmset_battery) -> "Metrics":
    from .base import Metrics
    fields = {}
    try:
        fields.update(metrics_from_macmon(json.loads(sampler())))
    except Exception:
        pass
    try:
        fields["battery_pct"] = parse_battery_pct(battery_reader())
    except Exception:
        pass
    return Metrics(**fields)
```

Replace the contents of `wptemps/metrics/__init__.py` with:

```python
from .macos import read_metrics

__all__ = ["read_metrics"]
```

- [ ] **Step 4: Lancer les tests unitaires**

Run: `.venv/bin/pytest tests/test_read_metrics.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Vérification réelle sur la machine**

Run:

```bash
.venv/bin/python -c "from wptemps.metrics import read_metrics; print(read_metrics())"
```

Expected: une ligne `Metrics(cpu_temp=..., gpu_temp=..., cpu_load=..., ram_used_gb=..., ram_total_gb=..., battery_pct=..., fan_rpm=None)` avec des valeurs réelles non nulles pour cpu_temp/gpu_temp/ram.

- [ ] **Step 6: Commit**

```bash
git add wptemps/metrics/macos.py wptemps/metrics/__init__.py tests/test_read_metrics.py
git commit -m "feat: read_metrics macOS (macmon + pmset) avec lecteurs injectables"
```

---

### Task 4: Rendu de l'image (`render.py`)

**Files:**
- Create: `wptemps/config.py`
- Create: `wptemps/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Metrics`, `format_lines`.
- Produces :
  - `wptemps.config.Config` — dataclass : `interval_sec=5.0`, `font_path="/System/Library/Fonts/Menlo.ttc"`,
    `font_size=28`, `color=(255,255,255)`, `opacity=190`, `shadow=True`, `position="top-right"`, `margin=40`, `line_spacing=10`.
  - `wptemps.render.render(m: Metrics, base: PIL.Image.Image, cfg: Config) -> PIL.Image.Image`
    — renvoie une **nouvelle** image RGB de **même taille** que `base`, texte incrusté.

- [ ] **Step 1: Écrire le test qui échoue**

Create `tests/test_render.py`:

```python
from PIL import Image

from wptemps.config import Config
from wptemps.metrics.base import Metrics
from wptemps.render import render


def _base():
    return Image.new("RGB", (400, 300), (0, 0, 0))  # fond noir uni


def test_render_preserves_size_and_mode():
    out = render(Metrics(cpu_temp=55.0), _base(), Config())
    assert out.size == (400, 300)
    assert out.mode == "RGB"


def test_render_draws_text_pixels():
    base = _base()
    out = render(Metrics(cpu_temp=55.0, gpu_temp=48.0), base, Config())
    # au moins un pixel non-noir => du texte a ete dessine
    assert any(px != (0, 0, 0) for px in out.getdata())


def test_render_does_not_mutate_base():
    base = _base()
    before = list(base.getdata())
    render(Metrics(cpu_temp=55.0), base, Config())
    assert list(base.getdata()) == before  # base inchangee
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_render.py -v`
Expected: FAIL (`ModuleNotFoundError: wptemps.config`).

- [ ] **Step 3: Implémenter config + rendu**

Create `wptemps/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    interval_sec: float = 5.0
    font_path: str = "/System/Library/Fonts/Menlo.ttc"
    font_size: int = 28
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: int = 190                 # 0-255 ; texte semi-transparent pour se fondre
    shadow: bool = True
    position: str = "top-right"        # top-left | top-right | bottom-left | bottom-right
    margin: int = 40
    line_spacing: int = 10
```

Create `wptemps/render.py`:

```python
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .metrics.base import Metrics, format_lines


def _load_font(cfg: Config) -> "ImageFont.FreeTypeFont":
    try:
        return ImageFont.truetype(cfg.font_path, cfg.font_size)
    except Exception:
        return ImageFont.load_default()


def _text_block_size(draw, lines, font, spacing):
    widths, heights = [], []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    width = max(widths) if widths else 0
    height = sum(heights) + spacing * (len(lines) - 1 if lines else 0)
    return width, height, heights


def _origin(position, img_size, block, margin):
    iw, ih = img_size
    bw, bh = block
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else iw - bw - margin
    y = margin if top else ih - bh - margin
    return x, y


def render(m: Metrics, base: Image.Image, cfg: Config) -> Image.Image:
    img = base.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(cfg)
    lines = format_lines(m)

    bw, bh, heights = _text_block_size(draw, lines, font, cfg.line_spacing)
    x, y = _origin(cfg.position, img.size, (bw, bh), cfg.margin)

    fill = cfg.color + (cfg.opacity,)
    shadow_fill = (0, 0, 0, min(cfg.opacity, 160))
    cy = y
    for line, h in zip(lines, heights):
        if cfg.shadow:
            draw.text((x + 2, cy + 2), line, font=font, fill=shadow_fill)
        draw.text((x, cy), line, font=font, fill=fill)
        cy += h + cfg.line_spacing

    return Image.alpha_composite(img, overlay).convert("RGB")
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_render.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add wptemps/config.py wptemps/render.py tests/test_render.py
git commit -m "feat: rendu image avec texte fondu (Pillow)"
```

---

### Task 5: Wallpaper macOS — lecture/écriture + chargement base

**Files:**
- Create: `wptemps/wallpaper.py`
- Test: `tests/test_wallpaper.py`

**Interfaces:**
- Consumes: rien.
- Produces :
  - `build_set_script(path: str) -> str` — script AppleScript (testé purement).
  - `get_current_wallpaper(run=subprocess.run) -> str` — chemin du wallpaper courant.
  - `set_wallpaper(path: str, run=subprocess.run) -> None`.
  - `load_base_image(path: str) -> PIL.Image.Image` — ouvre le wallpaper ; si format non lu par Pillow (ex. `.heic`), convertit via `sips` en PNG temporaire puis ouvre.

- [ ] **Step 1: Écrire le test qui échoue**

Create `tests/test_wallpaper.py`:

```python
from PIL import Image

from wptemps.wallpaper import build_set_script, get_current_wallpaper, load_base_image


def test_build_set_script_contains_path():
    s = build_set_script("/tmp/wp_a.png")
    assert "/tmp/wp_a.png" in s
    assert "every desktop" in s


def test_get_current_wallpaper_parses_run_output():
    class R:
        stdout = "/Users/me/Pictures/bg.heic\n"
    def fake_run(*a, **k):
        return R()
    assert get_current_wallpaper(run=fake_run) == "/Users/me/Pictures/bg.heic"


def test_load_base_image_reads_png(tmp_path):
    p = tmp_path / "bg.png"
    Image.new("RGB", (50, 40), (10, 20, 30)).save(p)
    img = load_base_image(str(p))
    assert img.size == (50, 40)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_wallpaper.py -v`
Expected: FAIL (`ModuleNotFoundError: wptemps.wallpaper`).

- [ ] **Step 3: Implémenter le module wallpaper**

Create `wptemps/wallpaper.py`:

```python
from __future__ import annotations

import os
import subprocess
import tempfile

from PIL import Image


def build_set_script(path: str) -> str:
    return f'tell application "System Events" to set picture of every desktop to "{path}"'


def get_current_wallpaper(run=subprocess.run) -> str:
    res = run(
        ["osascript", "-e",
         'tell application "System Events" to get picture of current desktop'],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return res.stdout.strip()


def set_wallpaper(path: str, run=subprocess.run) -> None:
    run(["osascript", "-e", build_set_script(path)],
        capture_output=True, text=True, timeout=10, check=True)


def load_base_image(path: str) -> Image.Image:
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        # Pillow ne lit pas le format (ex. .heic) -> conversion via sips macOS
        tmp = os.path.join(tempfile.gettempdir(), "wptemps_base.png")
        subprocess.run(
            ["sips", "-s", "format", "png", path, "--out", tmp],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return Image.open(tmp).convert("RGB")
```

- [ ] **Step 4: Lancer les tests unitaires**

Run: `.venv/bin/pytest tests/test_wallpaper.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Vérification réelle (lecture + conversion HEIC)**

Run:

```bash
.venv/bin/python -c "from wptemps.wallpaper import get_current_wallpaper, load_base_image; p=get_current_wallpaper(); print('wallpaper:', p); img=load_base_image(p); print('taille:', img.size)"
```

Expected: imprime le chemin du wallpaper courant et une taille d'image valide (gère le `.heic` par défaut sans erreur).

- [ ] **Step 6: Commit**

```bash
git add wptemps/wallpaper.py tests/test_wallpaper.py
git commit -m "feat: wallpaper macOS (osascript) + chargement base avec fallback sips/heic"
```

---

### Task 6: Boucle (`Engine` + `main`) avec ping-pong et restauration

**Files:**
- Create: `wptemps/engine.py`
- Create: `wptemps/main.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Config`, `render`, `read_metrics`, `set_wallpaper`, `get_current_wallpaper`, `load_base_image`, `Metrics`.
- Produces :
  - `wptemps.engine.Engine(base, out_dir, cfg, *, read_metrics_fn, render_fn, set_wallpaper_fn)`
    avec `tick() -> str` (chemin écrit) qui **alterne** entre deux fichiers de sortie
    (`wp_a.png`/`wp_b.png`) pour forcer le rafraîchissement du wallpaper macOS.
  - `wptemps.main.main() -> None` — point d'entrée : capture le wallpaper d'origine,
    boucle `tick`+`sleep`, **restaure** l'original à l'arrêt (Ctrl-C).

- [ ] **Step 1: Écrire le test qui échoue**

Create `tests/test_engine.py`:

```python
from PIL import Image

from wptemps.config import Config
from wptemps.engine import Engine
from wptemps.metrics.base import Metrics


def test_tick_alternates_output_paths(tmp_path):
    calls = []
    eng = Engine(
        base=Image.new("RGB", (40, 30), (0, 0, 0)),
        out_dir=str(tmp_path),
        cfg=Config(),
        read_metrics_fn=lambda: Metrics(cpu_temp=55.0),
        render_fn=lambda m, base, cfg: base,         # rendu factice = renvoie base
        set_wallpaper_fn=lambda p: calls.append(p),
    )
    p1 = eng.tick()
    p2 = eng.tick()
    p3 = eng.tick()
    assert p1 != p2          # alternance
    assert p1 == p3          # ping-pong (retour au premier)
    assert calls == [p1, p2, p3]
    import os
    assert os.path.exists(p1) and os.path.exists(p2)  # images ecrites


def test_tick_survives_render_error(tmp_path):
    eng = Engine(
        base=Image.new("RGB", (40, 30), (0, 0, 0)),
        out_dir=str(tmp_path),
        cfg=Config(),
        read_metrics_fn=lambda: (_ for _ in ()).throw(RuntimeError("capteur HS")),
        render_fn=lambda m, base, cfg: base,
        set_wallpaper_fn=lambda p: None,
    )
    # une erreur de lecture ne doit pas remonter : tick renvoie None et n'explose pas
    assert eng.tick() is None
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_engine.py -v`
Expected: FAIL (`ModuleNotFoundError: wptemps.engine`).

- [ ] **Step 3: Implémenter Engine puis main**

Create `wptemps/engine.py`:

```python
from __future__ import annotations

import os


class Engine:
    def __init__(self, base, out_dir, cfg, *, read_metrics_fn, render_fn, set_wallpaper_fn):
        self._base = base
        self._cfg = cfg
        self._read_metrics = read_metrics_fn
        self._render = render_fn
        self._set_wallpaper = set_wallpaper_fn
        self._outs = [os.path.join(out_dir, "wp_a.png"),
                      os.path.join(out_dir, "wp_b.png")]
        self._i = 0

    def tick(self):
        try:
            metrics = self._read_metrics()
            img = self._render(metrics, self._base, self._cfg)
            path = self._outs[self._i]
            img.save(path)
            self._set_wallpaper(path)
            self._i ^= 1
            return path
        except Exception as exc:  # robustesse : une iteration ratee ne tue pas la boucle
            print(f"[wptemps] tick error: {exc}")
            return None
```

Create `wptemps/main.py`:

```python
from __future__ import annotations

import os
import tempfile
import time

from .config import Config
from .engine import Engine
from .metrics import read_metrics
from .render import render
from .wallpaper import get_current_wallpaper, load_base_image, set_wallpaper


def main() -> None:
    cfg = Config()
    original = get_current_wallpaper()
    base = load_base_image(original)
    out_dir = os.path.join(tempfile.gettempdir(), "wptemps")
    os.makedirs(out_dir, exist_ok=True)

    engine = Engine(
        base=base, out_dir=out_dir, cfg=cfg,
        read_metrics_fn=read_metrics,
        render_fn=render,
        set_wallpaper_fn=set_wallpaper,
    )

    print("[wptemps] demarre. Ctrl-C pour arreter et restaurer le fond.")
    try:
        while True:
            engine.tick()
            time.sleep(cfg.interval_sec)
    except KeyboardInterrupt:
        print("\n[wptemps] restauration du wallpaper d'origine...")
        try:
            set_wallpaper(original)
        except Exception as exc:
            print(f"[wptemps] echec restauration: {exc}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer les tests unitaires**

Run: `.venv/bin/pytest tests/test_engine.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (tous les tests verts).

- [ ] **Step 6: Commit**

```bash
git add wptemps/engine.py wptemps/main.py tests/test_engine.py
git commit -m "feat: boucle Engine ping-pong + entree main avec restauration"
```

---

### Task 7: Vérification de bout en bout + README

**Files:**
- Create: `README.md`
- Test: vérification manuelle réelle (pas de test automatisé)

**Interfaces:**
- Consumes: tout le package.
- Produces: programme lançable + documentation d'usage.

- [ ] **Step 1: Lancer le programme réel quelques secondes**

Run:

```bash
.venv/bin/python -m wptemps.main & sleep 16; kill %1; wait 2>/dev/null
```

Expected : pendant l'exécution, le fond d'écran affiche les températures (coin haut-droit) et se met à jour ; à l'arrêt, le wallpaper d'origine est restauré. Vérifier visuellement qu'au moins deux rafraîchissements ont eu lieu (valeurs présentes, lisibles, fondues).

- [ ] **Step 2: Si le texte n'apparaît pas / illisible, ajuster la config**

Diagnostics possibles (n'appliquer que si nécessaire) :
- Texte invisible (wallpaper clair) → augmenter le contraste : `Config(color=(0,0,0))` ou `opacity=230`.
- Wallpaper qui ne change pas → confirmer que `tick()` alterne bien `wp_a.png`/`wp_b.png` (le ping-pong est requis car macOS ignore une ré-définition vers le même chemin).
Documenter le réglage retenu dans le README.

- [ ] **Step 3: Écrire le README**

Create `README.md`:

```markdown
# wptemps — températures du Mac sur le fond d'écran

Affiche les températures CPU/GPU, la charge CPU, la RAM et la batterie,
incrustées dans le fond d'écran macOS, rafraîchies toutes les 5 s.

## Prérequis
- macOS Apple Silicon
- `brew install macmon`
- Python 3.9+

## Installation
```bash
/usr/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Lancer
```bash
.venv/bin/python -m wptemps.main
```
Ctrl-C arrête le programme et restaure le fond d'écran d'origine.

## Configuration
Réglages dans `wptemps/config.py` : intervalle, position, couleur, opacité,
taille de police, ombre.

## Tests
```bash
.venv/bin/pytest -q
```

## Phase 2 (à venir)
Support Windows (Asus) : lecture des températures via LibreHardwareMonitor
et application du wallpaper via l'API Windows.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README + verification end-to-end Phase 1 (Mac)"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec :**
- Lecture capteurs M3 sans sudo (macmon) → Tasks 2-3. ✓
- Charge CPU / RAM / batterie → Tasks 2-3 (+ `pmset`). ✓
- Ventilo absent → `fan_rpm=None`, ligne FAN omise → Task 1. ✓
- Image régénérée = wallpaper + texte → Task 4. ✓
- Texte fondu (semi-transparent + ombre) → Task 4 (`opacity`, `shadow`). ✓
- Jamais écraser l'original / fichiers de sortie dédiés → Tasks 5-6 (ping-pong + `out_dir`). ✓
- Restauration à l'arrêt → Task 6. ✓
- Robustesse (mesure absente → N/A, pas de crash) → Tasks 1, 3, 6. ✓
- Refresh 5 s configurable → Task 4 (`Config.interval_sec`). ✓
- HEIC non lu par Pillow → conversion `sips` → Task 5. ✓
- Découpage interface OS (metrics/wallpaper) prêt pour Phase 2 → structure entière. ✓

**Placeholders :** aucun TODO/TBD ; tout le code est complet.

**Cohérence des types :** `Metrics`, `Config`, `render(m, base, cfg)`, `read_metrics(...)`,
`set_wallpaper(path)`, `Engine(..., read_metrics_fn, render_fn, set_wallpaper_fn).tick()`
utilisés de façon identique entre les tâches.
