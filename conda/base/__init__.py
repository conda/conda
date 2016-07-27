# -*- coding: utf-8 -*-
"""
Code in ``conda.base`` is the lowest level of the application stack.  It is loaded and executed
virtually every time the application is executed. Any code within, and any of its imports, must
be highly performant.

Conda modules importable from ``conda.base`` are

- ``conda._vendor``
- ``conda.base``
- ``conda.common``

Modules prohibited from importing ``conda.base`` are:

- ``conda._vendor``
- ``conda.common``

All other ``conda`` modules may import from ``conda.base``.
"""
from __future__ import absolute_import, division, print_function
from logging import getLogger

log = getLogger(__name__)
