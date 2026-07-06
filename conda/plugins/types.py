# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Definition of specific return types for use when defining a conda plugin hook.

Each type corresponds to the plugin hook for which it is used.

"""

from __future__ import annotations

import enum
import os
from abc import ABC, abstractmethod
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, overload

from requests.auth import AuthBase  # noqa: TID253

from ..auxlib import NULL
from ..auxlib.type_coercion import maybecall
from ..base.constants import APP_NAME
from ..exceptions import PluginError
from ..models.records import PackageRecord

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Callable, Iterable
    from contextlib import AbstractContextManager
    from types import TracebackType
    from typing import Any, ClassVar, Literal, Protocol, TypeAlias

    from ..auxlib import _Null
    from ..common.configuration import Parameter
    from ..common.path import PathType
    from ..core.path_actions import Action
    from ..core.solve import Solver
    from ..models.environment import Environment
    from ..models.match_spec import MatchSpec
    from ..models.records import PrefixRecord

    CondaPrefixDataLoaderCallable: TypeAlias = Callable[
        [PathType, dict[str, PrefixRecord]],
        dict[str, PrefixRecord],
    ]

    PackageExtract: TypeAlias = Callable[
        [PathType, PathType],  # (source_path, destination_directory)
        None,
    ]

    SinglePlatformEnvironmentExport = Callable[[Environment], str]
    MultiPlatformEnvironmentExport = Callable[[Iterable[Environment]], str]

    # Callback type for health check fixer confirmation prompts.
    # Raises CondaSystemExit if user declines, or DryRunExit in dry-run mode.
    ConfirmCallback: TypeAlias = Callable[[str], None]

    class CondaPluginWithAliases(Protocol):
        """
        Structural type for plugins that expose a canonical :attr:`~CondaPlugin.name`
        and :attr:`aliases`.

        Used when building lookup mappings that include alternate names (for example
        environment specifiers, exporters, and settings). Concrete types such as
        :class:`CondaSetting`, :class:`CondaEnvironmentSpecifier`, and
        :class:`CondaEnvironmentExporter` satisfy this protocol.
        """

        name: str
        aliases: tuple[str, ...]

    class CondaPluginWithEnvironmentFormat(CondaPluginWithAliases):
        """
        Structural type for plugins that expose a environment format.
        """

        environment_format: EnvironmentFormat
        default_filenames: tuple[str, ...]


@dataclass
class CondaPlugin:
    """
    Base class for all conda plugins.
    """

    name: str
    """User-facing name of the plugin used for selecting & filtering plugins and error messages."""

    def __post_init__(self):
        try:
            self.name = self.name.lower().strip()
        except AttributeError:
            # AttributeError: name is not a string
            raise PluginError(f"Invalid plugin name for {self!r}")


@dataclass(init=False)
class CondaSubcommand(CondaPlugin):
    """
    Return type to use when defining a conda subcommand plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_subcommands`.

    Subcommands support two shapes, distinguished by ``configure_parser``:

    * If ``configure_parser`` is set, ``action`` receives the parsed
      :class:`argparse.Namespace`.
    * If ``configure_parser`` is omitted, ``action`` receives the remaining
      argv as :class:`tuple[str, ...]`.

    Args:
        name: Subcommand name (e.g., ``conda my-subcommand-name``).
        summary: Subcommand summary, will be shown in ``conda --help``.
        action: Callable that will be run when the subcommand is invoked.
        aliases: Alternative name or names for the subcommand.
        configure_parser: Callable that will be run when the subcommand parser is initialized.
    """

    summary: str
    action: Callable[[Namespace], int | None] | Callable[[tuple[str, ...]], int | None]
    aliases: tuple[str, ...] = field(default_factory=tuple)
    configure_parser: Callable[[ArgumentParser], None] | None = field(default=None)

    @overload
    def __init__(
        self,
        *,
        name: str,
        summary: str,
        action: Callable[[Namespace], int | None],
        configure_parser: Callable[[ArgumentParser], None],
        aliases: str | Iterable[str] = (),
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        summary: str,
        action: Callable[[tuple[str, ...]], int | None],
        configure_parser: None = None,
        aliases: str | Iterable[str] = (),
    ) -> None: ...

    def __init__(
        self,
        *,
        name: str,
        summary: str,
        action: Callable[[Namespace], int | None]
        | Callable[[tuple[str, ...]], int | None],
        configure_parser: Callable[[ArgumentParser], None] | None = None,
        aliases: str | Iterable[str] = (),
    ) -> None:
        super().__init__(name=name)
        self.summary = summary
        self.action = action
        self.configure_parser = configure_parser
        self.aliases = ()
        if isinstance(aliases, str):
            aliases = (aliases,)
        try:
            self.aliases = tuple(
                dict.fromkeys(alias.lower().strip() for alias in aliases)
            )
        except (AttributeError, TypeError):
            raise PluginError(f"Invalid plugin aliases for {self!r}")
        if any(not alias for alias in self.aliases):
            raise PluginError(
                f"Invalid plugin aliases for {self!r}. "
                "Aliases must not be empty strings."
            )
        if self.name in self.aliases:
            raise PluginError(
                f"Invalid plugin aliases for {self!r}. "
                "Aliases must not match the plugin name."
            )


@dataclass
class CondaVirtualPackage(CondaPlugin):
    """
    Return type to use when defining a conda virtual package plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_virtual_packages`.

    .. note::
       The ``version`` and ``build`` parameters can be provided in two ways:

       1. Direct values: a string or ``None`` (where ``None`` translates to ``0``)
       2. Deferred callables: functions that return either a string, ``None`` (translates to ``0``),
          or ``NULL`` (indicates the virtual package should not be exported)

    Args:
        name: Virtual package name (e.g., ``my_custom_os``).
        version: Virtual package version (e.g., ``1.2.3``).
        build: Virtual package build string (e.g., ``x86_64``).
        override_entity: Can be set to either to "version" or "build", the corresponding
            value will be overridden if the environment variable
            ``CONDA_OVERRIDE_<name>`` is set.
        empty_override: Value to use for version or build if the override
            environment variable is set to an empty string. By default,
            this is ``NULL``.
        version_validation: Optional version validation function to ensure that the override version follows a certain pattern.
    """

    name: str
    version: str | None | Callable[[], str | None | _Null]
    build: str | None | Callable[[], str | None | _Null]
    override_entity: Literal["version", "build"] | None = None
    empty_override: None | _Null = NULL
    version_validation: Callable[[str], str | None] | None = None

    def to_virtual_package(self) -> PackageRecord | _Null:
        # Take the raw version and build as they are.
        # At this point, they may be callables (evaluated later) or direct values.
        from conda.base.context import context

        version = self.version
        build = self.build

        # Check for environment overrides.
        # Overrides always yield a concrete value (string, NULL, or None),
        # so after this step, version/build will no longer be callables if they were overridden.
        if self.override_entity:
            # environment variable has highest precedence
            override_value = os.getenv(f"{APP_NAME}_OVERRIDE_{self.name}".upper())
            # fallback to context
            if override_value is None and context.override_virtual_packages:
                override_value = context.override_virtual_packages.get(f"{self.name}")
            if override_value is not None:
                override_value = override_value.strip() or self.empty_override
                if self.override_entity == "version":
                    version = override_value
                elif self.override_entity == "build":
                    build = override_value

        # If version/build were not overridden and are callables, evaluate them now.
        version = maybecall(version)
        build = maybecall(build)

        if version is NULL or build is NULL:
            return NULL

        if self.version_validation and version is not None:
            version = self.version_validation(version)

        return PackageRecord.virtual_package(f"__{self.name}", version, build)


@dataclass
class CondaSolver(CondaPlugin):
    """
    Return type to use when defining a conda solver plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_solvers`.

    Args:
        name: Solver name (e.g., ``custom-solver``).
        backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


@dataclass
class CondaPreCommand(CondaPlugin):
    """
    Return type to use when defining a conda pre-command plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_commands`.

    Args:
        name: Pre-command name (e.g., ``custom_plugin_pre_commands``).
        action: Callable which contains the code to be run.
        run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
    """

    name: str
    action: Callable[[str], None]
    run_for: set[str]


@dataclass
class CondaPostCommand(CondaPlugin):
    """
    Return type to use when defining a conda post-command plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_post_commands`.

    Args:
        name: Post-command name (e.g., ``custom_plugin_post_commands``).
        action: Callable which contains the code to be run.
        run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
    """

    name: str
    action: Callable[[str], None]
    run_for: set[str]


class ChannelNameMixin:
    """
    Class mixin to make all plugin implementations compatible, e.g. when they
    use an existing (e.g. 3rd party) requests authentication handler.

    Please use the concrete :class:`~conda.plugins.types.ChannelAuthBase`
    in case you're creating an own implementation.
    """

    def __init__(self, channel_name: str, *args, **kwargs):
        self.channel_name = channel_name
        super().__init__(*args, **kwargs)


class ChannelAuthBase(ChannelNameMixin, AuthBase):
    """
    Base class that we require all plugin implementations to use to be compatible.

    Authentication is tightly coupled with individual channels. Therefore, an additional
    ``channel_name`` property must be set on the ``requests.auth.AuthBase`` based class.
    """


@dataclass
class CondaAuthHandler(CondaPlugin):
    """
    Return type to use when the defining the conda auth handlers hook.

    Args:
        name: Name (e.g., ``basic-auth``). This name should be unique
            and only one may be registered at a time.
        handler: Type that will be used as the authentication handler
            during network requests.
    """

    name: str
    handler: type[ChannelAuthBase]


@dataclass
class CondaHealthCheck(CondaPlugin):
    """
    Return type to use when defining conda health checks plugin hook.

    Health checks are diagnostic actions that report on the state of a conda
    environment. They are invoked via ``conda doctor``.

    Health checks can optionally provide a fix capability, which is invoked
    via ``conda doctor --fix`` or ``conda doctor --fix <name>``.

    **Fixer guidelines:**

    Fixers receive a ``confirm`` function that handles user confirmation and
    dry-run mode automatically. Simply call it with your message:

    - In normal mode: Prompts the user for confirmation (default: no).
    - In dry-run mode: Raises ``DryRunExit`` (handled by the framework).
    - If user declines: Raises ``CondaSystemExit`` (handled by the framework).

    Example::

        from conda.plugins.types import ConfirmCallback

        def my_fixer(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
            issues = find_issues(prefix)
            if not issues:
                print("No issues found.")
                return 0

            print(f"Found {len(issues)} issues")
            confirm("Fix these issues?")
            # ... perform fix ...
            return 0

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_health_checks`.

    Args:
        name: Health check identifier (e.g., ``missing-files``).
        action: Callable that performs the check: ``action(prefix, verbose) -> None``.
        fixer: Optional callable that fixes issues:
            ``fixer(prefix, args, confirm) -> int``.
            The ``confirm`` parameter is a function to call for user confirmation.
            It raises an exception if the user declines or in dry-run mode.
        summary: Short description of what the check detects (shown in ``--list``).
        fix: Short description of what the fix does (shown in ``--list``).
    """

    name: str
    action: Callable[[str, bool], None]
    fixer: Callable[[str, Namespace, ConfirmCallback], int] | None = None
    summary: str | None = None
    fix: str | None = None


@dataclass
class CondaPreSolve(CondaPlugin):
    """
    Return type to use when defining a conda pre-solve plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_solves`.

    Args:
        name: Pre-solve name (e.g., ``custom_plugin_pre_solve``).
        action: Callable which contains the code to be run.
    """

    name: str
    action: Callable[[frozenset[MatchSpec], frozenset[MatchSpec]], None]


@dataclass
class CondaPostSolve(CondaPlugin):
    """
    Return type to use when defining a conda post-solve plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_post_solves`.

    Args:
        name: Post-solve name (e.g., ``custom_plugin_post_solve``).
        action: Callable which contains the code to be run.
    """

    name: str
    action: Callable[[str, tuple[PackageRecord, ...], tuple[PackageRecord, ...]], None]


@dataclass
class CondaSetting(CondaPlugin):
    """
    Return type to use when defining a conda setting plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_settings`.

    Args:
        name: name of the setting (e.g., ``config_param``)
        description: description of the setting that should be targeted
            towards users of the plugin
        parameter: Parameter instance containing the setting definition
        aliases: alternative names of the setting
    """

    name: str
    description: str
    parameter: Parameter
    aliases: tuple[str, ...] = tuple()


class ProgressBarBase(ABC):
    def __init__(
        self,
        description: str,
        **kwargs,
    ):
        self.description = description

    @abstractmethod
    def update_to(self, fraction) -> None: ...

    @abstractmethod
    def refresh(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    def finish(self):
        self.update_to(1)

    @classmethod
    def get_lock(cls):
        pass


class SpinnerBase(ABC):
    def __init__(self, message: str, fail_message: str = "failed\n"):
        self.message = message
        self.fail_message = fail_message

    @abstractmethod
    def __enter__(self): ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb): ...


class ReporterRendererBase(ABC):
    """
    Base class for all reporter renderers.
    """

    def render(self, data: Any, **kwargs) -> str:
        return str(data)

    @abstractmethod
    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        """
        Render the output in a "tabular" format.
        """

    @abstractmethod
    def envs_list(
        self, data: Iterable[str] | dict[str, dict[str, str | bool | None]], **kwargs
    ) -> str:
        """
        Render a list of environments
        """

    @abstractmethod
    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        """
        Return a :class:`~conda.plugins.types.ProgressBarBase~` object to use as a progress bar
        """

    @classmethod
    def progress_bar_context_manager(cls) -> AbstractContextManager:
        """
        Returns a null context by default but allows plugins to define their own if necessary
        """
        return nullcontext()

    @abstractmethod
    def spinner(self, message, failed_message) -> SpinnerBase:
        """
        Return a :class:`~conda.plugins.types.SpinnerBase~` object to use as a spinner (i.e.
        loading dialog)
        """

    @abstractmethod
    def prompt(
        self,
        message: str = "Proceed",
        choices=("yes", "no"),
        default: str = "yes",
    ) -> str:
        """
        Allows for defining an implementation of a "yes/no" confirmation function
        """


@dataclass
class CondaReporterBackend(CondaPlugin):
    """
    Return type to use when defining a conda reporter backend plugin hook.

    For details on how this is used, see:
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_reporter_backends`.

    Args:
        name: name of the reporter backend (e.g., ``email_reporter``)
            This is how the reporter backend will be referenced in configuration files.
        description: short description of what the reporter handler does
        renderer: implementation of ``ReporterRendererBase`` that will be used as the
            reporter renderer
    """

    name: str
    description: str
    renderer: type[ReporterRendererBase]


@dataclass
class CondaRequestHeader(CondaPlugin):
    """
    Define vendor specific headers to include HTTP requests

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_request_headers` and
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_session_headers`.

    Args:
        name: name of the header used in the HTTP request
        value: value of the header used in the HTTP request
    """

    name: str
    value: str


@dataclass
class CondaPreTransactionAction(CondaPlugin):
    """
    Return type to use when defining a pre-transaction action hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_transaction_actions`.

    Args:
        name: Pre transaction name (this is just a label)
        action: Action class which implements
            plugin behavior. See
            :class:`~conda.core.path_actions.Action` for
            implementation details
    """

    name: str
    action: type[Action]


@dataclass
class CondaPostTransactionAction(CondaPlugin):
    """
    Return type to use when defining a post-transaction action hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_post_transaction_actions`.

    Args:
        name: Post transaction name (this is just a label)
        action: Action class which implements
            plugin behavior. See
            :class:`~conda.core.path_actions.Action` for
            implementation details
    """

    name: str
    action: type[Action]


@dataclass
class CondaPrefixDataLoader(CondaPlugin):
    """
    Define new loaders to expose non-conda packages in a given prefix
    as ``PrefixRecord`` objects.

    Args:
        name: name of the loader
        loader: a function that takes a prefix and a dictionary that maps
            package names to ``PrefixRecord`` objects. The newly loaded packages
            must be inserted in the passed dictionary accordingly, and also
            returned as a separate dictionary.
    """

    name: str
    loader: CondaPrefixDataLoaderCallable


class EnvironmentSpecBase(ABC):
    """
    **EXPERIMENTAL**

    Base class for all environment specifications.

    Environment specs parse different types of environment definition files
    (environment.yml, requirements.txt, pyproject.toml, etc.) into a common
    Environment object model.
    """

    # Determines if the EnvSpec plugin should be included in the set
    # of available plugins checked during environment_spec plugin detection.
    # If set to False, the only way to use the plugin will be through explicitly
    # requesting it as a cli argument or setting in .condarc. By default,
    # autodetection is enabled.
    detection_supported: ClassVar[bool] = True

    @abstractmethod
    def can_handle(self) -> bool:
        """
        Determines if the EnvSpec plugin can read and operate on the
        environment described by the `filename`.

        Returns:
            True, if the plugin can interpret the file.

        Raises:
            Exception: raises an exception if it can not handle the file. The exception should
                describe why the file can not be handled.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def env(self) -> Environment:
        """
        Express the provided environment file as a conda environment object.

        Returns:
            the conda environment represented by the file.
        """
        raise NotImplementedError()

    @property
    def available_platforms(self) -> tuple[str, ...]:
        """
        Platforms this spec can produce an ``Environment`` for.

        Defaults to ``(context.subdir,)``. Multi-platform specs
        (``conda-lock.yml``, ``pixi.lock``) override to return every
        platform declared in the input file.
        """
        from ..base.context import context

        return (context.subdir,)

    def env_for(self, platform: str) -> Environment:
        """
        Return the ``Environment`` for a specific platform.

        Defaults to returning :attr:`env` when ``platform`` matches
        ``context.subdir``, and raising :class:`ValueError` otherwise.
        Multi-platform specs override this method to build the
        ``Environment`` directly from the parsed input file without
        constructing one per platform.

        To iterate every platform a spec covers::

            envs = (spec.env_for(p) for p in spec.available_platforms)
        """
        if platform not in self.available_platforms:
            raise ValueError(
                f"Platform {platform!r} not available in this spec. "
                f"Available platforms: {', '.join(self.available_platforms)}"
            )
        return self.env


