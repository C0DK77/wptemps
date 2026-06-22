# wptemps — Infos machine + watts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter à l'overlay un en-tête machine statique (OS, modèle, puce, cœurs CPU/GPU, RAM, disque) et la consommation en watts sur les lignes CPU/GPU, tous deux activables depuis le menu.

**Architecture :** Un nouveau module `sysinfo.py` lit les infos machine une fois (macmon `--soc-info` + `sw_vers` + `system_profiler` + `shutil`). `Metrics` gagne les watts. Une fonction pure `compose_text(...)` assemble en-tête + séparateur + lignes live. L'overlay reçoit `machine_info()` une fois et lit deux booléens de `Config` ; le menu les bascule.

**Tech Stack :** Python 3.9, PyObjC (AppKit), pytest. Aucune nouvelle dépendance (stdlib `shutil`).

## Global Constraints

- macOS Apple Silicon, sans `sudo` ; l'app ne modifie jamais le wallpaper.
- Toute info indisponible → champ `None`, ligne/segment omis, **jamais de crash**.
- En-tête machine lu **une fois** au démarrage ; disque idem (espace libre lent).
- Nouveaux réglages persistés ; `settings.json` ancien (sans ces champs) → défauts.
- Unité mémoire/disque affichée : **GB** (cohérent avec les lignes live existantes).
- Package `wptemps/` ; tests `tests/` ; venv `.venv` ; pytest via `.venv/bin/pytest`.

---

### Task 1: Watts dans `Metrics` + `format_lines(show_power)`

**Files:**
- Modify: `wptemps/metrics/base.py`
- Modify: `wptemps/metrics/macos.py`
- Test: `tests/test_base.py`, `tests/test_macos_parsers.py`

**Interfaces:**
- Produces :
  - `Metrics` gagne `cpu_power: Optional[float] = None`, `gpu_power: Optional[float] = None`.
  - `format_lines(m, show_power: bool = False) -> list[str]` — ajoute `  X.XW` aux lignes
    CPU/GPU si `show_power` et watt disponible.
  - `metrics_from_macmon` extrait `cpu_power`/`gpu_power`.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_base.py`:

```python
def test_format_lines_show_power_appends_watts():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, gpu_temp=48.0,
                cpu_power=4.2, gpu_power=0.1)
    lines = format_lines(m, show_power=True)
    assert lines[0] == "CPU  55°C  10%  4.2W"
    assert lines[1] == "GPU  48°C  0.1W"


def test_format_lines_default_has_no_watts():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=4.2)
    assert format_lines(m)[0] == "CPU  55°C  10%"   # defaut inchange


def test_format_lines_show_power_omits_missing_watt():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=None)
    assert format_lines(m, show_power=True)[0] == "CPU  55°C  10%"
```

Add to `tests/test_macos_parsers.py` (the module-level `SAMPLE` already exists; add a test):

```python
def test_metrics_from_macmon_extracts_power():
    sample = dict(SAMPLE)
    sample["cpu_power"] = 4.25
    sample["gpu_power"] = 0.12
    d = metrics_from_macmon(sample)
    assert d["cpu_power"] == 4.25
    assert d["gpu_power"] == 0.12
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_base.py tests/test_macos_parsers.py -q`
Expected: FAIL (`TypeError: __init__() got an unexpected keyword argument 'cpu_power'` et clés
power absentes).

- [ ] **Step 3: Ajouter les champs watts à `Metrics`**

In `wptemps/metrics/base.py`, add to the dataclass (after `fan_rpm`):

```python
    fan_rpm: Optional[float] = None
    cpu_power: Optional[float] = None
    gpu_power: Optional[float] = None
```

- [ ] **Step 4: Étendre `format_lines`**

In `wptemps/metrics/base.py`, replace `format_lines` and add a `_watt` helper before it:

```python
def _watt(v: Optional[float]) -> str:
    return f"  {v:.1f}W" if v is not None else ""


def format_lines(m: Metrics, show_power: bool = False) -> list:
    cpu = f"CPU  {_temp(m.cpu_temp)}  {_pct(m.cpu_load)}"
    gpu = f"GPU  {_temp(m.gpu_temp)}"
    if show_power:
        cpu += _watt(m.cpu_power)
        gpu += _watt(m.gpu_power)
    lines = [cpu, gpu]
    if m.ram_used_gb is not None and m.ram_total_gb is not None:
        lines.append(f"RAM  {m.ram_used_gb:.1f} / {m.ram_total_gb:.1f} GB")
    else:
        lines.append("RAM  N/A")
    lines.append(f"BAT  {_pct(m.battery_pct)}")
    if m.fan_rpm is not None:
        lines.append(f"FAN  {m.fan_rpm:.0f} rpm")
    return lines
