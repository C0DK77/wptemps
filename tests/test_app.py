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


def test_config_from_settings_maps_show_flags():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(Settings(show_machine_info=False, show_power=False))
    assert cfg.show_machine_info is False and cfg.show_power is False


def test_config_from_settings_maps_extra_toggles():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    cfg = config_from_settings(
        Settings(show_details=True, show_swap=True, show_uptime=True, show_net=True))
    assert cfg.show_details and cfg.show_swap and cfg.show_uptime and cfg.show_net


def test_config_from_settings_maps_battery():
    from wptemps.app import config_from_settings
    from wptemps.settings import Settings
    assert config_from_settings(Settings(show_battery=False)).show_battery is False


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


def test_toggle_box_frame_updates_controller_and_saves():
    import types
    import wptemps.app as appmod
    from wptemps.settings import Settings

    saved = {}
    calls = []

    class FakeController:
        def set_decorations(self, show_box, show_frame, box_color=None, box_opacity=None):
            calls.append((show_box, show_frame))

    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings()
    app.controller = FakeController()

    original_save = appmod.save
    appmod.save = lambda s: saved.update({"show_box": s.show_box, "show_frame": s.show_frame})
    app._refresh_checks = types.MethodType(lambda self: None, app)

    try:
        app.toggleBox_(None)
        assert app.settings.show_box is True
        assert calls[-1] == (True, False)

        app.toggleFrame_(None)
        assert app.settings.show_frame is True
        assert calls[-1] == (True, True)
        assert saved == {"show_box": True, "show_frame": True}
    finally:
        appmod.save = original_save


def test_change_color_routes_to_box_target():
    import AppKit
    import wptemps.app as appmod
    from wptemps.settings import Settings

    AppKit.NSApplication.sharedApplication()
    calls = []

    class FakeController:
        def set_decorations(self, show_box, show_frame, box_color, box_opacity):
            calls.append((show_box, show_frame, box_color, box_opacity))
        def set_config(self, cfg):
            calls.append(("config", cfg))

    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings(show_box=True, show_frame=False)
    app.controller = FakeController()
    app._color_target = "box"

    # le panneau partage : on lui fixe une couleur connue, changeColor_ la relit
    cp = AppKit.NSColorPanel.sharedColorPanel()
    cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(1.0, 0.0, 0.0, 0.5))

    import types
    original_save = appmod.save
    appmod.save = lambda s: None
    app._refresh_checks = types.MethodType(lambda self: None, app)
    try:
        app.changeColor_(None)
    finally:
        appmod.save = original_save

    assert app.settings.box_color == (255, 0, 0)
    assert app.settings.box_opacity == 128          # round(0.5*255)
    # routé vers set_decorations avec la nouvelle couleur, pas set_config
    assert calls[-1] == (True, False, (255, 0, 0), 128)
    assert all(c[0] != "config" for c in calls)


def test_change_color_text_target_unchanged():
    import AppKit
    import wptemps.app as appmod
    from wptemps.settings import Settings

    AppKit.NSApplication.sharedApplication()
    applied = []

    class FakeController:
        def set_config(self, cfg):
            applied.append(cfg)
        def set_decorations(self, *a):
            applied.append(("deco", a))

    app = appmod.MenuBarApp.alloc().init()
    app.settings = Settings()
    app.controller = FakeController()
    app._color_target = "text"

    cp = AppKit.NSColorPanel.sharedColorPanel()
    cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.0, 1.0, 0.0, 1.0))

    import types
    original_save = appmod.save
    appmod.save = lambda s: None
    app._refresh_checks = types.MethodType(lambda self: None, app)
    try:
        app.changeColor_(None)
    finally:
        appmod.save = original_save

    assert app.settings.color == (0, 255, 0)
    assert app.settings.opacity == 255
    assert applied and not isinstance(applied[-1], tuple)   # set_config appelé (chemin texte)


def test_font_panel_excludes_effect_modes():
    # Regression : changer la taille de police avec un fond colore crashait dans
    # NSFontEffectsBox (_validateFontPanelFontAttributes accedait a une couleur de
    # fond desallouee). On restreint le panneau a face/taille/collection : pas de
    # boite d'effets -> pas de chemin de crash.
    import AppKit
    import wptemps.app as appmod

    AppKit.NSApplication.sharedApplication()
    app = appmod.MenuBarApp.alloc().init()
    mask = app.validModesForFontPanel_(AppKit.NSFontPanel.sharedFontPanel())

    effect_modes = (
        AppKit.NSFontPanelModeMaskTextColorEffect
        | AppKit.NSFontPanelModeMaskDocumentColorEffect
        | AppKit.NSFontPanelModeMaskShadowEffect
        | AppKit.NSFontPanelModeMaskStrikethroughEffect
        | AppKit.NSFontPanelModeMaskUnderlineEffect
    )
    assert mask & AppKit.NSFontPanelModeMaskSize          # la taille reste reglable
    assert mask & effect_modes == 0                        # aucun mode d'effet
