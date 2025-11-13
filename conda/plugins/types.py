# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Definition of specific return types for use when defining a conda plugin hook.

Each type corresponds to the plugin hook for which it is used.

"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from requests.auth import AuthBase

from ..auxlib import NULL
from ..auxlib.type_coercion import maybecall
from ..base.constants import APP_NAME
from ..exceptions import PluginError
from ..models.records import PackageRecord

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Callable, Iterable
    from contextlib import AbstractContextManager
    from typing import Any, ClassVar, Literal, TypeAlias

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

    SinglePlatformEnvironmentExport = Callable[[Environment], str]
    MultiPlatformEnvironmentExport = Callable[[Iterable[Environment]], str]


@dataclass
class CondaPlugin:
    """
    Base class for all conda plugins.
    """

    #: User-facing name of the plugin used for selecting & filtering plugins and error messages.
    name: str

    def __post_init__(self):
        try:
            self.name = self.name.lower().strip()
        except AttributeError:
            # AttributeError: name is not a string
            raise PluginError(f"Invalid plugin name for {self!r}")


@dataclass
class CondaSubcommand(CondaPlugin):
    """
    Return type to use when defining a conda subcommand plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_subcommands`.

    :param name: Subcommand name (e.g., ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param action: Callable that will be run when the subcommand is invoked.
    :param configure_parser: Callable that will be run when the subcommand parser is initialized.
    """

    name: str
    summary: str
    action: Callable[
        [Namespace | tuple[str]],  # arguments
        int | None,  # return code
    ]
    configure_parser: Callable[[ArgumentParser], None] | None = field(default=None)


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

    :param name: Virtual package name (e.g., ``my_custom_os``).
    :param version: Virtual package version (e.g., ``1.2.3``).
    :param build: Virtual package build string (e.g., ``x86_64``).
    :param override_entity: Can be set to either to "version" or "build", the corresponding
                            value will be overridden if the environment variable
                            ``CONDA_OVERRIDE_<name>`` is set.
    :param empty_override: Value to use for version or build if the override
                           environment variable is set to an empty string. By default,
                           this is ``NULL``.
    :param version_validation: Optional version validation function to ensure that the override version follows a certain pattern.
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

    :param name: Solver name (e.g., ``custom-solver``).
    :param backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


@dataclass
class CondaPreCommand(CondaPlugin):
    """
    Return type to use when defining a conda pre-command plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_commands`.

    :param name: Pre-command name (e.g., ``custom_plugin_pre_commands``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
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

    :param name: Post-command name (e.g., ``custom_plugin_post_commands``).
    :param action: Callable which contains the code to be run.
    :param run_for: Represents the command(s) this will be run on (e.g. ``install`` or ``create``).
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

    :param name: Name (e.g., ``basic-auth``). This name should be unique
                 and only one may be registered at a time.
    :param handler: Type that will be used as the authentication handler
                    during network requests.
    """

    name: str
    handler: type[ChannelAuthBase]


@dataclass
class CondaHealthCheck(CondaPlugin):
    """
    Return type to use when defining conda health checks plugin hook.
    """

    name: str
    action: Callable[[str, bool], None]


@dataclass
class CondaPreSolve(CondaPlugin):
    """
    Return type to use when defining a conda pre-solve plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_solves`.

    :param name: Pre-solve name (e.g., ``custom_plugin_pre_solve``).
    :param action: Callable which contains the code to be run.
    """

    name: str
    action: Callable[[frozenset[MatchSpec], frozenset[MatchSpec]], None]


@dataclass
class CondaPostSolve(CondaPlugin):
    """
    Return type to use when defining a conda post-solve plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_post_solves`.

    :param name: Post-solve name (e.g., ``custom_plugin_post_solve``).
    :param action: Callable which contains the code to be run.
    """

    name: str
    action: Callable[[str, tuple[PackageRecord, ...], tuple[PackageRecord, ...]], None]


@dataclass
class CondaSetting(CondaPlugin):
    """
    Return type to use when defining a conda setting plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_settings`.

    :param name: name of the setting (e.g., ``config_param``)
    :param description: description of the setting that should be targeted
                        towards users of the plugin
    :param parameter: Parameter instance containing the setting definition
    :param aliases: alternative names of the setting
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

    :param name: name of the reporter backend (e.g., ``email_reporter``)
                 This is how the reporter backend with be references in configuration files.
    :param description: short description of what the reporter handler does
    :param renderer: implementation of ``ReporterRendererBase`` that will be used as the
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

    :param name: name of the header used in the HTTP request
    :param value: value of the header used in the HTTP request
    """

    name: str
    value: str


@dataclass
class CondaPreTransactionAction(CondaPlugin):
    """
    Return type to use when defining a pre-transaction action hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_pre_transaction_actions`.

    :param name: Pre transaction name (this is just a label)
    :param action: Action class which implements
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

    :param name: Post transaction name (this is just a label)
    :param action: Action class which implements
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

    :param name: name of the loader
    :param loader: a function that takes a prefix and a dictionary that maps
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

        :returns bool: returns True, if the plugin can interpret the file.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def env(self) -> Environment:
        """
        Express the provided environment file as a conda environment object.

        :returns Environment: the conda environment represented by the file.
        """
        raise NotImplementedError()


@dataclass
class CondaEnvironmentSpecifier(CondaPlugin):
    """
    **EXPERIMENTAL**

    Return type to use when defining a conda env spec plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_environment_specifiers`.

    :param name: name of the spec (e.g., ``environment_yaml``)
    :param environment_spec: EnvironmentSpecBase subclass handler
    """

    name: str
    environment_spec: type[EnvironmentSpecBase]


@dataclass
class CondaEnvironmentExporter(CondaPlugin):
    """
    **EXPERIMENTAL**

    Return type to use when defining a conda environment exporter plugin hook supporting a single platform.

    :param name: name of the exporter (e.g., ``environment-yaml``)
    :param aliases: user-friendly format aliases (e.g., ("yaml",))
    :param default_filenames: default filenames this exporter handles (e.g., ("environment.yml", "environment.yaml"))
    :param export: callable that exports an Environment to string format
    """

    name: str
    aliases: tuple[str, ...]
    default_filenames: tuple[str, ...]
    export: SinglePlatformEnvironmentExport | None = None
    multiplatform_export: MultiPlatformEnvironmentExport | None = None

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
