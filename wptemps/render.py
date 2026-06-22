from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .config import Config
from .metrics.base import Metrics, format_lines


def _load_font(cfg: Config) -> "ImageFont.FreeTypeFont":
    try:
        return ImageFont.truetype(cfg.font_path, cfg.font_size)
    except Exception:
        return ImageFont.load_default()


def _text_block_size(draw, lines, font, spacing):
    widths, heights = [], []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    width = max(widths) if widths else 0
    height = sum(heights) + spacing * (len(lines) - 1 if lines else 0)
    return width, height, heights


def _origin(position, img_size, block, margin):
    iw, ih = img_size
    bw, bh = block
    left = position.endswith("left")
    top = position.startswith("top")
    x = margin if left else iw - bw - margin
    y = margin if top else ih - bh - margin
    return x, y


def render(m: Metrics, base: Image.Image, cfg: Config) -> Image.Image:
    img = base.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(cfg)
    lines = format_lines(m)

    bw, bh, heights = _text_block_size(draw, lines, font, cfg.line_spacing)
    x, y = _origin(cfg.position, img.size, (bw, bh), cfg.margin)

    fill = cfg.color + (cfg.opacity,)
    shadow_fill = (0, 0, 0, min(cfg.opacity, 160))
    cy = y
    for line, h in zip(lines, heights):
        if cfg.shadow:
            draw.text((x + 2, cy + 2), line, font=font, fill=shadow_fill)
        draw.text((x, cy), line, font=font, fill=fill)
        cy += h + cfg.line_spacing

    return Image.alpha_composite(img, overlay).convert("RGB")
