# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""OS-agnostic, system-level binary package manager."""
from __future__ import annotations

from json import JSONEncoder
import os
from os.path import abspath, dirname
import sys
import warnings

from .auxlib.packaging import get_version


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

if os.getenv("CONDA_ROOT") is None:
    os.environ["CONDA_ROOT"] = sys.prefix

#: The conda package directory.
CONDA_PACKAGE_ROOT = abspath(dirname(__file__))
#: The path within which to find the conda package.
#:
#: If `conda` is statically installed this is the site-packages. If `conda` is an editable install
#: or otherwise uninstalled this is the git repo.
CONDA_SOURCE_ROOT = dirname(CONDA_PACKAGE_ROOT)

def another_to_unicode(val):
    warnings.warn(
        "`conda.another_to_unicode` is pending deprecation and will be removed in a "
        "future release.",
        PendingDeprecationWarning,
    )
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
        super().__init__(message)

    def __repr__(self):
        return f"{self.__class__.__name__}: {self}"

    def __str__(self):
        try:
            return str(self.message % self._kwargs)
        except Exception:
            debug_message = "\n".join((
                "class: " + self.__class__.__name__,
                "message:",
                self.message,
                "kwargs:",
                str(self._kwargs),
                "",
            ))
            print(debug_message, file=sys.stderr)
            raise

    def dump_map(self):
        result = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        result.update(
            exception_type=str(type(self)),
            exception_name=self.__class__.__name__,
            message=str(self),
            error=repr(self),
            caused_by=repr(self._caused_by),
            **self._kwargs
        )
        return result


class CondaMultiError(CondaError):

    def __init__(self, errors):
        self.errors = errors
        super().__init__(None)

    def __repr__(self):
        errs = []
        for e in self.errors:
            if isinstance(e, EnvironmentError) and not isinstance(e, CondaError):
                errs.append(str(e))
            else:
                # We avoid Python casting this back to a str()
                # by using e.__repr__() instead of repr(e)
                # https://github.com/scrapy/cssselect/issues/34
                errs.append(e.__repr__())
        res = '\n'.join(errs)
        return res

    def __str__(self):
        return "\n".join(str(e) for e in self.errors) + "\n"

    def dump_map(self):
        return dict(exception_type=str(type(self)),
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


# inspired by deprecation (https://deprecation.readthedocs.io/en/latest/) and
# CPython's warnings._deprecated
class _deprecated:
    def __init__(
        self,
        deprecate_in: str,
        remove_in: str,
        addendum: str | None = None,
        _current: str | None = None,
    ):
        """
        Args:
            deprecate_in: Version in which code will be marked as deprecated.
            remove_in: Version in which code is expected to be removed.
            addendum: Additional messaging. Useful to indicate what should be used instead.
            _current: Testing variable, shouldn't be used in practice.
        """
        from packaging import version

        self.deprecate_version = version.parse(deprecate_in)
        self.remove_version = version.parse(remove_in)
        self.current_version = version.parse(_current or __version__)
        self.addendum = f" {addendum.strip()}" if addendum else ""

    def __call__(self, func):
        """Deprecation decorator for functions & methods."""
        from functools import wraps

        name = f"{func.__module__}.{func.__name__}"
        if self.current_version < self.deprecate_version:

            @wraps(func)
            def inner(*args, **kwargs):
                warnings.warn(self._pending_msg(name), PendingDeprecationWarning, stacklevel=5)
                return func(*args, **kwargs)

            return inner
        elif self.current_version < self.remove_version:

            @wraps(func)
            def inner(*args, **kwargs):
                warnings.warn(self._deprecated_msg(name), DeprecationWarning, stacklevel=5)
                return func(*args, **kwargs)

            return inner
        else:
            raise RuntimeError(self._remove_msg(name))

    @classmethod
    def module(cls, *args, **kwargs):
        """Deprecation function for modules."""
        import inspect

        self = cls(*args, **kwargs)

        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__

        if self.current_version < self.deprecate_version:
            warnings.warn(self._pending_msg(name), PendingDeprecationWarning, stacklevel=3)
        elif self.current_version < self.remove_version:
            warnings.warn(self._deprecated_msg(name), DeprecationWarning, stacklevel=3)
        else:
            raise RuntimeError(self._remove_msg(name))

    def _pending_msg(self, name: str) -> None:
        return (
            f"{name} is pending deprecation and will be removed in {self.remove_version}."
            f"{self.addendum}"
        )

    def _deprecated_msg(self, name: str) -> None:
        return (
            f"{name} is deprecated and will be removed in {self.remove_version}."
            f"{self.addendum}"
        )

    def _remove_msg(self, name: str) -> None:
        return f"{name} was slated for removal in {self.remove_version}." f"{self.addendum}"
