"""Artists that dynamically position canvas items"""

from __future__ import annotations
from typing import Self



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

class CellLock:
    def __init__(self):
        self.locked = False
    
    def __enter__(self):
        self.locked = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.locked = False

class Cell:
    """Cell of a grid"""

    def __init__(self, x, y, width, height, anchor=None):
        if anchor is None:
            anchor = "center" # center = default
        self.anchor = anchor
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.lock = CellLock()

    def _on_resize(self):
        """Callback for resize events"""
        pass

    def resize(self):
        """Trigger a resize event
        Does not trigger event if cell is currently locked
        """
        if not self.lock.locked:
            self._on_resize()

    def _corners_differ(self, corner: str|None) -> bool:
        if corner is None:
            return False
        if corner not in corner2center_x.keys():
            raise ValueError(f"Unexpected identifyer {corner}")
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
        old_x = self.get_x(corner)
        self.x += x - old_x

    @property
    def x(self) -> int:
        """Anchor coordinate x"""
        return self._x

    @x.setter
    def x(self, x: float):
        self._x = int(x)
        self.resize()

    def get_y(self, corner: str|None) -> int:
        """Get y coordinate of a corner"""
        y = self.y
        if self._corners_differ(corner):
            y = corner2center_y[self.anchor](y, self.width)
            y = center2corner_y[corner](y, self.width)
        return y

    def set_y(self, y: int, corner: str|None):
        """Move y coordinate of a corner to the given value"""
        old_y = self.get_y(corner)
        self.y += y - old_y

    @property
    def y(self) -> int:
        """Anchor coordinate y"""
        return self._y

    @y.setter
    def y(self, y: float):
        self._y = int(y)
        self.resize()

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, val: float):
        self._width = int(val)
        self.resize()

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, val: float):
        self._height = int(val)
        self.resize()

    @property
    def anchor(self) -> str:
        """Anchor of the cell"""
        return self._anchor

    @anchor.setter
    def anchor(self, val: str):
        if self._corners_differ(val):
            x = self.get_x(val)
            y = self.get_y(val)
            # no resize event necessary
            self._x = x
            self._y = y
            self._anchor = val

    def scale(self, factor: float) -> Self:
        """Scale width and height by a factor"""
        self.width = factor*self.width
        self.height = factor*self.height
        return self

    def bind_to_cell(self, cell: Cell):
        """Use cell to place the grid"""
        self.__dict__.update(cell.__dict__) # use inspect instead?
        self.resize()

    def to_grid(self, row_sizes: list[float]=None, col_weights: list[float]=None, anchor: str=None):
        x = self.get_x(anchor)
        y = self.get_y(anchor)
        return Grid(x, y, self.width, self.height, row_sizes=row_sizes, col_weights=col_weights, anchor=anchor)



def normal(weights: list[float]) -> list[float]:
    """Iterate over normalized weights"""
    if len(weights) == 0:
        raise ValueError("No weights given")
    N = sum(weights)
    if N == 0:
        raise ValueError("Weights should not sum to 0")
    return [w/N for w in weights]


class Grid(Cell):
    """Grid that evenly spaces cells

    padding is given in absolute units (pixels)
    rows (height) is given in absolute units (pixels)
    columns (width) is given in relative units (weights)
    """

    def __init__(self, 
            x: int=0, 
            y: int=0, 
            width: int=0,
            height: int=0,
            pad_col: int=0,
            anchor: str=None,
            row_sizes: list[float]=None,
            col_weights: list[float]=None,
    ):
        super().__init__(x, y, width, height, anchor=anchor)

        self.pad_col = pad_col

        if col_weights is None:
            col_weights = [1]
        self._cw = col_weights

        if row_sizes is None:
            row_sizes = [0]
        self._rs = row_sizes

    @property
    def free_width(self):
        """Available width after considering padding"""
        return self.width - self.pad_col*len(self._cw)

    @property
    def free_height(self):
        """Available height after considering padding"""
        return self.height - self.pad_row*len(self._rs)

    def append_row(self, size: float):
        """Append a row with size"""
        self._rs.append(size)

    def pop_row(self) -> float:
        """Pop rows"""
        return self._rs.pop()

    def append_col(self, weight: float):
        """Append a column with weights"""
        self._cw.append(weight)

    def pop_col(self) -> float:
        """Pop columns"""
        return self._cw.pop()

    def get_cell(self, row: int, col: int, row_span: int=1, col_span: int=1, anchor="center") -> Cell:
        """Get grid cell at (row, col)"""
        # x direction
        cweights = normal(self._cw)
        width  = sum(cweights[col:col+col_span])*self.free_width + (col_span-1)*self.pad_col
        xnw = self.get_x(corner="nw") + cweights[:col]*self.width + (col+1)*self.pad_col

        # y direction
        height = self._rs[row]

        # positions from the nw corner
        ynw = self.get_y(corner="nw") + rweights[:row]*self.height + (row+1)*self.pad_row

        # create cell
        cell = Cell(0, 0, width, height, anchor=anchor)
        cell.set_x(xnw, corner="nw")
        cell.set_y(ynw, corner="nw")
        return cell
