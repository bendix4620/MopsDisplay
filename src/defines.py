"""Project globals
sizes, fonts, colors, times, paths
"""

import time
from collections import OrderedDict
from functools import wraps
from itertools import cycle
from pathlib import Path
from tkinter.font import Font
from PIL.Image import open as open_image
from PIL.ImageTk import PhotoImage


def load_image(path: Path, width: int, height: int) -> PhotoImage:
    """Load a tkinter image with pillow"""
    image = open_image(path)
    image.thumbnail((width, height))
    return PhotoImage(image)

DEBUG = True
DEBUG_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


FONT_TITLE = Font(font=("Helvetica", 24, "bold"))
FONT_DEPARTURE = Font(font=("Helvetica", 14, "bold"))
FONT_EVENT = Font(font=("Helvetica", 14, "bold"))


HEIGHT_ICON = FONT_DEPARTURE.metrics("linespace") # icons and departures have same height
WIDTH_ICON = 40
WIDTH_DIRECTION = 250
WIDTH_TIME = FONT_DEPARTURE.measure("00") # space for MMM time format

WIDTH_DATE = FONT_EVENT.measure("00.00.") # space for DD.MM. date format

HEIGHT_POSTER = 600
WIDTH_POSTER = 450


COLOR_TXT    = "#ffffff"
COLOR_NOTIME = "#d22222"
COLOR_ERROR  = "#808080"
COLOR_BG_STATION = "#28282d"
COLOR_BG_EVENT   = "#4070c5"


STATION_UPDATE_TIME =  5_000
EVENT_UPDATE_TIME   = 18_000
POSTER_UPDATE_TIME  = 18_000


PATH = Path(__file__).parents[1].resolve() / "data"

POSTER_PATH = PATH / "posters"
CONFIG_PATH = PATH / "config.kdl"
ICON_PATH = PATH / "lines"

ICONS = {file.stem: load_image(file, WIDTH_ICON, HEIGHT_ICON) for file in ICON_PATH.glob("*.png")}


DIRECTION_FILTER = [
    ("Schienenersatzverkehr", "SEV"),
    ("Ersatzverkehr", "EV"),
    ("(Berlin)", ""),
    ("Bhf", ""),
    ("Flughafen BER", "BER")
]