class EnvironmentFormat(enum.Enum):
    """
    Represents supported environment formats.

    FUTURE: Python 3.11+, use enum.StrEnum
    """

    lockfile = "lockfile"
    environment = "environment"

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return {
            EnvironmentFormat.lockfile: "Lockfiles",
            EnvironmentFormat.environment: "Environment specs",
        }[self]


@dataclass
class CondaEnvironmentSpecifier(CondaPlugin):
    """
    **EXPERIMENTAL**

    Return type to use when defining a conda env spec plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_environment_specifiers`.

    Args:
        name: name of the spec (e.g., ``environment_yaml``)
        aliases: user-friendly format aliases (e.g., ("yaml",)). Defaults to an empty list.
        environment_spec: EnvironmentSpecBase subclass handler
        default_filenames: default filename patterns this specifier handles (e.g., ("environment.yml", "*.conda-lock.yml"))
        description: user-friendly description of what the format does. Defaults to the name if not provided.
        environment_format: EnvironmentFormat category. Defaults to EnvironmentFormat.environment.
    """

    name: str
    environment_spec: type[EnvironmentSpecBase]
    default_filenames: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    description: str | None = field(default=None)
    environment_format: EnvironmentFormat = field(default=EnvironmentFormat.environment)

    def __post_init__(self):
        super().__post_init__()  # Handle name normalization
        # Normalize aliases using same pattern as name normalization
        try:
            self.aliases = tuple(
                dict.fromkeys(alias.lower().strip() for alias in self.aliases)
            )
        except AttributeError:
            # AttributeError: alias is not a string
            raise PluginError(f"Invalid plugin aliases for {self!r}")

        # Set default description to name if not provided
        if self.description is None:
            self.description = self.name


