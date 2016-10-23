# -*- coding: utf-8 -*-
"""
Code in ``conda.core`` is the core logic.  It is strictly forbidden from having side effects.
No printing to stdout or stderr, no disk manipulation, no http requests.
All side effects should be implemented through ``conda.gateways``.  Objects defined in
``conda.models`` should be heavily preferred for ``conda.core`` function/method arguments
and return values.

Conda modules importable from ``conda.core`` are

- ``conda._vendor``
- ``conda.common``
- ``conda.core``
- ``conda.models``
- ``conda.gateways``

Conda modules strictly off limits for import within ``conda.core`` are

- ``conda.api``
- ``conda.cli``
- ``conda.client``

"""
from __future__ import absolute_import, division, print_function
