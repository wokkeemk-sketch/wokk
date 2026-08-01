# Did You Know — Shorts automation

Automated pipeline for a facts-based YouTube Shorts channel: picks a fact,
renders it into a vertical video, uploads it to YouTube, and repeats daily
via GitHub Actions.

## How it works

1. `scripts/generate_content.py` — picks the next unposted fact from
   `data/facts.json` and builds a title/description/tags.
2. `scripts/render_short.py` — renders a 1080x1920 video (gradient
   background + text overlays) with `ffmpeg`.
3. `scripts/upload_short.py` — uploads the video via the YouTube Data API v3.
4. `scripts/run_pipeline.py` — runs all three steps and logs the result to
   `data/posted_log.json` so facts don't repeat until the bank cycles.
5. `.github/workflows/post_short.yml` — runs the pipeline once a day.

## One-time setup required

The channel itself and API access have to be created by a human (Google
requires the account owner to do this) — see [SETUP.md](SETUP.md) for the
exact 10-15 minute walkthrough. Once that's done, the channel posts on its
own every day.

## Running locally

```bash
pip install -r requirements.txt
export YT_CLIENT_ID=...
export YT_CLIENT_SECRET=...
export YT_REFRESH_TOKEN=...
python scripts/run_pipeline.py
```
