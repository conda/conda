.. image:: https://img.shields.io/pypi/v/backports.functools_lru_cache.svg
   :target: https://pypi.org/project/backports.functools_lru_cache

.. image:: https://img.shields.io/pypi/pyversions/backports.functools_lru_cache.svg

.. image:: https://img.shields.io/travis/jaraco/backports.functools_lru_cache/master.svg
   :target: https://travis-ci.org/jaraco/backports.functools_lru_cache

.. .. image:: https://readthedocs.org/projects/backportsfunctools_lru_cache/badge/?version=latest
..    :target: https://backportsfunctools_lru_cache.readthedocs.io/en/latest/?badge=latest

Backport of functools.lru_cache from Python 3.3 as published at `ActiveState
<http://code.activestate.com/recipes/578078/>`_.

Usage
=====

Consider using this technique for importing the 'lru_cache' function::

    try:
        from functools import lru_cache
    except ImportError:
        from backports.functools_lru_cache import lru_cache


