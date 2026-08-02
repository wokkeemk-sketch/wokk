"""Fetch a real, freely-licensed photo for a fact from Wikimedia Commons.

Commons only hosts public-domain or freely-licensed media, so anything
returned here is safe to reuse without a separate per-image license check.
No API key needed. Returns None (caller should fall back to the gradient
background) if the search or download fails for any reason.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "wokk-shorts-bot/1.0 (personal YouTube Shorts automation)"


def find_image_url(query: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": "1600",
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        infos = page.get("imageinfo")
        if not infos:
            continue
        info = infos[0]
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if info.get("width", 0) < 600 or info.get("height", 0) < 600:
            continue
        return info.get("thumburl") or info.get("url")
    return None


def download_image(url: str, out_path: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            out_path.write_bytes(resp.read())
        return True
    except Exception:
        return False


def fetch_fact_image(query: str, out_path: Path) -> bool:
    url = find_image_url(query)
    if not url:
        return False
    return download_image(url, out_path)


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "planet"
    out = Path("/tmp/commons_test.jpg")
    ok = fetch_fact_image(query, out)
    print("OK" if ok else "FAILED", out if ok else "")
