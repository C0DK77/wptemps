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
