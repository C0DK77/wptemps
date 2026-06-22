"""App wptemps : icone de barre de menus pilotant l'overlay deplacable."""
from __future__ import annotations

import AppKit

from . import login
from .config import Config
from .overlay import OverlayController, build_font
from .settings import Settings, load, save
from .sysinfo import machine_info


class AppState:
    """Logique pure des bascules du menu (testable sans Cocoa)."""

    def __init__(self, settings, save_fn, apply_locked, apply_visible):
        self.settings = settings
        self._save = save_fn
        self._apply_locked = apply_locked
        self._apply_visible = apply_visible

    def toggle_locked(self):
        self.settings.locked = not self.settings.locked
        self._apply_locked(self.settings.locked)
        self._save(self.settings)
        return self.settings.locked

    def toggle_show(self):
        self.settings.show = not self.settings.show
        self._apply_visible(self.settings.show)
        self._save(self.settings)
        return self.settings.show

    def record_move(self, left, top):
        self.settings.x = left
        self.settings.y = top
        self._save(self.settings)


def config_from_settings(s: Settings) -> Config:
    return Config(
        font_size=s.font_size, opacity=s.opacity, color=tuple(s.color),
        font_name=s.font_name, bold=s.bold, italic=s.italic, align=s.align,
        show_machine_info=s.show_machine_info, show_power=s.show_power,
    )


def font_to_fields(font) -> dict:
    fm = AppKit.NSFontManager.sharedFontManager()
    tr = fm.traitsOfFont_(font)
    return {
        "font_name": font.familyName(),
        "font_size": int(round(font.pointSize())),
        "bold": bool(tr & AppKit.NSBoldFontMask),
        "italic": bool(tr & AppKit.NSItalicFontMask),
    }


def color_to_fields(color) -> dict:
    c = color.colorUsingColorSpace_(AppKit.NSColorSpace.sRGBColorSpace()) or color
    return {
        "color": (int(round(c.redComponent() * 255)),
                  int(round(c.greenComponent() * 255)),
                  int(round(c.blueComponent() * 255))),
        "opacity": int(round(c.alphaComponent() * 255)),
    }


def apply_style(settings, set_config_fn, save_fn) -> None:
    set_config_fn(config_from_settings(settings))
    save_fn(settings)


def login_supported() -> bool:
    # Le lancement au demarrage via SMAppService ne s'applique qu'a l'app empaquetee.
    return login.available()


def _make_item(menu, target, title, selector):
    item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, selector, "")
    item.setTarget_(target)
    menu.addItem_(item)
    return item


