# wptemps — Mesures supplémentaires Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter (en options de menu, désactivées par défaut) les détails CPU/GPU (% GPU + fréquences), le swap, l'uptime et le débit réseau dans l'overlay.

**Architecture :** macmon (déjà lu) fournit % GPU, fréquences et swap → `metrics_from_macmon`. Un nouveau `extras.py` calcule uptime (`kern.boottime`) et débit réseau (`NetRateMeter` à état, delta `netstat`/temps). `compose_text` prend désormais la `Config` et assemble les lignes selon les `show_*`. L'overlay détient le `NetRateMeter`.

**Tech Stack :** Python 3.9, PyObjC, pytest. Aucune nouvelle dépendance.

## Global Constraints

- macOS Apple Silicon, sans `sudo` ; l'app ne modifie jamais le wallpaper.
- Nouveaux toggles **désactivés par défaut** (`False`) ; ancien `settings.json` → `False`.
- Toute info indisponible → champ `None`, ligne/segment omis, **jamais de crash**.
- 1er échantillon réseau → débit `(0.0, 0.0)` (pas de delta).
- `machine_info()` reste lu **une seule fois** au démarrage.
- Package `wptemps/` ; tests `tests/` ; venv `.venv` ; pytest via `.venv/bin/pytest`.

---

### Task 1: Champs macmon (% GPU, fréquences, swap) + `format_lines(show_details)`

**Files:**
- Modify: `wptemps/metrics/base.py`
- Modify: `wptemps/metrics/macos.py`
- Test: `tests/test_base.py`, `tests/test_macos_parsers.py`

**Interfaces:**
- Produces :
  - `Metrics` gagne : `gpu_load`, `cpu_freq_mhz`, `gpu_freq_mhz`, `swap_used_gb`,
    `swap_total_gb`, `net_down_kbps`, `net_up_kbps`, `uptime_seconds` (tous `Optional[float]`,
    défaut `None`).
  - `format_lines(m, show_power=False, show_details=False)` — `show_details` ajoute `% GPU` et
    les fréquences aux lignes CPU/GPU.
  - `metrics_from_macmon` remplit `gpu_load`/`cpu_freq_mhz`/`gpu_freq_mhz`/`swap_*`.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_base.py`:

```python
def test_format_lines_show_details_adds_gpu_usage_and_freqs():
    m = Metrics(cpu_temp=54.0, cpu_load=8.0, gpu_temp=46.0, gpu_load=1.0,
                cpu_freq_mhz=3400, gpu_freq_mhz=416)
    lines = format_lines(m, show_details=True)
    assert lines[0] == "CPU  54°C  8%  3.4GHz"
    assert lines[1] == "GPU  46°C  1%  416MHz"


def test_format_lines_show_details_with_power_order():
    m = Metrics(cpu_temp=54.0, cpu_load=8.0, gpu_temp=46.0, gpu_load=1.0,
                cpu_power=2.7, gpu_power=0.1, cpu_freq_mhz=3400, gpu_freq_mhz=416)
    lines = format_lines(m, show_power=True, show_details=True)
    assert lines[0] == "CPU  54°C  8%  2.7W  3.4GHz"
    assert lines[1] == "GPU  46°C  1%  0.1W  416MHz"


def test_format_lines_show_details_omits_missing():
    m = Metrics(cpu_temp=54.0, cpu_load=8.0, gpu_temp=46.0)  # pas de freq/usage
    lines = format_lines(m, show_details=True)
    assert lines[0] == "CPU  54°C  8%"
    assert lines[1] == "GPU  46°C"
