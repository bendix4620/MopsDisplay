from __future__ import annotations
from contextlib import suppress
from itertools import cycle
from math import floor
from pathlib import Path
from tkinter import Canvas
from tkinter.font import Font
from typing import Self
from PIL import Image, ImageTk, ImageFont

from .config import Station, Event, Poster
from .departure import Departure, fetch_departures
from .grid import Cell, Grid

ICON_WIDTH = ICON_HEIGHT = 25

def load_icons() -> dict[str, ImageTk.PhotoImage]:
    """Load tkinter images. 
    Must run after App creation and before fetching departures
    """
    path = Path(__file__).parents[1].resolve() / "data" / "lines"
    files = path.glob("*.png")
    icons = {file.stem: _load_icon(file) for file in files}
    print(icons.keys())
    return icons

def _load_icon(path: Path) -> Image.Image:
    image = Image.open(path)
    image.thumbnail((ICON_WIDTH, ICON_HEIGHT))
    return ImageTk.PhotoImage(image)



class DepartureArtist(Grid):
    WIDTHS       = [2, 10, 1] # icon, destination, time width weights
    FONT_DEFUALT = ("Helvetica", 14, "bold")
    COLOR_TXT    = "#ffffff"
    COLOR_NOTIME = "#d22222"
    COLOR_ERROR  = "#a0a0a0"

    def __init__(
            self,
            cell: Cell,
            canvas: Canvas, 
            icons: dict[str, ImageTk.PhotoImage]=None, 
            font: Font=None
    ):
        super().__init__(cell, col_weights=self.WIDTHS)

        self.canvas = canvas
        self.icons = icons
        if self.icons is None:
            self.icons = {"default": None}
        self.font = font
        if self.font is None:
            self.font = Font(font=self.FONT_DEFAULT)

        self.last_tripId = None
        self.dest_space = 0

        # create items
        cell = self.get_cell(0, 0, anchor="center")
        self.id_icon = self.canvas.create_image(cell.x, cell.y, anchor="center")

        cell = self.get_cell(0, 1, anchor="w")
        self.dest_space = cell.width
        self.id_dest = self.canvas.create_text(cell.x, cell.y, anchor="w", font=self.FONT, fill=self.COLOR_TXT)
        
        cell = self.get_cell(0, 1, anchor="e")
        self.id_time = self.canvas.create_text(cell.x, cell.y, anchor="e", font=self.FONT, fill=self.COLOR_TXT)

    def update_departure(self, departure: Departure|None):
        if departure is None:
            self.last_tripId = None
            self.canvas.itemconfigure(self.id_icon, image=None)
            self.canvas.itemconfigure(self.id_dest, text="could not fetch departure", fill=self.COLOR_ERROR)
            self.canvas.itemconfigure(self.id_time, text=" ")
            return

        if departure.id != self.last_tripId:
            self.last_tripId = departure.id
            self.canvas.itemconfigure(self.id_icon, image=self._display_icon(departure))
            self.canvas.itemconfigure(self.id_dest, text=self._display_dest(departure), fill=self.COLOR_TXT)
        self.canvas.itemconfigure(self.id_time, text=self._display_time(departure), fill=self._display_color(departure))

    def _display_icon(self, departure: Departure) -> ImageTk.PhotoImage:
        icon = self.icons.get(departure.line, None)
        if icon is None:
            icon = self.icons.get(departure.product, None)
            print(f"Warning: Fallback images used for {departure.line}")
        if icon is None:
            icon = self.icons.get("default")
            print(f"Warning: Default images used for {departure.line}")
        return icon
    
    def _display_dest(self, departure: Departure) -> str:
        width = self.font.measure(departure.dest)
        idx = -1

        # only return text that fits in available space
        if width >= self.dest_space:
            available = self.dest_space
            occupied = self.font.measure("...")
            for i, char in enumerate(departure.dest):
                if occupied >= available:
                    idx = i
                    break
                occupied += self.font.measure(char)
        return departure.dest[:idx] + "..."

    def _display_time(self, departure: Departure) -> str:
        return str(floor(departure.time))

    def _display_color(self, departure: Departure) -> str:
        return self.COLOR_TXT if departure.reachable else self.COLOR_NOTIME


