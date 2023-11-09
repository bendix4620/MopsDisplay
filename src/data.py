"""Fetch departures of stations from BVG API"""

from __future__ import annotations
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Generator, Iterator, Union
from dateutil import parser as dateparser
from PIL.ImageTk import PhotoImage
import requests


session = requests.Session()


@dataclass(frozen=True)
class Event:
    """Event data"""
    date: str
    desc: str


@dataclass(frozen=True)
class Poster:
    """Poster data"""
    images: list[PhotoImage]

    def __post_init__(self):
        # ensure that images is a list
        if not isinstance(self.images, (list, tuple)):
            object.__setattr__(self, "images", [self.images])

@dataclass(frozen=True)
class DirectionsAndProducts:
    directions: list[str]
    S: bool = False
    U: bool = False
    T: bool = False
    B: bool = False
    F: bool = False
    E: bool = False
    R: bool = False

    def __post_init__(self):
        # ensure that directions is a list
        if not isinstance(self.directions, (list, tuple)):
            object.__setattr__(self, "directions", [self.directions])

@dataclass(frozen=True)
class Station:
    """Station data"""
    title: str
    id: str
    max_departures: int

    # times given in minutes
    min_time: float # min time left for fetched departures
    max_time: float # max time left for fetched departures
    time_needed: float # time needed to reach station

    start_night: str # start of night service
    stop_night: str # end of night service

    day: DirectionsAndProducts
    night: DirectionsAndProducts = None

    @property
    def is_in_night_service(self):
        """Return True if night service is currently active"""
        start = dateparser.parse(self.start_night)
        stop = dateparser.parse(self.stop_night)
        now = datetime.now()
        return time_is_between(start, now, stop)

    def get_urls(self) -> Iterator[str]:
        """Get BVG API url for every direction"""
        dap = self.night if self.is_in_night_service else self.day
        if dap is None:
            return []

        for direction in dap.directions:
            yield ( f"https://v6.bvg.transport.rest/stops/{self.id}/departures?"
                    f"direction={direction}&"
                    f"when=in+{self.min_time}+minutes&"
                    f"duration={self.max_time-self.min_time}&"
                    f"results={self.max_departures}&"
                    f"suburban={dap.S}&"
                    f"subway={dap.U}&"
                    f"tram={dap.T}&"
                    f"bus={dap.B}&"
                    f"ferry={dap.F}&"
                    f"express={dap.E}&"
                    f"regional={dap.R}")

    def fetch_departures(self):
        """Fetch departures from BVG API"""

        departures = []
        for url in self.get_urls():
            response = session.get(url, timeout=30_000)
            
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                data = {"departures": []}

            for departure_data in data.get("departures", []):
                departure = self._create_departure(departure_data)
                if departure is None:
                    continue
                departures.append(departure)
        departures.sort()
        return departures

    def _create_departure(self, data: dict) -> Union[Departure, None]:
        """Departure factory"""
        # resolve unexpected api departure time outputs
        timestr = data["when"]
        if timestr is None:
            return None
        time = time_left(timestr)
        if time < self.min_time:
            return None

        reachable = time > self.time_needed
        line = data["line"]

        departure = Departure(
            id=data["tripId"],
            line=line["id"],
            direction=data["direction"],
            time_left=time,
            delay=data["delay"],
            product=data["product"],
            reachable=reachable)
        return departure


@dataclass(frozen=True)
class Departure:
    """Departure data"""
    id: str
    line: str
    direction: str
    time_left: float
    delay: float
    product: str # suburban, subway, tram, bus, ferry, express, regional
    reachable: bool

    def __lt__(self, other: Departure):
        return self.time_left < other.time_left

    def __le__(self, other: Departure):
        return self.time_left <= other.time_left

    def __gt__(self, other: Departure):
        return self.time_left > other.time_left

    def __ge__(self, other: Departure):
        return self.time_left >= other.time_left

    def __eq__(self, other: Departure) -> bool:
        return self.id == other.id

def time_is_between(start: datetime|str, time: datetime|str, stop: datetime|str):
    """Check if time is between start and stop (considers midnight clock wrap)

    the 7 possible cases:
    time_is_between("06:00:00", "10:00:00", "18:00:00") # True
    time_is_between("06:00:00", "02:00:00", "18:00:00") # False
    time_is_between("06:00:00", "20:00:00", "18:00:00") # False
    time_is_between("18:00:00", "10:00:00", "6:00:00") # False
    time_is_between("18:00:00", "02:00:00", "6:00:00") # True
    time_is_between("18:00:00", "20:00:00", "6:00:00") # True
    time_is_between("10:00:00", Any, "10:00:00") # ValueError
    """
    if isinstance(start, str):
        start = dateparser.parse(start)
    if isinstance(time, str):
        time = dateparser.parse(time)
    if isinstance(stop, str):
        stop = dateparser.parse(stop)

    if start == stop:
        raise ValueError(f"Cannot resolve ambiguous time span {start}->{stop}")

    A = start < stop
    B = start < time
    C = time < stop
    return (B and C) if A else (B or C)

def time_left(timestr: Union[str, None]) -> int:
    """Parse string and calculate remaining time in minutes"""
    dep = dateparser.parse(timestr)
    time = dep - datetime.now(dep.tzinfo)
    return time.total_seconds() / 60

if __name__ == "__main__":
    print(time_is_between("06:00:00", "10:00:00", "18:00:00")) # True
    print(time_is_between("06:00:00", "02:00:00", "18:00:00")) # False
    print(time_is_between("06:00:00", "20:00:00", "18:00:00")) # False
    print(time_is_between("18:00:00", "10:00:00", "6:00:00")) # False
    print(time_is_between("18:00:00", "02:00:00", "6:00:00")) # True
    print(time_is_between("18:00:00", "20:00:00", "6:00:00")) # True
    print(time_is_between("10:00:00", "11:00:00", "10:00:00")) # True
