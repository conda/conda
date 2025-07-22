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
from ..core.prefix_data import PrefixData
from ..exceptions import CondaValueError


def _create_environment_from_prefix(prefix, env_name, args):
    """Create a models.Environment directly from prefix and arguments."""
    from ..base.context import context
    from ..history import History
    from ..models.environment import Environment, EnvironmentConfig
    from ..models.match_spec import MatchSpec

    # Get the current platform with proper subdir format
    platform = context.subdir

    # Get prefix data - always needed for packages and/or variables
    prefix_data = PrefixData(prefix)

    # Build requested packages from installed packages or history
    requested_packages = []

    if args.from_history:
        # Use explicit specs from history
        history = History(prefix)
        spec_map = history.get_requested_specs_map()
        requested_packages = list(spec_map.values())
    else:
        # Read all installed packages from prefix data
        for prefix_record in prefix_data.iter_records():
            # Create MatchSpec from installed package
            if args.no_builds:
                spec_str = f"{prefix_record.name}=={prefix_record.version}"
            else:
                spec_str = f"{prefix_record.name}=={prefix_record.version}={prefix_record.build}"

            if (
                not args.ignore_channels
                and prefix_record.channel
                and prefix_record.channel.name
            ):
                spec_str = f"{prefix_record.channel.name}::{spec_str}"

            requested_packages.append(MatchSpec(spec_str))

    # Build channels list
    channels = []

    # Add explicitly requested channels first
    if args.channel:
        channels.extend(args.channel)

    # Add default channels unless overridden
    if not args.override_channels:
        # Only add defaults that aren't already in the list
        for channel in context.channels:
            if channel not in channels:
                channels.append(channel)

    # Create environment config with channels if present
    config = None
    if channels:
        config = EnvironmentConfig(channels=channels)

    # Extract environment variables from prefix
    variables = prefix_data.get_environment_env_vars()

    # Create models.Environment
    return Environment(
        name=env_name,
        prefix=prefix,
        platform=platform,
        requested_packages=requested_packages,
        variables=variables,
        config=config,
    )


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
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

    def _get_available_export_formats():
        from ..plugins.manager import get_plugin_manager

        plugin_manager = get_plugin_manager()
        formats = []

        for exporter_config in plugin_manager.get_environment_exporters():
            # Add the canonical format name
            formats.append(exporter_config.name)

            # Add any aliases this exporter defines
            exporter_instance = exporter_config.handler()
            formats.extend(exporter_instance.aliases)

        # Return all formats sorted for consistent display
        return sorted(formats)

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
    from ..base.context import context, determine_target_prefix, env_name
    from ..plugins.manager import get_plugin_manager
    from .common import stdout_json

    # Validate export format early before doing expensive environment operations
    plugin_manager = get_plugin_manager()
    available_formats = list(
        exporter.name for exporter in plugin_manager.get_environment_exporters()
    )

    # Early format validation - fail fast if format is unsupported
    target_format = args.format
    environment_exporter = None

    # If explicit format provided, use it and find the appropriate exporter
    if target_format is not NULL:
        environment_exporter = plugin_manager.get_environment_exporter_by_format(
            target_format
        )
        if not environment_exporter:
            raise CondaValueError(
                f"Unknown export format '{target_format}'. "
                f"Available formats: {', '.join(available_formats)}."
            )
    # Otherwise, try to detect format by filename
    elif args.file:
        file_exporter = plugin_manager.detect_environment_exporter(args.file)
        if file_exporter:
            target_format = file_exporter.name
            environment_exporter = file_exporter
        else:
            # No exporter found for filename and no explicit format
            # Get default filenames from all exporters
            default_filenames = []
            for exporter in plugin_manager.get_environment_exporters():
                default_filenames.extend(exporter.default_filenames)

            raise CondaValueError(
                f"Filename '{args.file}' is not recognized. "
                f"Supported filenames: {', '.join(sorted(default_filenames))}. "
                f"Or specify the format explicitly with --format."
            )
    else:
        # No file and no explicit format, default to environment-yaml
        target_format = "environment-yaml"
        environment_exporter = plugin_manager.get_environment_exporter_by_format(
            target_format
        )

    prefix = determine_target_prefix(context, args)

    # Create models.Environment directly
    env = _create_environment_from_prefix(prefix, env_name(prefix), args)

    # Export the environment - use JSON format if --json flag without file
    export_format = (
        "environment-json" if (args.json and not args.file) else target_format
    )
    if export_format == "environment-json" and target_format != "environment-json":
        json_exporter = plugin_manager.get_environment_exporter_by_format(
            "environment-json"
        )
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
