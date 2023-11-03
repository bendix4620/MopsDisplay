"""Fetch departures of stations from BVG API"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from dateutil import parser as dateparser
import requests


session = requests.Session()


@dataclass(frozen=True, order=True, kw_only=True)
class Event:
    """Event data"""
    date: str
    desc: str


@dataclass(frozen=True, order=True, kw_only=True)
class Poster:
    """Poster data"""
    img: Path


@dataclass(frozen=True, order=True, kw_only=True)
class Station:
    """Station data"""
    name: str
    id: str

    # fetch during day time
    S_day: bool = False # fetch suburban
    U_day: bool = False # fetch subway
    T_day: bool = False # fetch tram
    B_day: bool = False # fetch bus
    F_day: bool = False # fetch ferry
    E_day: bool = False # fetch express
    R_day: bool = False # fetch regional

    # fetch during night time
    S_night: bool = False # fetch suburban
    U_night: bool = False # fetch subway
    T_night: bool = False # fetch tram
    B_night: bool = False # fetch bus
    F_night: bool = False # fetch ferry
    E_night: bool = False # fetch express
    R_night: bool = False # fetch regional

    start_night: str # start of night service
    stop_night: str # end of night service

    # times given in minutes
    min_time: float # min time left for fetched departures
    max_time: float # max time left for fetched departures
    time_needed: float # time needed to reach station

    max_departures: int

    def is_in_night_service(self):
        """Return True if night service is currently active"""
        start = dateparser.parse(self.start_night)
        stop = dateparser.parse(self.stop_night)
        now = datetime.now()
        return time_is_between(start, now, stop)

    def get_url(self) -> str:
        """Get BVG API url"""
        night = self.is_in_night_service()
        return (f"https://v6.bvg.transport.rest/stops/{self.id}/departures?"
                f"when=in+{self.min_time}+minutes&"
                f"duration={self.max_time-self.min_time}&"
                f"results={self.max_departures}&"
                f"suburban={self.S_night if night else self.S_day}&"
                f"subway={  self.U_night if night else self.U_day}&"
                f"tram={    self.T_night if night else self.T_day}&"
                f"bus={     self.B_night if night else self.B_day}&"
                f"ferry={   self.F_night if night else self.F_day}&"
                f"express={ self.E_night if night else self.E_day}&"
                f"regional={self.R_night if night else self.R_day}")

    def fetch_departures(self):
        """Fetch departures from BVG API"""

        url = self.get_url()
        try:
            response = session.get(url, timeout=30_000).json()
        except requests.exceptions.JSONDecodeError:
            response = {"departures": []}

        for data in response.get("departures", []):
            yield self._create_departure(data)

    def _create_departure(self, data: dict):
        """Departure factory"""
        time = time_left(data["when"])
        departure = Departure(
            id=data["tripID"],
            line=data["line"]["id"],
            direction=data["direction"],
            time=time,
            delay=data["delay"],
            product=data["line"]["product"],
            reachable=time > self.time_needed)
        return departure


@dataclass(frozen=True, order=True, kw_only=True)
class Departure:
    """Departure dataclass"""
    id: str
    line: str
    direction: str
    time: float # minutes remaining
    delay: float
    product: str # bus, tram, suburban, express
    reachable: bool


def time_is_between(start: datetime|str, time: datetime|str, stop: datetime|str):
    """Check if time is between start and stop (considers midnight clock wrap)

    the 6 possible cases:
    time_is_between("6:00:00", "10:00:00", "18:00:00") # True
    time_is_between("6:00:00", "02:00:00", "18:00:00") # False
    time_is_between("6:00:00", "20:00:00", "18:00:00") # False
    time_is_between("18:00:00", "10:00:00", "6:00:00") # False
    time_is_between("18:00:00", "02:00:00", "6:00:00") # True
    time_is_between("18:00:00", "20:00:00", "6:00:00") # True
    """
    if isinstance(start, str):
        start = dateparser.parse(start)
    if isinstance(time, str):
        time = dateparser.parse(time)
    if isinstance(stop, str):
        stop = dateparser.parse(stop)

    A = start < stop
    B = start < time
    C = time < stop
    return (B and C) if A else (B or C)

def time_left(timestr: str) -> int:
    """Parse string and calculate remaining time in minutes"""
    dep = dateparser.parse(timestr)
    time = dep - datetime.now(dep.tzinfo)
    return time.total_seconds() / 60
