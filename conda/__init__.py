# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""OS-agnostic, system-level binary package manager."""
from __future__ import annotations

from functools import wraps
from json import JSONEncoder
import os
from os.path import abspath, dirname
import sys
from types import ModuleType
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
    _version: tuple[int, ...]
    _category: Warning
    _message: Callable[str, str]
    _argument: str | None = None
    _rename: str | None = None

    @staticmethod
    def _parse_version(version: str) -> tuple[int, ...]:
        """A naive version parser to avoid circular imports. Do not use for other purposes."""

        def try_int(string: str) -> int | str:
            try:
                return int(string)
            except ValueError:
                return string

        return tuple(map(try_int, version.split(".")))

    def __init__(
        self,
        deprecate_in: str,
        remove_in: str,
        *,
        addendum: str | None = None,
    ):
        """Deprecation decorator for functions, methods, & classes.

        Args:
            deprecate_in: Version in which code will be marked as deprecated.
            remove_in: Version in which code is expected to be removed.
            addendum: Optional additional messaging. Useful to indicate what to do instead.
        """
        deprecate_version = self._parse_version(deprecate_in)
        remove_version = self._parse_version(remove_in)

        addendum = f" {addendum}" if addendum else ""
        if self._version < deprecate_version:
            self._category = PendingDeprecationWarning
            message = f"{{name}} is pending deprecation and will be removed in {remove_in}."
        elif self._version < remove_version:
            self._category = DeprecationWarning
            message = f"{{name}} is deprecated and will be removed in {remove_in}."
        else:
            self._category = None
            message = f"{{name}} was slated for removal in {remove_in}."
        self._message = lambda name: f"{message}{addendum}".format(name=name)

    def __call__(self, func: Callable) -> Callable:
        """Deprecation decorator for functions, methods, & classes."""
        # detect function name
        fullname = f"{func.__module__}.{func.__name__}"
        if self._argument:
            fullname = f"{func.__module__}.{func.__name__}({self._argument})"

        # alert developer that it's time to remove something
        if not self._category:
            raise RuntimeError(self._message(fullname))

        # alert user that it's time to remove something
        @wraps(func)
        def inner(*args, **kwargs):
            # always warn if not deprecating an argument
            # only warn about argument deprecations if the argument is used
            if not self._argument or self._argument in kwargs:
                warnings.warn(self._message(fullname), self._category, stacklevel=2)

                # rename argument deprecations as needed
                value = kwargs.pop(self._argument, None)
                if self._rename:
                    kwargs.setdefault(self._rename, value)

            return func(*args, **kwargs)

        return inner

    @classmethod
    def argument(
        cls,
        deprecate_in: str,
        remove_in: str,
        argument: str,
        *,
        rename: str | None = None,
        addendum: str | None = None,
    ) -> None:
        """Deprecation decorator for keyword arguments."""
        self = cls(deprecate_in=deprecate_in, remove_in=remove_in, addendum=addendum)

        # provide a default addendum if renaming and no addendum is provided
        if rename and not addendum:
            addendum = f"Use '{rename}' instead."

        self = cls(deprecate_in=deprecate_in, remove_in=remove_in, addendum=addendum)
        self._argument = argument
        self._rename = rename

        return self

    @staticmethod
    def _get_module() -> tuple[ModuleType, str]:
        import inspect  # expensive

        try:
            frame = inspect.stack()[2]
            module = inspect.getmodule(frame[0])
            return (module, module.__name__)
        except (IndexError, AttributeError):
            raise RuntimeError("unable to determine the calling module") from None

    @classmethod
    def module(cls, deprecate_in: str, remove_in: str, *, addendum: str | None = None) -> None:
        """Deprecation function for modules."""
        self = cls(deprecate_in=deprecate_in, remove_in=remove_in, addendum=addendum)

        # detect calling module
        _, fullname = self._get_module()

        # alert developer that it's time to remove something
        if not self._category:
            raise RuntimeError(self._message(fullname))

        # alert user that it's time to remove something
        warnings.warn(self._message(fullname), self._category, stacklevel=3)

    @classmethod
    def constant(
        cls,
        deprecate_in: str,
        remove_in: str,
        constant: str,
        value: Any,
        *,
        addendum: str | None = None,
    ) -> None:
        """Deprecation function for module constant (global)."""
        self = cls(deprecate_in=deprecate_in, remove_in=remove_in, addendum=addendum)

        # detect calling module
        module, fullname = self._get_module()

        # alert developer that it's time to remove something
        if not self._category:
            raise RuntimeError(self._message(f"{fullname}.{constant}"))

        super_getattr = getattr(module, "__getattr__", None)

        def __getattr__(name: str) -> Any:
            if name == constant:
                warnings.warn(self._message(f"{fullname}.{name}"), self._category, stacklevel=2)
                return value

            if super_getattr:
                return super_getattr(name)

            raise AttributeError(f"module '{fullname}' has no attribute '{name}'")

        module.__getattr__ = __getattr__

    @classmethod
    def _factory(cls, version: str) -> _deprecated:
        return type("_deprecated", (cls,), {"_version": cls._parse_version(version)})


# initialize conda's deprecation decorator with the current version
_deprecated = _deprecated._factory(__version__)
