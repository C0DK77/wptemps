from __future__ import annotations

import os
import subprocess
import tempfile

from PIL import Image


def build_set_script(path: str) -> str:
    return f'tell application "System Events" to set picture of every desktop to "{path}"'


def get_current_wallpaper(run=subprocess.run) -> str:
    res = run(
        ["osascript", "-e",
         'tell application "System Events" to get picture of current desktop'],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return res.stdout.strip()


def set_wallpaper(path: str, run=subprocess.run) -> None:
    run(["osascript", "-e", build_set_script(path)],
        capture_output=True, text=True, timeout=10, check=True)


def load_base_image(path: str) -> Image.Image:
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        # Pillow ne lit pas le format (ex. .heic) -> conversion via sips macOS
        tmp = os.path.join(tempfile.gettempdir(), "wptemps_base.png")
        subprocess.run(
            ["sips", "-s", "format", "png", path, "--out", tmp],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return Image.open(tmp).convert("RGB")
