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
