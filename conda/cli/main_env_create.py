# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env create`.

Creates new conda environments with the specified packages.
"""

from argparse import (
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)
from pathlib import Path

from .. import CondaError
from ..cli.main_config import set_keys
from ..common.configuration import DEFAULT_CONDARC_FILENAME
from ..notices import notices


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from ..base.context import context
    from .helpers import (
        add_output_and_prompt_options,
        add_parser_default_packages,
        add_parser_environment_specifier,
        add_parser_networking,
        add_parser_platform,
        add_parser_prefix,
        add_parser_solver,
    )

    plugin_manager = context.plugin_manager
    specifiers = list(plugin_manager.get_hook_results("environment_specifiers"))
    spec_example, lock_example = plugin_manager.resolve_format_examples(specifiers)

    summary = "Create an environment based on an environment definition file."
    description = dals(
        f"""
        {summary}

        The file format is detected from the filename or contents. Which
        formats are supported depends on the plugins installed in your
        environment. See the epilog for the list of formats available here.

        If the file declares a name in its contents (for instance as the
        first line of an environment.yml file), that name is used unless
        overridden on the CLI with -n/--name.

        Unless you are in the directory containing the environment definition
        file, use -f to specify the file path of the environment definition
        file you want to use.

        """
    )

    # See the comment in main_create.py for why these conditional blocks
    # are plain strings rather than ``dals`` calls.
    example_blocks = ["Examples:"]
    if spec_example:
        example_blocks.append(
            "  Create from an environment spec (solved at install time):\n"
            f"    conda env create -f /path/to/{spec_example}"
        )
    if lock_example:
        example_blocks.append(
            "  Create from a lockfile (no solve, exact reproduction):\n"
            f"    conda env create -f {lock_example}"
        )
    example_blocks.append(
        "  Use the default file in the current directory:\n"
        "    conda env create\n"
        "    conda env create -n envname"
    )
    epilog = "\n\n".join(example_blocks) + plugin_manager.describe_formats(
        specifiers, heading="Available input formats"
    )

    p = sub_parsers.add_parser(
        "create",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    p.add_argument(
        "-f",
        "--file",
        action="store",
        help=(
            "Environment definition file (default: environment.yml). Standard "
            "filenames registered by the installed format plugins are "
            "auto-detected. Custom filenames require --format."
        ),
        default="environment.yml",
    )

    # Add name and prefix args
    add_parser_prefix(p)

    # Add networking args
    add_parser_networking(p)

    # Add environment spec plugin args
    add_parser_environment_specifier(p)

    add_parser_default_packages(p)
    add_output_and_prompt_options(p)
    add_parser_solver(p)
    add_parser_platform(p)

    p.set_defaults(func="conda.cli.main_env_create.execute")

    return p


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..auxlib.ish import dals
    from ..base.context import context, determine_target_prefix
    from ..common.serialize import json
    from ..core.prefix_data import PrefixData
    from ..env.env import print_result
    from ..env.installers.base import get_installer
    from ..env.pip_util import get_pip_workdir
    from ..exceptions import (
        CondaEnvException,
        InvalidInstaller,
        PlatformMismatchError,
    )
    from ..gateways.disk.delete import rm_rf
    from .common import validate_file_exists

    # validate incoming arguments
    validate_file_exists(args.file)

    # detect the file format and get the env representation
    spec_hook = context.plugin_manager.get_environment_specifier(
        source=args.file,
        name=context.environment_specifier,
    )
    spec = spec_hook.environment_spec(args.file)
    if context.subdir not in spec.available_platforms:
        raise PlatformMismatchError(
            [(args.file, spec.available_platforms)], context.subdir
        )
    env = spec.env_for(context.subdir)

    # FIXME conda code currently requires args to have a name or prefix
    # don't overwrite name if it's given. gh-254
    if args.prefix is None and args.name is None:
        if env.name is None:  # requirements.txt won't populate Environment.name
            msg = dals(
                """
                Unable to create environment
                Please re-run this command with one of the following options:
                * Provide an environment name via --name or -n
                * Provide a path on disk via --prefix or -p
                """
            )
            raise CondaEnvException(msg)
        args.name = env.name

    prefix = determine_target_prefix(context, args)
    prefix_data = PrefixData(prefix)

    if args.yes and not prefix_data.is_base() and prefix_data.exists():
        rm_rf(prefix)

    prefix_data.validate_path()
    prefix_data.validate_name()

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    result = {"conda": None, "pip": None}

    args_packages = (
        context.create_default_packages if not args.no_default_packages else []
    )

    if args.dry_run:
        installer_type = "conda"
        installer = get_installer(installer_type)

        pkg_specs = [*env.requested_packages, *args_packages]

        solved_env = installer.dry_run(pkg_specs, args, env)
        if args.json:
            print(json.dumps(solved_env.to_dict()))
        else:
            print(solved_env.to_yaml(), end="")

    else:
        if args_packages:
            installer_type = "conda"
            installer = get_installer(installer_type)
            result[installer_type] = installer.install(prefix, args_packages, args, env)

        # install conda packages
        installer_type = "conda"
        installer = get_installer(installer_type)
        result[installer_type] = installer.install(
            prefix, env.requested_packages, args, env
        )

        # install all other external packages
        for installer_type, pkg_specs in env.external_packages.items():
            try:
                installer = get_installer(installer_type)
                if installer_type == "pip":
                    workdir = get_pip_workdir(args.file)
                    result[installer_type] = installer.install(
                        prefix, pkg_specs, args, env, workdir=workdir
                    )
                else:
                    result[installer_type] = installer.install(
                        prefix, pkg_specs, args, env
                    )
            except InvalidInstaller:
                raise CondaError(
                    dals(
                        f"""
                        Unable to install package for {installer_type}.

                        Please double check and ensure your dependencies file has
                        the correct spelling. You might also try installing the
                        conda-env-{installer_type} package to see if provides
                        the required installer.
                        """
                    )
                )

        if context.subdir != context._native_subdir():
            set_keys(
                ("subdir", context.subdir),
                path=Path(prefix, DEFAULT_CONDARC_FILENAME),
            )

        if env.variables:
            prefix_data.set_environment_env_vars(env.variables)

        prefix_data.set_nonadmin()
        print_result(args, prefix, result)

    return 0