```

Add to `tests/test_macos_parsers.py`:

```python
def test_metrics_from_macmon_extracts_details_and_swap():
    sample = dict(SAMPLE)
    sample["gpu_usage"] = [416, 0.01]
    sample["pcpu_usage"] = [3400, 0.08]
    sample["memory"] = dict(SAMPLE["memory"])
    sample["memory"]["swap_usage"] = 783351808
    sample["memory"]["swap_total"] = 2147483648
    d = metrics_from_macmon(sample)
    assert d["gpu_freq_mhz"] == 416
    assert d["gpu_load"] == 1.0          # 0.01 * 100
    assert d["cpu_freq_mhz"] == 3400
    assert d["swap_total_gb"] == 2.0     # 2147483648 / 1024^3
    assert round(d["swap_used_gb"], 1) == 0.7
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_base.py tests/test_macos_parsers.py -q`
Expected: FAIL (`TypeError` sur `gpu_load` et clés absentes).

- [ ] **Step 3: Ajouter les champs à `Metrics`**

In `wptemps/metrics/base.py`, extend the dataclass (after `gpu_power`):

```python
    cpu_power: Optional[float] = None
    gpu_power: Optional[float] = None
    gpu_load: Optional[float] = None
    cpu_freq_mhz: Optional[float] = None
    gpu_freq_mhz: Optional[float] = None
    swap_used_gb: Optional[float] = None
    swap_total_gb: Optional[float] = None
    net_down_kbps: Optional[float] = None
    net_up_kbps: Optional[float] = None
    uptime_seconds: Optional[float] = None
```

- [ ] **Step 4: Ajouter `_freq` et étendre `format_lines`**

In `wptemps/metrics/base.py`, add `_freq` next to `_watt`, then replace `format_lines`:

```python
def _freq(mhz: Optional[float]) -> str:
    if mhz is None:
        return ""
    if mhz >= 1000:
        return f"  {mhz / 1000:.1f}GHz"
    return f"  {mhz:.0f}MHz"


def format_lines(m: Metrics, show_power: bool = False, show_details: bool = False) -> list:
    cpu = f"CPU  {_temp(m.cpu_temp)}  {_pct(m.cpu_load)}"
    gpu = f"GPU  {_temp(m.gpu_temp)}"
    if show_details and m.gpu_load is not None:
        gpu += f"  {m.gpu_load:.0f}%"
    if show_power:
        cpu += _watt(m.cpu_power)
        gpu += _watt(m.gpu_power)
    if show_details:
        cpu += _freq(m.cpu_freq_mhz)
        gpu += _freq(m.gpu_freq_mhz)
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

- [ ] **Step 5: Étendre `metrics_from_macmon`**

In `wptemps/metrics/macos.py`, replace `metrics_from_macmon`:

```python
def metrics_from_macmon(sample: dict) -> dict:
    temp = sample.get("temp") or {}
    mem = sample.get("memory") or {}
    gpu = sample.get("gpu_usage") or []
    pcpu = sample.get("pcpu_usage") or []
    return {
        "cpu_temp": temp.get("cpu_temp_avg"),
        "gpu_temp": temp.get("gpu_temp_avg"),
        "cpu_load": _frac_to_pct(sample.get("cpu_usage_pct")),
        "ram_used_gb": _bytes_to_gb(mem.get("ram_usage")),
        "ram_total_gb": _bytes_to_gb(mem.get("ram_total")),
        "cpu_power": sample.get("cpu_power"),
        "gpu_power": sample.get("gpu_power"),
        "gpu_load": round(gpu[1] * 100, 1) if len(gpu) >= 2 else None,
        "gpu_freq_mhz": gpu[0] if len(gpu) >= 1 else None,
        "cpu_freq_mhz": pcpu[0] if len(pcpu) >= 1 else None,
        "swap_used_gb": _bytes_to_gb(mem.get("swap_usage")),
        "swap_total_gb": _bytes_to_gb(mem.get("swap_total")),
    }
```

