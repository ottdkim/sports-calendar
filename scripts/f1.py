"""F1 schedule, your driver's results, and standings from the Jolpica API.

Docs: https://github.com/jolpica/jolpica-f1
"""

import json
from pathlib import Path

from circuits import circuit_timezone
from common import get_json, iso_utc

BASE = "https://api.jolpi.ca/ergast/f1"
MANUAL_2027 = Path(__file__).resolve().parent / "f1_manual_2027.json"

# Jolpica key -> (our kind code, display name, approx. duration in minutes)
SESSIONS = [
    ("FirstPractice", "FP1", "Practice 1", 60),
    ("SecondPractice", "FP2", "Practice 2", 60),
    ("ThirdPractice", "FP3", "Practice 3", 60),
    ("SprintQualifying", "SQ", "Sprint Qualifying", 45),
    ("Sprint", "SPRINT", "Sprint", 60),
    ("Qualifying", "Q", "Qualifying", 60),
]
RACE = ("RACE", "Race", 120)

NON_CLASSIFIED = {"R": "DNF", "W": "DNS", "D": "DSQ", "N": "NC", "E": "EXC", "F": "DNQ"}


def short_gp(name):
    return name.replace(" Grand Prix", " GP")


def fetch_paged(path, list_key):
    """Fetch every page of a Jolpica results endpoint and merge races by round."""
    races = {}
    offset, limit = 0, 100
    while True:
        data = get_json(f"{BASE}/{path}?limit={limit}&offset={offset}")
        mr = data["MRData"]
        for race in mr["RaceTable"]["Races"]:
            rnd = int(race["round"])
            if rnd not in races:
                races[rnd] = dict(race, **{list_key: []})
            races[rnd][list_key].extend(race.get(list_key, []))
        offset += limit
        if offset >= int(mr.get("total", 0)):
            break
    return races


def driver_rows(races, list_key, driver_id):
    out = {}
    for rnd, race in races.items():
        for row in race.get(list_key, []):
            if row.get("Driver", {}).get("driverId") == driver_id:
                out[rnd] = row
    return out


def fmt_points(p):
    p = float(p)
    return str(int(p)) if p.is_integer() else f"{p:g}"


def finish_result(row):
    """Race or sprint finishing result -> {'main': 'P2', 'detail': '+18 pts'}."""
    text = row.get("positionText", "")
    pts = float(row.get("points", 0) or 0)
    if text.isdigit():
        main = f"P{text}"
        detail = f"+{fmt_points(pts)} pts" if pts > 0 else "0 pts"
    else:
        main = NON_CLASSIFIED.get(text, text or "—")
        detail = row.get("status", "")
    return {"main": main, "detail": detail}


def quali_result(row):
    stage = "Q3" if row.get("Q3") else "Q2" if row.get("Q2") else "Q1"
    return {"main": f"P{row.get('position')}", "detail": stage}


def schedule_from_jolpica(season):
    data = get_json(f"{BASE}/{season}/races.json?limit=100")
    return data["MRData"]["RaceTable"]["Races"]


def events_from_jolpica(season, races, results, sprints, qualis, warn):
    events = []
    total = len(races)
    for race in races:
        rnd = int(race["round"])
        circuit = race["Circuit"]
        loc = circuit.get("Location", {})
        tz = circuit_timezone(circuit["circuitId"], loc.get("country"))
        if tz is None:
            warn(f"F1: unknown time zone for circuit '{circuit['circuitId']}' - add it to circuits.py")
        sprint_weekend = "Sprint" in race
        base = {
            "league": "F1",
            "season": season,
            "round": rnd,
            "total_rounds": total,
            "gp_name": race["raceName"],
            "sprint_weekend": sprint_weekend,
            "venue": circuit.get("circuitName", ""),
            "city": loc.get("locality", ""),
            "country": loc.get("country", ""),
            "venue_tz": tz,
            "source": "jolpica",
        }

        sessions = []
        for key, kind, name, dur in SESSIONS:
            if key in race:
                s = race[key]
                sessions.append((kind, name, dur, s.get("date"), s.get("time")))
        sessions.append((RACE[0], RACE[1], RACE[2], race.get("date"), race.get("time")))

        for kind, name, dur, date, time in sessions:
            result = None
            if kind == "RACE" and rnd in results:
                result = finish_result(results[rnd])
            elif kind == "SPRINT" and rnd in sprints:
                result = finish_result(sprints[rnd])
            elif kind == "Q" and rnd in qualis:
                result = quali_result(qualis[rnd])
            events.append(dict(
                base,
                id=f"f1-{season}-{rnd}-{kind.lower()}",
                kind=kind,
                session_name=name,
                title=f"{short_gp(race['raceName'])} · {name}",
                start_utc=iso_utc(date, time),
                date_local=date,
                time_tbd=not time,
                duration_min=dur,
                status="final" if result else "scheduled",
                result=result,
            ))
    return events


