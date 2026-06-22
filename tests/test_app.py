from wptemps.app import AppState, config_from_settings, login_supported
from wptemps.settings import Settings


def _state(settings):
    saved, applied = [], []
    st = AppState(
        settings,
        save_fn=lambda s: saved.append((s.locked, s.show, s.x, s.y)),
        apply_locked=lambda locked: applied.append(("locked", locked)),
        apply_visible=lambda show: applied.append(("show", show)),
    )
    return st, saved, applied


def test_toggle_locked_flips_persists_and_applies():
    st, saved, applied = _state(Settings(locked=True))
    result = st.toggle_locked()
    assert result is False
    assert st.settings.locked is False
    assert ("locked", False) in applied
    assert saved and saved[-1][0] is False


def test_toggle_show_flips_persists_and_applies():
    st, saved, applied = _state(Settings(show=True))
    assert st.toggle_show() is False
    assert ("show", False) in applied
    assert saved[-1][1] is False


def test_record_move_persists_position():
    st, saved, applied = _state(Settings())
    st.record_move(123.0, 456.0)
    assert st.settings.x == 123.0 and st.settings.y == 456.0
    assert saved[-1][2:] == (123.0, 456.0)


def test_config_from_settings_maps_fields():
    cfg = config_from_settings(Settings(font_size=33, opacity=170, color=(1, 2, 3)))
    assert cfg.font_size == 33
    assert cfg.opacity == 170
    assert cfg.color == (1, 2, 3)


def test_login_supported_is_false_from_source():
    # lance depuis les sources (non empaquete) -> non supporte
    assert login_supported() is False


def test_config_from_settings_maps_style_fields():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(
        Settings(font_name="Courier New", bold=True, italic=True, align="right"))
    assert cfg.font_name == "Courier New"
    assert cfg.bold is True and cfg.italic is True
    assert cfg.align == "right"


def test_font_to_fields_extracts_family_size_traits():
    from wptemps.app import font_to_fields
    from wptemps.overlay import build_font
    fields = font_to_fields(build_font("Menlo", 24, bold=True, italic=False))
    assert fields["font_name"] == "Menlo"
    assert fields["font_size"] == 24
    assert fields["bold"] is True
    assert fields["italic"] is False


def test_color_to_fields_extracts_rgb_and_opacity():
    import AppKit
    from wptemps.app import color_to_fields
    col = AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(1.0, 0.0, 0.0, 0.5)
    f = color_to_fields(col)
    assert f["color"] == (255, 0, 0)
    assert f["opacity"] == 128   # round(0.5*255)


def test_apply_style_applies_and_saves():
    from wptemps.app import apply_style
    from wptemps.settings import Settings
    applied, saved = [], []
    s = Settings(font_name="Courier New", align="center")
    apply_style(s, set_config_fn=lambda cfg: applied.append(cfg),
                save_fn=lambda x: saved.append(x))
    assert applied and applied[0].font_name == "Courier New"
    assert applied[0].align == "center"
    assert saved == [s]
