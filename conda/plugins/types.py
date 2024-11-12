# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Definition of specific return types for use when defining a conda plugin hook.

Each type corresponds to the plugin hook for which it is used.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from requests.auth import AuthBase

from ..models.records import PackageRecord

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from contextlib import AbstractContextManager
    from typing import Any, Callable

    from ..common.configuration import Parameter
    from ..core.solve import Solver
    from ..models.match_spec import MatchSpec


@dataclass
class CondaSubcommand:
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


class CondaVirtualPackage(NamedTuple):
    """
    Return type to use when defining a conda virtual package plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_virtual_packages`.

    :param name: Virtual package name (e.g., ``my_custom_os``).
    :param version: Virtual package version (e.g., ``1.2.3``).
    :param build: Virtual package build string (e.g., ``x86_64``).
    """

    name: str
    version: str | None
    build: str | None

    def to_virtual_package(self) -> PackageRecord:
        return PackageRecord.virtual_package(f"__{self.name}", self.version, self.build)


class CondaSolver(NamedTuple):
    """
    Return type to use when defining a conda solver plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_solvers`.

    :param name: Solver name (e.g., ``custom-solver``).
    :param backend: Type that will be instantiated as the solver backend.
    """

    name: str
    backend: type[Solver]


class CondaPreCommand(NamedTuple):
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


class CondaPostCommand(NamedTuple):
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


class CondaAuthHandler(NamedTuple):
    """
    Return type to use when the defining the conda auth handlers hook.

    :param name: Name (e.g., ``basic-auth``). This name should be unique
                 and only one may be registered at a time.
    :param handler: Type that will be used as the authentication handler
                    during network requests.
    """

    name: str
    handler: type[ChannelAuthBase]


class CondaHealthCheck(NamedTuple):
    """
    Return type to use when defining conda health checks plugin hook.
    """

    name: str
    action: Callable[[str, bool], None]


@dataclass
class CondaPreSolve:
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
class CondaPostSolve:
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
class CondaSetting:
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
    def envs_list(self, data, **kwargs) -> str:
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
class CondaReporterBackend:
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
class CondaRequestHeader:
    """
    Define vendor specific headers to include HTTP requests

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_request_headers`.

    :param name: name of the header used in the HTTP request
    :param description: description of the HTTP header and its purpose
    :param value: value of the header used in the HTTP request
    :param hosts: host(s) for which this header should be used with; when not set the header
                        will be included in all HTTP requests.
    """

    name: str
    description: str
    value: str
    hosts: set[str] | None = None
