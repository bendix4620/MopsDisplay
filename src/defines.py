"""Project globals
sizes, fonts, colors, times, paths
"""

from pathlib import Path
from tkinter.font import Font
from PIL.Image import open as open_image
from PIL.ImageTk import PhotoImage


def load_image(path: Path, width: int, height: int) -> PhotoImage:
    """Load a tkinter image with pillow"""
    image = open_image(path)
    image.thumbnail((width, height))
    return PhotoImage(image)


HEIGHT_ICON = 40
WIDTH_ICON = 40
WIDTH_DIRECTION = 150
WIDTH_TIME = 20

WIDTH_DATE = 50
WIDTH_EVENT = 200

HEIGHT_POSTER = 500
WIDTH_POSTER = 300


FONT_TITLE = Font(font=("Helvetica", 24, "bold"))
FONT_DEPARTURE = Font(font=("Helvetica", 14, "bold"))
FONT_EVENT = Font(font=("Helvetica", 14, "bold"))


COLOR_TXT    = "#ffffff"
COLOR_NOTIME = "#d22222"
COLOR_ERROR  = "#808080"
COLOR_BG     = "#28282d"


STATION_UPDATE_TIME = 5_000
POSTER_UPDATE_TIME = 18_000


PATH = Path(__file__).parents[1].resolve() / "data"

POSTER_PATH = PATH / "posters"
CONFIG_PATH = PATH / "config.kdl"
ICON_PATH = PATH / "lines"

ICONS = {file.stem: load_image(file, WIDTH_ICON, HEIGHT_ICON) for file in ICON_PATH.glob("*.png")}
