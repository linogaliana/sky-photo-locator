from opensky_api import OpenSkyApi, FlightData, FlightTrack, Waypoint


class OpenSkyClient:
    def __init__(self, username: str | None = None, password: str | None = None):
        self._api = OpenSkyApi(client_id=username, client_secret=password)

    def get_departures(
        self, airport_icao: str, begin: int, end: int
    ) -> list[FlightData]:
        try:
            return self._api.get_departures_by_airport(airport_icao, begin, end) or []
        except Exception as e:
            raise RuntimeError(
                f"OpenSky API error: {e}\nResponse body: {getattr(getattr(e, 'response', None), 'text', 'n/a')}"
            ) from e

    def get_flight_track(self, icao24: str, departure_time: int) -> FlightTrack | None:
        return self._api.get_track_by_aircraft(icao24, departure_time)


def interpolate_position(
    waypoints: list[Waypoint], timestamp: float
) -> tuple[float, float, float] | None:
    """Interpolate lat/lon/altitude at timestamp from a FlightTrack's waypoints.

    Returns (lat, lon, altitude_m) or None if timestamp is outside the track range.
    """
    for wp, wp_next in zip(waypoints, waypoints[1:]):
        if wp.time is None or wp_next.time is None:
            continue
        if wp.time <= timestamp <= wp_next.time:
            frac = (timestamp - wp.time) / (wp_next.time - wp.time)
            lat = wp.latitude + frac * (wp_next.latitude - wp.latitude)
            lon = wp.longitude + frac * (wp_next.longitude - wp.longitude)
            alt = (wp.baro_altitude or 0) + frac * (
                (wp_next.baro_altitude or 0) - (wp.baro_altitude or 0)
            )
            return lat, lon, alt
    return None
