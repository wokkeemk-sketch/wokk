"""Render a fact into a vertical (1080x1920) YouTube Short using PIL + ffmpeg.

Audio is fully synthesized (offline TTS narration + generated ambient pad) so
there's zero copyright risk — nothing here is a real recording. Captions are
baked into the frame with PIL rather than ffmpeg's drawtext filter, since not
every ffmpeg build ships drawtext (some static/minimal builds omit it) — this
way rendering doesn't depend on that filter being present.
"""
import subprocess
import textwrap
import wave
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
GAP = 0.4  # seconds of silence between narration segments
FPS = 30

CATEGORY_COLORS = {
    "Space": ((15, 12, 41), (48, 43, 99)),
    "Ocean": ((0, 32, 63), (0, 91, 150)),
    "Human Body": ((90, 24, 60), (163, 52, 84)),
    "History": ((59, 40, 15), (120, 85, 40)),
    "Animals": ((15, 60, 30), (45, 110, 60)),
    "Psychology": ((40, 15, 70), (100, 40, 130)),
    "Science": ((10, 40, 50), (20, 100, 110)),
    "Colors": ((70, 20, 70), (200, 90, 150)),
    "Numbers": ((20, 60, 90), (60, 150, 200)),
    "Shapes": ((80, 50, 10), (220, 160, 60)),
    "Letters": ((20, 70, 50), (60, 180, 120)),
}
DEFAULT_COLORS = ((20, 20, 30), (60, 60, 90))

# Root note per category so the background pad varies a bit with content.
CATEGORY_TONES = {
    "Space": (98.0, 146.83),
    "Ocean": (110.0, 164.81),
    "Human Body": (123.47, 185.00),
    "History": (110.0, 174.61),
    "Animals": (130.81, 196.00),
    "Psychology": (116.54, 174.61),
    "Science": (110.0, 164.81),
    "Colors": (130.81, 196.00),
    "Numbers": (146.83, 220.00),
    "Shapes": (116.54, 174.61),
    "Letters": (130.81, 196.00),
}
DEFAULT_TONES = (110.0, 164.81)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font_path():
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise RuntimeError(
        "No bold font found. Install one, e.g. `apt-get install -y fonts-dejavu-core`."
    )


def _gradient(category: str):
    from PIL import Image

    top, bottom = CATEGORY_COLORS.get(category, DEFAULT_COLORS)
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = img.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(WIDTH):
            pixels[x, y] = (r, g, b)
    return img


def _cover_crop(img, target_w: int, target_h: int):
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale) + 1, int(src_h * scale) + 1
    img = img.resize((new_w, new_h))
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _darken(img, alpha: int = 80):
    from PIL import Image

    overlay = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _prepare_background_image(fact: dict, tmp_dir: Path):
    from PIL import Image

    query = fact.get("image_query")
    if query:
        from fetch_image import fetch_fact_image

        raw_path = tmp_dir / f"{fact['id']}_raw.jpg"
        try:
            if fetch_fact_image(query, raw_path):
                img = Image.open(raw_path).convert("RGB")
                img = _cover_crop(img, WIDTH, HEIGHT)
                return _darken(img)
        except Exception:
            pass  # fall through to the gradient background below
        finally:
            raw_path.unlink(missing_ok=True)
    return _gradient(fact["category"])


def _draw_caption(draw, lines: list[str], font, y0: float, line_h: int):
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) / 2
        y = y0 + i * line_h
        for dx, dy in ((-3, -3), (-3, 3), (3, -3), (3, 3), (-3, 0), (3, 0), (0, -3), (0, 3)):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))


def _make_caption_frame(base_img, lines: list[str], fontsize: int, y0: float, out_path: Path):
    from PIL import ImageDraw, ImageFont

    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(_font_path(), fontsize)
    line_h = int(fontsize * 1.15)
    _draw_caption(draw, lines, font, y0, line_h)
    img.save(out_path)


def _tts(text: str, out_path: Path, rate: int = 165):
    subprocess.run(
        ["espeak-ng", "-v", "en-us", "-s", str(rate), "-w", str(out_path), text],
        check=True,
    )


def _silence(out_path: Path, duration: float = GAP):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            str(out_path),
        ],
        check=True,
    )


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / f.getframerate()


def _concat_audio(paths: list[Path], out_path: Path):
    inputs = []
    for p in paths:
        inputs += ["-i", str(p)]
    n = len(paths)
    labels = "".join(f"[{i}:a]" for i in range(n))
    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", f"{labels}concat=n={n}:v=0:a=1[out]",
        "-map", "[out]", str(out_path),
    ]
    subprocess.run(cmd, check=True)


def _background_pad(category: str, duration: float, out_path: Path):
    low, high = CATEGORY_TONES.get(category, DEFAULT_TONES)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={low}:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={high}:duration={duration}",
        "-filter_complex",
        "[0:a]volume=0.05[a];[1:a]volume=0.035[b];[a][b]amix=inputs=2:duration=first[bg]",
        "-map", "[bg]", str(out_path),
    ]
    subprocess.run(cmd, check=True)


