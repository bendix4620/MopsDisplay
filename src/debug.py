"""Debugging tools"""

from functools import wraps
import time
from typing import Callable


DEBUG = False
BENCHMARK = False

class CycleWithIndex:
    """Similar to itertools.cycle, but allows element access by index"""

    def __init__(self, lst):
        self.lst = list(lst)

    def __getitem__(self, idx: int):
        return self.lst[idx % len(self.lst)]

# matplotlib default color cycle
COLORS = CycleWithIndex(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'])

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

class TimedCumulative:
    """Cumulative timer"""
    def __init__(self, name: str):
        self.name = name
        self.time = 0
        self.start = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        passed = time.perf_counter() - self.start
        self.time += passed

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                res = func(*args, **kwargs)
            return res
        return wrapper
