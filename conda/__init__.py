# (c) 2012-2016 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
"""OS-agnostic, system-level binary package manager."""
from __future__ import absolute_import, division, print_function

import os
import sys

from ._vendor.auxlib.packaging import get_version
from .common.compat import with_metaclass

__all__ = [
    "__name__", "__version__", "__author__",
    "__email__", "__license__", "__copyright__",
    "__summary__", "__url__",
]

__name__ = "conda"
__version__ = get_version(__file__)
__author__ = "Continuum Analytics, Inc."
__email__ = "conda@continuum.io"
__license__ = "BSD"
__summary__ = __doc__
__url__ = "https://github.com/conda/conda"

if os.getenv('CONDA_ROOT') is None:
    os.environ['CONDA_ROOT'] = sys.prefix


class CondaErrorType(type):
    def __init__(cls, name, bases, attr):
        super(CondaErrorType, cls).__init__(name, bases, attr)
        key = "%s.%s" % (cls.__module__, name)
        if key == "conda.CondaError":
            cls.registry = dict()
        else:
            cls.registry[cls.__name__] = cls


@with_metaclass(CondaErrorType)
class CondaError(Exception):
    def __init__(self, *args, **kwargs):
        super(CondaError, self).__init__(*args, **kwargs)

    def __repr__(self):
        ret_str = ' '.join([str(arg) for arg in self.args if not isinstance(arg, bool)])
        return ret_str

    def __str__(self):
        ret_str = ' '.join([str(arg) for arg in self.args if not isinstance(arg, bool)])
        return ret_str
