# (c) 2012-2016 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
"""OS-agnostic, system-level binary package manager."""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from os.path import dirname
import sys

from ._vendor.auxlib.packaging import get_version
from .common.compat import iteritems, text_type

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
    os.environ[str('CONDA_ROOT')] = sys.prefix

CONDA_PACKAGE_ROOT = dirname(__file__)


class CondaError(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        self._kwargs = kwargs
        super(CondaError, self).__init__(message)

    def __repr__(self):
        return '%s: %s\n' % (self.__class__.__name__, text_type(self))

    def __str__(self):
        return text_type(self.message % self._kwargs)

    def dump_map(self):
        result = dict((k, v) for k, v in iteritems(vars(self)) if not k.startswith('_'))
        result.update(exception_type=text_type(type(self)),
                      exception_name=self.__class__.__name__,
                      message=text_type(self),
                      error=repr(self),
                      **self._kwargs)
        return result


class CondaMultiError(CondaError):

    def __init__(self, errors):
        self.errors = errors
        super(CondaError, self).__init__(None)

    def __repr__(self):
        return '\n'.join(repr(e) for e in self.errors) + '\n'

    def __str__(self):
        return '\n'.join(text_type(e) for e in self.errors) + '\n'

    def dump_map(self):
        return dict(exception_type=text_type(type(self)),
                    exception_name=self.__class__.__name__,
                    errors=tuple(error.dump_map() for error in self.errors),
                    error="Multiple Errors Encountered.",
                    )


class CondaExitZero(CondaError):
    pass
