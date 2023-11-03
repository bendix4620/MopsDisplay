"""Import data from config.kdl"""

from pathlib import Path
from typing import Any
import kdl
from .data import Station, Event, Poster



PATH = Path(__file__).parents[1].resolve() / "data"
POSTER = PATH / "posters"
CONFIG = PATH / "config.kdl"


def kdl2imgpath(string: kdl.String, raw: kdl.ParseFragment) -> Path: # pylint: disable=unused-argument
    """Convert kdl string to an image path"""
    path = POSTER / string.value
    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"Could not find file {path}")
    return path

def reduce_node(node: kdl.Node, raw: kdl.ParseFragment) -> kdl.Node: # pylint: disable=unused-argument
    """Move child nodes to node args"""
    node.args = node.nodes
    node.nodes = []
    return node

class NodeConverter:
    """Convert kdl nodes to dataclass instances"""
    def __init__(self, cls: type, strip: bool=True):
        self._cls = cls
        self._strip = strip

    def node2args(self, node: kdl.Node) -> tuple[list, dict]:
        """Convert node to *args and **kwargs"""
        args = node.args
        kwargs = {child_node.name: self.strip(child_node.args)
                  for child_node in node.nodes}
        return args, kwargs

    def strip(self, lst: list) -> list | Any:
        """Strip list if it only has one element"""
        if self._strip and len(lst) == 1:
            return lst[0]
        return lst

    def __call__(self, node: kdl.Node, raw: kdl.ParseFragment):
        args, kwargs = self.node2args(node)
        return self._cls(*args, **kwargs)

KDL_PARSECONFIG = kdl.ParseConfig(
    valueConverters={"posterpath": kdl2imgpath},
    nodeConverters={"station": NodeConverter(Station),
                    "event":   NodeConverter(Event), 
                    "poster":  NodeConverter(Poster),
                    "stations": reduce_node,
                    "events":   reduce_node,
                    "posters":  reduce_node})

def load_config(path: Path):
    """Create list of Stations from station.kdl config"""
    with open(path, "r", encoding="utf-8") as file:
        doc = kdl.parse(file.read(), config=KDL_PARSECONFIG)
    return doc

def load_data() -> tuple[list[Station], list[Event], list[Poster]]:
    """Load stations, events and posters from kdl config"""
    doc = load_config(CONFIG)

    stations = doc.get("stations")
    if stations is None:
        raise ValueError("Node 'stations' not found")

    events = doc.get("events")
    if events is None:
        raise ValueError("Node 'events' not found")

    posters = doc.get("posters")
    if posters is None:
        raise ValueError("Node 'posters' not found")

    return stations.args, events.args, posters.args
