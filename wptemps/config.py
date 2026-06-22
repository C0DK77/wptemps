from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Config:
    interval_sec: float = 5.0
    font_size: int = 28
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: int = 190                 # 0-255 ; texte semi-transparent pour se fondre
    position: str = "top-right"        # top-left | top-right | bottom-left | bottom-right
    margin: int = 40
    line_spacing: int = 10
    font_name: str = "Menlo"
    bold: bool = False
    italic: bool = False
    align: str = "left"                # left | center | right
    show_machine_info: bool = True
    show_power: bool = True
    show_details: bool = False
    show_swap: bool = False
    show_uptime: bool = False
    show_net: bool = False
    show_battery: bool = True
