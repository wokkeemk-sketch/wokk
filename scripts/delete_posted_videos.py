"""One-off cleanup: delete every video listed in data/posted_log.json.

Run via the 'Delete posted videos' GitHub Actions workflow, which has the
same YT_* secrets as the upload pipeline. Not part of the normal pipeline.
"""
import json
from pathlib import Path

from googleapiclient.discovery import build

from upload_short import _credentials

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "posted_log.json"

if __name__ == "__main__":
    youtube = build("youtube", "v3", credentials=_credentials())
    log = json.loads(LOG_PATH.read_text()) if LOG_PATH.exists() else []

    for entry in log:
        video_id = entry["video_id"]
        try:
            youtube.videos().delete(id=video_id).execute()
            print(f"Deleted {video_id} ({entry['id']})")
        except Exception as exc:
            print(f"Failed to delete {video_id} ({entry['id']}): {exc}")

    LOG_PATH.write_text("[]\n")
    print("Cleared data/posted_log.json")
