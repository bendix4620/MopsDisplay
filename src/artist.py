
from abc import ABC, abstractmethod
from contextlib import suppress
from itertools import cycle
from math import ceil, floor
from pathlib import Path
from tkinter import Canvas
from tkinter.font import Font
from PIL.ImageTk import PhotoImage

from .defines import * # pylint: disable=wildcard-import,unused-wildcard-import
from .debug import * # pylint: disable=wildcard-import,unused-wildcard-import
from .config import Station, Event, Poster
from .data import Departure

def fontheight(font: Font):
    return font.metrics("linespace")

def lineheight(font: Font):
    return 1.3 * fontheight(font)

def textheight(text: str, font: Font):
    lines = 1 + text.count("\n")
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
    "n":  lambda y, h: y+h/2,
    "e":  lambda y, h: y,
    "s":  lambda y, h: y-h/2,
    "w":  lambda y, h: y,
    "center": lambda y, h: y
}

center2corner_y = {
    "nw": lambda y, h: y-h/2,
    "ne": lambda y, h: y-h/2,
    "se": lambda y, h: y+h/2,
    "sw": lambda y, h: y+h/2,
    "n":  lambda y, h: y-h/2,
    "e":  lambda y, h: y,
    "s":  lambda y, h: y+h/2,
    "w":  lambda y, h: y,
    "center": lambda y, h: y
}

def _validate_corner(corner: str|None) -> str:
    if corner is None:
        return "center"
    if corner in corner2center_x:
        return corner
    raise ValueError(f"Unexpected anchor/corner {corner}")