- [ ] **Step 6: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_base.py tests/test_macos_parsers.py tests/test_read_metrics.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add wptemps/metrics/base.py wptemps/metrics/macos.py tests/test_base.py tests/test_macos_parsers.py
git commit -m "feat: champs macmon (gpu usage/freqs/swap) + format_lines(show_details)"
```

---

### Task 2: `extras.py` (uptime + débit réseau)

**Files:**
- Create: `wptemps/extras.py`
- Test: `tests/test_extras.py`

**Interfaces:**
- Consumes: `Metrics` (mutation des champs `net_*`/`uptime_seconds`).
- Produces :
  - `parse_boottime(s) -> Optional[int]`, `uptime_seconds(boottime_reader, now) -> Optional[float]`.
  - `parse_net_counters(netstat_output) -> (int, int)`.
  - `NetRateMeter` avec `sample(in_bytes, out_bytes, now) -> (float, float)` (KB/s).
  - `apply_extras(m, net_meter, net_reader, uptime_fn, now) -> Metrics`.

- [ ] **Step 1: Écrire les tests qui échouent**

Create `tests/test_extras.py`:

```python
from wptemps.extras import (
    NetRateMeter, apply_extras, parse_boottime, parse_net_counters, uptime_seconds,
)
from wptemps.metrics.base import Metrics

NETSTAT = (
    "Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll\n"
    "lo0   16384 <Link#1>                           100     0       8000      100     0       8000     0\n"
    "en0   1500  <Link#11>     a4:83:e7:00:00:00   2000     0    1000000     1500     0     500000     0\n"
    "en0   1500  192.168.1     mymac               2000     0    1000000     1500     0     500000     0\n"
)


def test_parse_boottime():
    assert parse_boottime("{ sec = 1700000000, usec = 0 } Tue ...") == 1700000000
    assert parse_boottime("rien") is None


def test_uptime_seconds():
    up = uptime_seconds(boottime_reader=lambda: "{ sec = 100, usec = 0 }", now=lambda: 1000.0)
    assert up == 900.0


def test_uptime_seconds_survives_failure():
    def boom():
        raise RuntimeError("sysctl HS")
    assert uptime_seconds(boottime_reader=boom, now=lambda: 1.0) is None


def test_parse_net_counters_sums_link_rows_skips_lo():
    assert parse_net_counters(NETSTAT) == (1000000, 500000)


def test_net_rate_meter_first_sample_is_zero():
    meter = NetRateMeter()
    assert meter.sample(1000, 2000, now=10.0) == (0.0, 0.0)


def test_net_rate_meter_computes_kbps():
    meter = NetRateMeter()
    meter.sample(0, 0, now=0.0)
    # +2048 octets in / +1024 out sur 2 s -> 1.0 / 0.5 KB/s
    down, up = meter.sample(2048, 1024, now=2.0)
    assert round(down, 3) == 1.0
    assert round(up, 3) == 0.5


def test_net_rate_meter_zero_when_no_time_advance():
    meter = NetRateMeter()
    meter.sample(0, 0, now=5.0)
    assert meter.sample(9999, 9999, now=5.0) == (0.0, 0.0)


def test_apply_extras_fills_fields():
    meter = NetRateMeter()
    m = apply_extras(Metrics(), meter,
                     net_reader=lambda: (1000, 2000),
                     uptime_fn=lambda: 3600.0, now=lambda: 0.0)
    assert m.net_down_kbps == 0.0 and m.net_up_kbps == 0.0   # 1er echantillon
    assert m.uptime_seconds == 3600.0


def test_apply_extras_survives_failing_reader():
    def boom():
        raise RuntimeError("netstat HS")
    m = apply_extras(Metrics(), NetRateMeter(),
                     net_reader=boom, uptime_fn=lambda: 5.0, now=lambda: 0.0)
    assert m.net_down_kbps is None     # reseau a echoue
    assert m.uptime_seconds == 5.0     # uptime tient
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_extras.py -q`
Expected: FAIL (`ModuleNotFoundError: wptemps.extras`).

- [ ] **Step 3: Implémenter `extras.py`**

Create `wptemps/extras.py`:

```python
"""Mesures live non-macmon : uptime (kern.boottime) et debit reseau (delta netstat)."""
from __future__ import annotations

import re
import subprocess
import time
from typing import Optional


