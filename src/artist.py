
from abc import ABC, abstractmethod
from contextlib import suppress
from itertools import cycle
from math import ceil, floor
from pathlib import Path
from tkinter import Canvas
from tkinter.font import Font
from PIL.ImageTk import PhotoImage

from .defines import *
from .config import Station, Event, Poster
from .data import Departure

def fontheight(font: Font):
    return font.metrics("linespace")

def lineheight(font: Font):
    return 1.3 * fontheight(font)

def textheight(text: str, font: Font):
    lines = max(1, text.count("\n"))
    return (0.3 + lines) * fontheight(font)

def textwidth(text: str, font: Font):
    return font.measure(text)

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


class Artist(ABC):
    """Artist with static size"""

    def __init__(self, x, y, width, height, anchor=None):
        if anchor is None:
            anchor = "center" # center = default
        self._anchor = self._validate_corner(anchor)
        self._x = x
        self._y = y
        self._width = int(width)
        self._height = int(height)

    @abstractmethod
    def update_position(self):
        """Perform position update"""
        print(f"move {type(self).__name__: <20} x={self.x} y={self.y}")

    def _validate_corner(self, corner: str|None) -> str:
        if corner is None:
            return "center"
        if corner in corner2center_x:
            return corner
        raise ValueError(f"Unexpected anchor/corner {corner}")

    def _corners_differ(self, corner: str|None) -> bool:
        if corner == self.anchor:
            return False
        return True

    def get_x(self, corner: str|None) -> int:
        """Get x coordinate of a corner"""
        corner = self._validate_corner(corner)
        x = self.x
        if self._corners_differ(corner):
            x = corner2center_x[self.anchor](x, self.width)
            x = center2corner_x[corner](x, self.width)
        return x

    def set_x(self, x: int, corner: str|None):
        """Move x coordinate of a corner to the given value"""
        corner = self._validate_corner(corner)
        self.x += x - self.get_x(corner)

    @property
    def x(self) -> int:
        """Anchor coordinate x"""
        return self._x

    @x.setter
    def x(self, x: float):
        self._x = int(x)

    def get_y(self, corner: str|None) -> int:
        """Get y coordinate of a corner"""
        corner = self._validate_corner(corner)
        y = self.y
        if self._corners_differ(corner):
            y = corner2center_y[self.anchor](y, self.width)
            y = center2corner_y[corner](y, self.width)
        return y

    def set_y(self, y: int, corner: str|None):
        """Move y coordinate of a corner to the given value"""
        corner = self._validate_corner(corner)
        self.y += y - self.get_y(corner)

    @property
    def y(self) -> int:
        """Anchor coordinate y"""
        return self._y

    @y.setter
    def y(self, y: float):
        self._y = int(y)

    @property
    def width(self) -> int:
        """Artist width"""
        return self._width

    @property
    def height(self) -> int:
        """Artist height"""
        return self._height

    @property
    def anchor(self) -> str:
        """Artist anchor
        Possible values: "nw", "n", "ne", "e", "se", "s", "sw", "w", "center"
        """
        return self._anchor


class StackArtist(Artist):
    """Vertical stack of artists, has constant size"""

    def __init__(self, x, y, anchor=None, flush=None, artists: list[Artist]=None):
        self.flush = self._validate_corner(flush)
        self._artists: list[Artist] = [] if artists is None else artists

        height = sum(a.height for a in self._artists)
        width = max(a.width for a in self._artists) if len(self._artists) > 0 else 1
        super().__init__(x, y, width, height, anchor=anchor)

    def update_position(self):
        x = self.get_x(self.flush)
        y = self.get_y("n")
        for artist in self._artists:
            artist.set_x(x, self.flush)
            artist.set_y(y, "n")
            y += artist.height
            artist.update_position()
        return super().update_position()


