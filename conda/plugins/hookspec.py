# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Pluggy hook specifications ("hookspecs") to register conda plugins.

Each hookspec defined in :class:`~conda.plugins.hookspec.CondaSpecs` contains
an example of how to use it.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pluggy

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .types import (
        CondaAuthHandler,
        CondaEnvironmentExporter,
        CondaEnvironmentSpecifier,
        CondaHealthCheck,
        CondaPostCommand,
        CondaPostSolve,
        CondaPostTransactionAction,
        CondaPreCommand,
        CondaPrefixDataLoader,
        CondaPreSolve,
        CondaPreTransactionAction,
        CondaReporterBackend,
        CondaRequestHeader,
        CondaSetting,
        CondaSolver,
        CondaSubcommand,
        CondaVirtualPackage,
    )

spec_name = "conda"
"""Name used for organizing conda hook specifications"""

_hookspec = pluggy.HookspecMarker(spec_name)
"""
The conda plugin hook specifications, to be used by developers
"""

hookimpl = pluggy.HookimplMarker(spec_name)
"""
Decorator used to mark plugin hook implementations
"""


class CondaSpecs:
    """The conda plugin hookspecs, to be used by developers."""

    @_hookspec
    def conda_solvers(self) -> Iterable[CondaSolver]:
        """
        Register solvers in conda.

        **Example:**

        .. code-block:: python

            import logging

            from conda import plugins
            from conda.core import solve

            log = logging.getLogger(__name__)


            class VerboseSolver(solve.Solver):
                def solve_final_state(self, *args, **kwargs):
                    log.info("My verbose solver!")
                    return super().solve_final_state(*args, **kwargs)


            @plugins.hookimpl
            def conda_solvers():
                yield plugins.CondaSolver(
                    name="verbose-classic",
                    backend=VerboseSolver,
                )

        :return: An iterable of solver entries.
        """
        yield from ()

    @_hookspec
    def conda_subcommands(self) -> Iterable[CondaSubcommand]:
        """
        Register external subcommands in conda.

        **Example:**

        .. code-block:: python

            from conda import plugins


            def example_command(args):
                print("This is an example command!")


            @plugins.hookimpl
            def conda_subcommands():
                yield plugins.CondaSubcommand(
                    name="example",
                    summary="example command",
                    action=example_command,
                )

        :return: An iterable of subcommand entries.
        """
        yield from ()

    @_hookspec
    def conda_virtual_packages(self) -> Iterable[CondaVirtualPackage]:
        """
        Register virtual packages in Conda.

        **Example:**

        .. code-block:: python

            from conda import plugins


            @plugins.hookimpl
            def conda_virtual_packages():
                yield plugins.CondaVirtualPackage(
                    name="my_custom_os",
                    version="1.2.3",
                    build="x86_64",
                )

        :return: An iterable of virtual package entries.
        """
        yield from ()

    @_hookspec
    def conda_pre_commands(self) -> Iterable[CondaPreCommand]:
        """
        Register pre-command functions in conda.

        **Example:**

        .. code-block:: python

           from conda import plugins


           def example_pre_command(command):
               print("pre-command action")


           @plugins.hookimpl
           def conda_pre_commands():
               yield plugins.CondaPreCommand(
                   name="example-pre-command",
                   action=example_pre_command,
                   run_for={"install", "create"},
               )
        """
        yield from ()

    @_hookspec
    def conda_post_commands(self) -> Iterable[CondaPostCommand]:
        """
        Register post-command functions in conda.

        **Example:**

        .. code-block:: python

           from conda import plugins


           def example_post_command(command):
               print("post-command action")


           @plugins.hookimpl
           def conda_post_commands():
               yield plugins.CondaPostCommand(
                   name="example-post-command",
                   action=example_post_command,
                   run_for={"install", "create"},
               )
        """
        yield from ()

    @_hookspec
    def conda_auth_handlers(self) -> Iterable[CondaAuthHandler]:
        """
        Register a conda auth handler derived from the requests API.

        This plugin hook allows attaching requests auth handler subclasses,
        e.g. when authenticating requests against individual channels hosted
        at HTTP/HTTPS services.

        **Example:**

        .. code-block:: python

            import os
            from conda import plugins
            from requests.auth import AuthBase


            class EnvironmentHeaderAuth(AuthBase):
                def __init__(self, *args, **kwargs):
                    self.username = os.environ["EXAMPLE_CONDA_AUTH_USERNAME"]
                    self.password = os.environ["EXAMPLE_CONDA_AUTH_PASSWORD"]

                def __call__(self, request):
                    request.headers["X-Username"] = self.username
                    request.headers["X-Password"] = self.password
                    return request


            @plugins.hookimpl
            def conda_auth_handlers():
                yield plugins.CondaAuthHandler(
                    name="environment-header-auth",
                    handler=EnvironmentHeaderAuth,
                )
        """
        yield from ()

    @_hookspec
    def conda_health_checks(self) -> Iterable[CondaHealthCheck]:
        """
        Register health checks for conda doctor.

        This plugin hook allows you to add more "health checks" to conda doctor
        that you can write to diagnose problems in your conda environment.
        Check out the health checks already shipped with conda for inspiration.

        **Example:**

        .. code-block:: python

            from conda import plugins


            def example_health_check(prefix: str, verbose: bool):
                print("This is an example health check!")


            @plugins.hookimpl
            def conda_health_checks():
                yield plugins.CondaHealthCheck(
                    name="example-health-check",
                    action=example_health_check,
                )
        """
        yield from ()

    @_hookspec
    def conda_pre_transaction_actions(self) -> Iterable[CondaPreTransactionAction]:
        """Register pre-transaction hooks.

        Pre-transaction hooks run before all other actions run in a
        UnlinkLinkTransaction. For information about the Action class,
        see :class:`~conda.core.path_actions.Action`.

        **Example:**

        .. code-block:: python

            from conda import plugins
            from conda.core.path_actions import Action


            class PrintAction(Action):
                def verify(self):
                    print("Performing verification...")
                    self._verified = True

                def execute(self):
                    print(
                        self.transaction_context,
                        self.target_prefix,
                        self.unlink_precs,
                        self.link_precs,
                        self.remove_specs,
                        self.update_specs,
                        self.neutered_specs,
                    )

                def reverse(self):
                    print("Reversing only happens when `execute` raises an exception.")

                def cleanup(self):
                    print("Carrying out cleanup...")


            class PrintActionPlugin:
                @plugins.hookimpl
                def conda_pre_transaction_actions(
                    self,
                ) -> Iterable[plugins.CondaPreTransactionAction]:
                    yield plugins.CondaPreTransactionAction(
                        name="example-pre-transaction-action",
                        action=PrintAction,
                    )
        """
        yield from ()

    @_hookspec
    def conda_post_transaction_actions(self) -> Iterable[CondaPostTransactionAction]:
        """Register post-transaction hooks.

        Post-transaction hooks run after all other actions run in a
        UnlinkLinkTransaction. For information about the Action class,
        see :class:`~conda.core.path_actions.Action`.

        **Example:**

        .. code-block:: python

            from conda import plugins
            from conda.core.path_actions import Action


            class PrintAction(Action):
                def verify(self):
                    print("Performing verification...")
                    self._verified = True

                def execute(self):
                    print(
                        self.transaction_context,
                        self.target_prefix,
                        self.unlink_precs,
                        self.link_precs,
                        self.remove_specs,
                        self.update_specs,
                        self.neutered_specs,
                    )

                def reverse(self):
                    print("Reversing only happens when `execute` raises an exception.")

                def cleanup(self):
                    print("Carrying out cleanup...")


            class PrintActionPlugin:
                @plugins.hookimpl
                def conda_post_transaction_actions(
                    self,
                ) -> Iterable[plugins.CondaPostTransactionAction]:
                    yield plugins.CondaPostTransactionAction(
                        name="example-post-transaction-action",
                        action=PrintAction,
                    )
        """
        yield from ()

    @_hookspec
    def conda_pre_solves(self) -> Iterable[CondaPreSolve]:
        """
        Register pre-solve functions in conda that are used in the
        general solver API, before the solver processes the package specs in
        search of a solution.

        **Example:**

        .. code-block:: python

           from conda import plugins
           from conda.models.match_spec import MatchSpec


           def example_pre_solve(
               specs_to_add: frozenset[MatchSpec],
               specs_to_remove: frozenset[MatchSpec],
           ):
               print(f"Adding {len(specs_to_add)} packages")
               print(f"Removing {len(specs_to_remove)} packages")


           @plugins.hookimpl
           def conda_pre_solves():
               yield plugins.CondaPreSolve(
                   name="example-pre-solve",
                   action=example_pre_solve,
               )
        """
        yield from ()

    @_hookspec
    def conda_post_solves(self) -> Iterable[CondaPostSolve]:
        """
        Register post-solve functions in conda that are used in the
        general solver API, after the solver has provided the package
        records to add or remove from the conda environment.

        **Example:**

        .. code-block:: python

           from conda import plugins
           from conda.models.records import PackageRecord


           def example_post_solve(
               repodata_fn: str,
               unlink_precs: tuple[PackageRecord, ...],
               link_precs: tuple[PackageRecord, ...],
           ):
               print(f"Uninstalling {len(unlink_precs)} packages")
               print(f"Installing {len(link_precs)} packages")


           @plugins.hookimpl
           def conda_post_solves():
               yield plugins.CondaPostSolve(
                   name="example-post-solve",
                   action=example_post_solve,
               )
        """
        yield from ()

    @_hookspec
    def conda_settings(self) -> Iterable[CondaSetting]:
        """
        Register new setting

        The example below defines a simple string type parameter

        **Example:**

        .. code-block:: python

           from conda import plugins
           from conda.common.configuration import PrimitiveParameter, SequenceParameter


           @plugins.hookimpl
           def conda_settings():
               yield plugins.CondaSetting(
                   name="example_option",
                   description="This is an example option",
                   parameter=PrimitiveParameter("default_value", element_type=str),
                   aliases=("example_option_alias",),
               )
        """
        yield from ()

    @_hookspec
    def conda_reporter_backends(self) -> Iterable[CondaReporterBackend]:
        """
        Register new reporter backend

        The example below defines a reporter backend that uses the ``pprint`` module in Python.

        **Example:**

        .. code-block:: python

           from pprint import pformat

           from conda import plugins
           from conda.plugins.types import (
               CondaReporterBackend,
               ReporterRendererBase,
               ProgressBarBase,
           )


           class PprintReporterRenderer(ReporterRendererBase):
               "Implementation of the ReporterRendererBase"

               def detail_view(self, data):
                   return pformat(data)

               def envs_list(self, data):
                   formatted_data = pformat(data)
                   return f"Environments: {formatted_data}"

               def progress_bar(self, description, io_context_manager) -> ProgressBarBase:
                   "Returns our custom progress bar implementation"
                   return PprintProgressBar(description, io_context_manager)


           class PprintProgressBar(ProgressBarBase):
               "Blank implementation of ProgressBarBase which does nothing"

               def update_to(self, fraction) -> None:
                   pass

               def refresh(self) -> None:
                   pass

               def close(self) -> None:
                   pass


           @plugins.hookimpl
           def conda_reporter_backends():
               yield CondaReporterBackend(
                   name="pprint",
                   description="Reporter backend based on the pprint module",
                   renderer=PprintReporterRenderer,
               )

        """
        yield from ()

    @_hookspec
    def conda_session_headers(self, host: str) -> Iterable[CondaRequestHeader]:
        """
        Register new HTTP request headers

        The example below defines how to add HTTP headers for all requests
        with the hostname of ``example.com``.

        **Example:**

        .. code-block:: python

           from conda import plugins

           HOSTS = {"example.com", "sub.example.com"}


           @plugins.hookimpl
           def conda_session_headers(host: str):
               if host in HOSTS:
                   yield plugins.CondaRequestHeader(
                       name="Example-Header",
                       value="example",
                   )
        """
        yield from ()

    @_hookspec
    def conda_request_headers(
        self, host: str, path: str
    ) -> Iterable[CondaRequestHeader]:
        """
        Register new HTTP request headers

        The example below defines how to add HTTP headers for all requests
        with the hostname of ``example.com`` and a ``path/to/endpoint.json`` path.

        **Example:**

        .. code-block:: python

           from conda import plugins

           HOSTS = {"example.com", "sub.example.com"}
           ENDPOINT = "/path/to/endpoint.json"


           @plugins.hookimpl
           def conda_request_headers(host: str, path: str):
               if host in HOSTS and path == ENDPOINT:
                   yield plugins.CondaRequestHeader(
                       name="Example-Header",
                       value="example",
                   )
        """
        yield from ()

    @_hookspec
    def conda_prefix_data_loaders() -> Iterable[CondaPrefixDataLoader]:
        """
        Register new loaders for PrefixData

        The example below defines how to expose the packages installed
        by a hypothetical 'penguin' tool as conda packages.

        **Example:**

        .. code-block:: python

            from pathlib import Path

            from conda import plugins
            from conda.common.path import PathType
            from conda.models.records import PrefixRecord
            from conda.plugins.types import CondaPrefixDataLoader


            @plugins.hookimpl
            def conda_prefix_data_loaders():
                yield CondaPrefixDataLoader(
                    "hypothetical",
                    load_hypothetical_packages,
                )


            def load_hypothetical_packages(
                prefix: PathType, records: dict[str, PrefixRecord]
            ) -> dict[str, PrefixRecord]:
                penguin_records = {}
                for info in Path(prefix).glob("lib/penguin/*.penguin-info"):
                    name, version = info.name.rsplit("-", 1)
                    kwargs = {}  # retrieve extra fields here
                    penguin_records[name] = PrefixRecord(
                        name=name, version=version, build_number=0, build="0", **kwargs
                    )
                records.update(penguin_records)
                return penguin_records
        """
        yield from ()

    @_hookspec
    def conda_environment_specifiers(self) -> Iterable[CondaEnvironmentSpecifier]:
        """
        **EXPERIMENTAL**
        Register new conda env spec type

        The example below defines a type of conda env file called "random". It
        can parse a file with the file extension `.random`. This plugin will ignore
        whatever is in the input environment file and produce an environment with a
        random name and with random packages.

        **Example:**

        .. code-block:: python

            import json
            import random
            from pathlib import Path
            from subprocess import run
            from conda import plugins
            from ...plugins.types import EnvironmentSpecBase
            from conda.env.env import Environment

            packages = ["python", "numpy", "scipy", "matplotlib", "pandas", "scikit-learn"]


            class RandomSpec(EnvironmentSpecBase):
                extensions = {".random"}

                def __init__(self, filename: str):
                    self.filename = filename

                def can_handle(self):
                    # Return early if no filename was provided
                    if self.filename is None:
                        return False

                    # Extract the file extension (e.g., '.txt' or '' if no extension)
                    file_ext = os.path.splitext(self.filename)[1]

                    # Check if the file has a supported extension and exists
                    return any(
                        spec_ext == file_ext and os.path.exists(self.filename)
                        for spec_ext in RandomSpec.extensions
                    )

                def env(self):
                    return Environment(
                        name="".join(random.choice("0123456789abcdef") for i in range(6)),
                        dependencies=[random.choice(packages) for i in range(6)],
                    )


            @plugins.hookimpl
            def conda_environment_specifiers():
                yield plugins.CondaEnvSpec(
                    name="random",
                    environment_spec=RandomSpec,
                )
        """
        yield from ()

    @_hookspec
    def conda_environment_exporters(self) -> Iterable[CondaEnvironmentExporter]:
        """
        Register new conda environment exporter

        Environment exporters serialize conda Environment objects to different
        output formats (JSON, TOML, XML, etc.) for the 'conda export' command.
        This is separate from environment specifiers which parse input files.

        **Example:**

        .. code-block:: python

            import tomlkit
            from conda import plugins
            from conda.exceptions import CondaValueError
            from conda.models.environment import Environment
            from conda.plugins.types import CondaEnvironmentExporter


            def export_toml(env: Environment) -> str:
                # Export Environment to TOML format
                # For formats that use the standard dictionary structure,
                # you can use the shared utility:
                from conda.plugins.environment_exporters.standard import to_dict

                env_dict = to_dict(env)

                # Create TOML document
                toml_doc = tomlkit.document()

                if env_dict.get("name"):
                    toml_doc["name"] = env_dict["name"]

                if env_dict.get("channels"):
                    toml_doc["channels"] = env_dict["channels"]

                if env_dict.get("dependencies"):
                    toml_doc["dependencies"] = env_dict["dependencies"]

                if env_dict.get("variables"):
                    toml_doc["variables"] = env_dict["variables"]

                return tomlkit.dumps(toml_doc)


            @plugins.hookimpl
            def conda_environment_exporters():
                yield CondaEnvironmentExporter(
                    name="environment-toml",
                    aliases=("toml",),
                    default_filenames=("environment.toml",),
                    export=export_toml,
                )
        """
        yield from ()
