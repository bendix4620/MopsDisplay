"""Debugging tools"""

__all__ = ["DEBUG", "BENCHMARK", "DEBUG_COLORS", "Timed"]

from functools import wraps
import time
from typing import Callable


DEBUG = True
BENCHMARK = True
# matplotlib default color cycle
DEBUG_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class Timed:
    """Execution time measurement class
    instances can be used as function decorator
    instances support with statement
    """

    def __init__(self, name: str=None):
        self.name = name
        self.start = 0

    def __enter__(self):
        if BENCHMARK:
            self.start = time.perf_counter()
            return self

    def __exit__(self, *args):
        if BENCHMARK:
            passed = time.perf_counter() - self.start
            name = "unnamed code block" if self.name is None else self.name
            print(f"Executing {name} took {passed:.6f}s")

    def __call__(self, func: Callable):
        if self.name is None:
            self.name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                res = func(*args, **kwargs)
            return res
        return wrapper if BENCHMARK else func
