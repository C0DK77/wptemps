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


def _temp(v: Optional[float]) -> str:
    return f"{v:.0f}°C" if v is not None else "N/A"


def _pct(v: Optional[float]) -> str:
    return f"{v:.0f}%" if v is not None else "N/A"


def _watt(v: Optional[float]) -> str:
    return f"  {v:.1f}W" if v is not None else ""


def _freq(mhz: Optional[float]) -> str:
    if mhz is None:
        return ""
    if mhz >= 1000:
        return f"  {mhz / 1000:.1f}GHz"
    return f"  {mhz:.0f}MHz"


def format_lines(m: Metrics, show_power: bool = False, show_details: bool = False) -> list[str]:
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
