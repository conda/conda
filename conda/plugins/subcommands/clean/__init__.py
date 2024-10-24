# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import warnings
from contextlib import nullcontext
from itertools import chain
from logging import getLogger
from typing import TYPE_CHECKING

from ....base.context import context
from ... import hookimpl
from ...types import CondaSubcommand
from .cleanup_tasks import conda_cleanup_tasks

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from pathlib import Path

__all__ = ["conda_cleanup_tasks", "conda_subcommands"]

log = getLogger(__name__)


def configure_parser(parser: ArgumentParser) -> None:
    from ....cli.helpers import add_output_and_prompt_options

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Perform all standard cleanup actions.",
    )
    add_output_and_prompt_options(parser)

    for plugin in context.plugin_manager.get_hook_results("cleanup_tasks"):
        # action defaults to storing true unless overridden by the plugin
        kwargs = {"action": "store_true", **(plugin.add_argument_kwargs or {})}
        parser.add_argument(*plugin.flags, dest=plugin.name, help=plugin.help, **kwargs)


def _print_to_remove(name: str, to_remove: dict[Path | None, tuple[Path, ...]]) -> None:
    from ....gateways.disk.read import get_size
    from ....utils import human_bytes

    if context.verbose:
        # compute
        total_size = 0
        display: dict[Path | None, dict[Path, int]] = {}
        for directory, paths_list in to_remove.items():
            for path in paths_list:
                try:
                    total_size += (size := get_size(path))
                except OSError as e:
                    # OSError: get_size failed
                    warnings.warn(f"{path}: ({e.__class__.__name__}) {e}")
                    size = -1
                relative = path.relative_to(directory) if directory else path
                display.setdefault(directory, {})[relative] = size

        # display after computations to avoid interleaving warnings with printout
        print(f"Removing the following {name}:")
        for directory, paths_map in display.items():
            indent = " " * 2
            if directory:
                print(f"{indent}{directory}:")
                indent = " " * 4

            for path, size in paths_map.items():
                print(f"{indent}- {str(path):<60} {human_bytes(size):>10}")
            print()
        print("-" * 17)
        print(f"Total: {human_bytes(total_size):>10}")
        print()
    else:
        # compute
        count = sum(len(files) for files in to_remove.values())
        total_size = sum(
            get_size(file, error=False)
            for files in to_remove.values()
            for file in files
        )

        # display
        print(f"Removing {count} ({human_bytes(total_size)}) {name}.")


def execute(args: Namespace) -> int:
    from ....cli.common import confirm_ynq
    from ....gateways.disk.delete import rm_rf

    json_result = {}
    with (
        warnings.catch_warnings(record=True)
        if (quiet := context.json or context.quiet)
        else nullcontext()
    ) as warnings_list:
        for name, to_remove in context.plugin_manager.invoke_cleanup_tasks(
            args, all=args.all
        ):
            # flattened modern JSON format
            json_result[name] = files = tuple(chain.from_iterable(to_remove.values()))

            # skip if no files
            if not files:
                continue

            if not quiet:
                _print_to_remove(name, to_remove)

            if context.dry_run:
                continue

            if not context.json:
                if not confirm_ynq():
                    continue

            for file in chain.from_iterable(to_remove.values()):
                try:
                    if not rm_rf(file):
                        warnings.warn(f"cannot remove, file permissions: {file}")
                except OSError as e:
                    warnings.warn(f"cannot remove, file permissions: {file}\n{e!r}")

    if context.json:
        from ....cli.common import stdout_json

        stdout_json({**json_result, "warnings": warnings_list})

    if context.dry_run:
        from ....exceptions import DryRunExit

        raise DryRunExit
    return 0


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="clean",
        summary="Performs various cleanup tasks like removing unused packages and caches.",
        action=execute,
        configure_parser=configure_parser,
    )
