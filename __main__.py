"""
Displays realtime train departures for nearby stations, and upcoming events from the HU calendar.

Authored-By: Maris Baier
Co-Authored-By: Hazel Reimer
"""

from tkinter import Tk
from typing import Callable

from src.artist import GridCanvas, StationArtist, EventArtist, PosterArtist, load_icons
from src.config import Station, Event, Poster, load_data


POSTER_UPDATE_TIME = 180_000
STATION_UPDATE_TIME = 5_000


class App(Tk):
    """MopsDisplay application"""

    def __init__(self):
        super().__init__()

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)

        self.station_canvas = GridCanvas(self)
        self.station_canvas.grid(row=0, column=0, sticky="NESW")
        self.event_canvas = GridCanvas(self)
        self.event_canvas.grid(row=0, column=1, sticky="NESW")

    def update_stations(self, *args, **kwargs): # pylint: disable=unused-argument
        """Update station canvas. Call periodically"""
        self.station_canvas.update()
        self.after(STATION_UPDATE_TIME, self.update_stations) # every 5 seconds

    def update_posters(self, *args, **kwargs): # pylint: disable=unused-argument
        """Update event canvas. Call periodically"""
        self.event_canvas.update()
        self.after(POSTER_UPDATE_TIME, self.update_posters) # every 3 minutes


# create app
app = App()
app.geometry("1280x1024")
# app.attributes("-fullscreen", True)

# load data
stations, events, posters = load_data()

# add stations to canvas
icons = load_icons()
for i, station in enumerate(stations):
    for j in range(len(station.directions)):
        artist = StationArtist(app.station_canvas, station, j, show_title=j==0, icons=icons)
        app.station_canvas.set(i, j, artist)

# add events to canvas
event_artist = EventArtist(app.event_canvas, events)
app.event_canvas.set(1, 0, event_artist)

# add posters to canvas
poster_artist = PosterArtist(app.event_canvas, posters)
app.event_canvas.set(3, 0, poster_artist)
# dummy poster
app.event_canvas.set(5, 0, EventArtist(app.event_canvas, []))

app.update_stations()
app.update_posters()
# app.bind("<Return>", app.update_stations)
# app.bind("<Return>", app.update_posters)
app.mainloop()
