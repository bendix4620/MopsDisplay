"""Artists that dynamically position canvas items"""

from __future__ import annotations
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

corner2center_x = {
    "nw": lambda x, w: x+w/2,
    "ne": lambda x, w: x-w/2,
    "se": lambda x, w: x-w/2,
    "sw": lambda x, w: x+w/2,
    "n":  lambda x, w: x,
    "e":  lambda x, w: x-w/2,
    "s":  lambda x, w: x,
    "w":  lambda x, w: x+w/2,
    "center": lambda x, w: x,
}

center2corner_x = {
    "nw": lambda x, w: x-w/2,
    "ne": lambda x, w: x+w/2,
    "se": lambda x, w: x+w/2,
    "sw": lambda x, w: x-w/2,
    "n":  lambda x, w: x,
    "e":  lambda x, w: x+w/2,
    "s":  lambda x, w: x,
    "w":  lambda x, w: x-w/2,
    "center": lambda x, w: x
}

corner2center_y = {
    "nw": lambda y, h: y+h/2,
    "ne": lambda y, h: y+h/2,
    "se": lambda y, h: y-h/2,
    "sw": lambda y, h: y-h/2,
    "n":  lambda y, h: y-h/2,
    "e":  lambda y, h: y,
    "s":  lambda y, h: y+h/2,
    "w":  lambda y, h: y,
    "center": lambda y, h: y
}

center2corner_y = {
    "nw": lambda y, h: y-h/2,
    "ne": lambda y, h: y-h/2,
    "se": lambda y, h: y+h/2,
    "sw": lambda y, h: y+h/2,
    "n":  lambda y, h: y+h/2,
    "e":  lambda y, h: y,
    "s":  lambda y, h: y-h/2,
    "w":  lambda y, h: y,
    "center": lambda y, h: y
}

class Cell:
    """Cell of a grid"""


    def __init__(self, x, y, width, height, anchor="center"):
        self.anchor = anchor

        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def _corners_differ(self, corner: str|None) -> bool:
        if corner is None:
            return False
        if corner == self.anchor:
            return False
        return True

    def get_x(self, corner: str|None) -> int:
        """Get x coordinate of a corner"""
        x = self.x
        if self._corners_differ(corner):
            x = corner2center_x[self.anchor](x, self.width)
            x = center2corner_x[corner](x, self.width)
        return x

    def set_x(self, x: int, corner: str|None):
        """Move x coordinate of a corner to the given value"""
        old_x = self.get_x(corner=corner)
        self.x += x - old_x

    @property
    def x(self) -> int:
        """Anchor coordinate x"""
        return self._x

    @x.setter
    def x(self, x: int):
        self._x = x

    def get_y(self, corner: str|None) -> int:
        """Get y coordinate of a corner"""
        y = self.y
        if self._corners_differ(corner):
            y = corner2center_y[self.anchor](y, self.width)
            y = center2corner_y[corner](y, self.width)
        return y

    def set_y(self, y: int, corner: str|None):
        """Move y coordinate of a corner to the given value"""
        old_y = self.get_y(corner=corner)
        self.y += y - old_y

    @property
    def y(self) -> int:
        """Anchor coordinate y"""
        return self._y

    @y.setter
    def y(self, y: int):
        self._y = y


def normal(weights: list[float]) -> list[float]:
    """Iterate over normalized weights"""
    N = sum(weights)
    return [w/N for w in weights]

class Grid(Cell):
    """Canvas that evenly spaces artists"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 row_weights: list[float]=None, col_weights: list[float]=None,
                 anchor="center"):
        super().__init__(x, y, width, height, anchor=anchor)

        self._cw = col_weights
        if self._cw is None:
            self._cw = []

        self._rw = row_weights
        if self._rw is None:
            self._rw = []

    def append_row(self, weight: float):
        """Append a row with weight"""
        self._rw.append(weight)

    def pop_row(self) -> float:
        """Pop rows"""
        return self._rw.pop()

    def append_col(self, weight: float):
        """Append a column with weights"""
        self._cw.append(weight)

    def pop_col(self) -> float:
        """Pop columns"""
        return self._cw.pop()

    def get_cell(self, row: int, col: int, anchor="center") -> Cell:
        """Get grid cell at (row, col)"""
        cweights = normal(self._cw)
        rweights = normal(self._cw)

        width = cweights[col]*self.width
        height = rweights[row]*self.height
        xnw = self.get_x(corner="nw") + cweights[:col]*self.width
        ynw = self.get_y(corner="nw") + rweights[:row]*self.height

        cell = Cell(0, 0, width, height, anchor=anchor)
        cell.set_x(xnw, corner="nw")
        cell.set_y(ynw, corner="nw")
        return cell



class StationArtist(Grid):
    """Display station information"""

    def __init__(self, canvas: Canvas, station: Station, direction: int,
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
