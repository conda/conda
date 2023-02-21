from ...deprecations import deprecated
deprecated.module("23.3", "23.9", addendum="Use `tqdm` instead.")

from ._monitor import TMonitor, TqdmSynchronisationWarning
from .cli import main  # TODO: remove in v5.0.0
from .std import (
    TqdmDeprecationWarning, TqdmExperimentalWarning, TqdmKeyError, TqdmMonitorWarning,
    TqdmTypeError, TqdmWarning, tqdm, trange)
from .version import __version__

__all__ = ['tqdm', 'trange', 'main', 'TMonitor',
           'TqdmTypeError', 'TqdmKeyError',
           'TqdmWarning', 'TqdmDeprecationWarning',
           'TqdmExperimentalWarning',
           'TqdmMonitorWarning', 'TqdmSynchronisationWarning',
           '__version__']
