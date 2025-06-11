# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools to aid in deprecating code."""

from __future__ import annotations

import ast
import importlib.util
import pkgutil
import sys
import warnings
from abc import ABC, abstractmethod
from argparse import SUPPRESS, Action
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from types import ModuleType
    from typing import Any, Callable, ParamSpec, Self, TypeVar

    from packaging.version import Version

    T = TypeVar("T")
    P = ParamSpec("P")

    ActionType = TypeVar("ActionType", bound=type[Action])

from . import __version__


class DeprecatedError(RuntimeError):
    pass


class ExperimentConcluded(RuntimeError):
    pass


# Base class for both deprecation and experimental handlers
class BaseHandler(ABC):
    """Base handler for version-based feature lifecycle management."""

    _version: str | None
    _version_tuple: tuple[int, ...] | None
    _version_object: Version | None

    def __init__(self: Self, version: str) -> None:
        """Initialize the handler with a version for comparison.

        :param version: The version to compare against when checking statuses.
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

    def _get_module(self: Self, stack: int) -> tuple[ModuleType, str]:
        """Get the module and its name from the call stack.

        :param stack: How many stack frames to go back (0 = current frame).
        :return: The module object and its full name.
        """
        frame = sys._getframe(2 + stack)
        module_name = frame.f_globals.get("__name__")
        if module_name is None:
            raise RuntimeError("Cannot determine module name from frame")

        module = sys.modules[module_name]
        return module, module_name

    def _get_caller_module(self: Self) -> tuple[ModuleType, str]:
        """Find the calling module by walking up the stack frames.

        This intelligently finds the calling module, particularly useful when
        running under pytest where the call stack depth can vary.
        """
        # Look through all frames to find one that looks like a test module
        frame = sys._getframe(1)  # Start from caller
        while frame:
            module_name = frame.f_globals.get("__name__")
            if module_name and (
                "test" in module_name.lower() or module_name.startswith("tests")
            ):
                module = sys.modules[module_name]
                return module, module_name
            frame = frame.f_back

        # Fallback to regular stack-based detection
        return self._get_module(3)

    def _get_function_prefix(self: Self, func: Callable[P, T]) -> str:
        """Extract standard prefix for function/method/class.

        :param func: The function to extract prefix from.
        :return: Standard prefix string.
        """
        return f"{func.__module__}.{func.__qualname__}"

    def _get_argument_prefix(self: Self, func: Callable[P, T], argument: str) -> str:
        """Extract standard prefix for function argument.

        :param func: The function to extract prefix from.
        :param argument: The argument name.
        :return: Standard prefix string.
        """
        return f"{func.__module__}.{func.__qualname__}({argument})"

    def _get_action_prefix(self: Self, action_instance: Action) -> str:
        """Extract standard prefix for argparse action.

        :param action_instance: The action instance.
        :return: Standard prefix string.
        """
        return (
            # option_string are ordered shortest to longest,
            # use the longest as it's the most descriptive
            f"`{action_instance.option_strings[-1]}`"
            if action_instance.option_strings
            # if not a flag/switch, use the destination itself
            else f"`{action_instance.dest}`"
        )

    def _get_constant_prefix(self: Self, constant: str, stack: int = 0) -> str:
        """Extract standard prefix for module constant.

        :param constant: The constant name.
        :param stack: Stack level adjustment.
        :return: Standard prefix string.
        """
        _, fullname = self._get_module(stack)
        return f"{fullname}.{constant}"

    @abstractmethod
    def _handle_function(
        self: Self,
        func: Callable[P, T],
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[P, T]:
        """Handle function decoration logic (subclass-specific).

        :param func: The function to handle.
        :param prefix: The prefix string.
        :return: The decorated function.
        """
        pass

    @abstractmethod
    def _handle_validation(self: Self, prefix: str, *args: Any, **kwargs: Any) -> None:
        """Handle validation logic (subclass-specific).

        :param prefix: The prefix string.
        """
        pass

    def _create_function_decorator(
        self: Self,
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Create a decorator for functions, methods, and classes.

        :param prefix: The prefix string for the function.
        :return: Decorator function.
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            # Handle validation first
            self._handle_validation(prefix, *args, **kwargs)

            # Return the handled function
            return self._handle_function(func, prefix, *args, **kwargs)

        return decorator

    def _create_action_mixin(
        self: Self,
        action: ActionType,
        mixin_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> ActionType:
        """Create a mixin class for argparse actions.

        :param action: The base action class.
        :param mixin_name: Name for the mixin class.
        :return: Mixed action class.
        """
        base_handler = self

        class BaseMixin(Action):
            def __init__(inner_self: Self, *init_args: Any, **init_kwargs: Any) -> None:
                super().__init__(*init_args, **init_kwargs)

                prefix = base_handler._get_action_prefix(inner_self)

                # Handle validation
                base_handler._handle_validation(prefix, *args, **kwargs)

                # Store prefix for later use by subclass mixins
                inner_self._handler_prefix = prefix
                inner_self._handler_args = args
                inner_self._handler_kwargs = kwargs

        return type(mixin_name, (BaseMixin, action), {})  # type: ignore[return-value]


# inspired by deprecation (https://deprecation.readthedocs.io/en/latest/) and
# CPython's warnings._deprecated
class DeprecationHandler(BaseHandler):
    """Handler for deprecated features that warns users and can raise errors."""

    def _handle_validation(self: Self, prefix: str, *args: Any, **kwargs: Any) -> None:
        """Handle deprecation validation."""
        deprecate_in = args[0] if args else None
        remove_in = args[1] if len(args) > 1 else None
        addendum = kwargs.get("addendum")
        deprecation_type = kwargs.get("deprecation_type", DeprecationWarning)

        if deprecate_in and remove_in:
            category, message = self._generate_message(
                deprecate_in=deprecate_in,
                remove_in=remove_in,
                prefix=prefix,
                addendum=addendum,
                deprecation_type=deprecation_type,
            )

            # alert developer that it's time to remove something
            if not category:
                raise DeprecatedError(message)

    def _handle_function(
        self: Self,
        func: Callable[P, T],
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[P, T]:
        """Handle function decoration for deprecation."""
        deprecate_in = args[0] if args else None
        remove_in = args[1] if len(args) > 1 else None
        addendum = kwargs.get("addendum")
        stack = kwargs.get("stack", 0)
        deprecation_type = kwargs.get("deprecation_type", DeprecationWarning)

        if not deprecate_in or not remove_in:
            raise ValueError("deprecate_in and remove_in are required")

        category, message = self._generate_message(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            prefix=prefix,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        @wraps(func)
        def inner(*inner_args: P.args, **inner_kwargs: P.kwargs) -> T:
            warnings.warn(message, category, stacklevel=2 + stack)
            return func(*inner_args, **inner_kwargs)

        return inner

    def __call__(
        self: Self,
        deprecate_in: str,
        remove_in: str,
        *,
        addendum: str | None = None,
        stack: int = 0,
        deprecation_type: type[Warning] = DeprecationWarning,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Deprecation decorator for functions, methods, & classes."""

        def deprecated_decorator(func: Callable[P, T]) -> Callable[P, T]:
            prefix = self._get_function_prefix(func)
            return self._create_function_decorator(
                prefix,
                deprecate_in,
                remove_in,
                addendum=addendum,
                stack=stack,
                deprecation_type=deprecation_type,
            )(func)

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
        """Deprecation decorator for keyword arguments."""

        def deprecated_decorator(func: Callable[P, T]) -> Callable[P, T]:
            prefix = self._get_argument_prefix(func, argument)

            # Provide default addendum if renaming and no addendum is provided
            final_addendum = (
                f"Use '{rename}' instead." if rename and not addendum else addendum
            )

            # Handle validation
            self._handle_validation(
                prefix,
                deprecate_in,
                remove_in,
                addendum=final_addendum,
                deprecation_type=deprecation_type,
            )

            category, message = self._generate_message(
                deprecate_in=deprecate_in,
                remove_in=remove_in,
                prefix=prefix,
                addendum=final_addendum,
                deprecation_type=deprecation_type,
            )

            # Get the function signature to determine parameter positions
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Find the position of the deprecated argument
            deprecated_param_index = None
            if argument in param_names:
                deprecated_param_index = param_names.index(argument)

            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                # If the deprecated parameter can be passed positionally and too many positional args are given
                if (deprecated_param_index is not None and 
                    len(args) > deprecated_param_index):
                    raise TypeError(
                        f"{func.__name__}() got {len(args)} positional argument{'s' if len(args) > 1 else ''} "
                        f"but expected at most {deprecated_param_index} "
                        f"('{argument}' is deprecated and must be passed as keyword argument)"
                    )

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

        BaseMixin = self._create_action_mixin(
            action,
            "DeprecationMixin",
            deprecate_in,
            remove_in,
            addendum=addendum,
            stack=stack,
            deprecation_type=deprecation_type,
        )

        class DeprecationMixin(BaseMixin):
            category: type[Warning]
            help: str  # override argparse.Action's help type annotation
            _handler_prefix: str
            deprecation: str

            def __init__(inner_self: Self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)

                category, message = self._generate_message(
                    deprecate_in=deprecate_in,
                    remove_in=remove_in,
                    prefix=inner_self._handler_prefix,
                    addendum=addendum,
                    deprecation_type=deprecation_type,
                )

                # Category should never be None here since we validated in BaseMixin
                if category is None:
                    raise DeprecatedError(
                        f"Action {inner_self._handler_prefix} has already expired"
                    )

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
                    warnings.warn(
                        inner_self.deprecation,
                        inner_self.category,
                        stacklevel=7 + stack,
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
        """Deprecation function for modules."""
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
        """Deprecation function for module constant/global."""
        # detect calling module
        module, fullname = self._get_module(stack)
        prefix = self._get_constant_prefix(constant, stack)

        # Handle validation
        self._handle_validation(
            prefix,
            deprecate_in,
            remove_in,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        category, message = self._generate_message(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            prefix=prefix,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        # patch module level __getattr__ to alert user that it's time to remove something
        super_getattr = getattr(module, "__getattr__", None)

        def __getattr__(name: str) -> Any:
            if name == constant:
                warnings.warn(message, category, stacklevel=3 + stack)
                return value

            if super_getattr:
                return super_getattr(name)

            raise AttributeError(f"module '{fullname}' has no attribute '{name}'")

        module.__getattr__ = __getattr__  # type: ignore[method-assign]

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
        """Deprecation function for a topic."""
        # Handle validation
        self._handle_validation(
            topic,
            deprecate_in,
            remove_in,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        category, message = self._generate_message(
            deprecate_in=deprecate_in,
            remove_in=remove_in,
            prefix=topic,
            addendum=addendum,
            deprecation_type=deprecation_type,
        )

        # alert user that it's time to remove something
        warnings.warn(message, category, stacklevel=2 + stack)

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


class ExperimentalFeatureVisitor(ast.NodeVisitor):
    """Simple AST visitor to find experimental decorators."""

    def __init__(self, module_name: str, handler: ExperimentHandler):
        self.module_name = module_name
        self.handler = handler
        self.features: list[dict[str, Any]] = []
        self.class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        if isinstance(node.value, ast.Call):
            feature = self._parse_experimental_method_call(node.value, self.module_name)
            if feature:
                self.features.append(feature)
        self.generic_visit(node)

    def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            feature = self._parse_experimental_decorator(
                decorator, node.name, self.module_name
            )
            if feature:
                if self.class_stack:
                    class_path = ".".join(self.class_stack)
                    feature["prefix"] = f"{self.module_name}.{class_path}.{node.name}"
                else:
                    feature["prefix"] = f"{self.module_name}.{node.name}"
                self.features.append(feature)

    def _parse_experimental_decorator(
        self, decorator: ast.AST, name: str, module_name: str
    ) -> dict[str, Any] | None:
        """Parse an @experimental decorator."""
        if not isinstance(decorator, ast.Call):
            return None

        # Check if it's @experimental(...) or @experimental.method(...)
        until = None
        addendum = None

        if isinstance(decorator.func, ast.Name) and decorator.func.id == "experimental":
            # @experimental(until="...")
            until = self._get_call_arg(decorator, "until") or (
                decorator.args[0].value
                if decorator.args and isinstance(decorator.args[0], ast.Constant)
                else None
            )  # type: ignore[attr-defined]
            addendum = self._get_call_arg(decorator, "addendum")
        elif (
            isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "experimental"
        ):
            # @experimental.argument(...) etc
            until = self._get_call_arg(decorator, "until")
            addendum = self._get_call_arg(decorator, "addendum")

        if until:
            return {
                "prefix": f"{module_name}.{name}",
                "until": until,
                "addendum": addendum,
            }
        return None

    def _parse_experimental_method_call(
        self, call: ast.Call, module_name: str
    ) -> dict[str, Any] | None:
        """Parse experimental.method() calls."""
        if not (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "experimental"
        ):
            return None

        method = call.func.attr
        if method not in ("module", "constant", "topic"):
            return None

        until = self._get_call_arg(call, "until")
        addendum = self._get_call_arg(call, "addendum")

        if method == "module":
            prefix = module_name
        elif method == "topic":
            topic = self._get_call_arg(call, "topic")
            prefix = topic or f"{module_name}.topic"
        else:  # constant
            constant = self._get_call_arg(call, "constant")
            prefix = (
                f"{module_name}.{constant}" if constant else f"{module_name}.constant"
            )

        return (
            {"prefix": prefix, "until": until, "addendum": addendum} if until else None
        )

    def _get_call_arg(self, call: ast.Call, arg_name: str) -> str | None:
        """Get argument value from call - simplified for conda's controlled decorators."""
        # Check keyword arguments
        for keyword in call.keywords:
            if keyword.arg == arg_name and isinstance(keyword.value, ast.Constant):
                return keyword.value.value
        return None


class ExperimentHandler(BaseHandler):
    """Handler for experimental features that tracks usage without warning users."""

    def __init__(self: Self, version: str) -> None:
        """Initialize the experimental handler with a version for comparison."""
        super().__init__(version)

    def _check_concluded(self: Self, until: str, prefix: str) -> bool:
        """Check if an experimental feature has concluded."""
        if not self._version_less_than(until):
            raise ExperimentConcluded(
                f"{prefix} experimental feature concluded in {until}"
            )
        return False

    def _handle_validation(self: Self, prefix: str, *args: Any, **kwargs: Any) -> None:
        """Handle experimental validation."""
        until = args[0] if args else None
        if until:
            self._check_concluded(until, prefix)

    def _handle_function(
        self: Self,
        func: Callable[P, T],
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[P, T]:
        """Handle function decoration for experimental features."""
        return func  # Return unchanged

    def scan(
        self: Self, check: bool = False, grace_versions: int = 1
    ) -> list[dict[str, Any]]:
        """Scan for experimental features using proper Python module discovery.

        :param check: If True, validate that no features have expired beyond grace period
        :param grace_versions: Number of grace versions to allow past conclusion (only used if check=True)
        :return: List of experimental features found
        """
        # Import conda to get its package path
        import conda

        features = []

        # Use pkgutil to properly walk the conda package hierarchy
        for finder, module_name, ispkg in pkgutil.walk_packages(
            conda.__path__, conda.__name__ + "."
        ):
            # Skip test modules using more robust checking
            if any(part.startswith("test") for part in module_name.split(".")):
                continue

            # Get the module spec to find the actual file path
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin and spec.origin.endswith(".py"):
                file_path = Path(spec.origin)
                features.extend(self._scan_file(file_path, module_name))

        # Optionally validate that no features have expired
        if check:
            from packaging.version import parse

            current_version = (
                parse(self._version) if self._version else parse("0.0.0.dev0")
            )

            for feature in features:
                conclude_version = parse(feature["until"])
                grace_parts = list(conclude_version.release)
                if len(grace_parts) >= 2:
                    grace_parts[1] += grace_versions
                else:
                    grace_parts.append(grace_versions)
                grace_version = parse(".".join(str(p) for p in grace_parts))

                if current_version >= grace_version:
                    raise ExperimentConcluded(
                        f"{feature['prefix']} experimental feature concluded in {feature['until']} "
                        f"and has exceeded the grace period (current: {self._version})"
                    )

        return features

    def _scan_file(
        self: Self, file_path: Path, module_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Scan a single file - simplified for conda's well-formed codebase."""
        # Read file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        # Use provided module name or fall back to path-based logic
        if module_name is None:
            parts = file_path.with_suffix("").parts
            if "conda" in parts:
                conda_idx = parts.index("conda")
                module_name = ".".join(parts[conda_idx:])
            else:
                module_name = file_path.stem

        # Use visitor
        visitor = ExperimentalFeatureVisitor(module_name, self)
        visitor.visit(tree)
        return visitor.features

    # Consolidated decorator method
    def __call__(
        self: Self,
        until: str,
        *,
        addendum: str | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Experimental decorator for functions, methods, & classes."""

        def experimental_decorator(func: Callable[P, T]) -> Callable[P, T]:
            prefix = self._get_function_prefix(func)
            return self._create_function_decorator(prefix, until, addendum=addendum)(
                func
            )

        return experimental_decorator

    def argument(
        self: Self,
        until: str,
        argument: str,
        *,
        addendum: str | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Experimental decorator for keyword arguments."""

        def experimental_decorator(func: Callable[P, T]) -> Callable[P, T]:
            prefix = self._get_argument_prefix(func, argument)
            return self._create_function_decorator(prefix, until, addendum=addendum)(
                func
            )

        return experimental_decorator

    def action(
        self: Self,
        until: str,
        action: ActionType,
        *,
        addendum: str | None = None,
    ) -> ActionType:
        """Mark any argparse.Action as experimental."""
        return self._create_action_mixin(
            action, "ExperimentalMixin", until, addendum=addendum
        )

    def module(
        self: Self,
        until: str,
        *,
        addendum: str | None = None,
    ) -> None:
        """Mark a module as experimental."""
        module_name = self._get_module(0)[1]
        self._handle_validation(module_name, until, addendum=addendum)

    def constant(
        self: Self,
        until: str,
        constant: str,
        value: Any,
        *,
        addendum: str | None = None,
    ) -> None:
        """Mark a module constant/global as experimental."""
        try:
            module, fullname = self._get_caller_module()
        except Exception:
            module, fullname = self._get_module(1)

        prefix = f"{fullname}.{constant}"
        self._handle_validation(prefix, until, addendum=addendum)
        setattr(module, constant, value)

    def topic(
        self: Self,
        until: str,
        *,
        topic: str,
        addendum: str | None = None,
    ) -> None:
        """Mark a topic as experimental."""
        self._handle_validation(topic, until, addendum=addendum)


deprecated = DeprecationHandler(__version__)
experimental = ExperimentHandler(__version__)
