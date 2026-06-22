"""App wptemps : icone de barre de menus pilotant l'overlay deplacable."""
from __future__ import annotations

import sys

import AppKit

from .config import Config
from .overlay import OverlayController
from .settings import Settings, load, save


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
    return Config(font_size=s.font_size, opacity=s.opacity, color=tuple(s.color))


def login_supported() -> bool:
    # Le lancement au demarrage via SMAppService ne s'applique qu'a l'app empaquetee.
    return bool(getattr(sys, "frozen", False))


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

        if self.settings.x is not None and self.settings.y is not None:
            self.controller.set_position(self.settings.x, self.settings.y)
        self.controller.set_locked(self.settings.locked)
        self.controller.start()                       # rend une fois a la bonne position
        self.controller.set_visible(self.settings.show)  # puis montre (ou non) sans flash

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

    def toggleShow_(self, sender):
        self.state.toggle_show()
        self._refresh_checks()

    def toggleLock_(self, sender):
        self.state.toggle_locked()
        self._refresh_checks()

    def toggleLogin_(self, sender):
        pass  # active en Phase B (app empaquetee)

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
