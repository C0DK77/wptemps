from PIL import Image

from wptemps.config import Config
from wptemps.engine import Engine
from wptemps.metrics.base import Metrics


def test_tick_alternates_output_paths(tmp_path):
    calls = []
    eng = Engine(
        base=Image.new("RGB", (40, 30), (0, 0, 0)),
        out_dir=str(tmp_path),
        cfg=Config(),
        read_metrics_fn=lambda: Metrics(cpu_temp=55.0),
        render_fn=lambda m, base, cfg: base,         # rendu factice = renvoie base
        set_wallpaper_fn=lambda p: calls.append(p),
    )
    p1 = eng.tick()
    p2 = eng.tick()
    p3 = eng.tick()
    assert p1 != p2          # alternance
    assert p1 == p3          # ping-pong (retour au premier)
    assert calls == [p1, p2, p3]
    import os
    assert os.path.exists(p1) and os.path.exists(p2)  # images ecrites


def test_tick_survives_render_error(tmp_path):
    eng = Engine(
        base=Image.new("RGB", (40, 30), (0, 0, 0)),
        out_dir=str(tmp_path),
        cfg=Config(),
        read_metrics_fn=lambda: (_ for _ in ()).throw(RuntimeError("capteur HS")),
        render_fn=lambda m, base, cfg: base,
        set_wallpaper_fn=lambda p: None,
    )
    # une erreur de lecture ne doit pas remonter : tick renvoie None et n'explose pas
    assert eng.tick() is None