@dataclass
class CondaEnvironmentExporter(CondaPlugin):
    """
    **EXPERIMENTAL**

    Return type to use when defining a conda environment exporter plugin hook supporting a single platform.

    Args:
        name: name of the exporter (e.g., ``environment-yaml``)
        aliases: user-friendly format aliases (e.g., ("yaml",))
        default_filenames: default filenames this exporter handles (e.g., ("environment.yml", "environment.yaml"))
        export: callable that exports an Environment to string format for a single platform
        multiplatform_export: callable that exports an Environment to string format for multiple platforms
        description: user-friendly description of what the format does. Defaults to the name if not provided.
        environment_format: EnvironmentFormat category. Defaults to EnvironmentFormat.environment.
    """

    name: str
    aliases: tuple[str, ...]
    default_filenames: tuple[str, ...]
    export: SinglePlatformEnvironmentExport | None = None
    multiplatform_export: MultiPlatformEnvironmentExport | None = None
    description: str | None = field(default=None)
    environment_format: EnvironmentFormat = field(default=EnvironmentFormat.environment)

    def __post_init__(self):
        super().__post_init__()  # Handle name normalization
        # Normalize aliases using same pattern as name normalization
        try:
            self.aliases = tuple(
                dict.fromkeys(alias.lower().strip() for alias in self.aliases)
            )
        except AttributeError:
            # AttributeError: alias is not a string
            raise PluginError(f"Invalid plugin aliases for {self!r}")

        if bool(self.export) == bool(self.multiplatform_export):
            raise PluginError(
                f"Exactly one of export or multiplatform_export must be set for {self!r}"
            )

        # Set default description to name if not provided
        if self.description is None:
            self.description = self.name