def parse_boottime(s: str) -> Optional[int]:
    m = re.search(r"sec\s*=\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


def _read_boottime() -> str:
    return subprocess.run(["sysctl", "-n", "kern.boottime"],
                          capture_output=True, text=True, timeout=5, check=True).stdout


def uptime_seconds(boottime_reader=_read_boottime, now=time.time) -> Optional[float]:
    try:
        bt = parse_boottime(boottime_reader())
        if bt is None:
            return None
        return max(0.0, now() - bt)
    except Exception:
        return None


def parse_net_counters(netstat_output: str):
    total_in = total_out = 0
    for line in (netstat_output or "").splitlines():
        c = line.split()
        if len(c) < 10:
            continue
        if not c[2].startswith("<Link"):
            continue
        if c[0].startswith("lo"):
            continue
        try:
            total_in += int(c[6])
            total_out += int(c[9])
        except (ValueError, IndexError):
            continue
    return (total_in, total_out)


def read_net_counters():
    out = subprocess.run(["netstat", "-ib"],
                         capture_output=True, text=True, timeout=5, check=True).stdout
    return parse_net_counters(out)


class NetRateMeter:
    """Calcule le debit (KB/s) a partir du delta de compteurs d'octets entre deux appels."""

    def __init__(self):
        self._prev = None  # (in_bytes, out_bytes, t)

    def sample(self, in_bytes, out_bytes, now):
        if self._prev is None:
            self._prev = (in_bytes, out_bytes, now)
            return (0.0, 0.0)
        pi, po, pt = self._prev
        self._prev = (in_bytes, out_bytes, now)
        dt = now - pt
        if dt <= 0:
            return (0.0, 0.0)
        return ((in_bytes - pi) / dt / 1024.0, (out_bytes - po) / dt / 1024.0)


def apply_extras(m, net_meter, net_reader=read_net_counters,
                 uptime_fn=uptime_seconds, now=time.time):
    try:
        ib, ob = net_reader()
        m.net_down_kbps, m.net_up_kbps = net_meter.sample(ib, ob, now())
    except Exception:
        pass
    try:
        m.uptime_seconds = uptime_fn()
    except Exception:
        pass
    return m
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_extras.py -q`
Expected: PASS (9 tests).

- [ ] **Step 5: Vérification réelle**

Run:

```bash
.venv/bin/python -c "
from wptemps.extras import NetRateMeter, apply_extras
from wptemps.metrics.base import Metrics
mtr = NetRateMeter()
m = apply_extras(Metrics(), mtr)
m = apply_extras(m, mtr)  # 2e echantillon -> debit reel
print('uptime_s:', m.uptime_seconds, '| net down/up KB/s:', m.net_down_kbps, m.net_up_kbps)
"
```

Expected : `uptime_seconds` réaliste (grand nombre) et un débit réseau (≥ 0). Pas d'erreur.

- [ ] **Step 6: Commit**

```bash
git add wptemps/extras.py tests/test_extras.py
git commit -m "feat: extras.py (uptime kern.boottime + debit reseau NetRateMeter)"
```

---

### Task 3: Réglages `show_details/show_swap/show_uptime/show_net`

**Files:**
- Modify: `wptemps/settings.py`
- Modify: `wptemps/config.py`
- Modify: `wptemps/app.py` (`config_from_settings`)
- Test: `tests/test_settings.py`, `tests/test_app.py`

**Interfaces:**
- Produces : `Settings` ET `Config` gagnent `show_details: bool = False`,
  `show_swap: bool = False`, `show_uptime: bool = False`, `show_net: bool = False` ;
  `config_from_settings` les mappe.

- [ ] **Step 1: Écrire les tests qui échouent**

Add to `tests/test_settings.py`:

```python
def test_extra_toggles_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    save(Settings(show_details=True, show_swap=True, show_uptime=True, show_net=True), p)
    out = load(p)
    assert out.show_details and out.show_swap and out.show_uptime and out.show_net


def test_extra_toggles_default_false_for_old_file(tmp_path):
    import json
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 1}))
    out = load(str(p))
    assert out.show_details is False and out.show_swap is False
    assert out.show_uptime is False and out.show_net is False
