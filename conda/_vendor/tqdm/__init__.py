# -*- coding: utf-8 -*-
# source: https://raw.githubusercontent.com/tqdm/tqdm/v4.19.8/tqdm/__init__.py
# version: 4.22.0
# date: 2018-04-12
# The modules _tqdm_gui, _tqdm_notebook, and _tqdm_pandas are not included.
# Also removed syscall on import in _version module.

from ._tqdm import tqdm
from ._tqdm import trange
# from ._tqdm_gui import tqdm_gui
# from ._tqdm_gui import tgrange
# from ._tqdm_pandas import tqdm_pandas
from ._main import main
from ._monitor import TMonitor, TqdmSynchronisationWarning
from ._version import __version__  # NOQA
from ._tqdm import TqdmTypeError, TqdmKeyError, TqdmWarning, \
    TqdmDeprecationWarning, TqdmExperimentalWarning, \
    TqdmMonitorWarning

# __all__ = ['tqdm', 'tqdm_gui', 'trange', 'tgrange', 'tqdm_pandas',
#            'tqdm_notebook', 'tnrange', 'main', 'TMonitor',
#            'TqdmTypeError', 'TqdmKeyError',
#            'TqdmWarning', 'TqdmDeprecationWarning',
#            'TqdmExperimentalWarning',
#            'TqdmMonitorWarning', 'TqdmSynchronisationWarning',
#            '__version__']
__all__ = ['tqdm', 'trange',
           'main', 'TMonitor',
           'TqdmTypeError', 'TqdmKeyError',
           'TqdmWarning', 'TqdmDeprecationWarning',
           'TqdmExperimentalWarning',
           'TqdmMonitorWarning', 'TqdmSynchronisationWarning',
           '__version__']


# def tqdm_notebook(*args, **kwargs):  # pragma: no cover
#     """See tqdm._tqdm_notebook.tqdm_notebook for full documentation"""
#     from ._tqdm_notebook import tqdm_notebook as _tqdm_notebook
#     return _tqdm_notebook(*args, **kwargs)
#
#
# def tnrange(*args, **kwargs):  # pragma: no cover
#     """
#     A shortcut for tqdm_notebook(xrange(*args), **kwargs).
#     On Python3+ range is used instead of xrange.
#     """
#     from ._tqdm_notebook import tnrange as _tnrange
#     return _tnrange(*args, **kwargs)
