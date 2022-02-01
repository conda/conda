# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""OS-agnostic, system-level binary package manager."""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from os.path import abspath, dirname
import sys

from json import JSONEncoder

# This hack is from http://kmike.ru/python-with-strings-attached/
# It is needed ro prevent str() conversion of %r. Against general
# advice, we return `unicode` from various things on Python 2,
# in particular the `__repr__` and `__str__` of our exceptions.
if sys.version_info[0] == 2:
    # ignore flake8 on this because it finds this as an error on py3 even though it is guarded
    reload(sys)  # NOQA
    sys.setdefaultencoding('utf-8')

from .auxlib.packaging import get_version
from .common.compat import text_type, iteritems


__all__ = (
    "__name__", "__version__", "__author__", "__email__", "__license__", "__summary__", "__url__",
    "CONDA_PACKAGE_ROOT", "CondaError", "CondaMultiError", "CondaExitZero", "conda_signal_handler",
    "__copyright__",
)

__name__ = "conda"
__version__ = get_version(__file__)
__author__ = "Anaconda, Inc."
__email__ = "conda@continuum.io"
__license__ = "BSD-3-Clause"
__copyright__ = "Copyright (c) 2012, Anaconda, Inc."
__summary__ = __doc__
__url__ = "https://github.com/conda/conda"

if os.getenv('CONDA_ROOT') is None:
    os.environ[str('CONDA_ROOT')] = sys.prefix

#: The conda package directory.
CONDA_PACKAGE_ROOT = abspath(dirname(__file__))
#: The path within which to find the conda package.
#:
#: If `conda` is statically installed this is the site-packages. If `conda` is an editable install
#: or otherwise uninstalled this is the git repo.
CONDA_SOURCE_ROOT = dirname(CONDA_PACKAGE_ROOT)

def another_to_unicode(val):
    # ignore flake8 on this because it finds this as an error on py3 even though it is guarded
    if isinstance(val, basestring) and not isinstance(val, unicode):  # NOQA
        return unicode(val, encoding='utf-8')  # NOQA
    return val

class CondaError(Exception):
    return_code = 1
    reportable = False  # Exception may be reported to core maintainers

    def __init__(self, message, caused_by=None, **kwargs):
        self.message = message
        self._kwargs = kwargs
        self._caused_by = caused_by
        super(CondaError, self).__init__(message)

# If we add __unicode__ to CondaError then we must also add it to all classes that
# inherit from it if they have their own __repr__ (and maybe __str__) function.
    if sys.version_info[0] > 2:
        def __repr__(self):
            return '%s: %s' % (self.__class__.__name__, text_type(self))
    else:

        # We must return unicode here.
        def __unicode__(self):
            new_kwargs = dict()
            for k, v in iteritems(self._kwargs):
                new_kwargs[another_to_unicode(k)] = another_to_unicode(v)
            new_message = another_to_unicode(self.message)
            res = '%s' % (new_message % new_kwargs)
            return res

        def __repr__(self):
            return '%s: %s' % (self.__class__.__name__, self.__unicode__())

    def __str__(self):

        try:
            if sys.version_info[0] > 2:
                return text_type(self.message % self._kwargs)
            else:
                return self.__unicode__().encode('utf-8')
        except Exception:
            debug_message = "\n".join((
                "class: " + self.__class__.__name__,
                "message:",
                self.message,
                "kwargs:",
                text_type(self._kwargs),
                "",
            ))
            print(debug_message, file=sys.stderr)
            raise

    def dump_map(self):
        result = dict((k, v) for k, v in vars(self).items() if not k.startswith('_'))
        result.update(exception_type=text_type(type(self)),
                      exception_name=self.__class__.__name__,
                      message=text_type(self),
                      error=repr(self),
                      caused_by=repr(self._caused_by),
                      **self._kwargs)
        return result


class CondaMultiError(CondaError):

    def __init__(self, errors):
        self.errors = errors
        super(CondaMultiError, self).__init__(None)

    if sys.version_info[0] > 2:
        def __repr__(self):
            errs = []
            for e in self.errors:
                if isinstance(e, EnvironmentError) and not isinstance(e, CondaError):
                    errs.append(text_type(e))
                else:
                    # We avoid Python casting this back to a str()
                    # by using e.__repr__() instead of repr(e)
                    # https://github.com/scrapy/cssselect/issues/34
                    errs.append(e.__repr__())
            res = '\n'.join(errs)
            return res
    else:
        # We must return unicode here.
        def __unicode__(self):
            errs = []
            for e in self.errors:
                if isinstance(e, EnvironmentError) and not isinstance(e, CondaError):
                    errs.append(text_type(e))
                else:
                    # We avoid Python casting this back to a str()
                    # by using e.__repr__() instead of repr(e)
                    # https://github.com/scrapy/cssselect/issues/34
                    errs.append(e.__repr__())
            res = '\n'.join(errs)
            return res

        def __repr__(self):
            return '%s: %s' % (self.__class__.__name__, self.__unicode__())

    def __str__(self):
        return str('\n').join(str(e) for e in self.errors) + str('\n')

    def dump_map(self):
        return dict(exception_type=text_type(type(self)),
                    exception_name=self.__class__.__name__,
                    errors=tuple(error.dump_map() for error in self.errors),
                    error="Multiple Errors Encountered.",
                    )

    def contains(self, exception_class):
        return any(isinstance(e, exception_class) for e in self.errors)


class CondaExitZero(CondaError):
    return_code = 0


ACTIVE_SUBPROCESSES = set()


def conda_signal_handler(signum, frame):
    # This function is in the base __init__.py so that it can be monkey-patched by other code
    #   if downstream conda users so choose.  The biggest danger of monkey-patching is that
    #   unlink/link transactions don't get rolled back if interrupted mid-transaction.
    for p in ACTIVE_SUBPROCESSES:
        if p.poll() is None:
            p.send_signal(signum)

    from .exceptions import CondaSignalInterrupt
    raise CondaSignalInterrupt(signum)


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default
JSONEncoder.default = _default
