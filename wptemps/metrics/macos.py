from __future__ import annotations

import atexit
import json
import os
import re
import subprocess
import sys
import threading
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


class MacmonStream:
    """Un seul `macmon pipe` qui diffuse en continu ; on garde le dernier echantillon.
    Evite de relancer macmon (~1.3 s de demarrage) a chaque lecture."""

    def __init__(self, cmd):
        self._cmd = cmd
        self._proc = None
        self._latest = None

    def start(self, popen=subprocess.Popen):
        self._proc = popen(self._cmd, stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self._loop, args=(self._proc.stdout,), daemon=True).start()
        atexit.register(self.stop)
        return self

    def _loop(self, stream):
        for line in stream:
            line = line.strip()
            if line:
                self._latest = line   # affectation atomique (GIL)

    def latest(self):
        return self._latest

    def alive(self):
        return self._proc is not None and self._proc.poll() is None

    def stop(self):
        try:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass


_stream = None


def stop_macmon_stream():
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream = None


def _macmon_one_sample() -> str:
    global _stream
    if _stream is None or not _stream.alive():
        _stream = MacmonStream([_macmon_path(), "pipe", "-i", "1000"]).start()
    line = _stream.latest()
    if line is not None:
        return line
    # le flux vient de demarrer (pas encore d'echantillon) -> one-shot de secours
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
