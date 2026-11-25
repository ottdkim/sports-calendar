"""Shared helpers: HTTP with retries, config loading, small date utils."""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "personal-sports-calendar/1.0"


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def get_json(url, retries=4, pause=0.35):
    """GET a URL and return parsed JSON.

    Retries on network errors, HTTP 429 (rate limit) and any 5xx server error
    (including Cloudflare's 52x/530 codes), waiting a bit longer each time.
    """
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            time.sleep(pause)  # be polite to free APIs
            return data
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            if e.code != 429 and e.code < 500:
                raise RuntimeError(f"{last_error} for {url}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_error = str(e)
        if attempt < retries - 1:
            wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
            print(f"  ... {last_error} from {url.split('?')[0]} - retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{last_error} for {url} (gave up after {retries} tries)")


def iso_utc(date_str, time_str):
    """Combine Jolpica 'YYYY-MM-DD' + 'HH:MM:SSZ' into an ISO UTC string."""
    if not date_str or not time_str:
        return None
    t = time_str.rstrip("Z")
    return f"{date_str}T{t}Z"


def now_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
