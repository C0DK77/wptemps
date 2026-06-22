from __future__ import annotations

import os


class Engine:
    def __init__(self, base, out_dir, cfg, *, read_metrics_fn, render_fn, set_wallpaper_fn):
        self._base = base
        self._cfg = cfg
        self._read_metrics = read_metrics_fn
        self._render = render_fn
        self._set_wallpaper = set_wallpaper_fn
        self._outs = [os.path.join(out_dir, "wp_a.png"),
                      os.path.join(out_dir, "wp_b.png")]
        self._i = 0

    def tick(self):
        try:
            metrics = self._read_metrics()
            img = self._render(metrics, self._base, self._cfg)
            path = self._outs[self._i]
            img.save(path)
            self._set_wallpaper(path)
            self._i ^= 1
            return path
        except Exception as exc:  # robustesse : une iteration ratee ne tue pas la boucle
            print(f"[wptemps] tick error: {exc}")
            return None
