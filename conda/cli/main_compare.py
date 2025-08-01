# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda compare`.

Compare the packages in an environment with the packages listed in an environment file.
"""

from __future__ import annotations

import logging
import os
from os.path import abspath, expanduser, expandvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction

log = logging.getLogger(__name__)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_json, add_parser_prefix

    summary = "Compare packages between conda environments."
    description = summary
    epilog = dals(
        """
        Examples:

        Compare packages in the current environment with respect
        to 'environment.yml' located in the current working directory::

            conda compare environment.yml

        Compare packages installed into the environment 'myenv' with respect
        to 'environment.yml' in a different directory::

            conda compare -n myenv path/to/file/environment.yml

        """
    )

    p = sub_parsers.add_parser(
        "compare",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    add_parser_json(p)
    add_parser_prefix(p)
    p.add_argument(
        "file",
        action="store",
        help="Path to the environment file that is to be compared against.",
    )
    p.set_defaults(func="conda.cli.main_compare.execute")

    return p


def get_packages(prefix):
    from ..core.prefix_data import PrefixData
    from ..exceptions import EnvironmentLocationNotFound

    if not os.path.isdir(prefix):
        raise EnvironmentLocationNotFound(prefix)

    return sorted(
        PrefixData(prefix, interoperability=True).iter_records(),
        key=lambda x: x.name,
    )


def compare_packages(active_pkgs, specification_pkgs) -> tuple[int, list[str]]:
    from ..models.match_spec import MatchSpec

    output = []
    miss = False
    for pkg in specification_pkgs:
        pkg_spec = MatchSpec(pkg)
        if (name := pkg_spec.name) in active_pkgs:
            if not pkg_spec.match(active_pkg := active_pkgs[name]):
                miss = True
                output.append(
                    f"{name} found but mismatch. Specification pkg: {pkg}, "
                    f"Running pkg: {active_pkg.spec}"
                )
        else:
            miss = True
            output.append(f"{name} not found")
    if not miss:
        output.append(
            "Success. All the packages in the "
            "specification file are present in the environment "
            "with matching version and build string."
        )
    return int(miss), output


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..base.context import context
    from ..core.prefix_data import PrefixData
    from ..exceptions import SpecNotFound
    from ..gateways.connection.session import CONDA_SESSION_SCHEMES
    from .common import stdout_json

    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()
    prefix = str(prefix_data.prefix_path)

    try:
        url_scheme = args.file.split("://", 1)[0]
        if url_scheme in CONDA_SESSION_SCHEMES:
            filename = args.file
        else:
            filename = abspath(expanduser(expandvars(args.file)))

        spec_hook = context.plugin_manager.get_environment_specifier(
            source=filename,
            name=context.environment_specifier,
        )
        spec = spec_hook.environment_spec(filename)
        env = spec.env

        if args.prefix is None and args.name is None:
            args.name = env.name
    except SpecNotFound:
        raise

    active_pkgs = {pkg.name: pkg for pkg in get_packages(prefix)}
    specification_pkgs = env.requested_packages
    for packages in env.external_packages.values():
        specification_pkgs = specification_pkgs + packages

    exitcode, output = compare_packages(active_pkgs, specification_pkgs)

    if context.json:
        stdout_json(output)
    else:
        print("\n".join(map(str, output)))

    return exitcode