```

Add to `tests/test_app.py`:

```python
def test_config_from_settings_maps_extra_toggles():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(
        Settings(show_details=True, show_swap=True, show_uptime=True, show_net=True))
    assert cfg.show_details and cfg.show_swap and cfg.show_uptime and cfg.show_net
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: FAIL (`TypeError`/`AttributeError` sur `show_details`).

- [ ] **Step 3: Étendre `Settings`**

In `wptemps/settings.py`, add to the dataclass (after `show_power`):

```python
    show_machine_info: bool = True
    show_power: bool = True
    show_details: bool = False
    show_swap: bool = False
    show_uptime: bool = False
    show_net: bool = False
```

In `_from_dict`, add (next to the existing `show_*` lines):

```python
        show_details=bool(data.get("show_details", d.show_details)),
        show_swap=bool(data.get("show_swap", d.show_swap)),
        show_uptime=bool(data.get("show_uptime", d.show_uptime)),
        show_net=bool(data.get("show_net", d.show_net)),
```

In `_to_dict`, add to the returned dict:

```python
        "show_details": s.show_details, "show_swap": s.show_swap,
        "show_uptime": s.show_uptime, "show_net": s.show_net,
```

- [ ] **Step 4: Étendre `Config`**

In `wptemps/config.py`, add to the dataclass (after `show_power`):

```python
    show_machine_info: bool = True
    show_power: bool = True
    show_details: bool = False
    show_swap: bool = False
    show_uptime: bool = False
    show_net: bool = False
```

- [ ] **Step 5: Étendre `config_from_settings`**

In `wptemps/app.py`, replace `config_from_settings`:

```python
def config_from_settings(s: Settings) -> Config:
    return Config(
        font_size=s.font_size, opacity=s.opacity, color=tuple(s.color),
        font_name=s.font_name, bold=s.bold, italic=s.italic, align=s.align,
        show_machine_info=s.show_machine_info, show_power=s.show_power,
        show_details=s.show_details, show_swap=s.show_swap,
        show_uptime=s.show_uptime, show_net=s.show_net,
    )
```

- [ ] **Step 6: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_settings.py tests/test_app.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add wptemps/settings.py wptemps/config.py wptemps/app.py tests/test_settings.py tests/test_app.py
git commit -m "feat: reglages show_details/show_swap/show_uptime/show_net (defaut False)"
```

---

### Task 4: Formats + `compose_text(machine, metrics, cfg)`

**Files:**
- Modify: `wptemps/overlay.py`
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `Config` (avec tous les `show_*`), `format_lines`, `machine_header_lines`, `Metrics`.
- Produces :
  - `format_uptime(seconds) -> Optional[str]`, `format_net(down_kbps, up_kbps) -> Optional[str]`,
    `format_swap(used_gb, total_gb) -> Optional[str]`.
  - **Nouvelle signature** : `compose_text(machine, metrics, cfg) -> str`.

- [ ] **Step 1: Mettre à jour les tests existants + en écrire de nouveaux**

In `tests/test_overlay.py`, the two existing `compose_text` tests call the OLD signature.
Replace them and add new ones:

```python
def test_compose_text_with_header_and_power():
    from wptemps.overlay import compose_text
    from wptemps.config import Config
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    mi = MachineInfo(os_version="15.6.1")
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=4.2)
    txt = compose_text(mi, m, Config(show_machine_info=True, show_power=True))
    lines = txt.split("\n")
    assert lines[0] == "macOS 15.6.1"
    assert "────────────" in lines
    assert any(l.startswith("CPU  55°C  10%  4.2W") for l in lines)


def test_compose_text_machine_off():
    from wptemps.overlay import compose_text
    from wptemps.config import Config
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    txt = compose_text(MachineInfo(os_version="15.6.1"), Metrics(cpu_temp=55.0),
                       Config(show_machine_info=False, show_power=False))
    assert "macOS" not in txt
    assert txt.split("\n")[0].startswith("CPU")


