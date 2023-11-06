from dataclasses import dataclass
from functools import wraps


class _Required:
    """Use as dataclass_enfore_required field default to flag it as required"""
required = _Required

def do_nothing(*args, **kwargs): # pylint: disable=unused-argument
    """do nothing"""

def dataclass_enforce_required(cls):
    """Class decorator. Return a dataclass and enforce presence of keyword 
    fields flagged as required.
    
    Wraps __post_init__ to raise TypeError if a field value is set to required
    """
    __post_init__ = getattr(cls, "__post_init__", do_nothing)

    # the new init function
    @wraps(__post_init__)
    def __new_post_init__(self):
        # look for required fields
        for name, field in self.__dict__.items():
            if field is required:
                raise TypeError(f"{type(self).__name__} missing required keyword argument: '{name}'")

        # call original __post_init__
        __post_init__(self)

    cls.__post_init__ = __new_post_init__
    return dataclass(cls)


@dataclass_enforce_required
class C:
    a: int = required
    b: int = 0
    c: int = required

c = C(0)
print(C)
