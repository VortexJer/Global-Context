"""Generate a synthetic terminal demo GIF for Global Context.

Shows the flow: Claude Code creates a project, updates .globalcontext.md,
then Gemini CLI continues the same project.
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


try:
    import imageio.v3 as iio
except Exception:  # pragma: no cover
    import imageio as iio  # type: ignore[no-redef]


WIDTH, HEIGHT = 900, 520
BG = (30, 30, 30)
FG = (220, 220, 220)
GREEN = (80, 250, 123)
CYAN = (139, 233, 253)
YELLOW = (241, 250, 140)
ORANGE = (255, 184, 108)
GRAY = (120, 120, 120)
PROMPT = (255, 121, 198)
HEADER_BG = (50, 50, 50)

FONT_SIZE = 15
LINE_HEIGHT = 22
MARGIN = 18


def get_font() -> ImageFont.FreeTypeFont:
    candidates = [
        "Cascadia Mono",
        "Consolas",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Courier New",
        "monospace",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except Exception:
            pass
    return ImageFont.load_default()


FONT = get_font()


def new_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Window title bar
    draw.rectangle([0, 0, WIDTH, 30], fill=HEADER_BG)
    draw.ellipse([12, 10, 22, 20], fill=(255, 95, 86))
    draw.ellipse([28, 10, 38, 20], fill=(255, 189, 46))
    draw.ellipse([44, 10, 54, 20], fill=(39, 201, 63))
    draw.text((WIDTH // 2 - 80, 7), "Global Context demo", fill=GRAY, font=FONT)
    return img, draw


def text_size(draw: ImageDraw.ImageDraw, text: str) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=FONT)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def render_line(draw: ImageDraw.ImageDraw, y: int, parts: list[tuple[str, tuple[int, int, int]]]) -> None:
    x = MARGIN
    for text, color in parts:
        draw.text((x, y), text, fill=color, font=FONT)
        w, _ = text_size(draw, text)
        x += w


def typewriter_frames(lines: list[list[tuple[str, tuple[int, int, int]]]], hold: int = 2) -> list[Image.Image]:
    """Render frames where each line appears character-by-character."""
    frames: list[Image.Image] = []
    current_lines: list[list[tuple[str, tuple[int, int, int]]]] = []

    for line_idx, line in enumerate(lines):
        # Show all previous lines fully.
        max_len = sum(len(t) for t, _ in line)
        for pos in range(max_len + 1):
            img, draw = new_frame()
            y = 45
            for prev in current_lines:
                render_line(draw, y, prev)
                y += LINE_HEIGHT

            # Partial current line.
            remaining = pos
            partial: list[tuple[str, tuple[int, int, int]]] = []
            for text, color in line:
                if remaining <= 0:
                    break
                if remaining >= len(text):
                    partial.append((text, color))
                    remaining -= len(text)
                else:
                    partial.append((text[:remaining], color))
                    remaining = 0
            render_line(draw, y, partial)
            frames.append(img)
        current_lines.append(line)

    # Hold final frame.
    for _ in range(hold):
        frames.append(frames[-1])

    return frames


def full_frame(lines: list[list[tuple[str, tuple[int, int, int]]]]) -> Image.Image:
    img, draw = new_frame()
    y = 45
    for line in lines:
        render_line(draw, y, line)
        y += LINE_HEIGHT
    return img


def main() -> None:
    out_path = Path(__file__).parent / "docs" / "demo.gif"
    out_path.parent.mkdir(exist_ok=True)

    # Scene 1: Claude Code starts and user asks for a function.
    scene1 = [
        [("$ ", GRAY), ("claude ", FG), ("--dir ./calculadora", CYAN)],
        [("✓ Loaded .globalcontext.md", GREEN)],
        [],
        [("You: ", PROMPT), ("create a calculator module with add and subtract", FG)],
    ]

    # Scene 2: Claude works and writes context.
    scene2 = [
        [("Claude: ", ORANGE), ("I'll create calculator/__init__.py and operations.py", FG)],
        [("✓ Wrote calculator/operations.py", GREEN)],
        [("✓ Updated .globalcontext.md", GREEN)],
    ]

    # Scene 3: Switch to Gemini.
    scene3 = [
        [],
        [("$ ", GRAY), ("gemini ", FG), ("--dir ./calculadora", CYAN)],
        [("✓ Loaded .globalcontext.md", GREEN)],
        [("", FG)],
        [("You: ", PROMPT), ("continue — add multiply and divide", FG)],
    ]

    # Scene 4: Gemini continues.
    scene4 = [
        [("Gemini: ", YELLOW), ("Saw Claude created add/subtract. Adding multiply/divide now.", FG)],
        [("✓ Updated calculator/operations.py", GREEN)],
        [("✓ Appended to .globalcontext.md", GREEN)],
    ]

    all_frames: list[Image.Image] = []
    all_frames.extend(typewriter_frames(scene1, hold=6))
    all_frames.extend(typewriter_frames(scene2, hold=6))
    all_frames.extend(typewriter_frames(scene3, hold=6))
    all_frames.extend(typewriter_frames(scene4, hold=10))

    # Add a final "same context, any AI" banner frame.
    banner_lines = [
        [("Same .globalcontext.md. Any AI. Zero lost context.", CYAN)],
    ]
    final = full_frame(scene4 + [[]] + banner_lines)
    for _ in range(12):
        all_frames.append(final)

    # Convert to numpy arrays and write GIF.
    arrays = [f.convert("RGB") for f in all_frames]
    iio.imwrite(
        out_path,
        arrays,
        duration=80,  # ms per frame
        loop=0,
    )
    print(f"Demo GIF written to {out_path}")


if __name__ == "__main__":
    main()
