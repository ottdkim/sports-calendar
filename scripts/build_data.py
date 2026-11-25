"""Fetch all schedules and write the site's data files.

Run from the project folder:
    python scripts/build_data.py

Writes:
    site/data/events.json     every event (F1 sessions + NHL games), times in UTC
    site/data/standings.json  F1 driver/constructor standings + NHL division
"""

import json
import sys

import f1
import nhl
from common import ROOT, load_config, now_utc_iso

OUT_DIR = ROOT / "site" / "data"


def main():
    cfg = load_config()
    warnings = []

    def warn(msg):
        warnings.append(msg)
        print(f"  ! {msg}")

    events, standings = [], {}
    ok = 0

    for name, module in (("f1", f1), ("nhl", nhl)):
        try:
            evs, st = module.build(cfg, warn)
            events += evs
            standings[name] = st
            ok += 1
        except Exception as e:
            warn(f"{name.upper()} fetch failed: {e}")

    if ok == 0:
        print("Nothing fetched - keeping the existing data files.")
        sys.exit(1)

    # Keep previous data for a league whose fetch failed, so the site never goes blank.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prev_events = OUT_DIR / "events.json"
    if ok < 2 and prev_events.exists():
        fetched = {e["league"] for e in events}
        old = json.loads(prev_events.read_text(encoding="utf-8"))
        events += [e for e in old.get("events", []) if e["league"] not in fetched]
    prev_standings = OUT_DIR / "standings.json"
    if prev_standings.exists():
        old = json.loads(prev_standings.read_text(encoding="utf-8"))
        for key in ("f1", "nhl"):
            if not standings.get(key) and old.get(key):
                standings[key] = old[key]

    events.sort(key=lambda e: (e.get("start_utc") or f"{e['date_local']}T23:59:59Z"))

    meta = {
        "updated_utc": now_utc_iso(),
        "home_timezone": cfg["home_timezone"],
        "f1_driver": cfg["f1"]["driver_name"],
        "f1_constructor": cfg["f1"]["constructor_name"],
        "nhl_team": cfg["nhl"]["team"],
        "nhl_team_name": cfg["nhl"]["team_name"],
        "warnings": warnings,
    }

    (OUT_DIR / "events.json").write_text(
        json.dumps({"meta": meta, "events": events}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "standings.json").write_text(
        json.dumps({"meta": meta, **standings}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Wrote {len(events)} events to {OUT_DIR / 'events.json'}")
    if warnings:
        print(f"{len(warnings)} warning(s) - see above.")


if __name__ == "__main__":
    main()
