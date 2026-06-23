"""Overlay macOS : fenetre transparente affichant les temperatures, deplacable.
Verrouille (defaut) : niveau bureau, clic-traversant. Deverrouille : saisissable
au premier plan pour etre deplacee. La fenetre ne modifie jamais le wallpaper."""
from __future__ import annotations

import math
import threading

import AppKit
import objc
import Quartz

from .config import Config
from .extras import NetRateMeter, apply_extras
from .metrics import read_metrics
from .metrics.base import Metrics, format_battery, format_lines

_PAD = 8
_TEXT_SLACK = 6   # marge pour l'inset interne de la cellule de texte (evite le repli)
_UNLOCKED_BG_ALPHA = 0.25


_SEPARATOR = "────────────"


def machine_header_lines(machine):
    lines = []
    if machine is None:
        return lines
    if machine.os_version:
        lines.append(f"macOS {machine.os_version}")
    mc = " · ".join(x for x in (machine.model_name, machine.chip) if x)
    if mc:
        lines.append(mc)
    seg = []
    if machine.cpu_cores:
        if machine.cpu_p and machine.cpu_e:
            seg.append(f"CPU {machine.cpu_cores}c ({machine.cpu_p}P+{machine.cpu_e}E)")
        else:
            seg.append(f"CPU {machine.cpu_cores}c")
    if machine.gpu_cores:
        seg.append(f"GPU {machine.gpu_cores}c")
    if machine.ram_gb:
        seg.append(f"{machine.ram_gb} GB")
    if seg:
        lines.append(" · ".join(seg))
    if machine.disk_total_gb is not None and machine.disk_free_gb is not None:
        lines.append(f"Disk {machine.disk_free_gb:.0f}/{machine.disk_total_gb:.0f} GB free")
    return lines


def format_uptime(seconds):
    if seconds is None:
        return None
    s = int(seconds)
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    mnt = rem // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {mnt}m"
    return f"{mnt}m"


def format_net(down_kbps, up_kbps):
    if down_kbps is None or up_kbps is None:
        return None
    if max(down_kbps, up_kbps) >= 1024:
        return f"↓{down_kbps / 1024:.1f} ↑{up_kbps / 1024:.1f} MB/s"
    return f"↓{down_kbps:.0f} ↑{up_kbps:.0f} KB/s"


def format_swap(used_gb, total_gb):
    if used_gb is None or total_gb is None:
        return None
    return f"{used_gb:.1f} / {total_gb:.1f} GB"


def compose_text(machine, metrics, cfg):
    lines = []
    if cfg.show_machine_info:
        header = machine_header_lines(machine)
        if header:
            lines.extend(header)
            lines.append(_SEPARATOR)
    for line in format_lines(metrics, cfg.show_power, cfg.show_details):
        lines.append(line)
        if cfg.show_swap and line.startswith("RAM"):
            sw = format_swap(metrics.swap_used_gb, metrics.swap_total_gb)
            if sw:
                lines.append(f"SWAP {sw}")
    if cfg.show_battery:
        lines.append(format_battery(metrics.battery_pct))
    if cfg.show_uptime:
        up = format_uptime(metrics.uptime_seconds)
        if up:
            lines.append(f"UP   {up}")
    if cfg.show_net:
        net = format_net(metrics.net_down_kbps, metrics.net_up_kbps)
        if net:
            lines.append(f"NET  {net}")
    return "\n".join(lines)


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


def _alignment_constant(align):
    return {
        "left": AppKit.NSTextAlignmentLeft,
        "center": AppKit.NSTextAlignmentCenter,
        "right": AppKit.NSTextAlignmentRight,
    }.get(align, AppKit.NSTextAlignmentLeft)


def build_font(name, size, bold, italic):
    fm = AppKit.NSFontManager.sharedFontManager()
    font = (AppKit.NSFont.fontWithName_size_(name, size)
            or AppKit.NSFont.monospacedSystemFontOfSize_weight_(
                size, AppKit.NSFontWeightRegular))
    if bold:
        font = fm.convertFont_toHaveTrait_(font, AppKit.NSBoldFontMask)
    if italic:
        font = fm.convertFont_toHaveTrait_(font, AppKit.NSItalicFontMask)
    return font


