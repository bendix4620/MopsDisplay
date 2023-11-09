"""Import data from config.kdl"""

from pathlib import Path
from typing import Any, List, Tuple, Union
from PIL.ImageTk import PhotoImage
import kdl
from . import defines as d
from .data import Station, DirectionsAndProducts, Event, Poster


def kdl2poster(string: kdl.String, raw: kdl.ParseFragment) -> PhotoImage: # pylint: disable=unused-argument
    """Convert kdl string to an image path"""
    path = d.POSTER_PATH / string.value
    path = path.resolve()

    if not path.is_file():
        raise ValueError(f"Could not find file {path}")
    return d.load_image(path, d.WIDTH_POSTER, d.HEIGHT_POSTER)

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

    def node2args(self, node: kdl.Node) -> Tuple[list, dict]:
        """Convert node to *args and **kwargs"""
        print(repr(node))
        print()
        args = node.args
        kwargs = {child_node.name: self.strip(child_node.args)
                  for child_node in node.nodes}
        return args, kwargs

    def strip(self, lst: list) -> Union[list, Any]:
        """Strip list if it only has one element"""
        if self._strip and len(lst) == 1:
            return lst[0]
        return lst

    def __call__(self, node: kdl.Node, raw: kdl.ParseFragment):
        args, kwargs = self.node2args(node)
        return kdl.Node(name=node.name, args=[self._cls(*args, **kwargs)])

def load_config(path: Path):
    """Create list of Stations from station.kdl config"""
    parse_config = kdl.ParseConfig(
        valueConverters={"poster": kdl2poster},
        nodeConverters={"column":  NodeConverter(Station),
                        "day":     NodeConverter(DirectionsAndProducts),
                        "night":   NodeConverter(DirectionsAndProducts),
                        "event":   NodeConverter(Event), 
                        "poster":  NodeConverter(Poster),
                        "stations": reduce_node,
                        "rows":     reduce_node,
                        "events":   reduce_node,
                        "posters":  reduce_node})

    with open(path, "r", encoding="utf-8") as file:
        doc = kdl.parse(file.read(), config=parse_config)
    return doc

def load_data() -> Tuple[List[List[Station]], List[Event], List[Poster]]:
    """Load stations, events and posters from kdl config"""
    doc = load_config(d.CONFIG_PATH)

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