```

- [ ] **Step 5: Extraire les watts dans `metrics_from_macmon`**

In `wptemps/metrics/macos.py`, replace `metrics_from_macmon`:

```python
def metrics_from_macmon(sample: dict) -> dict:
    temp = sample.get("temp") or {}
    mem = sample.get("memory") or {}
    return {
        "cpu_temp": temp.get("cpu_temp_avg"),
        "gpu_temp": temp.get("gpu_temp_avg"),
        "cpu_load": _frac_to_pct(sample.get("cpu_usage_pct")),
        "ram_used_gb": _bytes_to_gb(mem.get("ram_usage")),
        "ram_total_gb": _bytes_to_gb(mem.get("ram_total")),
        "cpu_power": sample.get("cpu_power"),
        "gpu_power": sample.get("gpu_power"),
    }
```

- [ ] **Step 6: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_base.py tests/test_macos_parsers.py tests/test_read_metrics.py -q`
Expected: PASS (anciens + nouveaux ; `read_metrics` toujours vert).

- [ ] **Step 7: Commit**

```bash
git add wptemps/metrics/base.py wptemps/metrics/macos.py tests/test_base.py tests/test_macos_parsers.py
git commit -m "feat: watts CPU/GPU dans Metrics + format_lines(show_power)"
```

---

### Task 2: Infos machine (`sysinfo.py`)

**Files:**
- Create: `wptemps/sysinfo.py`
- Test: `tests/test_sysinfo.py`

**Interfaces:**
- Consumes: `wptemps.metrics.macos._macmon_path`.
- Produces :
  - `MachineInfo` dataclass : `os_version, model_name, chip, cpu_cores, cpu_p, cpu_e,
    gpu_cores, ram_gb, disk_total_gb, disk_free_gb` (tous `Optional`).
  - Purs : `parse_soc(soc) -> dict`, `parse_os_version(s) -> Optional[str]`,
    `parse_model_name(s) -> Optional[str]`, `disk_gb(total_bytes, free_bytes) -> (float, float)`.
  - `machine_info(soc_reader=_read_soc, os_reader=_read_os, model_reader=_read_model,
    disk_reader=_read_disk) -> MachineInfo`.

- [ ] **Step 1: Écrire les tests qui échouent**

Create `tests/test_sysinfo.py`:

```python
from wptemps.sysinfo import (
    MachineInfo, disk_gb, machine_info, parse_model_name, parse_os_version, parse_soc,
)

SOC = {"chip_name": "Apple M3", "pcpu_cores": 4, "ecpu_cores": 4,
       "gpu_cores": 8, "memory_gb": 16, "mac_model": "Mac15,12"}
_GB = 1024 ** 3


def test_parse_soc_full():
    d = parse_soc(SOC)
    assert d["chip"] == "Apple M3"
    assert d["cpu_cores"] == 8 and d["cpu_p"] == 4 and d["cpu_e"] == 4
    assert d["gpu_cores"] == 8 and d["ram_gb"] == 16


def test_parse_soc_empty():
    d = parse_soc({})
    assert d["chip"] is None and d["cpu_cores"] is None and d["gpu_cores"] is None


def test_parse_os_version():
    assert parse_os_version("15.6.1\n") == "15.6.1"
    assert parse_os_version("") is None


def test_parse_model_name():
    out = "Hardware:\n\n    Model Name: MacBook Air\n    Model Identifier: Mac15,12\n"
    assert parse_model_name(out) == "MacBook Air"
    assert parse_model_name("rien") is None


def test_disk_gb():
    assert disk_gb(228 * _GB, 24 * _GB) == (228.0, 24.0)


def test_machine_info_assembles_from_readers():
    mi = machine_info(
        soc_reader=lambda: SOC,
        os_reader=lambda: "15.6.1\n",
        model_reader=lambda: "Model Name: MacBook Air\n",
        disk_reader=lambda: (228 * _GB, 24 * _GB),
    )
    assert mi.os_version == "15.6.1"
    assert mi.model_name == "MacBook Air"
    assert mi.chip == "Apple M3" and mi.cpu_cores == 8 and mi.gpu_cores == 8
    assert mi.ram_gb == 16
    assert mi.disk_total_gb == 228.0 and mi.disk_free_gb == 24.0


def test_machine_info_survives_failing_reader():
    def boom():
        raise RuntimeError("macmon HS")
    mi = machine_info(
        soc_reader=boom,
        os_reader=lambda: "15.6.1\n",
        model_reader=lambda: "Model Name: MacBook Air\n",
        disk_reader=lambda: (228 * _GB, 24 * _GB),
    )
    assert mi.chip is None and mi.cpu_cores is None   # soc a echoue
    assert mi.os_version == "15.6.1"                  # le reste tient
    assert mi.model_name == "MacBook Air"
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_sysinfo.py -q`
Expected: FAIL (`ModuleNotFoundError: wptemps.sysinfo`).

