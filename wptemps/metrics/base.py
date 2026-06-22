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


def format_lines(m: Metrics) -> list[str]:
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