class Cell:
    """Cell with static size"""

    def __init__(self, x: int, y: int, width: int, height: int, anchor: str=None):
        self._x = int(x)
        self._y = int(y)
        self._width = int(width)
        self._height = int(height)
        if anchor is None:
            anchor = "center" # center = default
        self._anchor = _validate_corner(anchor)

    def _corners_differ(self, corner: str|None) -> bool:
        if corner == self.anchor:
            return False
        return True

    def get_x(self, corner: str|None) -> int:
        """Get x coordinate of a corner"""
        corner = _validate_corner(corner)
        x = self.x
        if self._corners_differ(corner):
            x = corner2center_x[self.anchor](x, self.width)
            x = center2corner_x[corner](x, self.width)
        return x

    def set_x(self, x: int, corner: str|None):
        """Move x coordinate of a corner to the given value"""
        corner = _validate_corner(corner)
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
        corner = _validate_corner(corner)
        y = self.y
        if self._corners_differ(corner):
            y = corner2center_y[self.anchor](y, self.height)
            y = center2corner_y[corner](y, self.height)
        return y

    def set_y(self, y: int, corner: str|None):
        """Move y coordinate of a corner to the given value"""
        corner = _validate_corner(corner)
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

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Artist bounding box (x0, y0, x1, y1)"""
        return self.get_x("nw"), self.get_y("nw"), self.get_x("se"), self.get_y("se")


class Artist(Cell):
    """Artist that draws on a canvas"""

    def __init__(self, canvas: Canvas, x: int, y: int, width: int, height: int, anchor: str=None):
        super().__init__(x, y, width, height, anchor=anchor)

        self.canvas = canvas
        self._debug_id_border = None
        self._debug_id_anchor = None

    def update_position(self):
        """Perform position update"""

    def draw_debug_outlines(self, depth: int=0):
        """Draw outlines and anchor position"""
        print(f"Drawing {type(self).__name__: <15} at x={self.x:<4} y={self.y:<4} w={self.width:<4} h={self.height:<4} a={self.anchor:<4} bbox={self.bbox}")

        color = DEBUG_COLORS[depth % len(DEBUG_COLORS)]
        radius = 5
        self.canvas.create_rectangle(*self.bbox, tags="debug_outlines", outline=color)
        self.canvas.create_oval(self.x-radius, self.y-radius, self.x+radius, self.y+radius, tags="debug_outlines", fill=color)


class StackArtist(Artist):
    """Vertical stack of artists, has constant size"""

    def __init__(self, canvas: Canvas, x: int, y: int, anchor=None, flush=None, artists: list[Artist]=None):
        self.flush = _validate_corner(flush)
        self._artists: list[Artist] = [] if artists is None else artists

        height = sum(a.height for a in self._artists)
        width = max(a.width for a in self._artists) if len(self._artists) > 0 else 0
        super().__init__(canvas, x, y, width, height, anchor=anchor)

    def update_position(self):
        """Perform position update"""
        x = self.get_x(self.flush)
        y = self.get_y("nw")
        for artist in self._artists:
            artist.set_x(x, self.flush)
            artist.set_y(y, "nw")
            y += artist.height
            artist.update_position()
        return super().update_position()

    def draw_debug_outlines(self, depth: int=0):
        """Draw a rectangle around the child bounding boxes and a circle at the anchor"""
        for artist in self._artists:
            artist.draw_debug_outlines(depth=depth+1)
        return super().draw_debug_outlines(depth)


class DepartureArtist(Artist):
    """Display a departure on a canvas"""
    WIDTH_SPACE = textwidth(" ", FONT_DEPARTURE)

    def __init__(self, canvas: Canvas, anchor: str=None):
        # create artist
        width = WIDTH_ICON + WIDTH_DIRECTION + WIDTH_TIME + 2*self.WIDTH_SPACE
        height = lineheight(FONT_DEPARTURE)
        super().__init__(canvas, 0, 0, width, height, anchor=anchor)

        # create contents
        self.last_tripid = None
        self.id_icon = self.canvas.create_image(0, 0, anchor="center")
        self.id_drct = self.canvas.create_text(0, 0, text="could not fetch departure", anchor="w", font=FONT_DEPARTURE, fill=COLOR_ERROR)
        self.id_dots = self.canvas.create_text(0, 0, anchor="e", font=FONT_DEPARTURE, fill=COLOR_TXT)
        self.id_time = self.canvas.create_text(0, 0, anchor="e", font=FONT_DEPARTURE, fill=COLOR_TXT)

    def update_position(self):
        x = self.get_x("w")
        y = self.get_y("w")
        self.canvas.coords(self.id_icon, x + WIDTH_ICON//2, y)
        x += WIDTH_ICON + self.WIDTH_SPACE
        self.canvas.coords(self.id_drct, x, y)
        x += WIDTH_DIRECTION
        self.canvas.coords(self.id_dots, x, y)
        x += self.WIDTH_SPACE + WIDTH_TIME
        self.canvas.coords(self.id_time, x, y)
        return super().update_position()

    def update_departure(self, departure: Departure|None):
        """Update departure information"""
        tripid = getattr(departure, "id", None)

        if tripid != self.last_tripid:
            self.last_tripid = tripid
            self.configure_icon(departure)
            self.configure_drct(departure)
        self.configure_time(departure)

    def clear_departure(self):
        """Clear departure display"""
        self.last_tripid = None
        self.configure_icon(None)
        self.configure_drct(None)
        self.configure_time(None)

    def configure_icon(self, departure: Departure|None):
        """Change the displayed icon"""
        # no deaprture found
        if departure is None:
            self.canvas.itemconfigure(self.id_icon, image=ICONS.get("empty"))
            return

        # get icon
        icon = ICONS.get(departure.line, None)
        if icon is None:
            icon = ICONS.get(departure.product, None)
            print(f"Warning: Fallback images used for {departure.line}")
        if icon is None:
            icon = ICONS.get("default")
            print(f"Warning: Default images used for {departure.line}")

        # configure
        self.canvas.itemconfigure(self.id_icon, image=icon)

    def configure_drct(self, departure: Departure|None):
        """Change the displayed direction"""
        # no departure found
        string = getattr(departure, "direction", None)
        if not isinstance(string, str):
            self.canvas.itemconfigure(self.id_drct, text="could not fetch departure", fill=COLOR_ERROR)
            self.canvas.itemconfigure(self.id_dots, text=" ")
            return

        # get display string and dots
        for filt, replacement in DIRECTION_FILTER:
            string = string.replace(filt, replacement)

        width_dot = textwidth(".", FONT_DEPARTURE)
        available = WIDTH_DIRECTION
        occupied = textwidth(string, FONT_DEPARTURE)

        if occupied < available:
            count = ((available-occupied) // width_dot)
            dots = "." * count if count > 1 else ""
        else:
            print(f"Warning: direction name too long! {string}")
            idx = len(string)
            occupied = width_dot
            for i, char in enumerate(string):
                new_occupied = occupied + textwidth(char, FONT_DEPARTURE)
                if new_occupied >= available:
                    idx = i
                    break
                occupied = new_occupied
            string = string[:idx] + "."
            dots = ""

        # configure
        self.canvas.itemconfigure(self.id_drct, text=string, fill=COLOR_TXT)
        self.canvas.itemconfigure(self.id_dots, text=dots)

    def configure_time(self, departure: Departure|None) -> str:
        """configure time left"""
        # no departure found
        if departure is None:
            self.canvas.itemconfigure(self.id_time, text=" ")
            return

        time = "?" if departure.time_left is None else str(floor(departure.time_left))
        color = COLOR_TXT if departure.reachable else COLOR_NOTIME
        self.canvas.itemconfigure(self.id_time, text=time, fill=color)


class TitleArtist(Artist):
    """Display a title"""

    def __init__(self, canvas: Canvas, text: str, font: Font = FONT_TITLE, anchor=None):
        height = textheight(text, font)
        super().__init__(canvas, 0, 0, 1, height, anchor=anchor)

        self.id_title = self.canvas.create_text(0, 0, text=text, anchor=self.anchor, font=font, fill=COLOR_TXT)

    def update_position(self):
        self.canvas.coords(self.id_title, self.x, self.y)
        return super().update_position()


class EventArtist(Artist):
    """Display event information"""
    WIDTH_SPACE = textwidth(" ", FONT_EVENT)

    def __init__(self, canvas: Canvas, event: Event, anchor=None):
        width = WIDTH_DATE + self.WIDTH_SPACE + textwidth(event.desc, FONT_EVENT)
        height = max(textheight(event.date, FONT_EVENT), textheight(event.desc, FONT_EVENT))
        super().__init__(canvas, 0, 0, width, height, anchor=anchor)

        self.id_date = self.canvas.create_text(0, 0, text=event.date, anchor="nw", font=FONT_EVENT, fill=COLOR_TXT)
        self.id_desc = self.canvas.create_text(0, 0, text=event.desc, anchor="nw", font=FONT_EVENT, fill=COLOR_TXT)

    def update_position(self):
        x = self.get_x("nw")
        y = self.get_y("nw")
        self.canvas.coords(self.id_date, x, y)
        self.canvas.coords(self.id_desc, x+WIDTH_DATE+self.WIDTH_SPACE, y)
        return super().update_position()


class PosterArtist(Artist):
    """Display cycling posters"""

    def __init__(self, canvas: Canvas, poster: Poster, anchor=None):
        width = max(img.width() for img in poster.images)
        height = max(img.height() for img in poster.images)
        super().__init__(canvas, 0, 0, width, height, anchor=anchor)

        self.canvas = canvas
        self.posters = cycle(poster.images)
        self.id_poster = self.canvas.create_image(0, 0, image=next(self.posters), anchor="center")

    def update_position(self):
        self.canvas.coords(self.id_poster, self.get_x("center"), self.get_y("center"))
        return super().update_position()

    def update_poster(self):
        """Cycle to next poster"""
        self.canvas.itemconfigure(self.id_poster, image=next(self.posters))


class GridCanvas(Canvas):
    """Canvas that evenly aligns artists in a grid"""

    def __init__(self, master, flush: str=None, **options):
        super().__init__(master, **options)
        self.bind("<Configure>", self.on_resize)

        self.flush = _validate_corner(flush)
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
            while len(widths) <= col:
                widths.append(0)
            while len(heights) <= row:
                heights.append(0)
            widths[col]  = max(widths[col],  artist.width)
            heights[row] = max(heights[row], artist.height)
        return widths, heights

    def on_resize(self, event):
        """Canvas resize event callback, venly space artists"""
        self.delete("debug_outlines") # delete debug outlines, since they will be redrawn

        widths, heights = self.query_size()
        padx = (event.width  - sum(widths) ) / (1 + len(widths) )
        pady = (event.height - sum(heights)) / (1 + len(heights))

        y = pady
        for row, height in enumerate(heights):
            x = padx
            for col, width in enumerate(widths):
                artist = self.artists.get((row, col), None)
                if artist is not None:
                    cell = Artist(self, x, y, width, height, anchor="nw")
                    artist.set_x(cell.get_x(self.flush), self.flush)
                    artist.set_y(cell.get_y(self.flush), self.flush)
                    artist.update_position()
                    if DEBUG:
                        cell.draw_debug_outlines(depth=0)
                        artist.draw_debug_outlines(depth=1)
                x += width + padx
            y += height + pady

class Banner(Artist):
    """Logo and clock"""
