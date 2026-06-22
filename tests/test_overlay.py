import AppKit
import Quartz

from wptemps.metrics.base import Metrics
from wptemps.overlay import compute_origin, lock_params, overlay_text, place_top_left


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


def test_place_top_left_in_bounds():
    # fenetre 200x100, coin haut-gauche (300, 700) sur ecran 1000x800
    x, y = place_top_left(300, 700, 200, 100, 1000, 800)
    assert x == 300
    assert y == 600          # origine bas-gauche = top - h


def test_place_top_left_clamps_offscreen():
    x, y = place_top_left(5000, 5000, 200, 100, 1000, 800)
    assert x == 800          # 1000 - 200
    assert y == 700          # 800 - 100


def test_place_top_left_clamps_negative():
    x, y = place_top_left(-50, 10, 200, 100, 1000, 800)
    assert x == 0
    assert y == 0


def test_lock_params_locked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(True, desktop)
    assert p["level"] == desktop + 1
    assert p["ignores_mouse"] is True
    assert p["draggable"] is False
    assert p["bg_alpha"] == 0.0


def test_lock_params_unlocked():
    desktop = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
    p = lock_params(False, desktop)
    assert p["level"] == AppKit.NSFloatingWindowLevel
    assert p["ignores_mouse"] is False
    assert p["draggable"] is True
    assert p["bg_alpha"] > 0.0


def test_alignment_constant_maps_values():
    from wptemps.overlay import _alignment_constant
    assert _alignment_constant("left") == AppKit.NSTextAlignmentLeft
    assert _alignment_constant("center") == AppKit.NSTextAlignmentCenter
    assert _alignment_constant("right") == AppKit.NSTextAlignmentRight
    assert _alignment_constant("nope") == AppKit.NSTextAlignmentLeft


def test_build_font_applies_traits():
    from wptemps.overlay import build_font
    fm = AppKit.NSFontManager.sharedFontManager()
    f = build_font("Menlo", 20, bold=True, italic=False)
    assert bool(fm.traitsOfFont_(f) & AppKit.NSBoldFontMask)
    assert round(f.pointSize()) == 20


def test_build_font_falls_back_for_unknown_family():
    from wptemps.overlay import build_font
    f = build_font("NoSuchFontFamily__xyz", 18, bold=False, italic=False)
    assert f is not None
    assert round(f.pointSize()) == 18
