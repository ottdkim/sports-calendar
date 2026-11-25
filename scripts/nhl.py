"""NHL team schedule, results, and division standings from the NHL web API.

This API is unofficial (no docs from the NHL). Community reference:
https://github.com/Zmalski/NHL-API-Reference
"""

from common import get_json

BASE = "https://api-web.nhle.com/v1"

GAME_TYPES = {1: "Preseason", 2: "Regular season", 3: "Playoffs"}
LIVE_STATES = {"LIVE", "CRIT"}
FINAL_STATES = {"FINAL", "OFF"}


def team_name(team):
    place = team.get("placeName", {}).get("default", "")
    common = team.get("commonName", {}).get("default", "")
    return f"{place} {common}".strip() or team.get("abbrev", "")


def game_event(g, my_team):
    home, away = g["homeTeam"], g["awayTeam"]
    is_home = home["abbrev"] == my_team
    me, opp = (home, away) if is_home else (away, home)

    state = g.get("gameState", "FUT")
    sched = g.get("gameScheduleState", "OK")
    if sched in ("PPD", "SUSP", "CNCL"):
        status = "postponed"
    elif state in FINAL_STATES:
        status = "final"
    elif state in LIVE_STATES:
        status = "live"
    else:
        status = "scheduled"

    result = None
    if status in ("final", "live") and "score" in me and "score" in opp:
        mine, theirs = me["score"], opp["score"]
        last = g.get("gameOutcome", {}).get("lastPeriodType", "")
        score = f"{mine}–{theirs}"
        if status == "final":
            score = f"{'W' if mine > theirs else 'L'} {score}"
        result = {"main": score, "detail": last if last in ("OT", "SO") else ""}

    return {
        "id": f"nhl-{g['id']}",
        "league": "NHL",
        "season": g.get("season"),
        "game_type": GAME_TYPES.get(g.get("gameType"), ""),
        "kind": "GAME",
        "title": team_name(opp),
        "opponent": team_name(opp),
        "opponent_abbrev": opp.get("abbrev", ""),
        "home": is_home,
        "venue": g.get("venue", {}).get("default", ""),
        "city": "",
        "venue_tz": g.get("venueTimezone"),
        "start_utc": g.get("startTimeUTC"),
        "date_local": g.get("gameDate"),
        "time_tbd": sched == "TBD",
        "duration_min": 160,
        "status": status,
        "result": result,
        "source": "nhl",
    }


DIVISION_ORDER = ["Atlantic", "Metropolitan", "Central", "Pacific"]


def team_row(r, my_team):
    abbrev = r.get("teamAbbrev", {}).get("default", "")
    return {
        "pos": r.get("divisionSequence"),
        "abbrev": abbrev,
        "name": r.get("teamName", {}).get("default", ""),
        "short_name": r.get("teamCommonName", {}).get("default", ""),  # e.g. "Blue Jackets", used on narrow screens
        "gp": r.get("gamesPlayed", 0),
        "w": r.get("wins", 0),
        "l": r.get("losses", 0),
        "otl": r.get("otLosses", 0),
        "points": r.get("points", 0),
        "streak": f"{r.get('streakCode', '')}{r.get('streakCount', '')}",
        "highlight": abbrev == my_team,
    }


def standings(default_division, my_team):
    """All four divisions, each sorted by division rank. The site opens on default_division."""
    data = get_json(f"{BASE}/standings/now")
    rows = data.get("standings", [])
    divisions = {}
    for r in rows:
        name = r.get("divisionName")
        if name:
            divisions.setdefault(name, []).append(r)
    ordered = sorted(divisions, key=lambda d: DIVISION_ORDER.index(d) if d in DIVISION_ORDER else 99)
    out = {}
    for name in ordered:
        teams = sorted(divisions[name], key=lambda r: r.get("divisionSequence", 99))
        out[name] = [team_row(r, my_team) for r in teams]
    as_of = rows[0].get("date") if rows else None
    return {"default_division": default_division, "as_of": as_of, "divisions": out}


def build(cfg, warn):
    ncfg = cfg["nhl"]
    team = ncfg["team"]
    data = get_json(f"{BASE}/club-schedule-season/{team}/{ncfg['season']}")
    allowed = {2, 3} | ({1} if ncfg.get("include_preseason") else set())
    games = [g for g in data.get("games", []) if g.get("gameType") in allowed]
    events = [game_event(g, team) for g in games]
    print(f"NHL {ncfg['season']}: {len(events)} {team} games")
    try:
        st = standings(ncfg["division"], team)
    except Exception as e:  # standings are a nice-to-have; don't fail the whole build
        warn(f"NHL standings failed: {e}")
        st = None
    return events, st
