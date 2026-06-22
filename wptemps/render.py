from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .metrics.base import Metrics, format_lines


def _load_font(cfg: Config) -> "ImageFont.FreeTypeFont":
    try:
        return ImageFont.truetype(cfg.font_path, cfg.font_size)
    except Exception:
        return ImageFont.load_default()


def _line_height(font, cfg: Config) -> int:
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except Exception:
        return cfg.font_size + 4


def _origin(position, img_size, block, margin):
    iw, ih = img_size
    bw, bh = block
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else iw - bw - margin
    y = margin if top else ih - bh - margin
    # clamp dans [0, dim - bloc] : le texte reste visible meme si l'image
    # est plus petite que le bloc ou que la marge.
    x = max(0, min(int(x), iw - int(bw)))
    y = max(0, min(int(y), ih - int(bh)))
    return x, y


def render(m: Metrics, base: Image.Image, cfg: Config) -> Image.Image:
    img = base.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(cfg)
    lines = format_lines(m)

    line_h = _line_height(font, cfg)
    widths = [draw.textlength(line, font=font) for line in lines]
    bw = max(widths) if widths else 0
    bh = line_h * len(lines) + cfg.line_spacing * (len(lines) - 1 if lines else 0)
    x, y = _origin(cfg.position, img.size, (bw, bh), cfg.margin)

    fill = cfg.color + (cfg.opacity,)
    shadow_fill = (0, 0, 0, min(cfg.opacity, 160))
    cy = y
    for line in lines:
        if cfg.shadow:
            draw.text((x + 2, cy + 2), line, font=font, fill=shadow_fill)
        draw.text((x, cy), line, font=font, fill=fill)
        cy += line_h + cfg.line_spacing

    return Image.alpha_composite(img, overlay).convert("RGB")
