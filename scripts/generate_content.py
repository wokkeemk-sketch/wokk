"""Pick the next unposted fact and build its YouTube metadata."""
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FACTS_PATH = DATA_DIR / "facts.json"
LOG_PATH = DATA_DIR / "posted_log.json"


def _load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def pick_next_fact():
    facts = _load_json(FACTS_PATH, [])
    posted = _load_json(LOG_PATH, [])
    posted_ids = {p["id"] for p in posted}

    remaining = [f for f in facts if f["id"] not in posted_ids]
    if not remaining:
        remaining = facts  # every fact has been posted once, start a new cycle
    if not remaining:
        raise RuntimeError("data/facts.json is empty")
    return random.choice(remaining)


def build_metadata(fact):
    title = f"{fact['hook']}? 🤯 #Shorts"[:100]
    hashtag = fact["category"].replace(" ", "")
    description = (
        f"{fact['body']}\n\n"
        f"#Shorts #DidYouKnow #{hashtag} #Facts #LearnSomethingNew"
    )
    tags = ["shorts", "did you know", "facts", fact["category"].lower(), "interesting facts"]
    return {"title": title, "description": description, "tags": tags}


if __name__ == "__main__":
    fact = pick_next_fact()
    print(json.dumps({"fact": fact, "metadata": build_metadata(fact)}, indent=2))
