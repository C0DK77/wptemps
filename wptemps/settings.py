from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple

APP_SUPPORT = os.path.expanduser("~/Library/Application Support/wptemps")
SETTINGS_PATH = os.path.join(APP_SUPPORT, "settings.json")


@dataclass
class Settings:
    x: Optional[float] = None
    y: Optional[float] = None
    locked: bool = True
    show: bool = True
    font_size: int = 28
    opacity: int = 190
    color: Tuple[int, int, int] = (255, 255, 255)


def _from_dict(data) -> Settings:
    d = Settings()
    if not isinstance(data, dict):
        return d
    return Settings(
        x=data.get("x", d.x),
        y=data.get("y", d.y),
        locked=bool(data.get("locked", d.locked)),
        show=bool(data.get("show", d.show)),
        font_size=int(data.get("font_size", d.font_size)),
        opacity=int(data.get("opacity", d.opacity)),
        color=tuple(data.get("color", d.color)),
    )


def _to_dict(s: Settings) -> dict:
    return {
        "x": s.x, "y": s.y, "locked": s.locked, "show": s.show,
        "font_size": s.font_size, "opacity": s.opacity, "color": list(s.color),
    }


def load(path: str = SETTINGS_PATH) -> Settings:
    try:
        with open(path, "r") as f:
            return _from_dict(json.load(f))
    except Exception:
        return Settings()


def save(s: Settings, path: str = SETTINGS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(_to_dict(s), f, indent=2)
