"""Small reusable renderer for Yuzhen's blue, vertical event-storytelling style.

It creates original editorial motion cards from supplied text. Optional images
can be supplied as scene backgrounds; all assets are still subject to the
project's rights preflight. It never downloads media or fabricates gameplay.
"""
from __future__ import annotations

import json
import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLE = ROOT / "config/styles/yuzhen-event-storytelling.json"


def load_style(path: Path = DEFAULT_STYLE) -> dict:
    style = json.loads(Path(path).read_text(encoding="utf-8"))
    canvas = style.get("canvas", {})
    if canvas.get("width") != 1080 or canvas.get("height") != 1920 or canvas.get("fps") != 30:
        raise ValueError("yuzhen-event-storytelling requires a 1080x1920, 30 FPS canvas")
    if not style.get("id") or style["id"] != "yuzhen-event-storytelling":
        raise ValueError("Unexpected style profile id")
    return style


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    def rgb(value: str) -> tuple[int, int, int]:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    a, b = rgb(top), rgb(bottom)
    width, height = size
    strip = Image.new("RGB", (1, height))
    pixels = []
    for y in range(height):
        t = y / max(height - 1, 1)
        pixels.append(tuple(round(a[c] * (1 - t) + b[c] * t) for c in range(3)))
    strip.putdata(pixels)
    return strip.resize((width, height))


