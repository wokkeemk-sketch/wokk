"""Render a fact into a vertical (1080x1920) YouTube Short using PIL + ffmpeg."""
import subprocess
import textwrap
from pathlib import Path

WIDTH, HEIGHT = 1080, 1920
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

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


def _drawtext(text: str, y_expr: str, start: float, end: float, size: int) -> str:
    escaped = _escape_drawtext(text)
    font = _font_path()
    return (
        f"drawtext=fontfile={font}:text='{escaped}':"
        f"fontcolor=white:fontsize={size}:borderw=4:bordercolor=black@0.6:"
        f"x=(w-text_w)/2:y={y_expr}:enable='between(t,{start},{end})'"
    )


def render_short(fact: dict, out_name: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_name = out_name or f"{fact['id']}.mp4"
    out_path = OUTPUT_DIR / out_name
    bg_path = OUTPUT_DIR / f"{fact['id']}_bg.png"

    _make_background(fact["category"], bg_path)

    hook_lines = textwrap.wrap(fact["hook"] + "?", width=20) or [""]
    body_lines = textwrap.wrap(fact["body"], width=26) or [""]

    hook_start, hook_end = 0.0, 3.0
    seconds_per_line = 1.8
    body_start = hook_end
    body_end = body_start + max(len(body_lines) * seconds_per_line, 6.0)
    outro_start, outro_end = body_end, body_end + 3.0
    total_duration = min(max(outro_end, 15.0), 45.0)

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

    filters.append(
        _drawtext("Follow for more! \U0001f514", "h-260", outro_start, outro_end, 56)
    )

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(bg_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", vf,
        "-t", str(total_duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    bg_path.unlink(missing_ok=True)
    return out_path


if __name__ == "__main__":
    import json
    import sys

    fact = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else None
    if fact is None:
        raise SystemExit("Pipe a fact JSON object into stdin, e.g. via generate_content.py")
    path = render_short(fact)
    print(path)