- [ ] **Step 3: Implémenter `sysinfo.py`**

Create `wptemps/sysinfo.py`:

```python
"""Infos machine (statiques) : OS, modele, puce, coeurs, RAM, disque. Lues une fois."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from .metrics.macos import _macmon_path

_GB = 1024 ** 3


@dataclass
class MachineInfo:
    os_version: Optional[str] = None
    model_name: Optional[str] = None
    chip: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_p: Optional[int] = None
    cpu_e: Optional[int] = None
    gpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    disk_total_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None


def parse_soc(soc) -> dict:
    soc = soc or {}
    p, e = soc.get("pcpu_cores"), soc.get("ecpu_cores")
    cores = (p + e) if (p is not None and e is not None) else None
    return {
        "chip": soc.get("chip_name"),
        "cpu_cores": cores, "cpu_p": p, "cpu_e": e,
        "gpu_cores": soc.get("gpu_cores"),
        "ram_gb": soc.get("memory_gb"),
    }


def parse_os_version(s: str) -> Optional[str]:
    s = (s or "").strip()
    return s or None


def parse_model_name(s: str) -> Optional[str]:
    m = re.search(r"Model Name:\s*(.+)", s or "")
    return m.group(1).strip() if m else None


def disk_gb(total_bytes, free_bytes):
    return (round(total_bytes / _GB, 1), round(free_bytes / _GB, 1))


def _read_soc():
    out = subprocess.run([_macmon_path(), "pipe", "-s", "1", "--soc-info"],
                         capture_output=True, text=True, timeout=10, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1]).get("soc") or {}


def _read_os():
    return subprocess.run(["sw_vers", "-productVersion"],
                          capture_output=True, text=True, timeout=5, check=True).stdout


def _read_model():
    return subprocess.run(["system_profiler", "SPHardwareDataType"],
                          capture_output=True, text=True, timeout=15, check=True).stdout


def _read_disk():
    u = shutil.disk_usage("/")
    return (u.total, u.free)


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def machine_info(soc_reader=_read_soc, os_reader=_read_os,
                 model_reader=_read_model, disk_reader=_read_disk) -> MachineInfo:
    soc = _safe(soc_reader, {}) or {}
    fields = parse_soc(soc)
    os_v = parse_os_version(_safe(os_reader, ""))
    model = parse_model_name(_safe(model_reader, "")) or soc.get("mac_model")
    disk = _safe(disk_reader, None)
    dt, df = disk_gb(*disk) if disk else (None, None)
    return MachineInfo(os_version=os_v, model_name=model,
                       disk_total_gb=dt, disk_free_gb=df, **fields)
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_sysinfo.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Vérification réelle sur la machine**

Run: `.venv/bin/python -c "from wptemps.sysinfo import machine_info; print(machine_info())"`
Expected : un `MachineInfo` avec valeurs réelles (os_version `15.6.1`, model_name `MacBook Air`,
chip `Apple M3`, cpu_cores 8, gpu_cores 8, ram_gb 16, disk renseigné).

- [ ] **Step 6: Commit**

```bash
git add wptemps/sysinfo.py tests/test_sysinfo.py
git commit -m "feat: sysinfo.py (infos machine OS/modele/puce/coeurs/RAM/disque)"
```

---

### Task 3: Composition du texte (`compose_text` + en-tête)

**Files:**
- Modify: `wptemps/overlay.py`
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `MachineInfo`, `format_lines`.
- Produces :
  - `wptemps.overlay.machine_header_lines(machine) -> list[str]` (omet les champs `None`).
  - `wptemps.overlay.compose_text(machine, metrics, show_machine, show_power) -> str`.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_overlay.py`:

