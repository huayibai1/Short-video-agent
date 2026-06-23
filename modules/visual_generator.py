from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PALETTES = [
    {"bg": (16, 19, 24), "panel": (231, 232, 222), "accent": (0, 166, 150), "hot": (224, 75, 55)},
    {"bg": (26, 27, 30), "panel": (238, 229, 209), "accent": (62, 128, 213), "hot": (235, 177, 52)},
    {"bg": (20, 26, 23), "panel": (236, 238, 229), "accent": (78, 157, 95), "hot": (213, 91, 73)},
    {"bg": (28, 24, 34), "panel": (233, 235, 226), "accent": (228, 190, 82), "hot": (79, 178, 202)},
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        test = current + ch
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def render_scene_image(scene: dict, plan: dict, output_path: str | Path, size: tuple[int, int] = (720, 1280)) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    palette = PALETTES[(scene["index"] - 1) % len(PALETTES)]
    img = Image.new("RGB", size, palette["bg"])
    draw = ImageDraw.Draw(img)

    # Large editorial blocks give each generated scene a designed visual anchor.
    offset = (scene["index"] * 37) % 180
    draw.rectangle([0, 0, width, 210 + offset // 3], fill=palette["panel"])
    draw.polygon(
        [(0, height), (width, height - 260 - offset), (width, height)],
        fill=palette["accent"],
    )
    draw.rectangle([42, 270, 54, 950], fill=palette["hot"])
    for i in range(8):
        y = 260 + i * 78 + offset // 4
        draw.line([(width - 210, y), (width - 36, y - 44)], fill=palette["accent"], width=3)

    title_font = _font(48, True)
    scene_font = _font(34, True)
    body_font = _font(31)
    small_font = _font(24)
    num_font = _font(92, True)

    draw.text((42, 48), plan["topic"][:18], font=title_font, fill=palette["bg"])
    draw.text((46, 148), f"{plan['audience']} / {plan['style']}", font=small_font, fill=(82, 86, 86))
    draw.text((74, 265), f"{scene['index']:02d}", font=num_font, fill=palette["panel"])

    label = scene["visual"].split("：", 1)[0]
    draw.text((112, 296), label, font=scene_font, fill=palette["panel"])

    # Keep fallback visuals clean; subtitles are burned in during final composition.
    visual_text = scene["visual"].split("。", 1)[0]
    lines = _wrap(draw, visual_text, body_font, width - 150)
    y = 470
    for line in lines[:3]:
        draw.text((74, y), line, font=body_font, fill=palette["panel"])
        y += 50

    keyword_lines = _wrap(draw, scene["asset_keyword"], small_font, width - 110)
    y = height - 190
    draw.text((42, y), "SCENE VISUAL", font=small_font, fill=palette["bg"])
    for line in keyword_lines[:2]:
        y += 36
        draw.text((42, y), line, font=small_font, fill=palette["bg"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)
    return output_path


def render_all_scene_images(plan: dict, output_dir: str | Path, size: tuple[int, int] = (720, 1280)) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images = []
    for scene in plan["scenes"]:
        images.append(render_scene_image(scene, plan, output_dir / f"scene_{scene['index']:02d}.jpg", size))
    return images
