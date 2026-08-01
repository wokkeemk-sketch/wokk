"""End-to-end: pick a fact, render it, upload it, record it as posted."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from generate_content import LOG_PATH, build_metadata, pick_next_fact
from render_short import render_short
from upload_short import upload_short


def main():
    fact = pick_next_fact()
    metadata = build_metadata(fact)
    print(f"Selected fact: {fact['id']} — {fact['hook']}")

    video_path = render_short(fact)
    print(f"Rendered: {video_path}")

    video_id = upload_short(
        str(video_path),
        title=metadata["title"],
        description=metadata["description"],
        tags=metadata["tags"],
    )

    log = json.loads(LOG_PATH.read_text()) if LOG_PATH.exists() else []
    log.append(
        {
            "id": fact["id"],
            "video_id": video_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    LOG_PATH.write_text(json.dumps(log, indent=2) + "\n")
    print(f"Logged {fact['id']} -> {video_id}")

    video_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # surface a clean failure in CI logs
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        raise