class DepartureArtist(Artist):
    """Display a departure on a canvas"""

    def __init__(self, canvas: Canvas, anchor: str=None):
        # create artist
        width = WIDTH_ICON + WIDTH_DIRECTION + WIDTH_TIME
        height = lineheight(FONT_DEPARTURE)
        super().__init__(0, 0, width, height, anchor=anchor)

        # create contents
        self.canvas = canvas
        self.last_tripId = None
        self.id_icon = self.canvas.create_image(0, 0, anchor="center")
        self.id_drct = self.canvas.create_text(0, 0, anchor="w", font=FONT_DEPARTURE, fill=COLOR_TXT)
        self.id_time = self.canvas.create_text(0, 0, anchor="e", font=FONT_DEPARTURE, fill=COLOR_TXT)

    def update_position(self):
        # pylint: disable=assignment-from-no-return

        x = self.get_x("w")
        y = self.get_y("w")
        self.canvas.coords(self.id_icon, x + WIDTH_ICON//2, y)
        self.canvas.coords(self.id_drct, x + WIDTH_ICON, y)
        self.canvas.coords(self.id_time, x + self.width, y)

        return super().update_position()

    def update_departure(self, departure: Departure|None):
        """Update departure information"""
        if departure is None:
            self.clear_departure()
            return

        if departure.id != self.last_tripId:
            self.last_tripId = departure.id
            self.canvas.itemconfigure(self.id_icon, image=self._display_icon(departure))
            self.canvas.itemconfigure(self.id_drct, text=self._display_dest(departure), fill=COLOR_TXT)
        self.canvas.itemconfigure(self.id_time, text=self._display_time(departure), fill=self._display_color(departure))

    def clear_departure(self):
        """Clear departure display"""
        self.last_tripId = None
        self.canvas.itemconfigure(self.id_icon, image=None)
        self.canvas.itemconfigure(self.id_drct, text="could not fetch departure", fill=COLOR_ERROR)
        self.canvas.itemconfigure(self.id_time, text=" ")

    def _display_icon(self, departure: Departure) -> PhotoImage:
        icon = ICONS.get(departure.line, None)
        if icon is None:
            icon = ICONS.get(departure.product, None)
            print(f"Warning: Fallback images used for {departure.line}")
        if icon is None:
            icon = ICONS.get("default")
            print(f"Warning: Default images used for {departure.line}")
        return icon

    def _display_dest(self, departure: Departure) -> str:
        width = textwidth(departure.direction, FONT_DEPARTURE)
        idx = -1

        # only return text that fits in available space
        available = WIDTH_DIRECTION
        if width >= available:
            occupied = textwidth("...", FONT_DEPARTURE)
            for i, char in enumerate(departure.direction):
                if occupied >= available:
                    idx = i
                    break
                occupied += textwidth(char, FONT_DEPARTURE)
            return departure.direction[:idx] + "..."

        # TODO: fill with monospaced dots from right if there is space
        return departure.direction

    def _display_time(self, departure: Departure) -> str:
        return str(floor(departure.time_left))

    def _display_color(self, departure: Departure) -> str:
        return COLOR_TXT if departure.reachable else COLOR_NOTIME


class TitleArtist(Artist):
    """Display a title"""

    def __init__(self, canvas: Canvas, text: str, anchor=None):
        height = lineheight(FONT_TITLE)
        super().__init__(0, 0, 1, height, anchor=anchor)

        self.canvas = canvas
        self.id_title = self.canvas.create_text(0, 0, text=text, anchor=self.anchor, font=FONT_TITLE, fill=COLOR_TXT)

    def update_position(self):
        self.canvas.coords(self.id_title, self.x, self.y)
        return super().update_position()


class EventArtist(Artist):
    """Display event information"""

    def __init__(self, canvas: Canvas, event: Event, anchor=None):
        width = WIDTH_DATE + WIDTH_EVENT
        height = max(textheight(event.date, FONT_EVENT), textheight(event.desc, FONT_EVENT))
        super().__init__(0, 0, width, height, anchor=anchor)

        self.canvas = canvas
        self.id_date = self.canvas.create_text(0, 0, text=event.date, anchor="nw", font=FONT_EVENT, fill=COLOR_TXT)
        self.id_desc = self.canvas.create_text(0, 0, text=event.desc, anchor="nw", font=FONT_EVENT, fill=COLOR_TXT)

    def update_position(self):
        x = self.get_x("nw")
        y = self.get_y("nw")
        self.canvas.coords(self.id_date, x, y)
        self.canvas.coords(self.id_desc, x+WIDTH_DATE, y)
        return super().update_position()


class PosterArtist(Artist):
    """Display cycling posters"""

    def __init__(self, canvas: Canvas, posters: list[Poster], anchor=None):
        super().__init__(0, 0, WIDTH_POSTER, HEIGHT_POSTER, anchor=anchor)

        self.canvas = canvas
        self.posters = cycle(p.img for p in posters)
        self.id_poster = self.canvas.create_image(0, 0, image=next(self.posters), anchor="center")

    def update_position(self):
        self.canvas.coords(self.id_poster, self.get_x("center"), self.get_y("center"))
        return super().update_position()

    def update_poster(self):
        """Cycle to next poster"""
        self.canvas.itemconfigure(self.id_poster, image=next(self.posters))


class GridCanvas(Canvas):
    """Canvas that evenly aligns artists in a grid"""

    def __init__(self, master):
        super().__init__(master, background=COLOR_BG, highlightthickness=0)
        self.bind("<Configure>", self.on_resize)

        self.artists: dict[tuple[int, int], Artist] = {}

    def set(self, row: int, col: int, artist: Artist):
        """Set artist to position"""
        self.artists[row, col] = artist

    def get(self, row: int, col: int, *default) -> Artist:
        """Get artist at position"""
        return self.artists.get((row, col), *default)

    def pop(self, row: int, col: int, *default) -> Artist:
        """Pop artist from position"""
        return self.artists.pop((row, col), *default)

    def query_size(self):
        """Get row and column sizes (widths, heights)"""
        widths = []
        heights = []
        for (row, col), artist in self.artists.items():
            while len(heights) <= row:
                heights.append(0)
            while len(widths) <= col:
                widths.append(0)
            heights[row] = max(heights[row], artist.height)
            widths[col] = max(widths[col], artist.width)
        return widths, heights

    def on_resize(self, event):
        """Canvas resize event callback, venly space artists"""
        print("move", type(self))

        widths, heights = self.query_size()
        padx = (event.width  - sum(widths) ) / (1 + len(widths) )
        pady = (event.height - sum(heights)) / (1 + len(heights))

        center_x = corner2center_x["nw"]
        center_y = corner2center_y["nw"]
        y = pady
        for row, height in enumerate(heights):
            x = padx
            for col, width in enumerate(widths):
                artist = self.artists.get((row, col), None)
                if artist is not None:
                    # align artist towards its anchor
                    # only has an effect if artists have different sizes
                    # artist.x = center2corner_x[artist.anchor](center_x(x, width), width)
                    # artist.y = center2corner_y[artist.anchor](center_y(y, height), height)
                    artist.set_x(x, "nw")
                    artist.set_y(y, "nw")
                    artist.update_position()
                x += width + padx
            y += height + pady
