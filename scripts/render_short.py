"""Render a fact into a vertical (1080x1920) YouTube Short using PIL + ffmpeg.

Audio is fully synthesized (offline TTS narration + generated ambient pad) so
there's zero copyright risk — nothing here is a real recording.
"""
import subprocess
import textwrap
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
GAP = 0.4  # seconds of silence between narration segments

CATEGORY_COLORS = {
    "Space": ((15, 12, 41), (48, 43, 99)),
    "Ocean": ((0, 32, 63), (0, 91, 150)),
    "Human Body": ((90, 24, 60), (163, 52, 84)),
    "History": ((59, 40, 15), (120, 85, 40)),
    "Animals": ((15, 60, 30), (45, 110, 60)),
    "Psychology": ((40, 15, 70), (100, 40, 130)),
    "Science": ((10, 40, 50), (20, 100, 110)),
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


def _make_background(category: str, out_path: Path):
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
    img.save(out_path)


def _escape_drawtext(text: str) -> str:
    # Sidestep drawtext's quoting rules: kill apostrophes, escape backslashes.
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "’")
    return text


def _drawtext(text: str, y_expr: str, start: float, end: float, size: int, fade: float = 0.3) -> str:
    escaped = _escape_drawtext(text)
    font = _font_path()
    # Inside the single-quoted alpha='...' value, commas don't need escaping.
    alpha_expr = f"if(lt(t,{start}),0,if(lt(t,{start + fade}),(t-{start})/{fade},1))"
    return (
        f"drawtext=fontfile={font}:text='{escaped}':"
        f"fontcolor=white:fontsize={size}:borderw=4:bordercolor=black@0.6:"
        f"x=(w-text_w)/2:y={y_expr}:alpha='{alpha_expr}':enable='between(t,{start},{end})'"
    )


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
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


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


def render_short(fact: dict, out_name: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_name = out_name or f"{fact['id']}.mp4"
    out_path = OUTPUT_DIR / out_name
    bg_path = OUTPUT_DIR / f"{fact['id']}_bg.png"

    _make_background(fact["category"], bg_path)

    hook_lines = textwrap.wrap(fact["hook"] + "?", width=20) or [""]
    body_lines = textwrap.wrap(fact["body"], width=26) or [""]
    outro_text = "Follow for more!"

    # Synthesize narration per segment so timing matches the actual speech.
    hook_wav = OUTPUT_DIR / f"{fact['id']}_hook.wav"
    body_wav = OUTPUT_DIR / f"{fact['id']}_body.wav"
    outro_wav = OUTPUT_DIR / f"{fact['id']}_outro.wav"
    gap_wav = OUTPUT_DIR / f"{fact['id']}_gap.wav"
    narration_wav = OUTPUT_DIR / f"{fact['id']}_narration.wav"
    bg_wav = OUTPUT_DIR / f"{fact['id']}_bgpad.wav"
    mixed_wav = OUTPUT_DIR / f"{fact['id']}_mixed.wav"

    _tts(fact["hook"] + "?", hook_wav)
    _tts(fact["body"], body_wav)
    _tts(outro_text + "!", outro_wav)
    _silence(gap_wav)

    hook_dur = _duration(hook_wav)
    body_dur = _duration(body_wav)
    outro_dur = _duration(outro_wav)

    hook_start, hook_end = 0.0, hook_dur
    body_start = hook_end + GAP
    body_end = body_start + body_dur
    outro_start = body_end + GAP
    outro_end = outro_start + outro_dur
    total_duration = outro_end + 0.3

    _concat_audio([hook_wav, gap_wav, body_wav, gap_wav, outro_wav], narration_wav)
    _background_pad(fact["category"], total_duration, bg_wav)
    _mix_audio(narration_wav, bg_wav, mixed_wav)

    filters = []
    line_h = 70
    hook_y0 = 260 - (len(hook_lines) - 1) * line_h / 2
    for i, line in enumerate(hook_lines):
        filters.append(_drawtext(line, str(int(hook_y0 + i * line_h)), hook_start, hook_end, 64))

    body_y0 = HEIGHT / 2 - (len(body_lines) - 1) * (line_h + 10) / 2
    for i, line in enumerate(body_lines):
        filters.append(
            _drawtext(line, str(int(body_y0 + i * (line_h + 10))), body_start, body_end, 58)
        )

    filters.append(_drawtext(f"{outro_text} \U0001f514", "h-260", outro_start, outro_end, 56))

    # Slow continuous zoom (Ken Burns) so a static gradient still reads as "video".
    fps = 30
    total_frames = max(1, round(total_duration * fps))
    zoompan = (
        f"zoompan=z='min(zoom+0.0006,1.15)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={WIDTH}x{HEIGHT}:fps={fps}"
    )
    vf = zoompan + "," + ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(bg_path),
        "-i", str(mixed_wav),
        "-vf", vf,
        "-t", str(total_duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)

    for tmp in (bg_path, hook_wav, body_wav, outro_wav, gap_wav, narration_wav, bg_wav, mixed_wav):
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