def events_from_manual(path, warn):
    with open(path, encoding="utf-8") as f:
        manual = json.load(f)
    season = manual["season"]
    total = len(manual["races"])
    events = []
    for r in manual["races"]:
        tz = circuit_timezone(r["circuit_id"], r.get("country"))
        if tz is None:
            warn(f"F1: unknown time zone for circuit '{r['circuit_id']}' - add it to circuits.py")
        events.append({
            "id": f"f1-{season}-{r['round']}-race",
            "league": "F1",
            "season": season,
            "round": r["round"],
            "total_rounds": total,
            "gp_name": r["name"],
            "sprint_weekend": r.get("sprint", False),
            "venue": "",
            "city": r.get("locality", ""),
            "country": r.get("country", ""),
            "venue_tz": tz,
            "source": "manual",
            "kind": "RACE",
            "session_name": "Race",
            "title": f"{short_gp(r['name'])} · Race",
            "start_utc": None,
            "date_local": r["race_date"],
            "time_tbd": True,
            "duration_min": 120,
            "status": "scheduled",
            "result": None,
        })
    return events, total


def standings(season, total_rounds, cfg):
    d = get_json(f"{BASE}/{season}/driverStandings.json?limit=100")
    lists = d["MRData"]["StandingsTable"]["StandingsLists"]
    if not lists:
        return None
    sl = lists[0]
    rnd = int(sl["round"])
    drivers = []
    for row in sl["DriverStandings"]:
        drv = row["Driver"]
        teams = row.get("Constructors", [])
        drivers.append({
            "pos": int(row.get("position") or 0) or None,
            "name": f"{drv['givenName']} {drv['familyName']}",
            "code": drv.get("code", ""),
            "team": teams[-1]["name"] if teams else "",
            "points": float(row["points"]),
            "wins": int(row.get("wins", 0)),
            "highlight": drv["driverId"] == cfg["driver_id"],
        })

    c = get_json(f"{BASE}/{season}/constructorStandings.json?limit=100")
    clists = c["MRData"]["StandingsTable"]["StandingsLists"]
    constructors = []
    if clists:
        for row in clists[0]["ConstructorStandings"]:
            con = row["Constructor"]
            constructors.append({
                "pos": int(row.get("position") or 0) or None,
                "name": con["name"],
                "points": float(row["points"]),
                "wins": int(row.get("wins", 0)),
                "highlight": con["constructorId"] == cfg["constructor_id"],
            })

    final = total_rounds and rnd >= total_rounds
    return {
        "season": season,
        "round": rnd,
        "label": f"{season} final standings" if final else f"{season} · after round {rnd} of {total_rounds}",
        "drivers": drivers,
        "constructors": constructors,
    }


def build(cfg, warn):
    """Return (events, standings_dict) for the configured F1 seasons."""
    fcfg = cfg["f1"]
    driver = fcfg["driver_id"]
    all_events, totals = [], {}

    def driver_results(season, endpoint, list_key):
        try:
            return driver_rows(fetch_paged(f"{season}/{endpoint}", list_key), list_key, driver)
        except Exception as e:
            warn(f"F1 {season} {endpoint} failed, showing schedule without these results: {e}")
            return {}

    for season in fcfg["seasons"]:
        try:
            races = schedule_from_jolpica(season)
        except Exception as e:
            warn(f"F1 {season} schedule failed: {e}")
            races = []
        if races:
            results = driver_results(season, "results.json", "Results")
            sprints = driver_results(season, "sprint.json", "SprintResults")
            qualis = driver_results(season, "qualifying.json", "QualifyingResults")
            all_events += events_from_jolpica(season, races, results, sprints, qualis, warn)
            totals[season] = len(races)
            print(f"F1 {season}: {len(races)} rounds from Jolpica")
        elif season == 2027 and MANUAL_2027.exists():
            evs, total = events_from_manual(MANUAL_2027, warn)
            all_events += evs
            totals[season] = total
            print(f"F1 {season}: not available from Jolpica - using manual calendar ({total} rounds, times TBD)")
        else:
            warn(f"F1 {season}: no schedule found")

    if not all_events:
        raise RuntimeError("no F1 schedule could be loaded")

    st = None
    for season in sorted(fcfg["seasons"], reverse=True):
        try:
            st = standings(season, totals.get(season), fcfg)
        except Exception as e:
            warn(f"F1 {season} standings failed: {e}")
            st = None
        if st:
            break

    return all_events, st
