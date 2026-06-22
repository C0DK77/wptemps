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