def test_format_uptime():
    from wptemps.overlay import format_uptime
    assert format_uptime(10 * 86400 + 2 * 3600 + 7 * 60) == "10d 2h"
    assert format_uptime(2 * 3600 + 7 * 60) == "2h 7m"
    assert format_uptime(5 * 60) == "5m"
    assert format_uptime(None) is None


def test_format_net():
    from wptemps.overlay import format_net
    assert format_net(120.0, 30.0) == "↓120 ↑30 KB/s"
    assert format_net(2048.0, 1024.0) == "↓2.0 ↑1.0 MB/s"
    assert format_net(None, 5.0) is None


def test_format_swap():
    from wptemps.overlay import format_swap
    assert format_swap(0.7, 2.0) == "0.7 / 2.0 GB"
    assert format_swap(None, 2.0) is None


def test_compose_text_inserts_swap_uptime_net():
    from wptemps.overlay import compose_text
    from wptemps.config import Config
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, ram_used_gb=9.0, ram_total_gb=16.0,
                swap_used_gb=0.7, swap_total_gb=2.0, uptime_seconds=3600 * 5,
                net_down_kbps=120.0, net_up_kbps=30.0)
    cfg = Config(show_machine_info=False, show_swap=True, show_uptime=True, show_net=True)
    lines = compose_text(MachineInfo(), m, cfg).split("\n")
    assert any(l == "SWAP 0.7 / 2.0 GB" for l in lines)
    assert any(l == "UP   5h 0m" for l in lines)
    assert any(l == "NET  ↓120 ↑30 KB/s" for l in lines)
    # SWAP est juste apres la ligne RAM
    assert lines.index("SWAP 0.7 / 2.0 GB") == lines.index("RAM  9.0 / 16.0 GB") + 1


def test_compose_text_details_on_gpu_line():
    from wptemps.overlay import compose_text
    from wptemps.config import Config
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, gpu_temp=46.0, gpu_load=2.0,
                cpu_freq_mhz=3400, gpu_freq_mhz=416)
    cfg = Config(show_machine_info=False, show_details=True)
    lines = compose_text(MachineInfo(), m, cfg).split("\n")
    assert lines[0] == "CPU  55°C  10%  3.4GHz"
    assert lines[1] == "GPU  46°C  2%  416MHz"
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: FAIL (anciens tests `compose_text` cassés par la nouvelle signature + `format_*`
manquants).

- [ ] **Step 3: Ajouter les formats et réécrire `compose_text`**

In `wptemps/overlay.py`, replace the existing `compose_text` (old signature
`(machine, metrics, show_machine, show_power)`) with the formats + new `compose_text`:

```python
def format_uptime(seconds):
    if seconds is None:
        return None
    s = int(seconds)
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    mnt = rem // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {mnt}m"
    return f"{mnt}m"


def format_net(down_kbps, up_kbps):
    if down_kbps is None or up_kbps is None:
        return None
    if max(down_kbps, up_kbps) >= 1024:
        return f"↓{down_kbps / 1024:.1f} ↑{up_kbps / 1024:.1f} MB/s"
    return f"↓{down_kbps:.0f} ↑{up_kbps:.0f} KB/s"


def format_swap(used_gb, total_gb):
    if used_gb is None or total_gb is None:
        return None
    return f"{used_gb:.1f} / {total_gb:.1f} GB"


def compose_text(machine, metrics, cfg):
    lines = []
    if cfg.show_machine_info:
        header = machine_header_lines(machine)
        if header:
            lines.extend(header)
            lines.append(_SEPARATOR)
    for line in format_lines(metrics, cfg.show_power, cfg.show_details):
        lines.append(line)
        if cfg.show_swap and line.startswith("RAM"):
            sw = format_swap(metrics.swap_used_gb, metrics.swap_total_gb)
            if sw:
                lines.append(f"SWAP {sw}")
    if cfg.show_uptime:
        up = format_uptime(metrics.uptime_seconds)
        if up:
            lines.append(f"UP   {up}")
    if cfg.show_net:
        net = format_net(metrics.net_down_kbps, metrics.net_up_kbps)
        if net:
            lines.append(f"NET  {net}")
    return "\n".join(lines)
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: PASS (anciens mis à jour + nouveaux).

- [ ] **Step 5: Commit**

```bash
git add wptemps/overlay.py tests/test_overlay.py
git commit -m "feat: compose_text(cfg) + formats uptime/net/swap + lignes SWAP/UP/NET"
```

---

### Task 5: Câblage overlay (extras) + menu

**Files:**
- Modify: `wptemps/overlay.py`
- Modify: `wptemps/app.py`
- Test: vérification réelle ; logique déjà couverte par Tasks 1-4.

**Interfaces:**
- Consumes: `NetRateMeter`, `apply_extras`, `compose_text(machine, metrics, cfg)`.
- Produces : `OverlayController` détient un `NetRateMeter` et applique les extras avant
  `compose_text` ; `MenuBarApp` gagne 4 toggles.

- [ ] **Step 1: Overlay — `NetRateMeter` + `apply_extras` + `compose_text(cfg)`**

In `wptemps/overlay.py`, add the import at the top (with the others):

```python
from .extras import NetRateMeter, apply_extras
```

In `OverlayController.initWithConfig_`, create the meter (after `self._machine = None`):

```python
        self._machine = None
        self._net_meter = NetRateMeter()