def render_card(scene: dict, index: int, count: int, destination: Path, style: dict) -> Path:
    """Draw one original 9:16 information card with safe margins and callouts."""
    w, h = style["canvas"]["width"], style["canvas"]["height"]
    palette = style["palette"]
    asset_path = scene.get("image_asset")
    if asset_path:
        source = Path(asset_path)
        if not source.is_file():
            raise FileNotFoundError(f"Scene image asset is missing: {source}")
        source_image = Image.open(source).convert("RGB")
        ratio = max(w / source_image.width, h / source_image.height)
        backdrop = source_image.resize((round(source_image.width * ratio), round(source_image.height * ratio)))
        left, top = (backdrop.width - w) // 2, (backdrop.height - h) // 2
        backdrop = backdrop.crop((left, top, left + w, top + h))
        backdrop = backdrop.filter(ImageFilter.GaussianBlur(style["motion"]["background_blur_radius"]))
        backdrop = Image.blend(backdrop, Image.new("RGB", (w, h), palette["background"]), 0.58)
        image = backdrop.convert("RGBA")
    else:
        image = _gradient((w, h), palette["background"], "#10283B").convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    # A self-authored orbital motif gives the cards slow-motion texture without
    # importing game UI, logos, screenshots, or third-party artwork.
    for ring in range(4):
        inset = 96 + ring * 72
        draw.ellipse((w - inset - 680, 300 - ring * 110, w - inset + 680, 300 + 1260 + ring * 110),
                    outline=(87, 217, 255, 20), width=3)
    draw.rounded_rectangle((72, 100, w - 72, h - 100), radius=48,
                           fill=(8, 25, 40, 192), outline=(87, 217, 255, 105), width=2)
    draw.rounded_rectangle((116, 146, 244, 160), radius=7, fill=palette["cyan"])
    if scene.get("motif") == "bus":
        # Generic transport icon drawn from geometry; it is not game or event art.
        draw.rounded_rectangle((792, 150, 944, 232), radius=18,
                               fill=(22, 143, 232, 52), outline=(87, 217, 255, 190), width=4)
        draw.rounded_rectangle((808, 166, 852, 197), radius=5, outline=palette["cyan"], width=3)
        draw.rounded_rectangle((865, 166, 928, 197), radius=5, outline=palette["cyan"], width=3)
        draw.line((806, 207, 930, 207), fill=palette["cyan"], width=4)
        for wheel_x in (824, 910):
            draw.ellipse((wheel_x - 10, 219, wheel_x + 10, 239), fill=palette["highlight"])
    elif scene.get("motif") == "route":
        draw.line((800, 190, 858, 190, 858, 228, 925, 228), fill=palette["cyan"], width=6)
        for px, py in ((800, 190), (858, 190), (858, 228), (925, 228)):
            draw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=palette["highlight"])
    small = _font(style["typography"]["font_bold"], 31)
    title_font = _font(style["typography"]["font_bold"], 76)
    body_font = _font(style["typography"]["font_regular"], 43)
    micro = _font(style["typography"]["font_bold"], 28)
    x = 116
    draw.text((x, 205), scene.get("kicker", "YUZHEN EVENT BRIEF"), font=small, fill=palette["cyan"])

    # Blue header card with one highlighted keyword, kept in the title safe zone.
    y_title = 350
    title_lines = _wrap(draw, scene["title"], title_font, w - 232)
    for line in title_lines[:3]:
        draw.text((x, y_title), line, font=title_font, fill=palette["white"],
                  stroke_width=1, stroke_fill="#071522")
        y_title += 96
    draw.rounded_rectangle((116, y_title + 34, w - 116, y_title + 38), radius=2, fill=palette["blue"])

    body_y = y_title + 92
    for line in _wrap(draw, scene.get("body", ""), body_font, w - 232):
        draw.text((x, body_y), line, font=body_font, fill=palette["muted"])
        body_y += 64

    # Optional locally supplied/right-cleared event image overlay. Image paths
    # are explicit per scene; this module never retrieves or substitutes them.
    if asset_path:
        source_image = Image.open(asset_path).convert("RGBA")
        max_size = (w - 300, 580)
        source_image.thumbnail(max_size, Image.Resampling.LANCZOS)
        overlay_x = (w - source_image.width) // 2
        overlay_y = int(scene.get("image_y", 810))
        image.alpha_composite(source_image, (overlay_x, overlay_y))
        draw = ImageDraw.Draw(image, "RGBA")

    # Scene-specific compact fact/callout panel.
    callout = scene.get("callout")
    if callout:
        cy = min(max(body_y + 62, 1230), 1480)
        draw.rounded_rectangle((116, cy, w - 116, cy + 210), radius=34,
                               fill=(22, 143, 232, 60), outline=(87, 217, 255, 175), width=3)
        callout_lines = _wrap(draw, callout, small, w - 288)
        for j, line in enumerate(callout_lines[:3]):
            draw.text((154, cy + 48 + 44 * j), line, font=small, fill=palette["highlight"])

    # Progress marker, timestamp/source cue, and continuous parallax guide.
    footer_y = h - 440
    draw.text((116, footer_y), scene.get("source", f"YUZHEN · {index:02d}/{count:02d}"), font=micro, fill=palette["muted"])
    draw.rounded_rectangle((116, footer_y + 52, w - 116, footer_y + 66), radius=7, fill=(255, 255, 255, 45))
    progress_x = 116 + round((w - 232) * index / count)
    draw.rounded_rectangle((116, footer_y + 52, progress_x, footer_y + 66), radius=7, fill=palette["cyan"])

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, format="PNG", optimize=True)
    return destination


