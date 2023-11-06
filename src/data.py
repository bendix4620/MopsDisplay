"""Fetch departures of stations from BVG API"""

from __future__ import annotations
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from dateutil import parser as dateparser
from PIL.ImageTk import PhotoImage
import requests


session = requests.Session()


class _Required:
    """Use as dataclass_enfore_required field default to flag it as required"""
required = _Required

def do_nothing(*args, **kwargs): # pylint: disable=unused-argument
    """do nothing"""

def enforce_required(cls):
    """Class decorator. Return a dataclass and enforce presence of keyword 
    fields flagged as required.
    
    Wraps __post_init__ to raise TypeError if a field value is set to required
    """
    __post_init__ = getattr(cls, "__post_init__", do_nothing)

    # the new init function
    @wraps(__post_init__)
    def __new_post_init__(self):
        # look for required fields
        for name, field in self.__dict__.items():
            if field is required:
                raise TypeError(f"{type(self).__name__} missing required keyword argument: '{name}'")

        # call original __post_init__
        __post_init__(self)

    cls.__post_init__ = __new_post_init__
    return cls


@dataclass(frozen=True)
@enforce_required
class Event:
    """Event data"""
    date: str = required
    desc: str = required


@dataclass(frozen=True)
@enforce_required
class Poster:
    """Poster data"""
    images: list[PhotoImage] = required

    def __post_init__(self):
        # ensure that images is iterable
        try:
            _ = iter(self.images)
        except TypeError:
            object.__setattr__(self, "images", [self.images])


@dataclass(frozen=True)
@enforce_required
class Station:
    """Station data"""
    name: str
    id: str
    departure_rows: int
    departure_cols: int

    # fetch during day time
    S_day: bool # fetch suburban
    U_day: bool # fetch subway
    T_day: bool # fetch tram
    B_day: bool # fetch bus
    F_day: bool # fetch ferry
    E_day: bool # fetch express
    R_day: bool # fetch regional

    # fetch during night time
    S_night: bool # fetch suburban
    U_night: bool # fetch subway
    T_night: bool # fetch tram
    B_night: bool # fetch bus
    F_night: bool # fetch ferry
    E_night: bool # fetch express
    R_night: bool # fetch regional

    start_night: str # start of night service
    stop_night: str # end of night service

    # times given in minutes
    min_time: float # min time left for fetched departures
    max_time: float # max time left for fetched departures
    time_needed: float # time needed to reach station


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
                f"results={self.departure_rows*self.departure_cols}&"
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
        response = session.get(url, timeout=30_000)
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            data = {"departures": []}

        for departure_data in data.get("departures", []):
            yield self._create_departure(departure_data)

    def _create_departure(self, data: dict):
        """Departure factory"""
        # TODO: what to do with time_left<0 departures?
        line = data.get("line", None)
        time = None
        reachable=False
        with suppress(Exception):
            time = time_left(data["when"])
            reachable = time > self.time_needed

        departure = Departure(
            id=data.get("tripId", None),
            line=line.get("id", None),
            direction=data.get("direction", None),
            time_left=time,
            delay=data.get("delay", None),
            product=data.get("product", None),
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

def time_left(timestr: str|None) -> int:
    """Parse string and calculate remaining time in minutes"""
    dep = dateparser.parse(timestr)
    time = dep - datetime.now(dep.tzinfo)
    return time.total_seconds() / 60