```

In `_update`, replace the block that builds `text`. It currently reads:

```python
        text = compose_text(self._machine, read_metrics(),
                            self.cfg.show_machine_info, self.cfg.show_power)
```

Replace with:

```python
        m = apply_extras(read_metrics(), self._net_meter)
        text = compose_text(self._machine, m, self.cfg)
```

- [ ] **Step 2: App — 4 toggles**

In `wptemps/app.py`, in `_build_status_item`, add after the `item_power` line:

```python
        self.item_details = _make_item(menu, self, "Détails CPU/GPU", b"toggleDetails:")
        self.item_swap = _make_item(menu, self, "Swap", b"toggleSwap:")
        self.item_uptime = _make_item(menu, self, "Uptime", b"toggleUptime:")
        self.item_net = _make_item(menu, self, "Réseau ↓/↑", b"toggleNet:")
```

Add the action methods to `MenuBarApp` (next to `togglePower_`):

```python
    def toggleDetails_(self, sender):
        self.settings.show_details = not self.settings.show_details
        self._apply()

    def toggleSwap_(self, sender):
        self.settings.show_swap = not self.settings.show_swap
        self._apply()

    def toggleUptime_(self, sender):
        self.settings.show_uptime = not self.settings.show_uptime
        self._apply()

    def toggleNet_(self, sender):
        self.settings.show_net = not self.settings.show_net
        self._apply()
```

In `_refresh_checks`, add (after the machine/power block):

```python
        if hasattr(self, "item_details"):
            for item, flag in ((self.item_details, self.settings.show_details),
                               (self.item_swap, self.settings.show_swap),
                               (self.item_uptime, self.settings.show_uptime),
                               (self.item_net, self.settings.show_net)):
                item.setState_(AppKit.NSControlStateValueOn if flag
                               else AppKit.NSControlStateValueOff)
```

- [ ] **Step 3: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (tous verts).

- [ ] **Step 4: Vérification réelle — texte composé avec toutes les extras**

Run:

```bash
.venv/bin/python - <<'PY'
import AppKit
from wptemps.app import MenuBarApp
from wptemps.config import Config
from wptemps.sysinfo import machine_info
from wptemps.metrics import read_metrics
from wptemps.extras import NetRateMeter, apply_extras
from wptemps.overlay import compose_text
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
d = MenuBarApp.alloc().init().setup()
mtr = NetRateMeter()
m = apply_extras(read_metrics(), mtr); m = apply_extras(read_metrics(), mtr)
cfg = Config(show_machine_info=True, show_power=True, show_details=True,
             show_swap=True, show_uptime=True, show_net=True)
