from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Config:
    interval_sec: float = 5.0
    font_path: str = "/System/Library/Fonts/Menlo.ttc"
    font_size: int = 28
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: int = 190                 # 0-255 ; texte semi-transparent pour se fondre
    shadow: bool = True
    position: str = "top-right"        # top-left | top-right | bottom-left | bottom-right
    margin: int = 40
    line_spacing: int = 10
