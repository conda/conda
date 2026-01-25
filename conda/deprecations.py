# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools to aid in deprecating code."""

from __future__ import annotations

import logging
import sys
import warnings
from argparse import SUPPRESS, Action
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Callable, Iterator
    from typing import Any, ParamSpec, Self, TypeVar

    from packaging.version import Version

    T = TypeVar("T")
    P = ParamSpec("P")

    ActionType = TypeVar("ActionType", bound=type[Action])

from . import __version__


class DeprecatedError(RuntimeError):
    pass


# inspired by deprecation (https://deprecation.readthedocs.io/en/latest/) and
# CPython's warnings._deprecated
class DeprecationHandler:
    _version: str | None
    _version_tuple: tuple[int, ...] | None
    _version_object: Version | None

    # Logger for deprecation messages - used by DeprecationCollector for summary
    # Uses a name outside the conda.* hierarchy to avoid conda's opinionated
    # logging configuration (level overrides, TokenURLFilter, etc.)
    # NullHandler prevents lastResort handler from outputting to stderr
    # propagate=False prevents messages from going to root logger
    _logger: logging.Logger = logging.getLogger("_conda_deprecations")
    _logger.addHandler(logging.NullHandler())
    _logger.propagate = False

    @classmethod
    def _warn(
        cls,
        message: str,
        category: type[Warning],
        stacklevel: int = 0,
        removal_version: str | None = None,
    ) -> None:
        """Issue a deprecation warning and log it for the summary collector.

        This hybrid approach maintains stdlib compatibility (warnings.warn) while
        using logging for flexible summary collection.

        :param message: The deprecation message.
        :param category: The warning category (DeprecationWarning, FutureWarning, etc.)
        :param stacklevel: Additional stack frames to skip (default 0).
        :param removal_version: The version when this will be removed (for sorting).
        """
        # +3 accounts for: _warn -> caller (e.g., inner/decorator) -> user code
        adjusted_stacklevel = stacklevel + 3
        # Stdlib warning for compatibility with PYTHONWARNINGS, pytest, etc.
        warnings.warn(message, category, stacklevel=adjusted_stacklevel)
        # Log for DeprecationCollector to collect (if attached)
        cls._logger.warning(
            message,
            stacklevel=adjusted_stacklevel,
            extra={
                "warning_category": category,
                "removal_version": removal_version,
            },
        )

    @contextmanager
    def collect(self) -> Iterator[_DeprecationCollection]:
        """Context manager that collects deprecation warnings.

        Usage:
            with deprecated.collect() as collected:
                ...
                # Inspect collected warnings if needed
                for (msg, category, removal_version), callers in collected.items():
                    ...
                # Print summary
                collected.print_summary()
        """
        collected = _DeprecationCollection()

        class Handler(logging.Handler):
            def emit(
                _,  # type: ignore[reportSelfClsParameterName]
                record: logging.LogRecord,
            ) -> None:
                # TODO: warning_category and removal_version should always be set
                # by _warn(), consider raising an error if missing to surface bugs
                category = getattr(record, "warning_category", DeprecationWarning)
                removal_version = getattr(record, "removal_version", None)
                key = (record.getMessage(), category, removal_version)
                collected.setdefault(key, set()).add((record.pathname, record.lineno))

        handler = Handler()
        self._logger.addHandler(handler)
        try:
            yield collected
        finally:
            self._logger.removeHandler(handler)

    def __init__(self: Self, version: str) -> None:
        """Factory to create a deprecation handle for the specified version.

        :param version: The version to compare against when checking deprecation statuses.
        """
        self._version = version
        # Try to parse the version string as a simple tuple[int, ...] to avoid
        # packaging.version import and costlier version comparisons.
        self._version_tuple = self._get_version_tuple(version)
        self._version_object = None

    @staticmethod
    def _get_version_tuple(version: str) -> tuple[int, ...] | None:
        """Return version as non-empty tuple of ints if possible, else None.

        :param version: Version string to parse.
        """
        try:
            return tuple(int(part) for part in version.strip().split(".")) or None
        except (AttributeError, ValueError):
            return None

    def _version_less_than(self: Self, version: str) -> bool:
        """Test whether own version is less than the given version.

        :param version: Version string to compare against.
        """
        if self._version_tuple and (version_tuple := self._get_version_tuple(version)):
            return self._version_tuple < version_tuple

        # If self._version or version could not be represented by a simple
        # tuple[int, ...], do a more elaborate version parsing and comparison.
        # Avoid this import otherwise to reduce import time for conda activate.
        from packaging.version import parse

        if self._version_object is None:
            try:
                self._version_object = parse(self._version)  # type: ignore[arg-type]
            except TypeError:
                # TypeError: self._version could not be parsed
                self._version_object = parse("0.0.0.dev0+placeholder")
        return self._version_object < parse(version)

    def __call__(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        *,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = DeprecationWarning,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Deprecation decorator for functions, methods, & classes.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """

        def deprecated_decorator(obj: Callable[P, T]) -> Callable[P, T]:
            # detect function name and generate message
            category, message = self._generate_message(
                deprecate_in=deprecate_in,
                remove_in=remove_in,
                prefix=f"{obj.__module__}.{obj.__qualname__}",
                addendum=addendum,
                deprecation_type=deprecation_type,
            )

            # alert developer that it's time to remove something
            if not category:
                raise DeprecatedError(message)

            # if obj is a class, wrap the __init__
            isclass = False
            func: Callable[P, T]
            if isinstance(obj, type):
                try:
                    func = obj.__init__  # type: ignore[misc]
                except AttributeError:
                    # AttributeError: obj has no __init__
                    func = obj
                else:
                    isclass = True
            else:
                func = obj

            # alert user that it's time to remove something
            @wraps(func)  # type: ignore[reportArgumentType]
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                self._warn(message, category, stack, remove_in)

                return func(*args, **kwargs)

            if isclass:
                obj.__init__ = inner  # type: ignore[misc]
                return obj
            else:
                return inner

        return deprecated_decorator

    def argument(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        argument: str,
        *,
        rename: str | None = None,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = DeprecationWarning,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Deprecation decorator for keyword arguments.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param argument: The argument to deprecate.
        :param rename: Optional new argument name.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """

        def deprecated_decorator(func: Callable[P, T]) -> Callable[P, T]:
            # detect function name and generate message
            category, message = self._generate_message(
                deprecate_in=deprecate_in,
                remove_in=remove_in,
                prefix=f"{func.__module__}.{func.__qualname__}({argument})",
                # provide a default addendum if renaming and no addendum is provided
                addendum=(
                    f"Use '{rename}' instead." if rename and not addendum else addendum
                ),
                deprecation_type=deprecation_type,
            )

            # alert developer that it's time to remove something
            if not category:
                raise DeprecatedError(message)

            # alert user that it's time to remove something
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                # only warn about argument deprecations if the argument is used
                if argument in kwargs:
                    self._warn(message, category, stack, remove_in)

                    # rename argument deprecations as needed
                    value = kwargs.pop(argument, None)
                    if rename:
                        kwargs.setdefault(rename, value)

                return func(*args, **kwargs)

            return inner

        return deprecated_decorator

    def action(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        action: ActionType,
        *,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = FutureWarning,
    ) -> ActionType:
        """Wraps any argparse.Action to issue a deprecation warning."""

        class DeprecationMixin(Action):
            category: type[Warning]
            help: str  # override argparse.Action's help type annotation

            def __init__(inner_self: Self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)

                category, message = self._generate_message(
                    deprecate_in=deprecate_in,
                    remove_in=remove_in,
                    prefix=(
                        # option_string are ordered shortest to longest,
                        # use the longest as it's the most descriptive
                        f"`{inner_self.option_strings[-1]}`"
                        if inner_self.option_strings
                        # if not a flag/switch, use the destination itself
                        else f"`{inner_self.dest}`"
                    ),
                    addendum=addendum,
                    deprecation_type=deprecation_type,
                )

                # alert developer that it's time to remove something
                if not category:
                    raise DeprecatedError(message)

                inner_self.category = category
                inner_self.deprecation = message
                if inner_self.help is not SUPPRESS:
                    inner_self.help = message

            def __call__(
                inner_self: Self,
                parser: ArgumentParser,
                namespace: Namespace,
                values: Any,
                option_string: str | None = None,
            ) -> None:
                # alert user that it's time to remove something
                from conda.common.constants import NULL

                if values is not NULL:
                    self._warn(
                        inner_self.deprecation,
                        inner_self.category,
                        stack + 5,
                        remove_in,
                    )

                super().__call__(parser, namespace, values, option_string)

        return type(action.__name__, (DeprecationMixin, action), {})  # type: ignore[return-value]

    def module(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        *,
        addendum: str | None = None,
        stack: int = 0,
    ) -> None:
        """Deprecation function for modules.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """
        self.topic(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            topic=self._get_module(stack)[1],
            addendum=addendum,
            stack=2 + stack,
        )

    def constant(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        constant: str,
        value: Any,
        *,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = DeprecationWarning,
    ) -> None:
        """Deprecation function for module constant/global.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param constant:
        :param value:
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """
        # detect calling module
        module, fullname = self._get_module(stack)
        # detect function name and generate message
        category, message = self._generate_message(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            prefix=f"{fullname}.{constant}",
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        # alert developer that it's time to remove something
        if not category:
            raise DeprecatedError(message)

        # patch module level __getattr__ to alert user that it's time to remove something
        if isinstance(
            fallback := getattr(module, "__getattr__", None),
            _ConstantDeprecationRegistry,
        ):
            deprecations = fallback
        else:
            deprecations = _ConstantDeprecationRegistry(fullname, fallback)
            module.__getattr__ = deprecations  # type: ignore[method-assign]

        deprecations.register(constant, message, category, stack, remove_in, value)

    def topic(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        *,
        topic: str,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = DeprecationWarning,
    ) -> None:
        """Deprecation function for a topic.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param topic: The topic being deprecated.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """
        # detect function name and generate message
        category, message = self._generate_message(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            prefix=topic,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        # alert developer that it's time to remove something
        if not category:
            raise DeprecatedError(message)

        # alert user that it's time to remove something
        self._warn(message, category, stacklevel=stack, removal_version=remove_in)

    def _get_module(self: Self, stack: int) -> tuple[ModuleType, str]:
        """Detect the module from which we are being called.

        :param stack: The stacklevel increment.
        :return: The module and module name.
        """
        try:
            frame = sys._getframe(2 + stack)
        except IndexError:
            # IndexError: 2 + stack is out of range
            pass
        else:
            # Shortcut finding the module by manually inspecting loaded modules.
            try:
                filename = frame.f_code.co_filename
            except AttributeError:
                # AttributeError: frame.f_code.co_filename is undefined
                pass
            else:
                # use a copy of sys.modules to avoid RuntimeError during iteration
                # see https://github.com/conda/conda/issues/13754
                for loaded in tuple(sys.modules.values()):
                    if not isinstance(loaded, ModuleType):
                        continue
                    if not hasattr(loaded, "__file__"):
                        continue
                    if loaded.__file__ == filename:
                        return (loaded, loaded.__name__)

            # If above failed, do an expensive import and costly getmodule call.
            import inspect

            module = inspect.getmodule(frame)
            if module is not None:
                return (module, module.__name__)

        raise DeprecatedError("unable to determine the calling module")

    def _generate_message(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        prefix: str,
        addendum: str | None,
        *,
        deprecation_type: type[Warning],
    ) -> tuple[type[Warning] | None, str]:
        """Generate the standardized deprecation message and determine whether the
        deprecation is pending, active, or past.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param prefix: The message prefix, usually the function name.
        :param addendum: Additional messaging. Useful to indicate what to do instead.
        :param deprecation_type: The warning type to use for active deprecations.
        :return: The warning category (if applicable) and the message.
        """
        category: type[Warning] | None
        if self._version_less_than(deprecate_in):
            category = PendingDeprecationWarning
            warning = f"is pending deprecation and will be removed in {remove_in}."
        elif self._version_less_than(remove_in):
            category = deprecation_type
            warning = f"is deprecated and will be removed in {remove_in}."
        else:
            category = None
            warning = f"was slated for removal in {remove_in}."

        return (
            category,
            " ".join(filter(None, [prefix, warning, addendum])),  # message
        )


@dataclass
class _ConstantDeprecationRegistry:
    """Registry of deprecated module constants.

    Serves as a module's __getattr__, issuing deprecation warnings
    when registered constants are accessed.
    """

    deprecations: dict[str, tuple[str, type[Warning], int, str, Any]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    fullname: str
    fallback: Callable[[str], Any] | None

    def __call__(self, name: str) -> Any:
        if name in self.deprecations:
            message, category, stacklevel, removal_version, value = self.deprecations[
                name
            ]
            DeprecationHandler._warn(message, category, stacklevel, removal_version)
            return value

        if self.fallback:
            return self.fallback(name)

        raise AttributeError(f"module '{self.fullname}' has no attribute '{name}'")

    def register(
        self,
        constant: str,
        message: str,
        category: type[Warning],
        stack: int,
        removal_version: str,
        value: Any,
    ) -> None:
        self.deprecations[constant] = (message, category, stack, removal_version, value)


class _DeprecationCollection(dict):
    """Collected deprecation warnings with print_summary capability.

    A dict mapping (message, category, removal_version) -> set of (filename, lineno).
    """

    def print_summary(self) -> None:
        """Print a summary of collected deprecation warnings to stderr.

        Grouped by removal version (earliest first), with headers.
        """
        if not self:
            return

        from .common.io import dashlist
        from .common.iterators import groupby_to_dict

        # Group by removal_version, sort groups by version tuple (earliest first)
        groups = groupby_to_dict(
            lambda item: DeprecationHandler._get_version_tuple(item[0][2]), self.items()
        )

        print(f"\nDeprecation warnings ({len(self)}):", file=sys.stderr)
        for removal_version, messages in sorted(groups.items()):
            print(f"  Removing in {removal_version}:", file=sys.stderr)
            for (message, _category, _removal_version), callers in messages:
                caller_list = [f"{filename}:{lineno}" for filename, lineno in callers]
                print(
                    f"    {message}{dashlist(caller_list, indent=6, prefix='↳ ')}",
                    file=sys.stderr,
                )


deprecated = DeprecationHandler(__version__)
