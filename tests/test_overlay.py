import AppKit
import Quartz

from wptemps.overlay import compute_origin, lock_params, place_top_left


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


def test_machine_header_lines_full():
    from wptemps.overlay import machine_header_lines
    from wptemps.sysinfo import MachineInfo
    mi = MachineInfo(os_version="15.6.1", model_name="MacBook Air", chip="Apple M3",
                     cpu_cores=8, cpu_p=4, cpu_e=4, gpu_cores=8, ram_gb=16,
                     disk_total_gb=228.0, disk_free_gb=24.0)
    lines = machine_header_lines(mi)
    assert lines[0] == "macOS 15.6.1"
    assert lines[1] == "MacBook Air · Apple M3"
    assert lines[2] == "CPU 8c (4P+4E) · GPU 8c · 16 GB"
    assert lines[3] == "Disk 24/228 GB free"


def test_machine_header_lines_omits_missing():
    from wptemps.overlay import machine_header_lines
    from wptemps.sysinfo import MachineInfo
    lines = machine_header_lines(MachineInfo(os_version="15.6.1"))
    assert lines == ["macOS 15.6.1"]   # le reste omis


def test_compose_text_with_header_and_power():
    from wptemps.overlay import compose_text
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    mi = MachineInfo(os_version="15.6.1")
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=4.2)
    txt = compose_text(mi, m, show_machine=True, show_power=True)
    lines = txt.split("\n")
    assert lines[0] == "macOS 15.6.1"
    assert "────────────" in lines
    assert any(l.startswith("CPU  55°C  10%  4.2W") for l in lines)


def test_compose_text_machine_off():
    from wptemps.overlay import compose_text
    from wptemps.metrics.base import Metrics
    from wptemps.sysinfo import MachineInfo
    txt = compose_text(MachineInfo(os_version="15.6.1"), Metrics(cpu_temp=55.0),
                       show_machine=False, show_power=False)
    assert "macOS" not in txt
    assert "────────────" not in txt
    assert txt.split("\n")[0].startswith("CPU")
