"""Circuit -> IANA time zone lookup.

Jolpica gives each circuit's city and country but not its time zone,
so we keep this small table. Add a line here if a new circuit shows up
(the build script prints a warning when it finds one it doesn't know).
"""

CIRCUIT_TZ = {
    "albert_park": "Australia/Melbourne",
    "shanghai": "Asia/Shanghai",
    "suzuka": "Asia/Tokyo",
    "bahrain": "Asia/Bahrain",
    "jeddah": "Asia/Riyadh",
    "miami": "America/New_York",
    "villeneuve": "America/Toronto",
    "monaco": "Europe/Monaco",
    "catalunya": "Europe/Madrid",
    "madring": "Europe/Madrid",
    "portimao": "Europe/Lisbon",
    "red_bull_ring": "Europe/Vienna",
    "silverstone": "Europe/London",
    "spa": "Europe/Brussels",
    "hungaroring": "Europe/Budapest",
    "zandvoort": "Europe/Amsterdam",
    "monza": "Europe/Rome",
    "imola": "Europe/Rome",
    "baku": "Asia/Baku",
    "istanbul": "Europe/Istanbul",
    "sepang": "Asia/Kuala_Lumpur",
    "marina_bay": "Asia/Singapore",
    "americas": "America/Chicago",
    "rodriguez": "America/Mexico_City",
    "interlagos": "America/Sao_Paulo",
    "vegas": "America/Los_Angeles",
    "losail": "Asia/Qatar",
    "yas_marina": "Asia/Dubai",
}

# Fallback when the circuit isn't in the table above.
COUNTRY_TZ = {
    "Australia": "Australia/Melbourne",
    "China": "Asia/Shanghai",
    "Japan": "Asia/Tokyo",
    "Bahrain": "Asia/Bahrain",
    "Saudi Arabia": "Asia/Riyadh",
    "Canada": "America/Toronto",
    "Monaco": "Europe/Monaco",
    "Spain": "Europe/Madrid",
    "Portugal": "Europe/Lisbon",
    "Austria": "Europe/Vienna",
    "UK": "Europe/London",
    "Belgium": "Europe/Brussels",
    "Hungary": "Europe/Budapest",
    "Netherlands": "Europe/Amsterdam",
    "Italy": "Europe/Rome",
    "Azerbaijan": "Asia/Baku",
    "Turkey": "Europe/Istanbul",
    "Malaysia": "Asia/Kuala_Lumpur",
    "Singapore": "Asia/Singapore",
    "Mexico": "America/Mexico_City",
    "Brazil": "America/Sao_Paulo",
    "Qatar": "Asia/Qatar",
    "UAE": "Asia/Dubai",
}


def circuit_timezone(circuit_id, country=None):
    if circuit_id in CIRCUIT_TZ:
        return CIRCUIT_TZ[circuit_id]
    if country in COUNTRY_TZ:
        return COUNTRY_TZ[country]
    return None
