"""Overlay macOS : une fenetre transparente au niveau du bureau qui affiche
les temperatures par-dessus le wallpaper, sans jamais le modifier."""
from __future__ import annotations

import math

import AppKit
import objc
import Quartz

from .config import Config
from .metrics import read_metrics
from .metrics.base import Metrics, format_lines

_PAD = 8  # marge interne autour du texte (points)


def overlay_text(m: Metrics) -> str:
    return "\n".join(format_lines(m))


def compute_origin(screen_w, screen_h, win_w, win_h, position, margin):
    """Origine (bas-gauche, coords Cocoa) de la fenetre dans le coin demande,
    clampee dans l'ecran."""
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else screen_w - win_w - margin
    y = screen_h - win_h - margin if top else margin
    return max(0, int(x)), max(0, int(y))


def _make_paragraph_style(position, line_spacing):
    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(
        AppKit.NSTextAlignmentRight if position.endswith("right")
        else AppKit.NSTextAlignmentLeft
    )
    para.setLineSpacing_(line_spacing)
    return para


class OverlayController(AppKit.NSObject):
    def initWithConfig_(self, cfg):
        self = objc.super(OverlayController, self).init()
        if self is None:
            return None
        self.cfg = cfg
        self._build_window()
        return self

    def _color(self):
        r, g, b = self.cfg.color
        return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.cfg.opacity / 255.0
        )

    def _attributes(self):
        font = (AppKit.NSFont.fontWithName_size_("Menlo", self.cfg.font_size)
                or AppKit.NSFont.monospacedSystemFontOfSize_weight_(
                    self.cfg.font_size, AppKit.NSFontWeightRegular))
        shadow = AppKit.NSShadow.alloc().init()
        shadow.setShadowColor_(AppKit.NSColor.blackColor().colorWithAlphaComponent_(0.6))
        shadow.setShadowBlurRadius_(2.0)
        shadow.setShadowOffset_(AppKit.NSMakeSize(1, -1))
        return {
            AppKit.NSFontAttributeName: font,
            AppKit.NSForegroundColorAttributeName: self._color(),
            AppKit.NSShadowAttributeName: shadow,
            AppKit.NSParagraphStyleAttributeName: _make_paragraph_style(
                self.cfg.position, self.cfg.line_spacing),
        }

    def _build_window(self):
        rect = AppKit.NSMakeRect(0, 0, 320, 160)
        win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered, False,
        )
        win.setOpaque_(False)
        win.setBackgroundColor_(AppKit.NSColor.clearColor())
        win.setHasShadow_(False)
        win.setIgnoresMouseEvents_(True)
        desktop_level = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
        win.setLevel_(desktop_level + 1)  # au-dessus du wallpaper, derriere icones/fenetres
        win.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
        )
        label = AppKit.NSTextField.alloc().initWithFrame_(rect)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.cell().setWraps_(False)
        win.contentView().addSubview_(label)
        win.orderFront_(None)
        self.window = win
        self.label = label

    def _update(self):
        text = overlay_text(read_metrics())
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text, self._attributes())
        size = astr.size()
        w = int(math.ceil(size.width)) + 2 * _PAD
        h = int(math.ceil(size.height)) + 2 * _PAD
        screen = AppKit.NSScreen.mainScreen().frame()
        x, y = compute_origin(screen.size.width, screen.size.height, w, h,
                              self.cfg.position, self.cfg.margin)
        self.window.setFrame_display_(AppKit.NSMakeRect(x, y, w, h), True)
        self.label.setFrame_(AppKit.NSMakeRect(_PAD, _PAD, w - 2 * _PAD, h - 2 * _PAD))
        self.label.setAttributedStringValue_(astr)

    def tick_(self, timer):
        self._update()

    def start(self):
        self._update()
        self.timer = (
            AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                self.cfg.interval_sec, self, b"tick:", None, True))


def main() -> None:
    cfg = Config()
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    controller = OverlayController.alloc().initWithConfig_(cfg)
    controller.start()
    print("[wptemps] overlay demarre. Ton wallpaper n'est pas modifie. "
          "Ctrl-C / kill pour quitter.")
    app.run()


if __name__ == "__main__":
    main()
