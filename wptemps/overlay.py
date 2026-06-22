"""Overlay macOS : fenetre transparente affichant les temperatures, deplacable.
Verrouille (defaut) : niveau bureau, clic-traversant. Deverrouille : saisissable
au premier plan pour etre deplacee. La fenetre ne modifie jamais le wallpaper."""
from __future__ import annotations

import math

import AppKit
import objc
import Quartz

from .config import Config
from .metrics import read_metrics
from .metrics.base import Metrics, format_lines

_PAD = 8
_UNLOCKED_BG_ALPHA = 0.25


def overlay_text(m: Metrics) -> str:
    return "\n".join(format_lines(m))


def compute_origin(screen_w, screen_h, win_w, win_h, position, margin):
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else screen_w - win_w - margin
    y = screen_h - win_h - margin if top else margin
    return max(0, int(x)), max(0, int(y))


def place_top_left(left, top, w, h, screen_w, screen_h):
    """Origine bas-gauche (coords Cocoa) d'une fenetre w x h dont le coin
    haut-gauche est (left, top), clampee pour rester entierement a l'ecran."""
    x = max(0, min(int(left), int(screen_w - w)))
    y = max(0, min(int(top - h), int(screen_h - h)))
    return x, y


def lock_params(locked, desktop_level):
    if locked:
        return {"level": desktop_level + 1, "ignores_mouse": True,
                "draggable": False, "bg_alpha": 0.0}
    return {"level": AppKit.NSFloatingWindowLevel, "ignores_mouse": False,
            "draggable": True, "bg_alpha": _UNLOCKED_BG_ALPHA}


def _make_paragraph_style(position, line_spacing):
    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(AppKit.NSTextAlignmentRight if position.endswith("right")
                       else AppKit.NSTextAlignmentLeft)
    para.setLineSpacing_(line_spacing)
    return para


class DraggableWindow(AppKit.NSWindow):
    def initWithContentRect_styleMask_backing_defer_(self, rect, style, backing, defer):
        self = objc.super(DraggableWindow, self).initWithContentRect_styleMask_backing_defer_(
            rect, style, backing, defer)
        if self is None:
            return None
        self._draggable = False
        self._on_moved = None
        self._drag_offset = None
        return self

    def setDraggable_(self, flag):
        self._draggable = bool(flag)

    def setOnMoved_(self, callback):
        self._on_moved = callback

    def canBecomeKeyWindow(self):
        return True

    def mouseDown_(self, event):
        if self._draggable:
            self._drag_offset = event.locationInWindow()

    def mouseDragged_(self, event):
        if self._draggable and self._drag_offset is not None:
            p = AppKit.NSEvent.mouseLocation()
            self.setFrameOrigin_(AppKit.NSMakePoint(
                p.x - self._drag_offset.x, p.y - self._drag_offset.y))

    def mouseUp_(self, event):
        # ne persister que si un drag a reellement commence (mouseDown recu)
        if self._draggable and self._drag_offset is not None and self._on_moved is not None:
            o = self.frame().origin
            self._on_moved(o.x, o.y)
        self._drag_offset = None


class OverlayController(AppKit.NSObject):
    def initWithConfig_(self, cfg):
        self = objc.super(OverlayController, self).init()
        if self is None:
            return None
        self.cfg = cfg
        self._top_left = None       # (left, top) coords Cocoa ; None => coin par defaut
        self._locked = True
        self._on_moved_cb = None
        self._desktop_level = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
        self._build_window()
        self.set_locked(True)
        return self

    def _color(self):
        r, g, b = self.cfg.color
        return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.cfg.opacity / 255.0)

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
        win = DraggableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, AppKit.NSWindowStyleMaskBorderless, AppKit.NSBackingStoreBuffered, False)
        win.setOpaque_(False)
        win.setBackgroundColor_(AppKit.NSColor.clearColor())
        win.setHasShadow_(False)
        win.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary)
        win.setOnMoved_(self._handle_moved)
        view = win.contentView()
        view.setWantsLayer_(True)
        label = AppKit.NSTextField.alloc().initWithFrame_(rect)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.cell().setWraps_(False)
        view.addSubview_(label)
        win.orderFront_(None)
        self.window = win
        self.label = label

    def setOnMoved_(self, cb):
        self._on_moved_cb = cb

    def _handle_moved(self, origin_x, origin_y):
        h = self.window.frame().size.height
        self._top_left = (origin_x, origin_y + h)
        if self._on_moved_cb is not None:
            self._on_moved_cb(self._top_left[0], self._top_left[1])

    def set_position(self, left, top):
        self._top_left = None if (left is None or top is None) else (left, top)
        self._update()

    def set_visible(self, visible):
        if visible:
            self.window.orderFront_(None)
        else:
            self.window.orderOut_(None)

    def set_locked(self, locked):
        self._locked = bool(locked)
        p = lock_params(self._locked, self._desktop_level)
        self.window.setLevel_(p["level"])
        self.window.setIgnoresMouseEvents_(p["ignores_mouse"])
        self.window.setDraggable_(p["draggable"])
        layer = self.window.contentView().layer()
        layer.setBackgroundColor_(
            AppKit.NSColor.blackColor().colorWithAlphaComponent_(p["bg_alpha"]).CGColor())
        layer.setCornerRadius_(0.0 if self._locked else 6.0)

    def _update(self):
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            overlay_text(read_metrics()), self._attributes())
        size = astr.size()
        w = int(math.ceil(size.width)) + 2 * _PAD
        h = int(math.ceil(size.height)) + 2 * _PAD
        screen = AppKit.NSScreen.mainScreen().frame()
        if self._top_left is None:
            x, y = compute_origin(screen.size.width, screen.size.height, w, h,
                                  self.cfg.position, self.cfg.margin)
            self._top_left = (x, y + h)
        x, y = place_top_left(self._top_left[0], self._top_left[1], w, h,
                              screen.size.width, screen.size.height)
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
    print("[wptemps] overlay demarre (mode autonome).")
    app.run()


if __name__ == "__main__":
    main()
