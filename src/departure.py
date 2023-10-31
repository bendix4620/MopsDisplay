"""Fetch departures of stations from BVG API"""

from __future__ import annotations
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from dateutil import parser as DateParser
import requests

from .config import Station


session = requests.Session()

SHORT_DEST_NAMES = {
    "S Spandau Bhf (Berlin)":               "Spandau",
    "S Grünau (Berlin)":                    "Grünau",
    "S Birkenwerder Bhf":                   "Birkenwerder",
    "S Südkreuz Bhf (Berlin)":              "Südkreuz",
    "S Westend (Berlin)":                   "Westend",
    "S Ostbahnhof (Berlin)":                "Ostbahnhof",
    "S Blankenburg (Berlin)":               "Blankenburg",
    "S Schöneweide (Berlin)":               "Schöneweide",
    "S Adlershof (Berlin)":                 "Adlershof",
    "S Köpenick (Berlin)":                  "Köpenick",
    "S Königs Wusterhausen Bhf":            "Königs W...",
    "S+U Gesundbrunnen Bhf (Berlin)":       "Gesundbr...",
    "S+U Pankow (Berlin)":                  "Pankow",
    "S+U Tempelhof (Berlin)":               "Tempelhof",
    "Flughafen BER - Terminal 1-2":         "BER T. 1-2",
    "Flughafen BER Terminal 5":             "BER T. 5",
    "Rahnsdorf/Waldschänke":                "Rahnsdorf",
    "Mahlsdorf, Rahnsdorfer Str.":          "Mahlsdorf",
    "Krankenhaus Köpenick":                 "Köpenick",
    "Schloßplatz Köpenick":                 "Köpenick",
    "Landschaftspark Johannisthal":         "Johannisthal",
    "Ersatzverkehr -> Falkenberg":          "Falkenberg",
    "Ersatzverkehr S Schöneweide":          "Schöneweide",
    "Ersatzverkehr S Adlershof":            "Adlershof",
}

def shorten_dest(dest: str) -> str:
    """Shorten destination names"""
    return SHORT_DEST_NAMES.get(dest, dest)

def time_left(timestr: str) -> int:
    """Parse string and calculate remaining time in minutes"""
    dep = DateParser.parse(timestr)
    time = dep - datetime.now(dep.tzinfo)
    return int(time.total_seconds() / 60)

def get_url(station: Station, direction: int) -> str:
    """Constructs the URL for the API request"""
    return f"https://v6.bvg.transport.rest/stops/{station.station_id}/departures?direction={station.directions[direction]}&results=20&suburban={station.fetch_suburban}&subway={station.fetch_subway}&tram={station.fetch_tram}&bus={station.fetch_bus}&ferry={station.fetch_ferry}&express={station.fetch_express}&regional={station.fetch_regional}&when=in+{station.min_time}+minutes&duration={station.max_time-station.min_time}"  # pylint: disable=line-too-long

def fetch_departures(station: Station, direction: int) -> list[Departure]:
    """Fetch departures in a given direction from BVG API

    TODO: always fetch night service lines (even if station.bus == False)
    """
    departures = []
    trips = []
    try:
        response = session.get(get_url(station, direction), timeout=30_000).json()
    except requests.exceptions.JSONDecodeError:
        response = {"departures": []}

    def create_departure(data: dict):
        """Departure factory"""
        time = time_left(data["when"])
        dept = Departure(
            line=data["line"]["id"],
            dest=shorten_dest(data["direction"]),
            time=time,
            delay=data["delay"],
            product=data["line"]["product"],
            reachable=time > station.min_time_needed)
        return dept

    for data in response["departures"]:
        if data["tripId"] in trips:
            continue
        with suppress(Exception):
            departures.append(create_departure(data))
            trips.append(data["tripId"])
        if len(departures) >= station.max_departures:
            break
    return departures

@dataclass
class Departure:
    """Departure dataclass"""
    line: str
    dest: str
    time: int
    delay: float
    product: str # bus, tram, suburban, express
    reachable: bool