print("---- tout active ----")
print(compose_text(machine_info(), m, cfg))
before = d.settings.show_net
d.toggleNet_(None)
assert d.settings.show_net != before
print("toggle Reseau OK ->", d.settings.show_net)
PY
```

Expected : texte avec en-tête machine + lignes CPU/GPU (freq), SWAP, UP, NET ; le toggle
bascule l'état sans erreur.

- [ ] **Step 5: Remettre les réglages par défaut (la vérif a sauvé via `_apply`)**

Run:

```bash
.venv/bin/python -c "
from wptemps.settings import load, save, Settings
s = load(); d = Settings()
s.show_details, s.show_swap, s.show_uptime, s.show_net = (
    d.show_details, d.show_swap, d.show_uptime, d.show_net)
save(s); print('toggles extras remis par defaut (False)')
"
```

- [ ] **Step 6: Commit**

```bash
git add wptemps/overlay.py wptemps/app.py
git commit -m "feat: overlay applique extras (reseau/uptime) + menu Details/Swap/Uptime/Reseau"
```

---

### Task 6: Vérification de bout en bout + README

**Files:**
- Modify: `README.md`
- Test: vérification manuelle réelle

- [ ] **Step 1: Lancer l'app et vérifier les nouveaux toggles**

Run: `.venv/bin/python -m wptemps.app`
Vérifier : le menu 🌡 contient « Détails CPU/GPU », « Swap », « Uptime », « Réseau ↓/↑ »
(décochés par défaut) ; activer chacun ajoute en direct sa ligne/segment ; les désactiver les
retire. Quitter via le menu.

- [ ] **Step 2: Vérifier la persistance**

Activer les quatre, quitter, relancer : ils doivent rester activés.

```bash
cat ~/Library/Application\ Support/wptemps/settings.json
```

Expected : `show_details`/`show_swap`/`show_uptime`/`show_net` reflètent les choix.

- [ ] **Step 3: Mettre à jour le README**

In `README.md`, in the menu description of `## Lancer (app barre de menus)`, extend the list of
toggles to mention the four new ones. Replace the part listing « Infos machine … Conso (watts) »
so it ends with:

```markdown
**Infos machine**, **Conso (watts)**, **Détails CPU/GPU** (% GPU + fréquences), **Swap**,
**Uptime** et **Réseau ↓/↑** (débit), et de quitter. Tous ces réglages — et la position — sont
mémorisés dans `~/Library/Application Support/wptemps/settings.json`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README — details CPU/GPU, swap, uptime, reseau"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec :**
- Détails CPU/GPU (% GPU + fréquences) → Task 1 (`format_lines(show_details)`,
  `metrics_from_macmon`) + Task 4 (compose). ✓
- Swap → Task 1 (champs/macmon) + Task 4 (`format_swap`, ligne SWAP). ✓
- Uptime → Task 2 (`uptime_seconds`) + Task 4 (`format_uptime`, ligne UP). ✓
- Réseau ↓/↑ → Task 2 (`NetRateMeter`, `parse_net_counters`, `apply_extras`) + Task 4
  (`format_net`) + Task 5 (meter dans l'overlay). ✓
- Toggles défaut `False` + persistance + défauts ancien fichier → Task 3. ✓
- `compose_text(machine, metrics, cfg)` → Task 4. ✓
- 4 toggles menu + ré-application live → Task 5. ✓
- 1er tick réseau = 0, tolérance aux pannes, champs `None` omis → Tasks 2, 4. ✓
- machine_info lu une fois (inchangé) ; wallpaper jamais touché. ✓

**Placeholders :** aucun ; code complet partout.

**Cohérence des types :** `Metrics` (8 champs), `format_lines(m, show_power, show_details)`,
`extras` (`parse_boottime`/`uptime_seconds`/`parse_net_counters`/`NetRateMeter.sample`/
`apply_extras`), `compose_text(machine, metrics, cfg)`, formats
`format_uptime`/`format_net`/`format_swap`, `Settings`/`Config.show_details/show_swap/
show_uptime/show_net`, `config_from_settings` — noms et signatures cohérents entre tâches.
Note : Task 4 change la signature de `compose_text` et met à jour ses tests existants ; Task 5
adapte l'appel dans `_update`.
