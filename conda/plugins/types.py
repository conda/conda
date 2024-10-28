# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Definition of specific return types for use when defining a conda plugin hook.

Each type corresponds to the plugin hook for which it is used.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from requests.auth import AuthBase

from ..models.records import PackageRecord

if TYPE_CHECKING:
    from argparse import Action, ArgumentParser, Namespace
    from pathlib import Path
    from typing import Any, Callable, Iterable, Literal, TypedDict

    from typing_extensions import NotRequired

    from ..common.configuration import Parameter
    from ..core.solve import Solver
    from ..models.match_spec import MatchSpec

    class AddArgumentDict(TypedDict):
        action: NotRequired[str | type[Action]]
        nargs: NotRequired[int | Literal["?", "*", "+"]]
        const: NotRequired[Any]
        default: NotRequired[Any]
        type: NotRequired[Callable[[str], Any]]
        choices: NotRequired[Iterable[Any]]
        required: NotRequired[bool]
        metavar: NotRequired[str | tuple[str, ...]]


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


@dataclass
class CondaCleanupTask:
    """
    Return type to use when defining a conda clean plugin hook.

    For details on how this is used, see
    :meth:`~conda.plugins.hookspec.CondaSpecs.conda_cleanup_tasks`.

    :param name: the name of the clean command used as the destination in argparse.ArgumentParser.add_argument
    :param flags: list of flags to be used in argparse.ArgumentParser.add_argument
    :param help: help message used in argparse.ArgumentParser.add_argument
    :param action: callable to determine which files to remove
    :param add_argument_kwargs: additional options used in argparse.ArgumentParser.add_argument
    :param all: whether to include in --all
    """

    name: str
    flags: list[str]
    help: str
    action: Callable[[Any], Iterable[Path] | dict[Path, Iterable[Path]]]
    add_argument_kwargs: AddArgumentDict | None = None
    all: bool = True