def _make_paragraph_style(align, line_spacing):
    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(_alignment_constant(align))
    para.setLineSpacing_(line_spacing)
    # clipping : une ligne ne se replie jamais (le defaut wordWrap repliait les
    # lignes calees pile a la largeur de la fenetre).
    para.setLineBreakMode_(AppKit.NSLineBreakByClipping)
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
        self._machine = None
        self._net_meter = NetRateMeter()
        self._last_metrics = None   # dernier echantillon (lu en arriere-plan)
        self._reading = False       # garde anti-lectures concurrentes
        self._top_left = None       # (left, top) coords Cocoa ; None => coin par defaut
        self._locked = True
        self._on_moved_cb = None
        self._desktop_level = Quartz.CGWindowLevelForKey(Quartz.kCGDesktopWindowLevelKey)
        self._build_window()
        self.set_locked(True)
        return self

    def _color(self):
        # sRGB pour correspondre exactement a la couleur choisie dans le selecteur
        # (qui lit/ecrit en sRGB) ; l'espace calibre (gamma 2.2) donnerait un decalage.
        r, g, b = self.cfg.color
        return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
            r / 255.0, g / 255.0, b / 255.0, self.cfg.opacity / 255.0)

    def _attributes(self):
        font = build_font(self.cfg.font_name, self.cfg.font_size,
                          self.cfg.bold, self.cfg.italic)
        shadow = AppKit.NSShadow.alloc().init()
        shadow.setShadowColor_(AppKit.NSColor.blackColor().colorWithAlphaComponent_(0.6))
        shadow.setShadowBlurRadius_(2.0)
        shadow.setShadowOffset_(AppKit.NSMakeSize(1, -1))
        return {
            AppKit.NSFontAttributeName: font,
            AppKit.NSForegroundColorAttributeName: self._color(),
            AppKit.NSShadowAttributeName: shadow,
            AppKit.NSParagraphStyleAttributeName: _make_paragraph_style(
                self.cfg.align, self.cfg.line_spacing),
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
        # pas d'orderFront ici : la fenetre n'est montree qu'apres positionnement
        # (via set_visible), pour eviter un flash au coin par defaut au lancement.
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
        # stocke seulement l'ancre ; le rendu se fait au prochain _update (start()).
        self._top_left = None if (left is None or top is None) else (left, top)

    def set_config(self, cfg):
        # re-rend instantanement depuis le dernier echantillon en cache
        # (aucune lecture capteur ici -> pas de blocage de l'UI au clic menu).
        self.cfg = cfg
        self._render()

    def setMachine_(self, machine):
        self._machine = machine

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

    def _render(self):
        # FIL PRINCIPAL UNIQUEMENT. Compose depuis le dernier echantillon en cache
        # (aucune lecture capteur ici) puis met a jour la fenetre/label.
        m = self._last_metrics
        if m is None:
            return
        text = compose_text(self._machine, m, self.cfg)
        astr = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text, self._attributes())
        size = astr.size()
        w = int(math.ceil(size.width)) + 2 * _PAD + _TEXT_SLACK
        h = int(math.ceil(size.height)) + 2 * _PAD + _TEXT_SLACK
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
        # lance la lecture des capteurs en ARRIERE-PLAN (pas sur le fil de l'UI)
        if self._reading:
            return  # une lecture est deja en cours -> on saute ce tick
        self._reading = True
        threading.Thread(target=self._bg_read, daemon=True).start()

    def _bg_read(self):
        try:
            self._last_metrics = apply_extras(read_metrics(), self._net_meter)
        except Exception as exc:  # robustesse : ne jamais tuer le thread
            print(f"[wptemps] read error: {exc}")
        # repasse sur le fil principal pour dessiner
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            b"_renderMain:", None, False)

    def _renderMain_(self, _arg):
        self._reading = False
        self._render()

    def start(self):
        self.tick_(None)   # premier echantillon en arriere-plan (lancement non bloquant)
        self.timer = (
            AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                self.cfg.interval_sec, self, b"tick:", None, True))


def main() -> None:
    cfg = Config()
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    controller = OverlayController.alloc().initWithConfig_(cfg)
    controller.start()
    controller.set_visible(True)
    print("[wptemps] overlay demarre (mode autonome).")
    app.run()


if __name__ == "__main__":
    main()
