# -*- coding: utf-8 -*-
"""
Models are data transfer objects or "light-weight" domain objects with no appreciable logic
other than their own validation. Models are used to pass data between layers of the stack. In
many ways they are similar to ORM objects.  Unlike ORM objects, they are NOT themselves allowed
to load data from a remote resource.  Thought of another way, they cannot import from
``conda.gateways``, but rather ``conda.gateways`` imports from ``conda.models`` as appropriate
to create model objects from remote resources.

Conda modules importable from ``conda.models`` are

- ``conda._vendor``
- ``conda.common``
- ``conda.models``

"""
from ..common.compat import text_type
from ..base.context import context


def translate_feature_str(val):
    if val.endswith('@'):
        val = val[:-1]

    if '=' in val:
        feature_name, feature_value = val.split('=', 1)
    else:
        if 'mkl' in val:
            if val == 'nomkl':
                if context.subdir == 'osx-64':
                    val = 'accelerate'
                else:
                    val = 'openblas'
            feature_name, feature_value = 'blas', val
        elif len(val) == 4 and val.startswith('vc'):
            feature_name, feature_value = val[:2], text_type(int(val[2:]))
        else:
            feature_name, feature_value = val, 'true'

    return feature_name, feature_value
