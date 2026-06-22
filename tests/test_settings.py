import json

from wptemps.settings import Settings, load, save


def test_save_then_load_roundtrip(tmp_path):
    p = str(tmp_path / "settings.json")
    s = Settings(x=100.0, y=200.0, locked=False, show=True,
                 font_size=30, opacity=180, color=(10, 20, 30))
    save(s, p)
    out = load(p)
    assert out == s


def test_load_missing_file_returns_defaults(tmp_path):
    out = load(str(tmp_path / "absent.json"))
    assert out == Settings()
    assert out.locked is True and out.x is None


def test_load_corrupt_file_returns_defaults(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("ceci n'est pas du json")
    assert load(str(p)) == Settings()


def test_load_ignores_unknown_keys_and_coerces_color(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"x": 5, "color": [1, 2, 3], "inconnu": 42}))
    out = load(str(p))
    assert out.x == 5
    assert out.color == (1, 2, 3)      # liste JSON -> tuple


def test_save_creates_directory(tmp_path):
    p = str(tmp_path / "sub" / "dir" / "settings.json")
    save(Settings(), p)
    assert load(p) == Settings()


def test_new_style_fields_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    s = Settings(font_name="Courier New", bold=True, italic=True, align="center")
    save(s, p)
    out = load(p)
    assert out.font_name == "Courier New"
    assert out.bold is True and out.italic is True
    assert out.align == "center"


def test_align_invalid_normalized_to_left(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"align": "diagonal"}))
    assert load(str(p)).align == "left"


def test_old_settings_without_style_fields_uses_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 10, "y": 20}))   # ancien fichier
    out = load(str(p))
    assert out.font_name == Settings().font_name
    assert out.bold is False and out.align == "left"


def test_show_flags_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    save(Settings(show_machine_info=False, show_power=False), p)
    out = load(p)
    assert out.show_machine_info is False and out.show_power is False


def test_show_flags_default_true_for_old_file(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 1}))
    out = load(str(p))
    assert out.show_machine_info is True and out.show_power is True
