from wptemps.metrics.base import Metrics
from wptemps.overlay import compute_origin, overlay_text


def test_overlay_text_joins_lines():
    t = overlay_text(Metrics(cpu_temp=55.0, gpu_temp=48.0))
    assert "CPU  55°C" in t
    assert "GPU  48°C" in t
    assert "\n" in t


def test_compute_origin_top_right():
    # coords Cocoa (origine bas-gauche) : "top" => y haut
    x, y = compute_origin(1000, 800, 200, 100, "top-right", 40)
    assert x == 1000 - 200 - 40
    assert y == 800 - 100 - 40


def test_compute_origin_bottom_left():
    x, y = compute_origin(1000, 800, 200, 100, "bottom-left", 40)
    assert (x, y) == (40, 40)


def test_compute_origin_clamps_negative():
    # fenetre plus grande que l'ecran -> origine clampee a 0
    x, y = compute_origin(100, 80, 200, 100, "top-right", 40)
    assert x == 0
    assert y == 0
