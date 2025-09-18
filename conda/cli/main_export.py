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
from ..models.environment import Environment
from ..plugins.environment_exporters.environment_yml import (
    ENVIRONMENT_JSON_FORMAT,
    ENVIRONMENT_YAML_FORMAT,
)


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
    # NOTE: This is a different platform option from the one in helpers.py
    # This is because we want to:
    # - Allow users to specify multiple platforms for export
    # - Change the help so that it's clearer that this is for export
    #
    #  The add_parser_platform in helpers.py is used to specify a single platform/subdir
    # for the current environment.  We may want to change the helper.
    p.add_argument(
        "--platform",
        "--subdir",
        action="append",
        dest="export_platforms",
        help="Target platform(s)/subdir(s) for export (e.g., linux-64, osx-64, win-64)",
    )
    p.add_argument(
        "--override-platforms",
        action="store_true",
        help="Override the platforms specified in the condarc",
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
        choices_func=lambda: sorted(
            context.plugin_manager.get_exporter_format_mapping()
        ),
        help=(
            "Format for the exported environment. "
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

    # TODO: Check if platform targets are valid

    # Early format validation - fail fast if format is unsupported
    target_format = args.format
    environment_exporter = None

    # Handle --json flag for backwards compatibility
    # If --json is specified without explicit --format AND no file, use JSON format
    # If both --json and --format are specified, --format takes precedence
    # If --json with file, --json only affects status messages
    if target_format is not NULL:
        # If explicit format provided, use it and find the appropriate exporter
        pass
    elif args.file:
        # Try to detect format by filename
        environment_exporter = context.plugin_manager.detect_environment_exporter(
            args.file
        )
        target_format = environment_exporter.name
    elif args.json:
        # Backwards compatibility: --json without --format and no file means JSON output
        target_format = ENVIRONMENT_JSON_FORMAT
    else:
        # No file and no explicit format, default to environment-yaml
        target_format = ENVIRONMENT_YAML_FORMAT

    # If no exporter was detected, try to get one by format
    if not environment_exporter:
        environment_exporter = (
            context.plugin_manager.get_environment_exporter_by_format(target_format)
        )

    prefix = context.target_prefix

    # Create models.Environment directly
    # TODO: Figure out how to handle source and target platforms.  Do we
    #       we need to specify the source platform and then export to
    #       the target platform?  If so, is this done in the
    #       environment_exporter?
    # target_platforms = context.export_platforms

    env = Environment.from_prefix(
        prefix=prefix,
        name=env_name(prefix),
        platform=context.subdir,
        from_history=args.from_history,
        no_builds=args.no_builds,
        ignore_channels=args.ignore_channels,
        channels=context.channels,
    )

    exported_content = environment_exporter.export(env)

    # Add trailing newline to the exported content
    exported_content = exported_content.rstrip() + "\n"

    # Output the content
    if args.file:
        with open(args.file, "w") as fp:
            fp.write(exported_content)
        if args.json:
            stdout_json({"success": True, "file": args.file, "format": target_format})
    else:
        print(exported_content, end="")

    return 0
