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

from ..auxlib.ish import dals
from ..base.context import context
from ..common.constants import NULL
from ..exceptions import CondaValueError
from ..models.environment import Environment
from ..plugins.environment_exporters.standard import ENVIRONMENT_JSON_FORMAT, ENVIRONMENT_YAML_FORMAT


def _get_available_export_formats() -> tuple[str, ...]:
    """Get a tuple of available export formats."""

    # Get all format names (including aliases) from the plugin manager
    format_mapping = context.plugin_manager.get_exporter_format_mapping()

    # Return all format names sorted for consistent display
    return tuple(sorted(format_mapping.keys()))


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from .helpers import LazyChoicesAction, add_parser_json, add_parser_prefix

    summary = "Export a given environment"
    description = summary
    epilog = dals(
        """
        Examples::

            conda export
            conda export --file FILE_NAME
            conda export --format yaml
            conda export --file environment.yaml
        """
    )

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
        action=LazyChoicesAction,
        choices_func=_get_available_export_formats,
        help=(
            "Format for the exported environment. "
            "Available formats include 'yaml', 'json', 'explicit' (and their full names). "
            "If not specified, format will be determined by file extension or default to YAML."
        ),
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
    from ..base.context import env_name
    from .common import stdout_json

    # Validate export format early before doing expensive environment operations
    available_formats = list(_get_available_export_formats())

    # Early format validation - fail fast if format is unsupported
    target_format = args.format
    environment_exporter = None

    # If explicit format provided, use it and find the appropriate exporter
    if target_format is not NULL:
        environment_exporter = (
            context.plugin_manager.get_environment_exporter_by_format(target_format)
        )
        if not environment_exporter:
            raise CondaValueError(
                f"Unknown export format '{target_format}'. "
                f"Available formats: {', '.join(available_formats)}."
            )
    # Otherwise, try to detect format by filename
    elif args.file:
        file_exporter = context.plugin_manager.detect_environment_exporter(args.file)
        if file_exporter:
            target_format = file_exporter.name
            environment_exporter = file_exporter
        else:
            # No exporter found for filename and no explicit format
            # Get default filenames from all exporters
            default_filenames = []
            for exporter in context.plugin_manager.get_environment_exporters():
                default_filenames.extend(exporter.default_filenames)

            raise CondaValueError(
                f"Filename '{args.file}' is not recognized. "
                f"Supported filenames: {', '.join(sorted(default_filenames))}. "
                f"Or specify the format explicitly with --format."
            )
    else:
        # No file and no explicit format, default to environment-yaml
        target_format = ENVIRONMENT_YAML_FORMAT
        environment_exporter = (
            context.plugin_manager.get_environment_exporter_by_format(target_format)
        )

    prefix = context.target_prefix

    # Create models.Environment directly
    env = Environment.from_prefix(
        prefix=prefix,
        name=env_name(prefix),
        platform=context.subdir,
        from_history=args.from_history,
        no_builds=args.no_builds,
        ignore_channels=args.ignore_channels,
        channels=args.channel,
        override_channels=args.override_channels,
    )

    # Export the environment - use JSON format if --json flag without file
    export_format = (
        ENVIRONMENT_JSON_FORMAT if (args.json and not args.file) else target_format
    )
    if export_format == ENVIRONMENT_JSON_FORMAT and target_format != ENVIRONMENT_JSON_FORMAT:
        json_exporter = context.plugin_manager.get_environment_exporter_by_format(
            ENVIRONMENT_JSON_FORMAT
        )
        if not json_exporter:
            raise CondaValueError("JSON exporter plugin not available")
        exported_content = json_exporter.export(env)
    else:
        # Use the detected or default exporter
        exported_content = environment_exporter.export(env)

    # Output the content
    if args.file:
        with open(args.file, "w") as fp:
            fp.write(exported_content)
        if args.json:
            stdout_json({"success": True, "file": args.file, "format": target_format})
    else:
        print(exported_content, end="")

    return 0
