import argparse
import json
import logging
import os
from dotenv import load_dotenv

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from locator.opensky import OpenSkyClient


load_dotenv()

log = logging.getLogger(__name__)


# IATA/ICAO → timezone. Extend as needed.
AIRPORT_INFO = {
    "MLA": {"icao": "LMML", "timezone": "Europe/Malta"},
    "LMML": {"icao": "LMML", "timezone": "Europe/Malta"},
    "CDG": {"icao": "LFPG", "timezone": "Europe/Paris"},
    "ORY": {"icao": "LFPO", "timezone": "Europe/Paris"},
    "LHR": {"icao": "EGLL", "timezone": "Europe/London"},
    "AMS": {"icao": "EHAM", "timezone": "Europe/Amsterdam"},
    "FCO": {"icao": "LIRF", "timezone": "Europe/Rome"},
}


def resolve_airport(code: str) -> tuple[str, str]:
    """Return (icao_code, tz_name). Falls back to code as-is + UTC if unknown."""
    info = AIRPORT_INFO.get(code.upper())
    if info:
        return info["icao"], info["timezone"]
    return code.upper(), "UTC"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve a flight track from OpenSky Network given departure info."
    )
    parser.add_argument(
        "--airport",
        required=True,
        help="Departure airport code (IATA e.g. MLA, or ICAO e.g. LMML)",
    )
    parser.add_argument(
        "--time",
        required=True,
        help="Scheduled departure time, local time (HH:MM)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Departure date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--timezone",
        default=None,
        help="Timezone for departure time (e.g. Europe/Malta). Inferred from airport if known.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Search window in minutes on each side of departure time (default: 30).",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("OPENSKY_CLIENT_ID"),
        help="OpenSky OAuth2 client_id (or set OPENSKY_CLIENT_ID in .env).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("OPENSKY_CLIENT_SECRET"),
        help="OpenSky OAuth2 client_secret (or set OPENSKY_CLIENT_SECRET in .env).",
    )
    parser.add_argument(
        "--output",
        default="track.json",
        help="Output JSON file for the flight track (default: track.json).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(asctime)s - %(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    icao, default_tz = resolve_airport(args.airport)
    tz = ZoneInfo(args.timezone or default_tz)

    date_str = args.date or datetime.now(tz).strftime("%Y-%m-%d")
    dt_local = datetime.fromisoformat(f"{date_str}T{args.time}").replace(tzinfo=tz)
    dt_utc = dt_local.astimezone(timezone.utc)

    begin = int(dt_utc.timestamp()) - args.window * 60
    end = int(dt_utc.timestamp()) + args.window * 60

    def fmt_utc(ts: int) -> str:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M UTC")

    log.info(
        "Searching departures from %s [%s — %s] on %s",
        icao,
        fmt_utc(begin),
        fmt_utc(end),
        date_str,
    )

    client = OpenSkyClient(args.username, args.password)
    flights = client.get_departures(icao, begin, end)

    if not flights:
        log.warning("No flights found in this window.")
        return

    log.info("Found %d flight(s):", len(flights))
    for i, f in enumerate(flights):
        dep_time = fmt_utc(f.firstSeen) if f.firstSeen else "?"
        callsign = (f.callsign or "?").strip()
        dest = f.estArrivalAirport or "?"
        log.info(
            "  [%d] %-10s  ICAO24: %s  dep: %s  dest: %s",
            i,
            callsign,
            f.icao24,
            dep_time,
            dest,
        )

    selected = (
        flights[0]
        if len(flights) == 1
        else flights[int(input("Select flight index: "))]
    )

    callsign = (selected.callsign or "?").strip()
    log.info("Fetching track for %s (%s)…", callsign, selected.icao24)

    track = client.get_flight_track(selected.icao24, selected.firstSeen)
    if track is None:
        log.error("No track data returned.")
        return

    log.info("Track: %d waypoints", len(track.path))

    track_dict = {**vars(track), "path": [vars(wp) for wp in track.path]}
    with open(args.output, "w") as fp:
        json.dump(track_dict, fp, indent=2)
    log.info("Saved to %s", args.output)


if __name__ == "__main__":
    main()