@dataclass
class CondaPackageExtractor(CondaPlugin):
    """
    Return type to use when defining a conda package extractor plugin hook.

    Package extractors handle the extraction of different package archive formats.
    Each extractor specifies which file extensions it supports and provides an
    extraction function to unpack the archive.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_package_extractors`.

    Args:
        name: Extractor name (e.g., ``conda-package``, ``wheel-package``).
        extensions: List of file extensions this extractor handles
            (e.g., ``[".conda", ".tar.bz2"]`` or ``[".whl"]``).
        extract: Callable that extracts the package archive. Takes the source
            archive path and the destination directory where the package
            contents should be extracted.
    """

    name: str
    extensions: list[str]
    extract: PackageExtract


@dataclass(frozen=True)
class CondaExceptionEvent:
    """
    Structured exception event passed to exception observer plugin callbacks.

    Frozen to prevent plugins from mutating exception state. Structured args
    follow the ``threading.ExceptHookArgs`` / ``sys.UnraisableHookArgs``
    pattern for forward compatibility.

    The exception triple (``exc_type``, ``exc_value``, ``exc_traceback``) is
    always populated. The remaining fields describe the conda runtime state
    and default to ``None`` when the runtime isn't initialized (e.g.
    ``MemoryError`` during early startup). Runtime fields are populated
    all-or-nothing: if ``conda_version`` is not ``None``, the runtime was
    available and all other fields are populated (``active_prefix`` may
    still be ``None`` when no environment is active).

    .. warning::

       Do not store references to ``exc_value`` or ``exc_traceback`` beyond
       the lifetime of the callback. This can create reference cycles and
       prevent garbage collection.

    Args:
        exc_type: The exception class.
        exc_value: The exception instance.
        exc_traceback: The traceback object.
        argv: The command-line arguments at the time of error (frozen copy
            of ``sys.argv``). ``None`` if unavailable.
        conda_version: The conda version string. ``None`` if unavailable.
        return_code: The exit code conda will return for this error.
            ``None`` if unavailable.
        active_prefix: The currently active conda environment prefix,
            or ``None`` if no environment is active (also
            ``None`` when the runtime is unavailable).
        target_prefix: The prefix the command was operating on.
        channels: The configured channel names at the time of error
            (canonical names, e.g. ``defaults``, ``conda-forge``).
        subdir: The platform subdirectory (e.g., ``linux-64``, ``osx-arm64``).
        offline: Whether conda is running in offline mode (``--offline``).
        dry_run: Whether conda is running in dry-run mode (``--dry-run``).
        quiet: Whether conda is running in quiet mode (``--quiet``).
        json: Whether conda is running in JSON output mode (``--json``).
    """

    exc_type: type[BaseException]
    exc_value: BaseException
    exc_traceback: TracebackType
    argv: tuple[str, ...] | None = None
    conda_version: str | None = None
    return_code: int | None = None
    active_prefix: str | None = None
    target_prefix: str | None = None
    channels: tuple[str, ...] | None = None
    subdir: str | None = None
    offline: bool | None = None
    dry_run: bool | None = None
    quiet: bool | None = None
    json: bool | None = None


