"""Project globals
sizes, fonts, colors, times, paths
"""

__all__ = [
    "FONT_TITLE", "FONT_DEPARTURE", "FONT_EVENT", "FONT_CLOCK",
    "WIDTH_ROOT", "HEIGHT_ROOT",
    "HEIGHT_ICON", "WIDTH_ICON", "WIDTH_DIRECTION", "WIDTH_TIME",
    "WIDTH_DATE", "HEIGHT_POSTER", "WIDTH_POSTER", "HEIGHT_LOGO", "WIDTH_LOGO",
    "COLOR_TXT", "COLOR_NOTIME", "COLOR_ERROR", "COLOR_BG_STATION", "COLOR_BG_INFO",
    "STATION_UPDATE_TIME", "EVENT_UPDATE_TIME", "POSTER_UPDATE_TIME", "CLOCK_UPDATE_TIME",
    "PATH", "POSTER_PATH", "CONFIG_PATH", "LOGO_PATH", "ICON_PATH",
    "ICONS", "LOGO",
    "DIRECTION_FILTER"
]

from pathlib import Path
from tkinter.font import Font
from PIL.Image import open as open_image
from PIL.ImageTk import PhotoImage


# used fonts
# ----------
FONT_TITLE = Font(font=("Helvetica", 24, "bold"))
FONT_DEPARTURE = Font(font=("Helvetica", 14, "bold"))
FONT_EVENT = Font(font=("Helvetica", 14, "bold"))
FONT_CLOCK = Font(font=("Helvetica", 14, "bold"))


# root window size
# ----------------
# (only for reference, not used since application runs in fullscreen mode)
WIDTH_ROOT = 1280
HEIGHT_ROOT = 1024


# station departure sizes
# -----------------------
HEIGHT_ICON = FONT_DEPARTURE.metrics("linespace") # icons and departures have same height
WIDTH_ICON = 40
WIDTH_DIRECTION = 250
WIDTH_TIME = FONT_DEPARTURE.measure("00") # space for MMM time format


# information sizes
# -----------------
WIDTH_DATE = FONT_EVENT.measure("00.00.") # space for DD.MM. date format
HEIGHT_POSTER = 600
WIDTH_POSTER = 450
HEIGHT_LOGO = 100
WIDTH_LOGO = 450

# colors
# ------
COLOR_TXT    = "#ffffff" # for any basic text
COLOR_NOTIME = "#d22222" # for time remaining if departure is not reachable
COLOR_ERROR  = "#808080" # to display errors on canvas
COLOR_BG_STATION = "#28282d" # station departure background
COLOR_BG_INFO    = "#4070c5" # information background

# update times
# ------------
STATION_UPDATE_TIME =  5_000
EVENT_UPDATE_TIME   = 18_000
POSTER_UPDATE_TIME  = 18_000
CLOCK_UPDATE_TIME   =  5_000


# resource paths
# --------------
PATH = Path(__file__).parents[1].resolve() / "data"

POSTER_PATH = PATH / "posters"
CONFIG_PATH = PATH / "config.kdl"
LOGO_PATH = PATH / "logo.png"
ICON_PATH = PATH / "lines"

def load_image(path: Path, width: int, height: int) -> PhotoImage:
    """Load a tkinter image with pillow"""
    image = open_image(path)
    image.thumbnail((width, height))
    return PhotoImage(image)

ICONS = {file.stem: load_image(file, WIDTH_ICON, HEIGHT_ICON) for file in ICON_PATH.glob("*.png")}
LOGO = load_image(LOGO_PATH, WIDTH_LOGO, HEIGHT_LOGO)

# direction name replacement filter
# ---------------------------------
# (keep list short, the algorithm is slow)
DIRECTION_FILTER = [
    ("Schienenersatzverkehr", "SEV"),
    ("Ersatzverkehr", "EV"),
    ("(Berlin)", ""),
    ("Bhf", ""),
    ("Flughafen BER", "BER")
]
