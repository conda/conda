from ...deprecations import deprecated
deprecated.module("23.3", "23.9", addendum="Use `toolz`/`cytoolz` instead.")

try:
    from cytoolz import __version__ as cytoolz_version
    if tuple(int(x) for x in cytoolz_version.split(".")) < (0, 8, 2):
        raise ImportError()
    from cytoolz.itertoolz import *
    from cytoolz.dicttoolz import *
    from cytoolz.functoolz import excepts
except (ImportError, ValueError):
    from .itertoolz import *
    from .dicttoolz import *

    # Importing from toolz.functoolz is slow since it imports inspect.
    # Copy the relevant part of excepts' implementation instead:
    class excepts(object):
        def __init__(self, exc, func, handler=lambda exc: None):
            self.exc = exc
            self.func = func
            self.handler = handler

        def __call__(self, *args, **kwargs):
            try:
                return self.func(*args, **kwargs)
            except self.exc as e:
                return self.handler(e)

__version__ = '0.9.0'
