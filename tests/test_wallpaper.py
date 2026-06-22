from PIL import Image

from wptemps.wallpaper import (
    build_set_script,
    get_current_wallpaper,
    load_base_image,
    load_base_or_default,
)


def test_build_set_script_contains_path():
    s = build_set_script("/tmp/wp_a.png")
    assert "/tmp/wp_a.png" in s
    assert "every desktop" in s


def test_get_current_wallpaper_parses_run_output():
    class R:
        stdout = "/Users/me/Pictures/bg.heic\n"
    def fake_run(*a, **k):
        return R()
    assert get_current_wallpaper(run=fake_run) == "/Users/me/Pictures/bg.heic"


def test_load_base_image_reads_png(tmp_path):
    p = tmp_path / "bg.png"
    Image.new("RGB", (50, 40), (10, 20, 30)).save(p)
    img = load_base_image(str(p))
    assert img.size == (50, 40)


def test_load_base_or_default_empty_path_returns_image():
    img = load_base_or_default("")          # wallpaper dynamique -> chemin vide
    assert img.mode == "RGB" and img.size[0] > 0


def test_load_base_or_default_missing_file_returns_image(tmp_path):
    img = load_base_or_default(str(tmp_path / "absent.png"))
    assert img.mode == "RGB" and img.size[0] > 0


def test_load_base_or_default_reads_real_png(tmp_path):
    p = tmp_path / "bg.png"
    Image.new("RGB", (60, 50), (1, 2, 3)).save(p)
    assert load_base_or_default(str(p)).size == (60, 50)