```python
def test_machine_header_lines_full():
    from wptemps.overlay import machine_header_lines
    from wptemps.sysinfo import MachineInfo
    mi = MachineInfo(os_version="15.6.1", model_name="MacBook Air", chip="Apple M3",
                     cpu_cores=8, cpu_p=4, cpu_e=4, gpu_cores=8, ram_gb=16,
                     disk_total_gb=228.0, disk_free_gb=24.0)
    lines = machine_header_lines(mi)
    assert lines[0] == "macOS 15.6.1"
    assert lines[1] == "MacBook Air · Apple M3"
    assert lines[2] == "CPU 8c (4P+4E) · GPU 8c · 16 GB"
    assert lines[3] == "Disk 24/228 GB free"


def test_machine_header_lines_omits_missing():
    from wptemps.overlay import machine_header_lines
    from wptemps.sysinfo import MachineInfo
    lines = machine_header_lines(MachineInfo(os_version="15.6.1"))
    assert lines == ["macOS 15.6.1"]   # le reste omis


def test_compose_text_with_header_and_power():
    from wptemps.overlay import compose_text
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    mi = MachineInfo(os_version="15.6.1")
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=4.2)
    txt = compose_text(mi, m, show_machine=True, show_power=True)
    lines = txt.split("\n")
    assert lines[0] == "macOS 15.6.1"
    assert "────────────" in lines
    assert any(l.startswith("CPU  55°C  10%  4.2W") for l in lines)


def test_compose_text_machine_off():
    from wptemps.overlay import compose_text
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    txt = compose_text(MachineInfo(os_version="15.6.1"), Metrics(cpu_temp=55.0),
                       show_machine=False, show_power=False)
    assert "macOS" not in txt
    assert "────────────" not in txt
    assert txt.split("\n")[0].startswith("CPU")
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: FAIL (`ImportError: cannot import name 'machine_header_lines'`).

- [ ] **Step 3: Implémenter `machine_header_lines` et `compose_text`**

In `wptemps/overlay.py`, add (just after the existing `overlay_text` function):

```python
_SEPARATOR = "────────────"


def machine_header_lines(machine):
    lines = []
    if machine is None:
        return lines
    if machine.os_version:
        lines.append(f"macOS {machine.os_version}")
    mc = " · ".join(x for x in (machine.model_name, machine.chip) if x)
    if mc:
        lines.append(mc)
    seg = []
    if machine.cpu_cores:
        if machine.cpu_p and machine.cpu_e:
            seg.append(f"CPU {machine.cpu_cores}c ({machine.cpu_p}P+{machine.cpu_e}E)")
        else:
            seg.append(f"CPU {machine.cpu_cores}c")
    if machine.gpu_cores:
        seg.append(f"GPU {machine.gpu_cores}c")
    if machine.ram_gb:
        seg.append(f"{machine.ram_gb} GB")
    if seg:
        lines.append(" · ".join(seg))
    if machine.disk_total_gb is not None and machine.disk_free_gb is not None:
        lines.append(f"Disk {machine.disk_free_gb:.0f}/{machine.disk_total_gb:.0f} GB free")
    return lines


