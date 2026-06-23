"""Genere l'icone de l'app (wptemps.icns) : carre arrondi degrade + thermometre."""
import os
import subprocess

import AppKit


def _draw(size):
    img = AppKit.NSImage.alloc().initWithSize_(AppKit.NSMakeSize(size, size))
    img.lockFocus()
    s = float(size)

    # fond : carre arrondi avec degrade orange -> rouge
    inset = s * 0.06
    rect = AppKit.NSMakeRect(inset, inset, s - 2 * inset, s - 2 * inset)
    radius = s * 0.22
    bg = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius)
    grad = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(
        AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(1.0, 0.58, 0.18, 1.0),
        AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.86, 0.13, 0.15, 1.0))
    grad.drawInBezierPath_angle_(bg, -90.0)

    # thermometre (blanc) : tige + ampoule + mercure rouge
    cx = s * 0.5
    stem_w = s * 0.12
    bulb_r = s * 0.12
    bulb_cy = s * 0.30
    stem_top = s * 0.74
    AppKit.NSColor.whiteColor().set()
    stem = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        AppKit.NSMakeRect(cx - stem_w / 2, bulb_cy, stem_w, stem_top - bulb_cy),
        stem_w / 2, stem_w / 2)
    stem.fill()
    bulb = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
        AppKit.NSMakeRect(cx - bulb_r, bulb_cy - bulb_r, 2 * bulb_r, 2 * bulb_r))
    bulb.fill()
    # mercure rouge
    AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.86, 0.13, 0.15, 1.0).set()
    inner = stem_w * 0.42
    merc_top = s * 0.62
    AppKit.NSBezierPath.bezierPathWithOvalInRect_(
        AppKit.NSMakeRect(cx - bulb_r * 0.6, bulb_cy - bulb_r * 0.6,
                          1.2 * bulb_r, 1.2 * bulb_r)).fill()
    AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        AppKit.NSMakeRect(cx - inner, bulb_cy, 2 * inner, merc_top - bulb_cy),
        inner, inner).fill()

    img.unlockFocus()
    rep = AppKit.NSBitmapImageRep.alloc().initWithData_(img.TIFFRepresentation())
    png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
    return png


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    iconset = os.path.join(root, "build", "wptemps.iconset")
    os.makedirs(iconset, exist_ok=True)
    specs = [(16, ""), (16, "@2x"), (32, ""), (32, "@2x"),
             (128, ""), (128, "@2x"), (256, ""), (256, "@2x"),
             (512, ""), (512, "@2x")]
    for base, suffix in specs:
        px = base * (2 if suffix == "@2x" else 1)
        png = _draw(px)
        name = f"icon_{base}x{base}{suffix}.png"
        png.writeToFile_atomically_(os.path.join(iconset, name), True)
    out = os.path.join(root, "wptemps.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    print("icone generee ->", out)


if __name__ == "__main__":
    main()