def render_video(cards: list[Path], durations: list[float], audio: Path, subtitles: Path,
                 output: Path, style: dict) -> dict:
    """Animate each card with a restrained zoom/pan and crossfade, then mux voice/captions."""
    output = Path(output)
    if output.exists():
        return {"status": "refused", "reason": "Output exists; refusing to overwrite.", "path": str(output)}
    if not cards or len(cards) != len(durations):
        raise ValueError("Each storyboard scene needs one card and a duration")
    missing = [str(path) for path in [*cards, audio, subtitles] if not Path(path).is_file()]
    if missing:
        return {"status": "blocked", "reason": "Required render inputs are missing.", "missing": missing}
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"status": "blocked", "reason": "FFmpeg is unavailable"}
    trans = float(style["motion"]["scene_transition_seconds"])
    fps, width, height = (style["canvas"][k] for k in ("fps", "width", "height"))
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n"]
    for i, card in enumerate(cards):
        # Add transition overlap to each source except the last. The xfade chain
        # subtracts it, preserving the sum of storyboard beat durations.
        input_duration = durations[i] + (trans if i < len(cards) - 1 else 0)
        command += ["-loop", "1", "-framerate", str(fps), "-t", f"{input_duration:.4f}", "-i", str(card)]
    command += ["-i", str(audio)]
    filters = []
    for i in range(len(cards)):
        filters.append(
            f"[{i}:v]zoompan=z='min(zoom+0.00004,{style['motion']['zoom_end']})':"
            f"x='iw/2-(iw/zoom/2)+sin(on/210)*{style['motion']['pan_amplitude_pixels']}':"
            f"y='ih/2-(ih/zoom/2)+cos(on/260)*{style['motion']['pan_amplitude_pixels']}':"
            f"d=1:s={width}x{height}:fps={fps},setsar=1,format=yuv420p[v{i}]"
        )
    current = "v0"
    elapsed = durations[0]
    for i in range(1, len(cards)):
        nxt = f"mix{i}"
        filters.append(f"[{current}][v{i}]xfade=transition=fade:duration={trans}:offset={elapsed:.4f}[{nxt}]")
        current = nxt
        elapsed += durations[i]
    sub_path = str(subtitles.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    # SRT has no declared PlayRes. libass uses a 384x288 default script space,
    # so convert design pixels from the 1920px canvas to that space to avoid
    # gigantic captions on vertical video.
    scale = 288 / height
    ass_size = max(1, round(style["typography"]["caption_font_size"] * scale))
    ass_outline = max(0.5, style["typography"]["caption_outline_width"] * scale)
    ass_margin = round(style["safe_area"]["bottom"] * scale)
    force_style = f"FontName=Noto Sans,FontSize={ass_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00152207,BorderStyle=1,Outline={ass_outline:.2f},Shadow=0,Alignment=2,MarginV={ass_margin}"
    filters.append(f"[{current}]subtitles='{sub_path}':force_style='{force_style}'[vout]")
    command += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(cards)}:a:0",
                "-t", f"{sum(durations):.4f}", "-r", str(fps), "-c:v", "libx264", "-preset", "medium",
                "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode or not output.is_file() or output.stat().st_size == 0:
        return {"status": "failed", "detail": result.stderr[-3000:]}
    return {"status": "rendered", "path": str(output), "duration_seconds": sum(durations), "width": width, "height": height, "fps": fps}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Yuzhen event-storytelling storyboard")
    parser.add_argument("--storyboard", required=True, help="JSON storyboard with timed scenes and card text")
    parser.add_argument("--audio", required=True, help="validated narration WAV")
    parser.add_argument("--subtitles", required=True, help="SRT subtitle file")
    parser.add_argument("--output", required=True, help="new MP4 path; existing outputs are preserved")
    parser.add_argument("--style", default=str(DEFAULT_STYLE), help="style profile JSON")
    args = parser.parse_args(argv)

    def resolve(value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else ROOT / path

    output = resolve(args.output)
    if output.exists():
        print(json.dumps({"status": "refused", "reason": "Output exists; refusing to overwrite.", "path": str(output)}))
        return 2
    storyboard_path = resolve(args.storyboard)
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = storyboard.get("scenes", [])
    if not scenes:
        print(json.dumps({"status": "blocked", "reason": "Storyboard has no scenes."}))
        return 2
    style = load_style(resolve(args.style))
    cards_dir = output.parent / f"{output.stem}-scene-cards"
    if cards_dir.exists():
        print(json.dumps({"status": "refused", "reason": "Scene card directory exists; refusing to overwrite.", "path": str(cards_dir)}))
        return 2
    cards = []
    durations = []
    for index, scene in enumerate(scenes, 1):
        card = cards_dir / f"card-{index:02d}.png"
        render_card(scene, index, len(scenes), card, style)
        cards.append(card)
        durations.append(float(scene["end"]) - float(scene["start"]) + float(scene.get("pause_after_seconds", 0)))
    result = render_video(cards, durations, resolve(args.audio), resolve(args.subtitles), output, style)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "rendered" else 2


if __name__ == "__main__":
    raise SystemExit(main())
