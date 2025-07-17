# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""OS-agnostic, system-level binary package manager."""

from __future__ import annotations

import os
import sys
from json import JSONEncoder  # noqa: TID251
from os.path import abspath, dirname
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from subprocess import Popen
    from typing import Any

try:
    from ._version import __version__
except ImportError:
    # _version.py is only created after running `pip install`
    try:
        from setuptools_scm import get_version

        __version__ = get_version(root="..", relative_to=__file__)
    except (ImportError, OSError, LookupError):
        # ImportError: setuptools_scm isn't installed
        # OSError: git isn't installed
        # LookupError: setuptools_scm unable to detect version
        # Conda abides by CEP-8 which specifies using CalVer, so the dev version is:
        #     YY.MM.MICRO.devN+gHASH[.dirty]
        __version__ = "0.0.0.dev0+placeholder"

__all__ = (
    "__name__",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__summary__",
    "__url__",
    "CONDA_PACKAGE_ROOT",
    "CondaError",
    "CondaMultiError",
    "CondaExitZero",
    "conda_signal_handler",
    "__copyright__",
)

__name__ = "conda"
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


class CondaError(Exception):
    return_code: int = 1
    reportable: bool = False  # Exception may be reported to core maintainers

    def __init__(self, message: str | None, caused_by: Any = None, **kwargs):
        self.message = message or ""
        self._kwargs = kwargs
        self._caused_by = caused_by
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self}"

    def __str__(self) -> str:
        try:
            return str(self.message) % self._kwargs
        except Exception:
            debug_message = "\n".join(
                (
                    "class: " + self.__class__.__name__,
                    "message:",
                    self.message,
                    "kwargs:",
                    str(self._kwargs),
                    "",
                )
            )
            print(debug_message, file=sys.stderr)
            raise

    def dump_map(self) -> dict[str, Any]:
        result = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        result.update(
            exception_type=str(type(self)),
            exception_name=self.__class__.__name__,
            message=str(self),
            error=repr(self),
            caused_by=repr(self._caused_by),
            **self._kwargs,
        )
        return result


class CondaMultiError(CondaError):
    def __init__(self, errors: Iterable[CondaError]):
        self.errors = errors
        super().__init__(None)

    def __repr__(self) -> str:
        errs = []
        for e in self.errors:
            if isinstance(e, EnvironmentError) and not isinstance(e, CondaError):
                errs.append(str(e))
            else:
                # We avoid Python casting this back to a str()
                # by using e.__repr__() instead of repr(e)
                # https://github.com/scrapy/cssselect/issues/34
                errs.append(e.__repr__())
        res = "\n".join(errs)
        return res

    def __str__(self) -> str:
        return "\n".join(str(e) for e in self.errors) + "\n"

    def dump_map(self) -> dict[str, str | tuple[str, ...]]:
        return dict(
            exception_type=str(type(self)),
            exception_name=self.__class__.__name__,
            errors=tuple(error.dump_map() for error in self.errors),
            error="Multiple Errors Encountered.",
        )

    def contains(self, exception_class: BaseException | tuple[BaseException]) -> bool:
        return any(isinstance(e, exception_class) for e in self.errors)


class CondaExitZero(CondaError):
    return_code = 0


ACTIVE_SUBPROCESSES: Iterable[Popen] = set()


def conda_signal_handler(signum: int, frame: Any):
    # This function is in the base __init__.py so that it can be monkey-patched by other code
    #   if downstream conda users so choose.  The biggest danger of monkey-patching is that
    #   unlink/link transactions don't get rolled back if interrupted mid-transaction.
    for p in ACTIVE_SUBPROCESSES:
        if p.poll() is None:
            p.send_signal(signum)

    from .exceptions import CondaSignalInterrupt

    raise CondaSignalInterrupt(signum)


def _default(self, obj):
    from frozendict import frozendict

    from .deprecations import deprecated

    if isinstance(obj, frozendict):
        deprecated.topic(
            "26.3",
            "26.9",
            topic="Monkey-patching `json.JSONEncoder` to support `frozendict`",
            addendum="Use `conda.common.serialize.json.CondaJSONEncoder` instead.",
        )
        return dict(obj)
    elif hasattr(obj, "to_json"):
        deprecated.topic(
            "26.3",
            "26.9",
            topic="Monkey-patching `json.JSONEncoder` to support `obj.to_json()`",
            addendum="Use `conda.common.serialize.json.CondaJSONEncoder` instead.",
        )
        return obj.to_json()
    return _default.default(obj)


# FUTURE: conda 26.3, remove the following monkey patching
_default.default = JSONEncoder().default
JSONEncoder.default = _default
