from __future__ import annotations

import os
import tempfile
import time

from .config import Config
from .engine import Engine
from .metrics import read_metrics
from .render import render
from .wallpaper import get_current_wallpaper, load_base_image, set_wallpaper


def main() -> None:
    cfg = Config()
    original = get_current_wallpaper()
    base = load_base_image(original)
    out_dir = os.path.join(tempfile.gettempdir(), "wptemps")
    os.makedirs(out_dir, exist_ok=True)

    engine = Engine(
        base=base, out_dir=out_dir, cfg=cfg,
        read_metrics_fn=read_metrics,
        render_fn=render,
        set_wallpaper_fn=set_wallpaper,
    )

    print("[wptemps] demarre. Ctrl-C pour arreter et restaurer le fond.")
    try:
        while True:
            engine.tick()
            time.sleep(cfg.interval_sec)
    except KeyboardInterrupt:
        print("\n[wptemps] restauration du wallpaper d'origine...")
        try:
            set_wallpaper(original)
        except Exception as exc:
            print(f"[wptemps] echec restauration: {exc}")


if __name__ == "__main__":
    main()
