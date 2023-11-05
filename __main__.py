"""
Displays realtime train departures for nearby stations, and upcoming events from the HU calendar.

Authored-By: Maris Baier
Co-Authored-By: Hazel Reimer
"""

from itertools import zip_longest
from functools import wraps
import time
from src import root
from src.defines import *
from src.data import Event, Poster, Station, Departure
from src.config import load_data
from src.artist import StackArtist, DepartureArtist, TitleArtist, EventArtist, PosterArtist, GridCanvas


type StationArtist = tuple[Station, list[DepartureArtist]]

STATION_ARTISTS: list[StationArtist] = []
EVENT_ARTISTS: list[EventArtist] = []
POSTER_ARTISTS: PosterArtist = []



def timed(func):
    """Decorator that measures function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        if DEBUG:
            print(f'{func.__name__} took {total_time:.4f} seconds')
        return result
    return wrapper

def update_stations():
    """periodically update stations"""
    for station, artists in STATION_ARTISTS:
        update_departures(station, artists)
    root.after(STATION_UPDATE_TIME, update_stations)

def update_events():
    """periodically update events"""
    # events currently dont update
    root.after(EVENT_UPDATE_TIME, update_events)

def update_posters():
    """periodically update posters"""
    for artist in POSTER_ARTISTS:
        artist.update_poster()
    root.after(POSTER_UPDATE_TIME, update_posters)

def update_departures(station: Station, artists: list[DepartureArtist]):
    """update departures of a station"""
    for departure, artist in zip_longest(station.fetch_departures(), artists):
        if artist is None:
            break
        artist.update_departure(departure)


def create_station_artist(canvas: GridCanvas, row: int, station: Station) -> StationArtist:
    """Create departures for a station"""
    title = station.name
    artists = []
    for col in range(station.departure_cols):
        title_artist = TitleArtist(canvas, title, anchor="w")
        title = ""

        departure_artists = [DepartureArtist(canvas, anchor="w") for _ in range(station.departure_rows)]
        stack = StackArtist(canvas, 0, 0, anchor="w", flush="w", artists=[title_artist] + departure_artists)

        artists += departure_artists
        canvas.set(row, col, stack)
    return station, artists


def main(root):
    # define root geometry
    # ------------------------------------------------------------------------------
    root.geometry("1280x1024")
    root.rowconfigure(0, weight=0)
    root.rowconfigure(1, weight=1)
    root.columnconfigure(0, weight=3)
    root.columnconfigure(1, weight=1)
    # root.attributes("-fullscreen", True)

    stations, events, posters = load_data()

    # create stations
    # ---------------
    station_canvas = GridCanvas(root, flush="w", background=COLOR_BG_STATION, highlightthickness=0)
    station_canvas.grid(row=0, column=0, rowspan=2, sticky="NESW")

    for row, station in enumerate(stations):
        artist = create_station_artist(station_canvas, row, station)
        STATION_ARTISTS.append(artist)


    # create events and posters
    # -------------------------
    event_canvas = GridCanvas(root, flush="center", background=COLOR_BG_EVENT, highlightthickness=0)
    event_canvas.grid(row=1, column=1, sticky="NSEW")

    for event in events:
        event_artist = EventArtist(event_canvas, event)
        EVENT_ARTISTS.append(event_artist)
    title_artist = TitleArtist(event_canvas, "nächste Veranstaltungen:\n", font=FONT_EVENT, anchor="w")
    stack = StackArtist(event_canvas, 0, 0, anchor="center", flush="w", artists=[title_artist] + EVENT_ARTISTS)
    event_canvas.set(0, 0, stack)
    offset = 1

    for row, poster in enumerate(posters):
        artist = PosterArtist(event_canvas, poster)
        event_canvas.set(offset+row, 0, artist)
        POSTER_ARTISTS.append(artist)
    
    # create clock and hu logo
    # ------------------------
    logo_canvas = GridCanvas(root, flush="nw", background=COLOR_BG_EVENT, highlightthickness=0)
    logo_canvas.grid(row=0, column=1, sticky="NESW")
    # TODO: create clock and hu logo

    root.after(0, update_stations)
    root.after(0, update_posters)
    root.mainloop()

if __name__ == "__main__":
    main(root)
