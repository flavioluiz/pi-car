#!/usr/bin/env python3
"""Render splash.txt into splash.png for Plymouth.

Uses Pillow (python3-pil) so it doesn't depend on ImageMagick policy quirks.
Monospace font + green-on-black to get the classic terminal look.
"""

import sys
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]

FG = "#33ff66"
BG = "#000000"
FONT_SIZE = 16
PADDING = 48
LINE_SPACING = 1.25


def load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(input_txt, output_png):
    with open(input_txt, encoding="utf-8") as f:
        lines = f.read().splitlines() or [""]

    font = load_font(FONT_SIZE)

    max_w = 0
    line_h = 0
    for line in lines:
        bbox = font.getbbox(line or " ")
        max_w = max(max_w, bbox[2] - bbox[0])
        line_h = max(line_h, bbox[3] - bbox[1])

    step = int(line_h * LINE_SPACING)
    w = max_w + PADDING * 2
    h = step * len(lines) + PADDING * 2

    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    y = PADDING
    for line in lines:
        draw.text((PADDING, y), line, fill=FG, font=font)
        y += step

    img.save(output_png)
    print(f"Wrote {output_png} ({w}x{h})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: render_splash.py INPUT.txt OUTPUT.png", file=sys.stderr)
        sys.exit(1)
    render(sys.argv[1], sys.argv[2])