@dataclass
class CondaExceptionObserver(CondaPlugin):
    """
    Return type to use when defining a conda exception observer plugin hook.

    Exception observers are purely observational, modelled after CPython's
    ``sys.excepthook``. They cannot suppress, modify, or redirect the
    exception. Their return value is ignored.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_exception_observers`.

    .. warning::

       Do not store references to ``exc_value`` or ``exc_traceback`` beyond
       the lifetime of the callback. This can create reference cycles and
       prevent garbage collection.

    Args:
        name: Observer name (e.g., ``missing-package-reporter``).
        hook: Callable invoked with a :class:`CondaExceptionEvent` instance.
            Must not raise; any exception is caught and logged.
        watch_for: Set of exception class names this observer watches for.
            Matches against the full MRO. Examples:

            - ``{"BaseException"}`` — fires for every exception.
            - ``{"Exception"}`` — all standard exceptions (excludes
              ``KeyboardInterrupt``, ``SystemExit``).
            - ``{"CondaError"}`` — all conda errors and subclasses.
            - ``{"PackagesNotFoundError"}`` — a specific error and
              its subclasses (e.g. ``PackagesNotFoundInChannelsError``).
            - ``{"MemoryError"}``, ``{"KeyboardInterrupt"}``,
              ``{"SystemExit"}`` — specific non-conda exceptions.
            - ``{"CondaError", "MemoryError"}`` — combine scopes.

            For non-``CondaError`` exceptions the conda-specific fields
            on :class:`CondaExceptionEvent` may be ``None``.
    """

    name: str
    hook: Callable[[CondaExceptionEvent], None]
    watch_for: set[str]
