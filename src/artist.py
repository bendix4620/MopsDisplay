"""Artists that dynamically position canvas items"""

from __future__ import annotations
from abc import ABC, abstractmethod
from itertools import cycle
from pathlib import Path
from tkinter import Canvas
from PIL import Image, ImageTk

from .config import Station, Event, Poster
from .departure import Departure, fetch_departures



FONT_TITLE = ("Helvetica", 28, "bold") # font of titles
FONT_TEXT = ("Helvetica", 17, "bold") # font of text

# heights include padding on the bottom
# widths include padding to the right

# (2 = 16/12 * 3/2 = px/pt + 50% padding)
HEIGHT_TITLE = FONT_TITLE[1] * 2 # height of titles
HEIGHT_TEXT = FONT_TEXT[1] * 2 # height of text

HEIGHT_POSTER = 500 # maximum height of poster
WIDTH_POSTER = 500 # maximum width of poster

WIDTH_DATE = 80 # width of event date
WIDTH_EVENT = 300 # width of event description text

WIDTH_ICON = 50 # width of departure line icon
WIDTH_DEST = 200 # width of departure destination
WIDTH_TIME = 30 # width of departure time

COLOR_BG = "#202020" # background color
COLOR_TEXT = "#ffffff" # text color
COLOR_TEXT_NOTIME = "#d03030" # text color if time is too short
COLOR_TEXT_ERROR = "#807070" # text color if nothing can be displayed

