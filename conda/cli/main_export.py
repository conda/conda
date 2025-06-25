# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda export`.

Dumps specified environment package specifications to the screen.
"""

from argparse import (
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)

from ..common.constants import NULL
from ..exceptions import CondaValueError


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_json, add_parser_prefix

    # Use static help text - plugin manager not initialized during CLI setup
    format_help = (
        "Format for the exported environment (e.g., yaml, json). "
        "If not specified, format will be determined by file extension or default to YAML."
    )

    examples = """
    Examples::

        conda export
        conda export --file FILE_NAME
        conda export --format yaml
        conda export --file environment.yaml

    """

    summary = "Export a given environment"
    description = summary
    epilog = dals(examples)

    p = sub_parsers.add_parser(
        "export",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )

    p.add_argument(
        "-c",
        "--channel",
        action="append",
        help="Additional channel to include in the export",
    )

    p.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not include .condarc channels",
    )
    add_parser_prefix(p)

    p.add_argument(
        "-f",
        "--file",
        default=None,
        required=False,
        help=(
            "File name or path for the exported environment. "
            "Note: This will silently overwrite any existing file "
            "of the same name in the current directory."
        ),
    )

    p.add_argument(
        "--format",
        default=NULL,
        required=False,
        help=format_help,
    )

    p.add_argument(
        "--no-builds",
        default=False,
        action="store_true",
        required=False,
        help="Remove build specification from dependencies",
    )

    p.add_argument(
        "--ignore-channels",
        default=False,
        action="store_true",
        required=False,
        help="Do not include channel names with package names.",
    )
    add_parser_json(p)

    p.add_argument(
        "--from-history",
        default=False,
        action="store_true",
        required=False,
        help="Build environment spec from explicit specs in history",
    )
    p.set_defaults(func="conda.cli.main_export.execute")

    return p


# TODO Make this aware of channels that were used to install packages
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..base.context import context, determine_target_prefix, env_name
    from ..env.env import from_environment
    from ..plugins.manager import get_plugin_manager
    from .common import stdout_json

    prefix = determine_target_prefix(context, args)
    env = from_environment(
        env_name(prefix),
        prefix,
        no_builds=args.no_builds,
        ignore_channels=args.ignore_channels,
        from_history=args.from_history,
    )

    if args.override_channels:
        env.remove_channels()

    if args.channel is not None:
        env.add_channels(args.channel)

    # Determine export format and handle via environment exporter plugins
    plugin_manager = get_plugin_manager()

    target_format = args.format
    environment_exporter = None

    # Try to find exporter by filename first
    if args.file:
        file_exporter = plugin_manager.find_exporter_by_filename(args.file)
        if file_exporter:
            exporter_instance = file_exporter.handler()
            target_format = exporter_instance.format
            environment_exporter = file_exporter

    # If format is still NULL, default to yaml
    if target_format is NULL:
        target_format = "yaml"

    # Find appropriate exporter if we don't already have one
    if not environment_exporter:
        environment_exporter = plugin_manager.find_exporter_by_format(target_format)

    if not environment_exporter:
        # No exporter found for the requested format
        available_formats = plugin_manager.get_available_export_formats()
        raise CondaValueError(
            f"Unknown export format '{target_format}'. "
            f"Available formats: {', '.join(available_formats)}"
        )

    # Export the environment - use JSON format if --json flag without file
    export_format = "json" if (args.json and not args.file) else target_format
    if export_format == "json" and target_format != "json":
        json_exporter = plugin_manager.find_exporter_by_format("json")
        if not json_exporter:
            raise CondaValueError("JSON exporter plugin not available")
        exporter = json_exporter.handler()
    else:
        exporter = environment_exporter.handler()

    exported_content = exporter.export(env, export_format)

    # Output the content
    if args.file:
        with open(args.file, "w") as fp:
            fp.write(exported_content)
        if args.json:
            stdout_json({"success": True, "file": args.file, "format": target_format})
    else:
        print(exported_content, end="")

    return 0