class DirectionArtist(Grid):
    """Display station information for a direction"""

    WEIGHT_TITLE = 3
    WEIGHT_TXT   = 1
    FONT_DEFAULT = ("Helvetica", 24, "bold")
    COLOR_TXT    = "#ffffff"

    def __init__(
            self, 
            cell: Cell,
            canvas: Canvas,
            station: Station,
            direction: str,
            show_title: bool=True,
            font_title: Font=None, 
            font_departure: Font=None,
            icons: dict[str, ImageTk.PhotoImage]=None, 
            *args, **kwargs
    ):
        row_weights = [self.WEIGHT_TITLE]+[self.WEIGHT_TXT]*station.max_departures
        super().__init__(cell, row_weights=row_weights)

        self.canvas = canvas

        if direction not in station.directions:
            raise ValueError(f"Direction {direction} is not available on station {station.name}")
        self.station = station
        self.direction = direction

        self.show_title = show_title
        if font_title is None:
            font_title = Font(font=self.FONT_DEFAULT)
        self.font = font_title

        # create title
        if self.show_title:
            cell = self.get_cell(0, 0, col_span=len(self.station.directions), anchor="w")
            self.canvas.create_text(cell.x, cell.y, text=station.name, font=self.font, fill=self.COLOR_TXT, anchor="w")
        
        # create departures
        self.departure_artists: list[DepartureArtist] = []
        for row in range(station.max_departures):
            cell = self.get_cell(1+row, 0)
            artist = DepartureArtist(self.canvas, icons=icons, font=font_departure, cell.x, cell.y, )
            self.departure_artists.append(artist)
        self.resize()

    def _on_resize(self):
        # place station title
        if self.show_title:
            self.canvas.coords(self.id_title, cell.x, cell.y)

        # place departures
        for row in range(self.station.max_departures):
            cell = self.get_cell(1+row) # +1 row for title
            artist = self.departure_artists[row]
            artist.bind_to_cell(cell)
        return super()._on_resize()

    def update(self):
        """Update departure informations, call regularily"""
        departures = fetch_departures(self.station, self.direction)
        for row in range(self.station.max_departures):
            departure = None
            with suppress(IndexError):
                departure = departures[row]
            artist = self.departure_artists[row]
            artist.update_departure(departure)


class EventArtist(Grid):
    """Display events"""
    WEIGHTS_COLS  = [1, 10] # date, description width weight
    WEIGHT_EVENT  = 1
    WEIGHT_POSTER = 10
    FONT_DEFUALT  = ("Helvetica", 14, "bold")
    COLOR_TXT     = "#ffffff"

    def __init__(self,
            cell: Cell,
            canvas: Canvas,
            events: list[Event],
            posters: list[Poster],
            font: Font=None,
    ):
        row_weights = [self.WEIGHT_EVENT]*len(events)+[self.WEIGHT_POSTER]
        super().__init__(cell, row_weights=row_weights, col_weights=self.WEIGHTS_COLS)

        self.canvas = canvas
        if font is None:
            font = Font(font=self.FONT_DEFAULT)
        self.font = font
        font.metrics

        # events
        self.id_events: list[tuple[int, int]] = []
        for i, event in enumerate(events):
            self._create_event(event)

        # posters
        self.posters = posters
        self.images = cycle([])
        self.id_poster = self.canvas.create_image(0, 0, anchor="center")
        self.resize()

    def _create_event(self, event: Event):
        id_date = self.canvas.create_text(0, 0, text=event.date,
            font=self.font, fill=self.COLOR_TXT, anchor="e")
        id_desc = self.canvas.create_text(0, 0, text=event.desc,
            font=self.font, fill=self.COLOR_TXT, anchor="w")
        self.id_events.append((id_date, id_desc))

    def _load_poster(self, poster:Poster, width: int, height: int):
        image = Image.open(poster.img)
        image.thumbnail((width, height))
        return ImageTk.PhotoImage(image)

    def _on_resize(self):
        # events
        for row, (id_date, id_desc) in enumerate(self.id_events):
            cell = self.get_cell(row, 0, anchor="e")
            self.canvas.coords(id_date, cell.x, cell.y)
            cell = self.get_cell(row, 1, anchor="w")
            self.canvas.coords(id_desc, cell.x, cell.y)
        
        # posters
        cell = self.get_cell(-1, 0, row_span=2, anchor="center")
        self.images = cycle([self._load_poster(poster, cell.width, cell.height) 
                             for poster in self.posters])
        self.canvas.coords(self.id_poster, cell.x, cell.y)
        self.update()

    def update(self):
        """Cycle to next poster"""
        self.canvas.itemconfigure(self.id_poster, image=next(self.images))