# TODO: use a cleaner alternative
_ERROR_DEPARTURE = Departure(line="empty", dest="no data", time=0, delay=0, product="error", reachable=False) # pylint: disable=line-too-long


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
    image.thumbnail((WIDTH_ICON, FONT_TEXT[1]*16//12))
    return ImageTk.PhotoImage(image)



class GridCanvas(Canvas):
    """Canvas that evenly spaces artists"""

    def __init__(self, master):
        super().__init__(master, bg=COLOR_BG, highlightthickness=0)
        self.bind("<Configure>", self.on_resize)

        self.artists = {}
        self.rows = 0
        self.cols = 0

    def on_resize(self, event):
        """Move all contents on the canvas"""
        rpad = event.height / (2*self.rows)
        cpad = event.width / (2*self.cols)
        for (row, col), artist in self.artists.items():
            artist.x = cpad*(1 + 2*col)
            artist.y = rpad*(1 + 2*row)

    def get(self, row: int, col: int) -> None | Artist:
        """Get artist on position (row, col)"""
        return self.artists.get((row, col), None)

    def set(self, row: int, col:int, value: Artist):
        """Insert artist on position (row, col)"""
        self.rows = max(row+1, self.rows)
        self.cols = max(col+1, self.cols)
        self.artists[(row, col)] = value

    def pop(self, row: int, col:int) -> None | Artist:
        """Pop artist on position (row, col)
        Warning: Does NOT reduce number of rows and columns automatically
        """
        return self.artists.pop((row, col))

    def update(self):
        """Update items of all artists"""
        for artist in self.artists.values():
            artist.update()


class Artist(ABC):
    """Artist base class"""

    def __init__(self, canvas: GridCanvas, x: int, y: int):
        self.canvas = canvas
        self._x = x
        self._y = y

    @abstractmethod
    def on_resize(self):
        """Actions to be done on resize/move"""

    @property
    @abstractmethod
    def width(self) -> int:
        """Artist width"""

    @property
    @abstractmethod
    def height(self) -> int:
        """Artist height"""

    @property
    def x(self) -> int:
        """Center coordinate x"""
        return self._x

    @x.setter
    def x(self, val: int):
        self._x = val
        self.on_resize()

    @property
    def y(self) -> int:
        """Center coordinate y"""
        return self._y

    @y.setter
    def y(self, val: int):
        self._y = val
        self.on_resize()

    @property
    def x_nw(self) -> int:
        """Anchor coordinate x (nw)"""
        return self.x - self.width//2

    @x_nw.setter
    def x_nw(self, val: int):
        self.x = val + self.width//2

    @property
    def y_nw(self) -> int:
        """Anchor coordinate y (nw)"""
        return self.y - self.height//2

    @y_nw.setter
    def y_nw(self, val: int):
        self.y = val + self.height//2

    @abstractmethod
    def update(self):
        """Update artist items"""


class StationArtist(Artist):
    """Display station information"""

    def __init__(self, canvas: GridCanvas, station: Station, direction: int,
                 show_title: bool=False, icons: dict[str, ImageTk.PhotoImage]=None):
        super().__init__(canvas, 0, 0)

        self.station = station
        self.direction = direction # also the column
        self.show_title = show_title
        self.icons = icons
        if self.icons is None:
            self.icons = {"default": None}

        # create items
        self._create_title()
        self.id_departures: list[tuple[int, int, int]] = []
        for _ in range(station.max_departures):
            self._create_departure()
        self.on_resize()

    def _create_title(self):
        text = self.station.name if self.show_title else " "
        self.id_title = self.canvas.create_text(0, 0, text=text,
            font=FONT_TITLE, fill=COLOR_TEXT, anchor="nw")

    def _create_departure(self):
        id_icon = self.canvas.create_image(0, 0, anchor="nw")
        # id_icon = self.canvas.create_rectangle(0, 0, 20, 20, fill="#00ff00")
        id_dest = self.canvas.create_text(0, 0, text="",
            font=FONT_TEXT, fill=COLOR_TEXT, anchor="nw")
        id_time = self.canvas.create_text(0, 0, text="",
            font=FONT_TEXT, fill=COLOR_TEXT, anchor="nw")

        self.id_departures.append((id_icon, id_dest, id_time))

    def _place_departure(self, i: int):
        id_icon, id_dest, id_time = self.id_departures[i]
        y_nw = self.y_nw + HEIGHT_TITLE + HEIGHT_TEXT*i
        x_nw = self.x_nw
        self.canvas.coords(id_icon, x_nw, y_nw)
        x_nw += WIDTH_ICON
        self.canvas.coords(id_dest, x_nw, y_nw)
        x_nw += WIDTH_DEST
        self.canvas.coords(id_time, x_nw, y_nw)

    def on_resize(self):
        self.canvas.coords(self.id_title, self.x_nw, self.y_nw)
        for i in range(len(self.id_departures)):
            self._place_departure(i)

    @property
    def width(self) -> int:
        return WIDTH_ICON + WIDTH_DEST + WIDTH_TIME

    @property
    def height(self) -> int:
        return HEIGHT_TITLE + HEIGHT_TEXT * self.station.max_departures

    def update(self):
        """Update departure informations, call regularily"""
        data_departures = fetch_departures(self.station, self.direction)
        for i, departure in enumerate(data_departures):
            if i >= len(data_departures):
                self._update_departure(i, _ERROR_DEPARTURE)
            self._update_departure(i, departure)

    def _update_departure(self, i: int, departure: Departure):
        id_icon, id_dest, id_time = self.id_departures[i]
        self.canvas.itemconfigure(id_icon, image=self._get_icon(departure))
        self.canvas.itemconfigure(id_dest, text=departure.dest)
        self.canvas.itemconfigure(id_time, text=self._get_time(departure),
                                           fill=self._get_color(departure))
        # log entries that are too large
        bbox = self.canvas.bbox(id_dest)
        width = bbox[2]-bbox[0]
        if width > WIDTH_DEST:
            print(f"Destination too large ({width: <3} > {WIDTH_DEST: <3}): {departure.dest}")

    def _get_icon(self, departure: Departure) -> ImageTk.PhotoImage:
        # TODO: use bus image if SEV?
        icon = self.icons.get(departure.line, None)
        if icon is None:
            icon = self.icons.get(departure.product, None)
            print(f"Warning: Fallback images used for {departure.line}")
        if icon is None:
            icon = self.icons["default"]
            print(f"Warning: Default images used for {departure.line}")
        return icon

    def _get_color(self, departure: Departure):
        if departure.product == "error":
            return COLOR_TEXT_ERROR
        if not departure.reachable:
            return COLOR_TEXT_NOTIME
        return COLOR_TEXT

    def _get_time(self, departure: Departure) -> str:
        if departure.product == "error":
            return ""
        return str(departure.time)


class EventArtist(Artist):
    """Display events"""

    def __init__(self, canvas: GridCanvas, events: list[Event]):
        super().__init__(canvas, 0, 0)

        self.id_events: list[tuple[int, int]] = []
        for event in events:
            self._create_event(event)
        self.on_resize()

    def _create_event(self, event: Event):
        id_date = self.canvas.create_text(0, 0, text=event.date,
            font=FONT_TEXT, fill=COLOR_TEXT, anchor="nw")
        id_desc = self.canvas.create_text(0, 0, text=event.desc,
            font=FONT_TEXT, fill=COLOR_TEXT, anchor="nw")
        self.id_events.append((id_date, id_desc))

    def _place_event(self, i: int):
        id_date, id_desc = self.id_events[i]
        y = self.y_nw + HEIGHT_TEXT*i
        x = self.x_nw
        self.canvas.coords(id_date, x, y)
        x += WIDTH_DATE
        self.canvas.coords(id_desc, x, y)

    def on_resize(self):
        for i in range(len(self.id_events)):
            self._place_event(i)

    @property
    def width(self) -> int:
        return WIDTH_DATE + WIDTH_EVENT

    @property
    def height(self) -> int:
        return HEIGHT_TEXT * len(self.id_events)

    def update(self):
        pass


class PosterArtist(Artist):
    """Display and cycle through posters"""

    def __init__(self, canvas: GridCanvas, posters: list[Poster]):
        super().__init__(canvas, 0, 0)

        self.id_poster = self.canvas.create_image(self.x, self.y, anchor="center")
        self.posters = cycle([self._load_poster(poster) for poster in posters])

    def _load_poster(self, poster: Poster):
        image = Image.open(poster.img)
        image.thumbnail((WIDTH_POSTER, HEIGHT_POSTER))
        return ImageTk.PhotoImage(image)

    def on_resize(self):
        self.canvas.coords(self.id_poster, self.x, self.y)

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def x_nw(self) -> int:
        return self.bbox[0]

    @property
    def y_nw(self) -> int:
        return self.bbox[1]

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Artist bounding box"""
        return self.canvas.bbox(self.id_poster)

    def update(self):
        """Cycle to next poster"""
        p = next(self.posters)
        print("p", p)
        self.canvas.itemconfigure(self.id_poster, image=p)
