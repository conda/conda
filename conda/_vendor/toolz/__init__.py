# from .itertoolz import *
#
# from .functoolz import *
#
# from .dicttoolz import *
#
# from .recipes import *
#
# from .compatibility import map, filter
#
# from . import sandbox
#
# from functools import partial, reduce
#
# sorted = sorted
#
# # Aliases
# comp = compose
#
# functoolz._sigs.create_signature_registry()

# source: https://github.com/pytoolz/toolz
# updated: 2017-05-30
__version__ = '0.8.2'


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
