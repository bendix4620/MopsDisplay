"""
Displays realtime train departures for nearby stations, and upcoming events from the HU calendar.

Authored-By: Maris Baier
Co-Authored-By: Hazel Reimer
"""

from collections import namedtuple
from itertools import zip_longest
from tkinter import Canvas
from src import root
from src.defines import *
from src.data import Event, Poster, Station, Departure
from src.config import load_data
from src.artist import StackArtist, DepartureArtist, TitleArtist, EventArtist, PosterArtist, GridCanvas

root.geometry("1280x1024")
# root.attributes("-fullscreen", True)
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=2)
root.columnconfigure(1, weight=1)

def create_departures(canvas: GridCanvas, row: int, station: Station) -> list[DepartureArtist]:
    """Create departures for a station"""
    artists = []
    for col in range(station.departure_cols):
        stacked_artists = [DepartureArtist(canvas, anchor="w") 
                           for _ in range(station.departure_rows)]
        stack = StackArtist(0, 0, anchor="w", flush="w", artists=stacked_artists)

        artists += stacked_artists
        canvas.set(row, col, stack)
    return artists

def update_departures(station: Station, artists: list[DepartureArtist]):
    """update departures of a station"""
    for departure, artist in zip_longest(station.fetch_departures(), artists):
        if artist is None:
            break
        artist.update_departure(departure)

def update_stations():
    """periodically update stations"""
    for station, artists in station_departure_artists:
        update_departures(station, artists)
    root.after(STATION_UPDATE_TIME, update_stations)

stations, events, posters = load_data()

# create stations
station_canvas = GridCanvas(root)
station_canvas.grid(row=0, column=0, sticky="NESW")

station_departure_artists: list[tuple[Station, list[DepartureArtist]]] = []
row = 0
for station in stations:
    print(station.name)
    title = TitleArtist(station_canvas, station.name, anchor="w")
    station_canvas.set(row, 0, title)
    row += 1
    artists = create_departures(station_canvas, row, station)
    station_departure_artists.append((station, artists))
    row += 1

update_stations()


# create events and posters
# event_canvas = ColumnCanvas(root)

root.mainloop()
