# -*- coding: utf-8 -*-
"""Auxlib is an auxiliary library to the python standard library.

The aim is to provide core generic features for app development in python. Auxlib fills in some
python stdlib gaps much like `pytoolz <https://github.com/pytoolz/>`_ has for functional
programming, `pyrsistent <https://github.com/tobgu/pyrsistent/>`_ has for data structures, or
`boltons <https://github.com/mahmoud/boltons/>`_ has generally.

Major areas addressed include:
  - :ref:`packaging`: package versioning, with a clean and less invasive alternative to
    versioneer
  - :ref:`entity`: robust base class for type-enforced data models and transfer objects
  - :ref:`type_coercion`: intelligent type coercion utilities
  - :ref:`configuration`: a map implementation designed specifically to hold application
    configuration and context information
  - :ref:`factory`: factory pattern implementation
  - :ref:`path`: file path utilities especially helpful when working with various python
    package formats
  - :ref:`logz`: logging initialization routines to simplify python logging setup
  - :ref:`crypt`: simple, but correct, pycrypto wrapper


"""
from __future__ import absolute_import, division, print_function

# don't mess up logging for library users
from .logz import getLogger, NullHandler
getLogger('auxlib').addHandler(NullHandler())

__all__ = [
    "__name__", "__version__", "__author__",
    "__email__", "__license__", "__copyright__",
    "__summary__", "__url__",
    "BuildPyCommand", "SDistCommand", "Tox", "get_version",
]

__name__ = "auxlib"
__author__ = 'Kale Franz'
__email__ = 'kale@franz.io'
__url__ = 'https://github.com/kalefranz/auxlib'
__license__ = "ISC"
__copyright__ = "(c) 2015 Kale Franz. All rights reserved."
__summary__ = """auxiliary library to the python standard library"""
