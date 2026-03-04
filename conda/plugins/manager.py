# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This module contains a subclass implementation of pluggy's
`PluginManager <https://pluggy.readthedocs.io/en/stable/api_reference.html#pluggy.PluginManager>`_.

Additionally, it contains a function we use to construct the ``PluginManager`` object and
register all plugins during conda's startup process.
"""

from __future__ import annotations

import fnmatch
import functools
import logging
import os
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from importlib.metadata import distributions
from inspect import getmodule, isclass
from typing import TYPE_CHECKING, overload

import pluggy

from ..auxlib import NULL
from ..base.constants import APP_NAME, DEFAULT_CONSOLE_REPORTER_BACKEND
from ..base.context import context
from ..common.io import dashlist, load_file
from ..common.iterators import groupby_to_dict
from ..exceptions import (
    AmbiguousEnvironmentSpecPlugin,
    CondaValueError,
    EnvironmentExporterNotDetected,
    EnvironmentSpecPluginNotDetected,
    EnvironmentSpecPluginSelectionError,
    PluginError,
)
from . import (
    environment_exporters,
    environment_specifiers,
    package_extractors,
    post_solves,
    prefix_data_loaders,
    reporter_backends,
    solvers,
    subcommands,
    virtual_packages,
)
from .config import PluginConfig
from .hookspec import CondaSpecs
from .subcommands.doctor import health_checks

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any, Literal, cast

    from pluggy import HookImpl
    from requests.auth import AuthBase

    from ..common.path import PathType
    from ..core.path_actions import Action
    from ..core.solve import Solver
    from ..models.environment import Environment
    from ..models.match_spec import MatchSpec
    from ..models.records import PackageRecord
    from .types import (
        CondaAuthHandler,
        CondaEnvironmentExporter,
        CondaEnvironmentSpecifier,
        CondaEnvironmentSpecifier2,
        CondaHealthCheck,
        CondaPackageExtractor,
        CondaPlugin,
        CondaPostCommand,
        CondaPostSolve,
        CondaPostTransactionAction,
        CondaPreCommand,
        CondaPrefixDataLoader,
        CondaPrefixDataLoaderCallable,
        CondaPreSolve,
        CondaPreTransactionAction,
        CondaReporterBackend,
        CondaRequestHeader,
        CondaSetting,
        CondaSolver,
        CondaSubcommand,
        CondaVirtualPackage,
    )

log = logging.getLogger(__name__)


@dataclass
class _HookImplWrapper:
    impl: HookImpl

    def function(self, *args):
        result = self.impl.function(*args)
        if self.impl.hookwrapper or self.impl.wrapper:
            # hookwrappers/wrappers do not return plugins, return as is
            return result
        elif self._isiterable(result):
            # return a generator of the wrapped plugins
            if TYPE_CHECKING:
                result = cast("Iterable[Any]", result)
            return (self._set_impl(item, self.impl) for item in result)
        else:
            # return the wrapped plugin
            return self._set_impl(result, self.impl)

    def __getattr__(self, name):
        # delegate to the wrapped impl
        return getattr(self.impl, name)

    @staticmethod
    def _isiterable(obj):
        # check if the result is iterable and not a string, bytes, bytearray, or mapping
        return isinstance(obj, Iterable) and not isinstance(
            obj, (str, bytes, bytearray, Mapping)
        )

    @staticmethod
    def _set_impl(result, impl):
        with suppress(AttributeError, TypeError):
            setattr(result, "impl", impl)
        return result


class CondaPluginManager(pluggy.PluginManager):
    """
    The conda plugin manager to implement behavior additional to pluggy's default plugin manager.
    """

    get_cached_solver_backend: Callable[[str | None], type[Solver]]
    """Cached version of the :meth:`~conda.plugins.manager.CondaPluginManager.get_solver_backend` method."""

    get_cached_session_headers: Callable[[str], dict[str, str]]
    """Cached version of the :meth:`~conda.plugins.manager.CondaPluginManager.get_session_headers` method."""

    get_cached_request_headers: Callable[[str, str], dict[str, str]]
    """Cached version of the :meth:`~conda.plugins.manager.CondaPluginManager.get_request_headers` method."""

    def __init__(self, *args, **kwargs):
        super().__init__(APP_NAME, *args, **kwargs)
        # Make the cache containers local to the instances so that the
        # reference from cache to the instance gets garbage collected with the instance
        self.get_cached_solver_backend = functools.cache(self.get_solver_backend)
        self.get_cached_session_headers = functools.cache(self.get_session_headers)
        self.get_cached_request_headers = functools.cache(self.get_request_headers)

    def get_canonical_name(self, plugin: object) -> str:
        # detect the fully qualified module name
        prefix = "<unknown_module>"
        if (module := getmodule(plugin)) and module.__spec__:
            prefix = module.__spec__.name

        # return the fully qualified name for modules
        if module is plugin:
            return prefix

        # return the fully qualified name for classes
        elif isclass(plugin):
            return f"{prefix}.{plugin.__qualname__}"

        # return the fully qualified name for instances
        else:
            return f"{prefix}.{plugin.__class__.__qualname__}[{id(plugin)}]"

    def register(self, plugin, name: str | None = None) -> str | None:
        """
        Call :meth:`pluggy.PluginManager.register` and return the result or
        ignore errors raised, except ``ValueError``, which means the plugin
        had already been registered.
        """
        try:
            # register plugin but ignore ValueError since that means
            # the plugin has already been registered
            plugin_name = super().register(plugin, name=name)
            with suppress(AttributeError, TypeError):
                setattr(plugin, "plugin_name", plugin_name)
            return plugin_name
        except ValueError:
            return None
        except Exception as err:
            raise PluginError(
                f"Error while loading conda plugin: "
                f"{name or self.get_canonical_name(plugin)} ({err})"
            ) from err

    def load_plugins(self, *plugins) -> int:
        """
        Load the provided list of plugins and fail gracefully on error.
        The provided list of plugins can either be classes or modules with
        :attr:`~conda.plugins.hookimpl`.
        """
        count = 0
        for plugin in plugins:
            if self.register(plugin):
                count += 1
        return count

    def load_entrypoints(self, group: str, name: str | None = None) -> int:
        """Load modules from querying the specified setuptools ``group``.

        :param str group: Entry point group to load plugins.
        :param str name: If given, loads only plugins with the given ``name``.
        :rtype: int
        :return: The number of plugins loaded by this call.
        """
        count = 0
        for dist in distributions():
            for entry_point in dist.entry_points:
                # skip entry points that don't match the group/name
                if entry_point.group != group or (
                    name is not None and entry_point.name != name
                ):
                    continue

                # attempt to load plugin from entry point
                try:
                    plugin = entry_point.load()
                except Exception as err:
                    # not using exc_info=True here since the CLI loggers are
                    # set up after CLI initialization and argument parsing,
                    # meaning that it comes too late to properly render
                    # a traceback; instead we pass exc_info conditionally on
                    # context.verbosity
                    log.warning(
                        f"Error while loading conda entry point: {entry_point.name} ({err})",
                        exc_info=err if context.info else None,
                    )
                    continue

                if self.register(plugin):
                    count += 1
        return count

    def _hookexec(
        self,
        hook_name: str,
        methods: Sequence[HookImpl],
        kwargs: Mapping[str, object],
        firstresult: bool,
    ) -> object | list[object]:
        wrapped_methods = [_HookImplWrapper(method) for method in methods]
        if TYPE_CHECKING:
            methods = cast("Sequence[HookImpl]", wrapped_methods)
        else:
            methods = wrapped_methods
        return super()._hookexec(hook_name, methods, kwargs, firstresult)

    @overload
    def get_hook_results(
        self, name: Literal["subcommands"]
    ) -> list[CondaSubcommand]: ...

    @overload
    def get_hook_results(
        self, name: Literal["virtual_packages"]
    ) -> list[CondaVirtualPackage]: ...

    @overload
    def get_hook_results(self, name: Literal["solvers"]) -> list[CondaSolver]: ...

    @overload
    def get_hook_results(
        self, name: Literal["pre_commands"]
    ) -> list[CondaPreCommand]: ...

    @overload
    def get_hook_results(
        self, name: Literal["post_commands"]
    ) -> list[CondaPostCommand]: ...

    @overload
    def get_hook_results(
        self, name: Literal["auth_handlers"]
    ) -> list[CondaAuthHandler]: ...

    @overload
    def get_hook_results(
        self, name: Literal["health_checks"]
    ) -> list[CondaHealthCheck]: ...

    @overload
    def get_hook_results(self, name: Literal["pre_solves"]) -> list[CondaPreSolve]: ...

    @overload
    def get_hook_results(
        self, name: Literal["post_solves"]
    ) -> list[CondaPostSolve]: ...

    @overload
    def get_hook_results(
        self, name: Literal["session_headers"], *, host: str
    ) -> list[CondaRequestHeader]: ...

    @overload
    def get_hook_results(
        self, name: Literal["request_headers"], *, host: str, path: str
    ) -> list[CondaRequestHeader]: ...

    @overload
    def get_hook_results(self, name: Literal["settings"]) -> list[CondaSetting]: ...

    @overload
    def get_hook_results(
        self, name: Literal["reporter_backends"]
    ) -> list[CondaReporterBackend]: ...

    @overload
    def get_hook_results(
        self, name: Literal["pre_transaction_actions"]
    ) -> list[CondaPreTransactionAction]: ...

    @overload
    def get_hook_results(
        self, name: Literal["post_transaction_actions"]
    ) -> list[CondaPostTransactionAction]: ...

    @overload
    def get_hook_results(
        self, name: Literal["prefix_data_loaders"]
    ) -> list[CondaPrefixDataLoader]: ...

    @overload
    def get_hook_results(
        self, name: Literal["environment_specifiers"]
    ) -> list[CondaEnvironmentSpecifier]: ...

    @overload
    def get_hook_results(
        self, name: Literal["package_extractors"]
    ) -> list[CondaPackageExtractor]: ...

    @overload
    def get_hook_results(
        self, name: Literal["environment_exporters"]
    ) -> list[CondaEnvironmentExporter]: ...

    def get_hook_results(self, name, **kwargs):
        """
        Return results of the plugin hooks with the given name and
        raise an error if there is a conflict.
        """
        specname = f"{self.project_name}_{name}"  # e.g. conda_solvers
        hook = getattr(self.hook, specname, None)
        if hook is None:
            raise PluginError(f"Could not find requested `{name}` plugins")

        plugins = [plugin for plugins in hook(**kwargs) for plugin in plugins]

        # Validate plugin names since plugins may not properly inherit from CondaPlugin
        invalid = [
            plugin
            for plugin in plugins
            if not hasattr(plugin, "name")
            or not isinstance(plugin.name, str)
            or plugin.name != plugin.name.lower().strip()
        ]
        if invalid:
            plugin_names = (
                f"{repr(plugin)} ({plugin.impl.plugin_name})" for plugin in invalid
            )
            raise PluginError(
                f"Invalid plugin names found for `{name}`:\n"
                f"{dashlist(plugin_names)}\n"
                f"\n"
                f"Please report this issue to the plugin author(s)."
            )

        # Check for conflicts since no two plugins can have the same name
        conflicts = [
            plugin
            for plugins in groupby_to_dict(lambda plugin: plugin.name, plugins).values()
            if len(plugins) > 1
            for plugin in plugins
        ]
        if conflicts:
            plugin_names = (
                f"{plugin.__class__.__name__}(name={plugin.name}) (source: {plugin.impl.plugin_name})"
                for plugin in conflicts
            )
            raise PluginError(
                f"Conflicting plugins found for `{name}`:\n"
                f"{dashlist(plugin_names)}\n"
                f"\n"
                f"Multiple conda plugins are registered via the `{specname}` hook. "
                f"Please make sure that you don't have any incompatible plugins installed."
            )

        return sorted(plugins, key=lambda plugin: plugin.name)

    def get_solvers(self) -> dict[str, CondaSolver]:
        """Return a mapping from solver name to solver class."""
        return {
            solver_plugin.name: solver_plugin
            for solver_plugin in self.get_hook_results("solvers")
        }

    def get_solver_backend(self, name: str | None = None) -> type[Solver]:
        """
        Get the solver backend with the given name (or fall back to the
        name provided in the context).

        See ``context.solver`` for more details.

        Please use the cached version of this method called
        :meth:`get_cached_solver_backend` for high-throughput code paths
        which is set up as a instance-specific LRU cache.
        """
        # Some light data validation in case name isn't given.
        name = (name or context.solver).lower().strip()

        solvers_mapping = self.get_solvers()

        # Look up the solver mapping and fail loudly if it can't
        # find the requested solver.
        solver_plugin = solvers_mapping.get(name, None)
        if solver_plugin is None:
            raise CondaValueError(
                f"You have chosen a non-default solver backend ({name}) "
                f"but it was not recognized. Choose one of: "
                f"{', '.join(solvers_mapping)}"
            )

        return solver_plugin.backend

    def get_auth_handler(self, name: str) -> type[AuthBase] | None:
        """
        Get the auth handler with the given name or None
        """
        name = name.lower().strip()
        auth_handlers = self.get_hook_results("auth_handlers")
        matches = [item for item in auth_handlers if item.name == name]

        if len(matches) > 0:
            return matches[0].handler
        return None

    def get_settings(self) -> dict[str, CondaSetting]:
        """
        Return a mapping of plugin setting name to CondaSetting objects.

        This method intentionally overwrites any duplicates that may be present
        """
        return {
            config_param.name: config_param
            for config_param in self.get_hook_results("settings")
        }

    def invoke_pre_commands(self, command: str) -> None:
        """
        Invokes ``CondaPreCommand.action`` functions registered with ``conda_pre_commands``.

        :param command: name of the command that is currently being invoked
        """
        for hook in self.get_hook_results("pre_commands"):
            if command in hook.run_for:
                hook.action(command)

    def invoke_post_commands(self, command: str) -> None:
        """
        Invokes ``CondaPostCommand.action`` functions registered with ``conda_post_commands``.

        :param command: name of the command that is currently being invoked
        """
        for hook in self.get_hook_results("post_commands"):
            if command in hook.run_for:
                hook.action(command)

    def disable_external_plugins(self) -> None:
        """
        Disables all currently registered plugins except built-in conda plugins
        """
        for name, plugin in self.list_name_plugin():
            if not name.startswith("conda.plugins.") and not self.is_blocked(name):
                self.set_blocked(name)

    def get_subcommands(self) -> dict[str, CondaSubcommand]:
        return {
            subcommand.name: subcommand
            for subcommand in self.get_hook_results("subcommands")
        }

    def get_health_checks(self) -> dict[str, CondaHealthCheck]:
        """Return a mapping of health check name to health check."""
        return {check.name: check for check in self.get_hook_results("health_checks")}

    def get_reporter_backends(self) -> tuple[CondaReporterBackend, ...]:
        return tuple(self.get_hook_results("reporter_backends"))

    def get_reporter_backend(self, name: str) -> CondaReporterBackend:
        """
        Attempts to find a reporter backend while providing a fallback option if it is
        not found.

        This method must return a valid ``CondaReporterBackend`` object or else it will
        raise an exception.
        """
        reporter_backends_map = {
            reporter_backend.name: reporter_backend
            for reporter_backend in self.get_reporter_backends()
        }
        reporter_backend = reporter_backends_map.get(name, None)
        if reporter_backend is None:
            log.warning(
                f'Unable to find reporter backend: "{name}"; '
                f'falling back to using "{DEFAULT_CONSOLE_REPORTER_BACKEND}"'
            )
            return reporter_backends_map.get(DEFAULT_CONSOLE_REPORTER_BACKEND)
        else:
            return reporter_backend

    def get_virtual_package_records(self) -> tuple[PackageRecord, ...]:
        return tuple(
            virtual_package
            for hook in self.get_hook_results("virtual_packages")
            if (virtual_package := hook.to_virtual_package()) is not NULL
        )

    def get_session_headers(self, host: str) -> dict[str, str]:
        return {
            hook.name: hook.value
            for hook in self.get_hook_results("session_headers", host=host)
        }

    def get_request_headers(self, host: str, path: str) -> dict[str, str]:
        return {
            hook.name: hook.value
            for hook in self.get_hook_results("request_headers", host=host, path=path)
        }

    def get_prefix_data_loaders(self) -> Iterable[CondaPrefixDataLoaderCallable]:
        for hook in self.get_hook_results("prefix_data_loaders"):
            yield hook.loader

    def invoke_pre_solves(
        self,
        specs_to_add: frozenset[MatchSpec],
        specs_to_remove: frozenset[MatchSpec],
    ) -> None:
        """
        Invokes ``CondaPreSolve.action`` functions registered with ``conda_pre_solves``.

        :param specs_to_add:
        :param specs_to_remove:
        """
        for hook in self.get_hook_results("pre_solves"):
            hook.action(specs_to_add, specs_to_remove)

    def invoke_post_solves(
        self,
        repodata_fn: str,
        unlink_precs: tuple[PackageRecord, ...],
        link_precs: tuple[PackageRecord, ...],
    ) -> None:
        """
        Invokes ``CondaPostSolve.action`` functions registered with ``conda_post_solves``.

        :param repodata_fn:
        :param unlink_precs:
        :param link_precs:
        """
        for hook in self.get_hook_results("post_solves"):
            hook.action(repodata_fn, unlink_precs, link_precs)

    def load_settings(self) -> None:
        """
        Iterates through all registered settings and adds them to the
        :class:`conda.common.configuration.PluginConfig` class.
        """
        for name, setting in self.get_settings().items():
            PluginConfig.add_plugin_setting(name, setting.parameter, setting.aliases)

    def get_config(self, data) -> PluginConfig:
        """
        Retrieve the configuration for the plugin.
        Returns:
            PluginConfig: The configuration object for the plugin, initialized with raw data from the context.
        """
        return PluginConfig(data)

    def get_environment_specifiers(
        self, *, supports_detection: bool | None = None, with_aliases: bool = True
    ) -> dict[str, CondaEnvironmentSpecifier]:
        """
         Returns a mapping from environment specifier name to environment specifier.

        :param supports_detection: ternary value that returns either everything, only supporting
                                    detection or not supporting detection.
        :param with_aliases: whether to include aliased values of environment specifiers.
        """
        if supports_detection is None:
            env_spec_hooks = [
                h for h in self.get_hook_results("environment_specifiers")
            ]
        else:
            env_spec_hooks = [
                h
                for h in self.get_hook_results("environment_specifiers")
                if h.environment_spec.detection_supported == supports_detection
            ]

        if not with_aliases:
            return {hook.name: hook for hook in env_spec_hooks}

        try:
            return self._get_name_and_alias_mapping(env_spec_hooks)
        except PluginError as err:
            raise PluginError(
                f"Plugin name conflicts detected in environment specifiers.\n{err}"
            )

    def _get_name_and_alias_mapping(
        self, plugins: Iterable[CondaPlugin]
    ) -> dict[str, CondaEnvironmentSpecifier]:
        """
        Get a mapping from plugin names (including aliases) to plugin.

        :param plugins: List of plugins that have a name and aliases attribute.
        :return: Dict mapping format name to CondaEnvironmentExporter
        :raises PluginError: If multiple exporters use the same format name or alias
        """
        mapping = {}
        conflicts = {}  # format_name -> set of plugin names

        for plugin in plugins:
            for format_name in (plugin.name, *plugin.aliases):
                if format_name in mapping:
                    if format_name not in conflicts:
                        conflicts[format_name] = {mapping[format_name].name}
                    conflicts[format_name].add(plugin.name)
                else:
                    mapping[format_name] = plugin

        if conflicts:
            conflict_details = []
            for format_name, plugin_names in sorted(conflicts.items()):
                plugins_str = ", ".join(sorted(plugin_names))
                conflict_details.append(
                    f"'{format_name}' name or alias used by plugins: {plugins_str}"
                )

            raise PluginError(
                f"Multiple plugins cannot use the same name or alias:"
                f"{dashlist(conflict_details)}\n"
            )

        return mapping

    def get_environment_specifier_by_name(
        self,
        source: str,
        name: str,
    ) -> CondaEnvironmentSpecifier:
        """Get an environment specifier plugin by name

        :param source: full path to the environment spec file/source
        :param name: name of the environment plugin to load
        :raises CondaValueError: if the requested plugin is not available.
        :raises PluginError: if the requested plugin is unable to handle the provided file.
        :returns: an environment specifier plugin that matches the provided plugin name, or can handle the provided file
        """
        name = name.lower().strip()
        plugins = self.get_environment_specifiers()

        try:
            plugin = plugins[name]
        except KeyError:
            raise EnvironmentSpecPluginSelectionError(
                msg=(
                    f"You have chosen an unrecognized environment "
                    f"specifier type ({name}). Please choose one "
                    "of the available formats."
                ),
                plugin_specs=self.get_hook_results("environment_specifiers"),
            )
        else:
            # Try to load the plugin and check if it can handle the environment spec
            try:
                if plugin.environment_spec(source).can_handle():
                    return plugin
            except Exception as e:
                raise EnvironmentSpecPluginSelectionError(
                    msg=(
                        f"Could not parse '{source}' as '{name}'. Check "
                        "that the file contents match the expected format. "
                        f"Errors reported from '{name}':\n\n"
                        f"    ->  {type(e).__name__}: {str(e)}\n"
                    ),
                    plugin_specs=self.get_hook_results("environment_specifiers"),
                )
            else:
                # If the plugin was not able to handle the environment spec, raise an error
                raise PluginError(
                    f"Requested plugin '{name}' is unable to handle environment spec '{source}'"
                )

    def _detect_filename_env_spec(
        self,
        source: str,
        basename: str,
        hooks: dict[str, CondaEnvironmentSpecifier],
    ) -> list[CondaEnvironmentSpecifier]:
        """Detect environment specifier by filename pattern matching.

        :param basename: basename of the source file
        :param hooks: mapping of environment specifier plugins
        :returns: list of matching plugins, or None if no filename matches
        """
        found = [
            hook
            for hook_name, hook in hooks.items()
            if hook.default_filenames
            and any(
                fnmatch.fnmatch(basename, pattern) for pattern in hook.default_filenames
            )
        ]

        if len(found) > 1:
            raise AmbiguousEnvironmentSpecPlugin(
                msg=f"File '{source}' matches the default filename pattern for multiple formats.",
                plugins=found,
            )

        if len(found) == 1:
            try:
                if found[0].environment_spec(source).can_handle():
                    return found
            except Exception as e:
                raise PluginError(
                    f"Failed to parse environment specification from file: {e}"
                ) from e

        return found

    @staticmethod
    def _detect_content_env_spec(
        source: str,
        hooks: dict[str, CondaEnvironmentSpecifier],
    ) -> list[CondaEnvironmentSpecifier]:
        """Detect environment specifier by content-based autodetection.

        :param source: full path to the environment spec file or source
        :param hooks: mapping of environment specifier plugins
        :returns: tuple of (found plugins, autodetect disabled plugin names)
        """
        found = []

        for hook_name, hook in hooks.items():
            log.debug("EnvironmentSpec hook: checking %s", hook_name)
            try:
                if hook.environment_spec(source).can_handle():
                    log.debug(
                        "EnvironmentSpec hook: %s can be %s",
                        source,
                        hook_name,
                    )
                    found.append(hook)
            except Exception:
                pass

        return found

    def detect_environment_specifier(self, source: str) -> CondaEnvironmentSpecifier:
        """Detect the environment specifier plugin for a given spec source

        Uses two-phase detection:
        1. Filename-based filtering using fnmatch patterns
        2. Fallback to content-based autodetection (can_handle())

        Raises PluginError if more than one environment_spec plugin is found to be able to handle the file.
        Raises EnvironmentSpecPluginNotDetected if no plugins were found.

        :param source: full path to the environment spec file or source
        :returns: an environment specifier plugin that can handle the provided file
        """
        hooks = self.get_environment_specifiers(
            supports_detection=True, with_aliases=False
        )
        basename = os.path.basename(source)

        # Filename detection
        found = self._detect_filename_env_spec(source, basename, hooks)

        if len(found) == 0:
            # Filename matching didn't find anything; try content based detection
            found = self._detect_content_env_spec(source, hooks)

            if len(found) > 1:
                raise AmbiguousEnvironmentSpecPlugin(
                    msg=f"File '{source}' can be handled by multiple formats.",
                    plugins=found,
                )

        if len(found) == 1:
            return found[0]

        # HACK: if there was no plugin found, try to catch all `environment.yml` plugin
        # FUTURE: Remove this final try at using the environment.yml to read the environment
        # file. This should be removed in "26.9" when the deprecations warning for
        # environment.yml's that are not compliant with cep-0024 are removed.
        try:
            return self.get_environment_specifier_by_name(
                source=source, name="environment.yml"
            )
        except (
            PluginError,
            CondaValueError,
            EnvironmentSpecPluginSelectionError,
        ) as exc:
            # raise error if no plugins found that can read the environment file
            raise EnvironmentSpecPluginNotDetected(
                plugin_specs=self.get_hook_results("environment_specifiers")
            ) from exc

    def get_environment_specifier(
        self,
        source: str,
        name: str | None = None,
    ) -> CondaEnvironmentSpecifier:
        """Get the environment specifier plugin for a given spec source, or given a plugin name
        Raises PluginError if more than one environment_spec plugin is found to be able to handle the file.
        Raises EnvironmentSpecPluginNotDetected if no plugins were found.
        Raises CondaValueError if the requested plugin is not available.

        :param filename: full path to the environment spec file/source
        :param name: name of the environment plugin to load
        :returns: an environment specifier plugin that matches the provided plugin name, or can handle the provided file
        """
        if not name:
            return self.detect_environment_specifier(source)
        else:
            return self.get_environment_specifier_by_name(source=source, name=name)

    def get_environment_specifiers2(
        self, *, supports_detection: bool | None = None, with_aliases: bool = True
    ) -> dict[str, CondaEnvironmentSpecifier2]:
        """
         Returns a mapping from environment specifier v2 name to environment specifier v2.

         :param supports_detection: ternary value that returns either everything, only supporting
                                    detection or not supporting detection.
        :param with_aliases: whether to include aliased values of environment specifiers.
        """
        if supports_detection is None:
            env_spec_hooks = [
                h for h in self.get_hook_results("environment_specifiers2")
            ]
        else:
            env_spec_hooks = [
                h
                for h in self.get_hook_results("environment_specifiers2")
                if h.detection_supported == supports_detection
            ]

        if not with_aliases:
            return {hook.name: hook for hook in env_spec_hooks}

        try:
            return self._get_name_and_alias_mapping(env_spec_hooks)
        except PluginError as err:
            raise PluginError(
                f"Plugin name conflicts detected in environment specifiers.\n{err}"
            )

    def get_environment_specifier2_by_name(
        self,
        source: str,
        name: str,
    ) -> CondaEnvironmentSpecifier2:
        """Get an environment specifier v2 plugin by name

        :param source: full path to the environment spec file/source
        :param name: name of the environment plugin to load
        :raises CondaValueError: if the requested plugin is not available.
        :raises PluginError: if the requested plugin is unable to handle the provided file.
        :returns: an environment specifier plugin that matches the provided plugin name, or can handle the provided file
        """
        name = name.lower().strip()
        plugins = self.get_environment_specifiers2()

        try:
            plugin = plugins[name]
        except KeyError:
            raise CondaValueError(
                f"You have chosen an unrecognized environment"
                f" specifier type ({name}). Choose one of: "
                f"{dashlist(plugins)}"
            )
        else:
            data = load_file(source)
            # Try to load the plugin and check if it can handle the environment spec
            try:
                if plugin.validate(data):
                    return plugin
            except Exception as e:
                raise PluginError(
                    dals(
                        f"""
                        An error occurred when handling '{source}' with plugin '{name}'.

                        {type(e).__name__}: {e}
                        """
                    )
                )
            else:
                # If the plugin was not able to handle the environment spec, raise an error
                raise PluginError(
                    f"Requested plugin '{name}' is unable to handle environment spec '{source}'"
                )

    def _detect_filename_env_spec2(
        self,
        source: str,
        basename: str,
        hooks: dict[str, CondaEnvironmentSpecifier2],
    ) -> list[CondaEnvironmentSpecifier2]:
        """Detect environment specifier v2 by filename pattern matching.

        :param basename: basename of the source file
        :param hooks: mapping of environment specifier plugins
        :returns: list of matching plugins, or None if no filename matches
        """
        found = [
            hook
            for hook_name, hook in hooks.items()
            if hook.default_filenames
            and any(
                fnmatch.fnmatch(basename, pattern) for pattern in hook.default_filenames
            )
        ]

        if len(found) > 1:
            raise PluginError(
                f"Too many plugins found that can handle the environment file '{source}'.\n\n"
                "Try using --env-spec=<spec-name> to more exactly specify the environment spec\n"
                "parser you want to use.\n\n"
                "Available env specs:\n"
                f"{dashlist(self.get_environment_specifiers2())}"
            )

        if len(found) == 1:
            data = load_file(source)
            try:
                if found[0].validate(data):
                    return found
            except Exception as e:
                raise PluginError(
                    f"Failed to parse environment specification from file: {e}"
                ) from e

        return found

    @staticmethod
    def _detect_content_env_spec2(
        source: str,
        hooks: dict[str, CondaEnvironmentSpecifier2],
    ) -> list[CondaEnvironmentSpecifier2]:
        """Detect environment specifier v2 by content-based autodetection.

        :param source: full path to the environment spec file or source
        :param hooks: mapping of environment specifier plugins
        :returns: tuple of (found plugins, autodetect disabled plugin names)
        """
        found = []
        data = load_file(source)
        for hook_name, hook in hooks.items():
            log.debug("EnvironmentSpec hook: checking %s", hook_name)
            try:
                if hook.validate(data):
                    log.debug(
                        "EnvironmentSpec hook: %s can be %s",
                        source,
                        hook_name,
                    )
                    found.append(hook)
            except Exception:
                pass

        return found

    def detect_environment_specifier2(self, source: str) -> CondaEnvironmentSpecifier2:
        """Detect the environment specifier v2 plugin for a given spec source

        Uses two-phase detection:
        1. Filename-based filtering using fnmatch patterns
        2. Fallback to content-based autodetection (can_handle())

        Raises PluginError if more than one environment_spec plugin is found to be able to handle the file.
        Raises EnvironmentSpecPluginNotDetected if no plugins were found.

        :param source: full path to the environment spec file or source
        :returns: an environment specifier plugin that can handle the provided file
        """
        hooks = self.get_environment_specifiers2(
            supports_detection=True, with_aliases=False
        )
        basename = os.path.basename(source)

        # Filename detection
        found = self._detect_filename_env_spec2(source, basename, hooks)

        if len(found) == 0:
            # Filename matching didn't find anything; try content based detection
            found = self._detect_content_env_spec2(source, hooks)

            if len(found) > 1:
                raise PluginError(
                    f"Too many plugins found that can handle the environment file '{source}'.\n\n"
                    "Try using --env-spec=<spec-name> to more exactly specify the environment spec\n"
                    "parser you want to use.\n\n"
                    "Available env specs:\n"
                    f"{dashlist(self.get_environment_specifiers2())}"
                )

        if len(found) == 1:
            return found[0]

        # HACK: if there was no plugin found, try to catch all `environment.yml` plugin
        # FUTURE: Remove this final try at using the environment.yml to read the environment
        # file. This should be removed in "26.9" when the deprecations warning for
        # environment.yml's that are not compliant with cep-0024 are removed.
        try:
            return self.get_environment_specifier2_by_name(
                source=source, name="environment.yml"
            )
        except (PluginError, CondaValueError) as exc:
            # raise error if no plugins found that can read the environment file
            raise EnvironmentSpecPluginNotDetected(
                name=source,
                plugin_names=hooks,
                autodetect_disabled_plugins=self.get_environment_specifiers2(
                    supports_detection=False
                ),
            ) from exc

    def get_environment_specifier2(
        self,
        source: str,
        name: str | None = None,
    ) -> CondaEnvironmentSpecifier2:
        """Get the environment specifier v2 plugin for a given spec source, or given a plugin name
        Raises PluginError if more than one environment_spec plugin is found to be able to handle the file.
        Raises EnvironmentSpecPluginNotDetected if no plugins were found.
        Raises CondaValueError if the requested plugin is not available.

        :param filename: full path to the environment spec file/source
        :param name: name of the environment plugin to load
        :returns: an environment specifier plugin that matches the provided plugin name, or can handle the provided file
        """
        if not name:
            return self.detect_environment_specifier2(source)
        else:
            return self.get_environment_specifier2_by_name(source=source, name=name)

    def get_environment(
        self,
        source: str,
        name: str | None = None,
    ) -> Environment:
        plugin = self.get_environment_specifier2(source, name)
        data = load_file(source)
        return plugin.env(data)

    def get_environment_exporters(self) -> Iterable[CondaEnvironmentExporter]:
        """
        Yields all detected environment exporters.
        """
        yield from self.get_hook_results("environment_exporters")

    def get_exporter_format_mapping(self) -> dict[str, CondaEnvironmentExporter]:
        """
        Get a mapping from format names (including aliases) to environment exporters.

        :return: Dict mapping format name to CondaEnvironmentExporter
        :raises PluginError: If multiple exporters use the same format name or alias
        """
        try:
            return self._get_name_and_alias_mapping(self.get_environment_exporters())
        except PluginError as err:
            raise PluginError(
                f"Format name conflicts detected in environment exporters.\n{err}"
            )

    def detect_environment_exporter(self, filename: str) -> CondaEnvironmentExporter:
        """
        Detect an environment exporter based on filename matching against default_filenames.

        Uses fnmatch pattern matching for flexible filename patterns (e.g., *.conda-lock.yml).

        :param filename: Filename to find an exporter for (basename is used for detection)
        :return: CondaEnvironmentExporter that supports the filename
        :raises EnvironmentExporterNotDetected: If no exporter supports the filename
        :raises PluginError: If multiple exporters claim to support the same filename
        """
        # Extract just the basename for matching
        basename = os.path.basename(filename)

        matches = []
        for exporter_config in self.get_environment_exporters():
            # Check if basename matches any of the default filename patterns
            if any(
                fnmatch.fnmatch(basename, pattern)
                for pattern in exporter_config.default_filenames
            ):
                matches.append(exporter_config)

        if not matches:
            raise EnvironmentExporterNotDetected(
                filename=basename,
                exporters=self.get_environment_exporters(),
            )
        elif len(matches) > 1:
            raise PluginError(
                f"Multiple environment exporters found that can handle filename '{basename}':"
                f"{dashlist([match.name for match in matches])}\n"
                f"\n"
                f"Please make sure that you don't have any conflicting exporter plugins installed."
            )
        return matches[0]

    def get_environment_exporter_by_format(
        self, format_name: str
    ) -> CondaEnvironmentExporter:
        """
        Get an environment exporter based on the format name.

        :param format_name: Format name to find an exporter for (e.g., 'yaml', 'json', 'environment-yaml')
        :return: CondaEnvironmentExporter that supports the format
        :raises CondaValueError: If no exporter is found for the given format
        """
        format_mapping = self.get_exporter_format_mapping()
        exporter = format_mapping.get(format_name)

        if exporter is None:
            raise CondaValueError(
                f"Unknown export format '{format_name}'. "
                f"Available formats:{dashlist(sorted(format_mapping.keys()))}"
            )

        return exporter

    def get_pre_transaction_actions(
        self,
        transaction_context: dict[str, str] | None = None,
        target_prefix: str | None = None,
        unlink_precs: Iterable[PackageRecord] | None = None,
        link_precs: Iterable[PackageRecord] | None = None,
        remove_specs: Iterable[MatchSpec] | None = None,
        update_specs: Iterable[MatchSpec] | None = None,
        neutered_specs: Iterable[MatchSpec] | None = None,
    ) -> list[Action]:
        """Get the plugin-defined pre-transaction actions.

        :param transaction_context: Mapping between target prefixes and PrefixActionGroup
            instances
        :param target_prefix: Target prefix for the action
        :param unlink_precs: Package records to be unlinked
        :param link_precs: Package records to link
        :param remove_specs: Specs to be removed
        :param update_specs: Specs to be updated
        :param neutered_specs: Specs to be neutered
        :return: The plugin-defined pre-transaction actions
        """
        return [
            hook.action(
                transaction_context,
                target_prefix,
                unlink_precs,
                link_precs,
                remove_specs,
                update_specs,
                neutered_specs,
            )
            for hook in self.get_hook_results("pre_transaction_actions")
        ]

    def get_post_transaction_actions(
        self,
        transaction_context: dict[str, str] | None = None,
        target_prefix: str | None = None,
        unlink_precs: Iterable[PackageRecord] | None = None,
        link_precs: Iterable[PackageRecord] | None = None,
        remove_specs: Iterable[MatchSpec] | None = None,
        update_specs: Iterable[MatchSpec] | None = None,
        neutered_specs: Iterable[MatchSpec] | None = None,
    ) -> list[Action]:
        """Get the plugin-defined post-transaction actions.

        :param transaction_context: Mapping between target prefixes and PrefixActionGroup
            instances
        :param target_prefix: Target prefix for the action
        :param unlink_precs: Package records to be unlinked
        :param link_precs: Package records to link
        :param remove_specs: Specs to be removed
        :param update_specs: Specs to be updated
        :param neutered_specs: Specs to be neutered
        :return: The plugin-defined post-transaction actions
        """
        return [
            hook.action(
                transaction_context,
                target_prefix,
                unlink_precs,
                link_precs,
                remove_specs,
                update_specs,
                neutered_specs,
            )
            for hook in self.get_hook_results("post_transaction_actions")
        ]

    def get_package_extractors(self) -> dict[str, CondaPackageExtractor]:
        """
        Return a mapping from file extension to package extractor plugin.

        Extensions are lowercased for case-insensitive matching.

        :return: Dictionary mapping lowercased extensions (e.g., ``".conda"``) to their
            :class:`~conda.plugins.types.CondaPackageExtractor` plugins.
        """
        return {
            extension.lower(): hook
            for hook in self.get_hook_results("package_extractors")
            for extension in hook.extensions
        }

    def get_package_extractor(
        self,
        source_full_path: PathType,
    ) -> CondaPackageExtractor:
        """
        Get the package extractor plugin for a given package path.

        Searches through registered package extractor plugins to find one that
        handles the file extension of the provided package path.

        :param source_full_path: Full path to the package archive file.
        :return: The matching :class:`~conda.plugins.types.CondaPackageExtractor` plugin.
        :raises PluginError: If no registered extractor handles the file extension.
        """
        source_str = os.fspath(source_full_path).lower()
        for extension, extractor in self.get_package_extractors().items():
            if source_str.endswith(extension):
                return extractor

        raise PluginError(
            f"No registered 'package_extractors' plugin found for package: {source_full_path}"
        )

    def extract_package(
        self,
        source_full_path: PathType,
        destination_directory: PathType,
    ) -> None:
        """
        Extract a package archive to a destination directory.

        Finds the appropriate extractor plugin based on the file extension
        and extracts the package.

        :param source_full_path: Full path to the package archive file.
        :param destination_directory: Directory to extract the package contents to.
        :raises PluginError: If no registered extractor handles the file extension.
        """
        extractor = self.get_package_extractor(source_full_path)
        extractor.extract(source_full_path, destination_directory)

    def has_package_extension(self, path: PathType) -> str | None:
        """
        Check if a path has a supported package file extension.

        :param path: Path to check.
        :return: The matched extension (lowercased) if found, None otherwise.
        """
        path_str = os.fspath(path).lower()
        for ext in self.get_package_extractors():
            if path_str.endswith(ext):
                return ext
        return None


@functools.cache
def get_plugin_manager() -> CondaPluginManager:
    """
    Get a cached version of the :class:`~conda.plugins.manager.CondaPluginManager` instance,
    with the built-in and entrypoints provided by the plugins loaded.
    """
    plugin_manager = CondaPluginManager()
    plugin_manager.add_hookspecs(CondaSpecs)
    plugin_manager.load_plugins(
        solvers,
        *virtual_packages.plugins,
        *subcommands.plugins,
        *health_checks.plugins,
        *post_solves.plugins,
        *reporter_backends.plugins,
        *package_extractors.plugins,
        *prefix_data_loaders.plugins,
        *environment_specifiers.plugins,
        *environment_exporters.plugins,
    )
    plugin_manager.load_entrypoints(APP_NAME)
    return plugin_manager
