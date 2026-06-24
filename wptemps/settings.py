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
    font_name: str = "Menlo"
    bold: bool = False
    italic: bool = False
    align: str = "left"
    show_machine_info: bool = True
    show_power: bool = True
    show_details: bool = False
    show_swap: bool = False
    show_uptime: bool = False
    show_net: bool = False
    show_battery: bool = True
    show_box: bool = False
    show_frame: bool = False


_ALIGNS = ("left", "center", "right")


def _from_dict(data) -> Settings:
    d = Settings()
    if not isinstance(data, dict):
        return d
    align = data.get("align", d.align)
    if align not in _ALIGNS:
        align = "left"
    return Settings(
        x=data.get("x", d.x),
        y=data.get("y", d.y),
        locked=bool(data.get("locked", d.locked)),
        show=bool(data.get("show", d.show)),
        font_size=int(data.get("font_size", d.font_size)),
        opacity=int(data.get("opacity", d.opacity)),
        color=tuple(data.get("color", d.color)),
        font_name=str(data.get("font_name", d.font_name)),
        bold=bool(data.get("bold", d.bold)),
        italic=bool(data.get("italic", d.italic)),
        show_machine_info=bool(data.get("show_machine_info", d.show_machine_info)),
        show_power=bool(data.get("show_power", d.show_power)),
        show_details=bool(data.get("show_details", d.show_details)),
        show_swap=bool(data.get("show_swap", d.show_swap)),
        show_uptime=bool(data.get("show_uptime", d.show_uptime)),
        show_net=bool(data.get("show_net", d.show_net)),
        show_battery=bool(data.get("show_battery", d.show_battery)),
        show_box=bool(data.get("show_box", d.show_box)),
        show_frame=bool(data.get("show_frame", d.show_frame)),
        align=align,
    )


def _to_dict(s: Settings) -> dict:
    return {
        "x": s.x, "y": s.y, "locked": s.locked, "show": s.show,
        "font_size": s.font_size, "opacity": s.opacity, "color": list(s.color),
        "font_name": s.font_name, "bold": s.bold, "italic": s.italic, "align": s.align,
        "show_machine_info": s.show_machine_info, "show_power": s.show_power,
        "show_details": s.show_details, "show_swap": s.show_swap,
        "show_uptime": s.show_uptime, "show_net": s.show_net,
        "show_battery": s.show_battery, "show_box": s.show_box, "show_frame": s.show_frame,
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