class MenuBarApp(AppKit.NSObject):
    def setup(self):
        self.settings = load()
        cfg = config_from_settings(self.settings)
        self.controller = OverlayController.alloc().initWithConfig_(cfg)

        self.state = AppState(
            self.settings, save_fn=save,
            apply_locked=self.controller.set_locked,
            apply_visible=self.controller.set_visible,
        )
        self.controller.setOnMoved_(self.state.record_move)

        self.controller.setMachine_(machine_info())
        if self.settings.x is not None and self.settings.y is not None:
            self.controller.set_position(self.settings.x, self.settings.y)
        self.controller.set_locked(self.settings.locked)
        self.controller.start()                       # rend une fois a la bonne position
        self.controller.set_visible(self.settings.show)  # puis montre (ou non) sans flash

        # panneaux natifs police/couleur -> callbacks via cible/action
        fm = AppKit.NSFontManager.sharedFontManager()
        fm.setTarget_(self)
        fm.setAction_(b"changeFont:")
        cp = AppKit.NSColorPanel.sharedColorPanel()
        cp.setTarget_(self)
        cp.setAction_(b"changeColor:")
        cp.setShowsAlpha_(True)

        self._build_status_item()
        return self

    def _build_status_item(self):
        bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        button = self.status_item.button()
        img = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "thermometer", None)
        if img is not None:
            button.setImage_(img)
        else:
            button.setTitle_("\U0001F321")

        menu = AppKit.NSMenu.alloc().init()
        self.item_show = _make_item(menu, self, "Afficher les temperatures", b"toggleShow:")
        self.item_lock = _make_item(menu, self, "", b"toggleLock:")
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.item_login = _make_item(menu, self, "Lancer au demarrage", b"toggleLogin:")
        if not login_supported():
            self.item_login.setEnabled_(False)
            self.item_login.setToolTip_("Disponible uniquement dans l'app empaquetee (.app)")
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        _make_item(menu, self, "Police…", b"openFont:")
        _make_item(menu, self, "Couleur…", b"openColor:")
        align_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Alignement", None, "")
        align_menu = AppKit.NSMenu.alloc().init()
        self.align_items = {}
        for key, label in (("left", "Gauche"), ("center", "Centre"), ("right", "Droite")):
            it = _make_item(align_menu, self, label, b"setAlign:")
            it.setRepresentedObject_(key)
            self.align_items[key] = it
        align_item.setSubmenu_(align_menu)
        menu.addItem_(align_item)
        self.item_machine = _make_item(menu, self, "Infos machine", b"toggleMachine:")
        self.item_power = _make_item(menu, self, "Conso (watts)", b"togglePower:")

        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        _make_item(menu, self, "Quitter", b"quit:")
        self.status_item.setMenu_(menu)
        self._refresh_checks()

    def _refresh_checks(self):
        self.item_show.setState_(
            AppKit.NSControlStateValueOn if self.settings.show
            else AppKit.NSControlStateValueOff)
        self.item_lock.setTitle_(
            "Verrouiller la position" if not self.settings.locked
            else "Deverrouiller pour deplacer")
        if login_supported():
            self.item_login.setState_(
                AppKit.NSControlStateValueOn if login.is_enabled()
                else AppKit.NSControlStateValueOff)
        if hasattr(self, "align_items"):
            for key, item in self.align_items.items():
                item.setState_(
                    AppKit.NSControlStateValueOn if self.settings.align == key
                    else AppKit.NSControlStateValueOff)
        if hasattr(self, "item_machine"):
            self.item_machine.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_machine_info
                else AppKit.NSControlStateValueOff)
            self.item_power.setState_(
                AppKit.NSControlStateValueOn if self.settings.show_power
                else AppKit.NSControlStateValueOff)

    def toggleShow_(self, sender):
        self.state.toggle_show()
        self._refresh_checks()

    def toggleLock_(self, sender):
        self.state.toggle_locked()
        self._refresh_checks()

    def toggleLogin_(self, sender):
        login.set_enabled(not login.is_enabled())
        self._refresh_checks()

    def _apply(self):
        apply_style(self.settings,
                    set_config_fn=self.controller.set_config,
                    save_fn=save)
        self._refresh_checks()

    def openFont_(self, sender):
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        fm = AppKit.NSFontManager.sharedFontManager()
        cur = build_font(self.settings.font_name, self.settings.font_size,
                         self.settings.bold, self.settings.italic)
        fm.setSelectedFont_isMultiple_(cur, False)
        fm.orderFrontFontPanel_(self)

    def changeFont_(self, sender):
        fm = AppKit.NSFontManager.sharedFontManager()
        cur = build_font(self.settings.font_name, self.settings.font_size,
                         self.settings.bold, self.settings.italic)
        new = fm.convertFont_(cur)
        f = font_to_fields(new)
        self.settings.font_name = f["font_name"]
        self.settings.font_size = f["font_size"]
        self.settings.bold = f["bold"]
        self.settings.italic = f["italic"]
        self._apply()

    def openColor_(self, sender):
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        cp = AppKit.NSColorPanel.sharedColorPanel()
        r, g, b = self.settings.color
        cp.setColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.settings.opacity / 255.0))
        cp.orderFront_(self)

    def changeColor_(self, sender):
        f = color_to_fields(AppKit.NSColorPanel.sharedColorPanel().color())
        self.settings.color = f["color"]
        self.settings.opacity = f["opacity"]
        self._apply()

    def setAlign_(self, sender):
        self.settings.align = sender.representedObject()
        self._apply()

    def toggleMachine_(self, sender):
        self.settings.show_machine_info = not self.settings.show_machine_info
        self._apply()

    def togglePower_(self, sender):
        self.settings.show_power = not self.settings.show_power
        self._apply()

    def quit_(self, sender):
        AppKit.NSApp.terminate_(self)


def main() -> None:
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    delegate = MenuBarApp.alloc().init().setup()
    app.setDelegate_(delegate)  # retient la reference
    app.run()


if __name__ == "__main__":
    main()
