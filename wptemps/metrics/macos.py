from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Optional

from .base import Metrics

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
        "cpu_power": sample.get("cpu_power"),
        "gpu_power": sample.get("gpu_power"),
    }


def parse_battery_pct(pmset_output: str) -> Optional[float]:
    m = re.search(r"(\d+)%", pmset_output)
    return float(m.group(1)) if m else None


def _macmon_path(frozen=None, executable=None, exists=os.path.exists) -> str:
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = sys.executable if executable is None else executable
    if frozen:
        res = os.path.normpath(
            os.path.join(os.path.dirname(executable), "..", "Resources", "macmon"))
        if exists(res):
            return res
    return "macmon"


def _macmon_one_sample() -> str:
    out = subprocess.run(
        [_macmon_path(), "pipe", "-s", "1", "-i", "200"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return out.stdout.strip().splitlines()[-1]


def _pmset_battery() -> str:
    out = subprocess.run(
        ["pmset", "-g", "batt"],
        capture_output=True, text=True, timeout=5, check=True,
    )
    return out.stdout


def read_metrics(sampler=_macmon_one_sample, battery_reader=_pmset_battery) -> Metrics:
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
