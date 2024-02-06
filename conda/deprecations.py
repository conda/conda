# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools to aid in deprecating code."""
from __future__ import annotations

import sys
import warnings
from functools import wraps
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Action
    from typing import Any, Callable

    from packaging.version import Version

from . import __version__


class DeprecatedError(RuntimeError):
    pass


# inspired by deprecation (https://deprecation.readthedocs.io/en/latest/) and
# CPython's warnings._deprecated
class DeprecationHandler:
    _version_str: str
    _version_tuple: tuple[int, ...]
    _version_object: Version | None

    def __init__(self, version: Version | str):
        """Factory to create a deprecation handle for the specified version.

        :param version: The version to compare against when checking deprecation statuses.
        """
        self._version_str = None
        self._version_object = None
        self._version_tuple = None
        if version is not None:
            self._version_str = str(version)
            if not isinstance(version, str):
                self._version_object = version
            # Try to parse the version string as a simple tuple[int, ...] to
            # avoid packaging.version import and costlier version comparisons.
            self._version_tuple = self._get_version_tuple(self._version_str)

    @property
    def _version(self) -> Version:
        """Populate and return self._version_object with parsed version string."""
        # Lazily import this to reduce import time for conda activate.
        from packaging.version import parse

        if self._version_object is None:
            try:
                self._version_object = parse(self._version_str)
            except TypeError:
                self._version_object = parse("0.0.0.dev0+placeholder")
        return self._version_object

    @staticmethod
    def _get_version_tuple(version_str: str) -> tuple[int, ...]:
        """Parse version as a tuple of ints if possible, else return empty tuple.

        :param version_str: Version string to parse.
        """
        try:
            return tuple(int(part) for part in version_str.strip().split("."))
        except (AttributeError, ValueError):
            return tuple()

    def _version_less_than(self, version_str: str) -> bool:
        """Test whether own version is less than the given version.

        :param version_str: Version string to compare against.
        """
        if self._version_tuple:
            if version_tuple := self._get_version_tuple(version_str):
                return self._version_tuple < version_tuple

        # If self._version_str or version_str could not be represented by a
        # simple tuple[int, ...], do a more elaborate version parse and compare.
        # Avoid this import otherwise to reduce import time for conda activate.
        from packaging.version import parse

        return self._version < parse(version_str)

    def __call__(
        self,
        deprecate_in: str,
        remove_in: str,
        *,
        addendum: str | None = None,
        stack: int = 0,
    ) -> Callable[[Callable], Callable]:
        """Deprecation decorator for functions, methods, & classes.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """

        def deprecated_decorator(func: Callable) -> Callable:
            # detect function name and generate message
            category, message = self._generate_message(
                deprecate_in,
                remove_in,
                f"{func.__module__}.{func.__qualname__}",
                addendum=addendum,
            )

            # alert developer that it's time to remove something
            if not category:
                raise DeprecatedError(message)

            # alert user that it's time to remove something
            @wraps(func)
            def inner(*args, **kwargs):
                warnings.warn(message, category, stacklevel=2 + stack)

                return func(*args, **kwargs)

            return inner

        return deprecated_decorator

    def argument(
        self,
        deprecate_in: str,
        remove_in: str,
        argument: str,
        *,
        rename: str | None = None,
        addendum: str | None = None,
        stack: int = 0,
    ) -> Callable[[Callable], Callable]:
        """Deprecation decorator for keyword arguments.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param argument: The argument to deprecate.
        :param rename: Optional new argument name.
        :param addendum: Optional additional messaging. Useful to indicate what to do instead.
        :param stack: Optional stacklevel increment.
        """

        def deprecated_decorator(func: Callable) -> Callable:
            # detect function name and generate message
            category, message = self._generate_message(
                deprecate_in,
                remove_in,
                f"{func.__module__}.{func.__qualname__}({argument})",
                # provide a default addendum if renaming and no addendum is provided
                addendum=f"Use '{rename}' instead."
                if rename and not addendum
                else addendum,
            )

            # alert developer that it's time to remove something
            if not category:
                raise DeprecatedError(message)

            # alert user that it's time to remove something
            @wraps(func)
            def inner(*args, **kwargs):
                # only warn about argument deprecations if the argument is used
                if argument in kwargs:
                    warnings.warn(message, category, stacklevel=2 + stack)

                    # rename argument deprecations as needed
                    value = kwargs.pop(argument, None)
                    if rename:
                        kwargs.setdefault(rename, value)

                return func(*args, **kwargs)

            return inner

        return deprecated_decorator

    def action(
        self,
        deprecate_in: str,
        remove_in: str,
        action: type[Action],
        *,
        addendum: str | None = None,
        stack: int = 0,
    ):
        class DeprecationMixin:
            def __init__(inner_self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                category, message = self._generate_message(
                    deprecate_in,
                    remove_in,
                    (
                        # option_string are ordered shortest to longest,
                        # use the longest as it's the most descriptive
                        f"`{inner_self.option_strings[-1]}`"
                        if inner_self.option_strings
                        # if not a flag/switch, use the destination itself
                        else f"`{inner_self.dest}`"
                    ),
                    addendum=addendum,
                )

                # alert developer that it's time to remove something
                if not category:
                    raise DeprecatedError(message)

                inner_self.category = category
                inner_self.help = message

            def __call__(inner_self, parser, namespace, values, option_string=None):
                # alert user that it's time to remove something
                warnings.warn(
                    inner_self.help, inner_self.category, stacklevel=7 + stack
                )

                super().__call__(parser, namespace, values, option_string)

        return type(action.__name__, (DeprecationMixin, action), {})

    def module(
        self,
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
        self,
        deprecate_in: str,
        remove_in: str,
        constant: str,
        value: Any,
        *,
        addendum: str | None = None,
        stack: int = 0,
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
            deprecate_in,
            remove_in,
            f"{fullname}.{constant}",
            addendum,
        )

        # alert developer that it's time to remove something
        if not category:
            raise DeprecatedError(message)

        # patch module level __getattr__ to alert user that it's time to remove something
        super_getattr = getattr(module, "__getattr__", None)

        def __getattr__(name: str) -> Any:
            if name == constant:
                warnings.warn(message, category, stacklevel=2 + stack)
                return value

            if super_getattr:
                return super_getattr(name)

            raise AttributeError(f"module '{fullname}' has no attribute '{name}'")

        module.__getattr__ = __getattr__

    def topic(
        self,
        deprecate_in: str,
        remove_in: str,
        *,
        topic: str,
        addendum: str | None = None,
        stack: int = 0,
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
            deprecate_in,
            remove_in,
            topic,
            addendum,
        )

        # alert developer that it's time to remove something
        if not category:
            raise DeprecatedError(message)

        # alert user that it's time to remove something
        warnings.warn(message, category, stacklevel=2 + stack)

    def _get_module(self, stack: int) -> tuple[ModuleType, str]:
        """Detect the module from which we are being called.

        :param stack: The stacklevel increment.
        :return: The module and module name.
        """
        import inspect  # expensive

        try:
            frame = sys._getframe(2 + stack)
            module = inspect.getmodule(frame)
            if module is not None:
                return (module, module.__name__)
        except IndexError:
            # IndexError: 2 + stack is out of range
            pass

        raise DeprecatedError("unable to determine the calling module")

    def _generate_message(
        self,
        deprecate_in: str,
        remove_in: str,
        prefix: str,
        addendum: str | None,
    ) -> tuple[type[Warning] | None, str]:
        """Deprecation decorator for functions, methods, & classes.

        :param deprecate_in: Version in which code will be marked as deprecated.
        :param remove_in: Version in which code is expected to be removed.
        :param prefix: The message prefix, usually the function name.
        :param addendum: Additional messaging. Useful to indicate what to do instead.
        :return: The warning category (if applicable) and the message.
        """
        category: type[Warning] | None
        if self._version_less_than(deprecate_in):
            category = PendingDeprecationWarning
            warning = f"is pending deprecation and will be removed in {remove_in}."
        elif self._version_less_than(remove_in):
            category = DeprecationWarning
            warning = f"is deprecated and will be removed in {remove_in}."
        else:
            category = None
            warning = f"was slated for removal in {remove_in}."

        return (
            category,
            " ".join(filter(None, [prefix, warning, addendum])),  # message
        )


deprecated = DeprecationHandler(__version__)