def _mix_audio(narration_path: Path, bg_path: Path, out_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration_path), "-i", str(bg_path),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:weights=1 1[mix]",
        "-map", "[mix]", str(out_path),
    ]
    subprocess.run(cmd, check=True)


def _zoompan_clip(image_path: Path, duration: float, out_path: Path):
    total_frames = max(1, round(duration * FPS))
    vf = (
        f"zoompan=z='min(zoom+0.0008,1.15)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
        "-vf", vf, "-t", str(duration),
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def _concat_videos(paths: list[Path], out_path: Path):
    list_path = paths[0].parent / f"{out_path.stem}_concat.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in paths))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out_path)]
    subprocess.run(cmd, check=True)
    list_path.unlink(missing_ok=True)


def _mux_audio(video_path: Path, audio_path: Path, out_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path), "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def render_short(fact: dict, out_name: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_name = out_name or f"{fact['id']}.mp4"
    out_path = OUTPUT_DIR / out_name
    fid = fact["id"]

    hook_lines = textwrap.wrap(fact["hook"] + "?", width=20) or [""]
    body_lines = textwrap.wrap(fact["body"], width=26) or [""]
    outro_text = "Follow for more! \U0001f514"

    # --- narration, timed per segment ---
    hook_wav = OUTPUT_DIR / f"{fid}_hook.wav"
    body_wav = OUTPUT_DIR / f"{fid}_body.wav"
    outro_wav = OUTPUT_DIR / f"{fid}_outro.wav"
    gap_wav = OUTPUT_DIR / f"{fid}_gap.wav"
    narration_wav = OUTPUT_DIR / f"{fid}_narration.wav"
    bg_wav = OUTPUT_DIR / f"{fid}_bgpad.wav"
    mixed_wav = OUTPUT_DIR / f"{fid}_mixed.wav"

    _tts(fact["hook"] + "?", hook_wav)
    _tts(fact["body"], body_wav)
    _tts(outro_text, outro_wav)
    _silence(gap_wav)

    hook_dur = _duration(hook_wav)
    body_dur = _duration(body_wav)
    outro_dur = _duration(outro_wav) + 0.3

    _concat_audio([hook_wav, gap_wav, body_wav, gap_wav, outro_wav], narration_wav)
    total_duration = hook_dur + GAP + body_dur + GAP + outro_dur
    _background_pad(fact["category"], total_duration, bg_wav)
    _mix_audio(narration_wav, bg_wav, mixed_wav)

    # --- one captioned, slowly-zooming clip per segment, sharing one background photo ---
    base_img = _prepare_background_image(fact, OUTPUT_DIR)

    hook_img = OUTPUT_DIR / f"{fid}_hook.png"
    body_img = OUTPUT_DIR / f"{fid}_body.png"
    outro_img = OUTPUT_DIR / f"{fid}_outro.png"
    hook_clip = OUTPUT_DIR / f"{fid}_hook.mp4"
    hook_gap_clip = OUTPUT_DIR / f"{fid}_hookgap.mp4"
    body_clip = OUTPUT_DIR / f"{fid}_body.mp4"
    body_gap_clip = OUTPUT_DIR / f"{fid}_bodygap.mp4"
    outro_clip = OUTPUT_DIR / f"{fid}_outro.mp4"
    video_only = OUTPUT_DIR / f"{fid}_video.mp4"

    line_h = 70
    hook_y0 = 260 - (len(hook_lines) - 1) * line_h / 2
    _make_caption_frame(base_img, hook_lines, 64, hook_y0, hook_img)
    _zoompan_clip(hook_img, hook_dur, hook_clip)
    _zoompan_clip(hook_img, GAP, hook_gap_clip)  # holds the hook frame through the pause

    body_y0 = HEIGHT / 2 - (len(body_lines) - 1) * (line_h + 10) / 2
    _make_caption_frame(base_img, body_lines, 58, body_y0, body_img)
    _zoompan_clip(body_img, body_dur, body_clip)
    _zoompan_clip(body_img, GAP, body_gap_clip)  # holds the body frame through the pause

    _make_caption_frame(base_img, [outro_text], 56, HEIGHT - 320, outro_img)
    _zoompan_clip(outro_img, outro_dur, outro_clip)

    # Video segments must match the audio's [hook, gap, body, gap, outro] layout exactly,
    # otherwise captions drift out of sync with narration as gaps accumulate.
    _concat_videos([hook_clip, hook_gap_clip, body_clip, body_gap_clip, outro_clip], video_only)
    _mux_audio(video_only, mixed_wav, out_path)

    for tmp in (
        hook_wav, body_wav, outro_wav, gap_wav, narration_wav, bg_wav, mixed_wav,
        hook_img, body_img, outro_img,
        hook_clip, hook_gap_clip, body_clip, body_gap_clip, outro_clip, video_only,
    ):
        tmp.unlink(missing_ok=True)
    return out_path


if __name__ == "__main__":
    import json
    import sys

    fact = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else None
    if fact is None:
        raise SystemExit("Pipe a fact JSON object into stdin, e.g. via generate_content.py")
    path = render_short(fact)
    print(path)
