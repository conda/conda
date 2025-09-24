# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda rename`.

Renames an existing environment by cloning it and then removing the original environment.
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from conda.deprecations import deprecated
from conda.exceptions import CondaEnvException

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_output_and_prompt_options, add_parser_prefix

    summary = "Rename an existing environment."
    description = dals(
        f"""
        {summary}

        This command renames a conda environment via its name (-n/--name) or
        its prefix (-p/--prefix).

        The base environment and the currently-active environment cannot be renamed.
        """
    )
    epilog = dals(
        """
        Examples::

            conda rename -n test123 test321

            conda rename --name test123 test321

            conda rename -p path/to/test123 test321

            conda rename --prefix path/to/test123 test321

        """
    )

    p = sub_parsers.add_parser(
        "rename",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    # Add name and prefix args
    add_parser_prefix(p)

    p.add_argument("destination", help="New name for the conda environment.")

    add_output_and_prompt_options(p)

    p.set_defaults(func="conda.cli.main_rename.execute")

    return p


@deprecated("25.9", "26.3", addendum="Use PrefixData.validate_path()")
def check_protected_dirs(prefix: str | Path, json: bool = False) -> None:
    """Ensure that the new prefix does not contain protected directories."""
    from conda.core.prefix_data import PrefixData

    if PrefixData(Path(prefix).parent).is_environment():
        raise CondaEnvException(
            f"The specified prefix '{prefix}' "
            "appears to be a top level directory within an existing conda environment "
            "(i.e., {history_file} exists). Creating an environment in this location "
            "has the potential to irreversibly corrupt your conda installation and/or "
            "other conda environments, please choose a different location for your "
            "new conda environment. Aborting.",
            json,
        )


@deprecated(
    "25.9",
    "26.3",
    addendum="Use PrefixData.validate_path(), PrefixData.validate_name()",
)
def validate_src() -> str:
    """
    Ensure that we are receiving at least one valid value for the environment
    to be renamed and that the "base" environment is not being renamed
    """
    from ..base.context import context
    from .install import validate_prefix_exists

    prefix = Path(context.target_prefix)
    validate_prefix_exists(prefix)

    if prefix.samefile(context.root_prefix):
        raise CondaEnvException("The 'base' environment cannot be renamed")
    if context.active_prefix and prefix.samefile(context.active_prefix):
        raise CondaEnvException("Cannot rename the active environment")
    else:
        check_protected_dirs(prefix)

    return str(prefix)


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """Executes the command for renaming an existing environment."""
    from ..base.constants import DRY_RUN_PREFIX
    from ..base.context import context
    from ..cli import install
    from ..core.prefix_data import PrefixData
    from ..gateways.disk.delete import rm_rf
    from ..gateways.disk.update import rename_context

    # Validate source
    source_prefix_data = PrefixData.from_context()
    source_prefix_data.assert_environment()
    if source_prefix_data.is_base():
        raise CondaEnvException("The 'base' environment cannot be renamed")
    if context.active_prefix and source_prefix_data.prefix_path.samefile(
        context.active_prefix
    ):
        raise CondaEnvException("Cannot rename the active environment")

    if source_prefix_data == PrefixData(context.default_activation_prefix):
        raise CondaEnvException(
            "Cannot rename an environment if it is configured as `default_activation_env`."
        )

    source = str(source_prefix_data.prefix_path)

    # Validate destination
    if os.sep in args.destination:
        dest_prefix_data = PrefixData(args.destination)
        dest_prefix_data.validate_path(expand_path=True)
    else:
        dest_prefix_data = PrefixData.from_name(args.destination)
    destination = str(dest_prefix_data.prefix_path)
    if not args.yes and dest_prefix_data.exists():
        raise CondaEnvException(
            f"The environment '{dest_prefix_data.prefix_path}' already exists. Override with --yes."
        )

    def clone_and_remove() -> None:
        actions: tuple[partial, ...] = (
            partial(
                install.clone,
                source,
                destination,
                quiet=context.quiet,
                json=context.json,
            ),
            partial(rm_rf, source),
        )

        # We now either run collected actions or print dry run statement
        for func in actions:
            if args.dry_run:
                print(f"{DRY_RUN_PREFIX} {func.func.__name__} {','.join(func.args)}")
            else:
                func()

    if args.yes:
        with rename_context(destination, dry_run=args.dry_run):
            clone_and_remove()
    else:
        clone_and_remove()
    return 0
