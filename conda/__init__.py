# (c) 2012-2016 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
"""OS-agnostic, system-level binary package manager."""
from __future__ import absolute_import, division, print_function

import os
import sys
from logging import basicConfig, INFO

from ._vendor.auxlib.packaging import get_version
from .compat import text_type, iteritems
from .gateways.logging import initialize_logging

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

initialize_logging()


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
                    errors=tuple(error.dump_map() for error in self.errors))


class Message(object):

    def __init__(self, message_name, message_str, **kwargs):
        self._message_name = message_name
        self._message_str = message_str
        self._kwargs = kwargs

    @property
    def message(self):
        return self._message_str % self._kwargs

    def __str__(self):
        from .base.context import context
        if context.json:
            return self.to_json()
        else:
            return self.message

    def to_json(self):
        from json import dumps
        return dumps(dict(message_name=self._message_name, message=self.message,
                          **self._kwargs), indent=2)


basicConfig(level=INFO)