def compose_text(machine, metrics, show_machine, show_power):
    lines = []
    if show_machine:
        header = machine_header_lines(machine)
        if header:
            lines.extend(header)
            lines.append(_SEPARATOR)
    lines.extend(format_lines(metrics, show_power))
    return "\n".join(lines)
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: PASS (anciens + 4 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat: compose_text + en-tete machine (machine_header_lines)"
```

---

### Task 4: Champs `show_machine_info` / `show_power` (Settings/Config)

**Files:**
- Modify: `wptemps/settings.py`
- Modify: `wptemps/config.py`
- Modify: `wptemps/app.py` (`config_from_settings`)
- Test: `tests/test_settings.py`, `tests/test_app.py`

**Interfaces:**
- Produces : `Settings` et `Config` gagnent `show_machine_info: bool = True`,
  `show_power: bool = True` ; `config_from_settings` les mappe.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_settings.py`:

```python
def test_show_flags_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    save(Settings(show_machine_info=False, show_power=False), p)
    out = load(p)
    assert out.show_machine_info is False and out.show_power is False


def test_show_flags_default_true_for_old_file(tmp_path):
    import json
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 1}))
    out = load(str(p))
    assert out.show_machine_info is True and out.show_power is True
```

Add to `tests/test_app.py`:

```python
def test_config_from_settings_maps_show_flags():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(Settings(show_machine_info=False, show_power=False))
    assert cfg.show_machine_info is False and cfg.show_power is False
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: FAIL (`TypeError`/`AttributeError` sur `show_machine_info`).

- [ ] **Step 3: Étendre `Settings`**

In `wptemps/settings.py`, add to the dataclass (after `align`):

```python
    align: str = "left"
    show_machine_info: bool = True
    show_power: bool = True
```

In `_from_dict`, add (before `align=align,`):

```python
        show_machine_info=bool(data.get("show_machine_info", d.show_machine_info)),
        show_power=bool(data.get("show_power", d.show_power)),
```

In `_to_dict`, add to the returned dict:

```python
        "show_machine_info": s.show_machine_info, "show_power": s.show_power,
```

- [ ] **Step 4: Étendre `Config`**

In `wptemps/config.py`, add to the dataclass (after `align`):

```python
    align: str = "left"                # left | center | right
    show_machine_info: bool = True
    show_power: bool = True
```

- [ ] **Step 5: Étendre `config_from_settings`**

In `wptemps/app.py`, replace `config_from_settings`:

```python
def config_from_settings(s: Settings) -> Config:
    return Config(
        font_size=s.font_size, opacity=s.opacity, color=tuple(s.color),
        font_name=s.font_name, bold=s.bold, italic=s.italic, align=s.align,
        show_machine_info=s.show_machine_info, show_power=s.show_power,
    )
```

- [ ] **Step 6: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add wptemps/settings.py wptemps/config.py wptemps/app.py tests/test_settings.py tests/test_app.py
git commit -m "feat: reglages show_machine_info / show_power (Settings/Config)"
```

---

### Task 5: Câblage overlay + menu

**Files:**
- Modify: `wptemps/overlay.py`
- Modify: `wptemps/app.py`
- Test: vérification réelle (le câblage Cocoa) ; logique déjà couverte par Tasks 1-4.

**Interfaces:**
- Consumes: `compose_text`, `machine_info`, `Config.show_machine_info`/`show_power`.
- Produces :
  - `OverlayController.setMachine_(machine)` ; `_update` utilise `compose_text(...)`.
  - `MenuBarApp` : items « Infos machine » (`toggleMachine:`) et « Conso (watts) »
    (`togglePower:`), cochés selon l'état.

- [ ] **Step 1: Overlay — stocker `machine` et composer le texte**

In `wptemps/overlay.py`, in `OverlayController.initWithConfig_`, add the machine attribute
(after `self.cfg = cfg`):

```python
        self.cfg = cfg
        self._machine = None
```

Add the setter (just after `set_config`):

```python
    def setMachine_(self, machine):
        self._machine = machine
```

In `_update`, replace the first line that builds the attributed string. It currently reads:

```python
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            overlay_text(read_metrics()), self._attributes())
```

Replace the string argument with `compose_text(...)`:

```python
        text = compose_text(self._machine, read_metrics(),
                            self.cfg.show_machine_info, self.cfg.show_power)
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text, self._attributes())
```

- [ ] **Step 2: App — passer `machine_info()` et ajouter les toggles**

In `wptemps/app.py`, add the import:

```python
from .sysinfo import machine_info
```

In `setup`, after the controller is created and before `self.controller.start()`, give it the
machine info:

```python
        self.controller.setMachine_(machine_info())
```

In `_build_status_item`, add two checkboxes in the same separator group as Police/Couleur
(just after the `align_item` block, before the `separatorItem` that precedes Quitter):

```python
        self.item_machine = _make_item(menu, self, "Infos machine", b"toggleMachine:")
        self.item_power = _make_item(menu, self, "Conso (watts)", b"togglePower:")
```

Add the action methods to `MenuBarApp` (next to `setAlign_`):

```python
    def toggleMachine_(self, sender):
        self.settings.show_machine_info = not self.settings.show_machine_info
        self._apply()

    def togglePower_(self, sender):
        self.settings.show_power = not self.settings.show_power
        self._apply()
```

In `_refresh_checks`, add (after the alignment loop):

```python
        if hasattr(self, "item_machine"):
            self.item_machine.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_machine_info
                else AppKit.NSControlStateValueOff)
            self.item_power.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_power
                else AppKit.NSControlStateValueOff)
```

- [ ] **Step 3: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (tous verts).

- [ ] **Step 4: Vérification réelle — texte composé avec en-tête machine**

Run:

```bash
.venv/bin/python - <<'PY'
import AppKit
from wptemps.app import MenuBarApp
from wptemps.sysinfo import machine_info
from wptemps.metrics import read_metrics
from wptemps.overlay import compose_text
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
d = MenuBarApp.alloc().init().setup()
print("---- texte compose (infos machine + watts) ----")
print(compose_text(machine_info(), read_metrics(), True, True))
# verifier que les toggles basculent l'etat
before = d.settings.show_machine_info
d.toggleMachine_(None)
assert d.settings.show_machine_info != before
print("toggle Infos machine OK ->", d.settings.show_machine_info)
PY
```

Expected : le texte imprimé montre l'en-tête (macOS / modèle · puce / cœurs · RAM / disque), un
séparateur, puis les lignes live avec watts ; le toggle bascule l'état sans erreur.

- [ ] **Step 5: Remettre les réglages par défaut (la vérif a sauvé via `_apply`)**

Run:

```bash
.venv/bin/python -c "
from wptemps.settings import load, save, Settings
s = load(); d = Settings()
s.show_machine_info, s.show_power = d.show_machine_info, d.show_power
save(s)
print('reglages show_* remis par defaut (position/style preserves)')
"
```

- [ ] **Step 6: Commit**

```bash
git add wptemps/overlay.py wptemps/app.py
git commit -m "feat: overlay compose en-tete machine + menu Infos machine / Conso (watts)"
```

---

### Task 6: Vérification de bout en bout + README

**Files:**
- Modify: `README.md`
- Test: vérification manuelle réelle

- [ ] **Step 1: Lancer l'app et vérifier visuellement**

Run: `.venv/bin/python -m wptemps.app`
Vérifier : le menu 🌡 contient « Infos machine » et « Conso (watts) » (cochés) ; l'overlay
affiche l'en-tête machine + les watts ; décocher « Infos machine » retire l'en-tête en direct ;
décocher « Conso (watts) » retire les watts. Quitter via le menu.

- [ ] **Step 2: Vérifier la persistance**

Décocher les deux, quitter, relancer : ils doivent rester décochés (et l'overlay sans en-tête /
sans watts).

```bash
cat ~/Library/Application\ Support/wptemps/settings.json
```

Expected : `show_machine_info` et `show_power` reflètent les choix.

- [ ] **Step 3: Mettre à jour le README**

In `README.md`, in the `## Lancer (app barre de menus)` section, extend the menu description to
mention the two new toggles. Replace the menu-actions sentence's end so it includes:

```markdown
… **Alignement** (gauche/centre/droite), **Infos machine** (en-tête OS / modèle / puce /
cœurs / RAM / disque) et **Conso (watts)** (puissance CPU/GPU), et de quitter. Tous ces
réglages — et la position — sont mémorisés dans `~/Library/Application Support/wptemps/settings.json`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README — infos machine et consommation (watts)"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec :**
- En-tête machine (OS/modèle/puce/cœurs/RAM/disque) → Task 2 (`sysinfo`) + Task 3
  (`machine_header_lines`). ✓
- Watts CPU/GPU → Task 1 (`Metrics`, `format_lines(show_power)`, `metrics_from_macmon`). ✓
- Composition avec sections on/off → Task 3 (`compose_text`). ✓
- Réglages persistés + défauts pour ancien fichier → Task 4. ✓
- Overlay reçoit machine une fois + lit les booléens de Config → Task 5. ✓
- Menu 2 toggles cochés par défaut → Task 5. ✓
- Lecture unique des infos machine/disque → Task 5 (`setMachine_(machine_info())` au démarrage). ✓
- Tout `None` → omis, jamais de crash → Tasks 2-3 (`_safe`, omission des champs). ✓
- Pas de modification du wallpaper → aucune dépendance wallpaper. ✓

**Placeholders :** aucun ; code complet partout.

**Cohérence des types :** `Metrics.cpu_power/gpu_power`, `format_lines(m, show_power)`,
`MachineInfo`, `machine_info(...)`, `machine_header_lines`/`compose_text`,
`Settings/Config.show_machine_info/show_power`, `config_from_settings`,
`OverlayController.setMachine_` — noms et signatures cohérents entre tâches. Unité « GB »
uniforme (en-tête + lignes live existantes).
