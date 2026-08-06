# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env create`.

Creates new conda environments with the specified packages.
"""

from argparse import (
    ArgumentParser,
    _SubParsersAction,
)


def epilog() -> str:
    """Build ``conda env create`` epilog (examples and plugin-driven format list)."""
    from ..base.context import context
    from .formats import get_available_environment_formats

    # get environment specifiers grouped by format
    formats = context.plugin_manager.get_environment_specifiers_grouped()

    # compose examples/epilog
    examples = [
        "Examples:",
        "  Create from an environment spec (solved at install time):",
        "    conda env create -f /path/to/environment.yml",
        "",
        "  Create from a lockfile (no solve, exact reproduction):",
        "    conda env create -f explicit.txt",
        "",
        "  Use the default file in the current directory:",
        "    conda env create",
        "    conda env create -n envname",
    ]
    # include available formats if any are registered
    if formats:
        examples.append("")
        examples.append("Available input formats:")
        examples.append(get_available_environment_formats(formats, indent=2))
    return "\n".join(examples)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..common.constants import NULL
    from .helpers import (
        add_output_and_prompt_options,
        add_parser_default_packages,
        add_parser_environment_specifier,
        add_parser_networking,
        add_parser_platform,
        add_parser_prefix,
        add_parser_solver,
    )

    summary = "Create an environment based on an environment definition file."
    description = (
        "The file format is detected from the filename or contents. Which "
        "formats are supported depends on the plugins installed in your "
        "environment. See the epilog for the list of formats available here. "
        "\n\n"
        "If the file declares a name in its contents (for instance as the "
        "first line of an environment.yml file), that name is used unless "
        "overridden on the CLI with -n/--name. "
        "\n\n"
        "Unless you are in the directory containing the environment definition "
        "file, use -f to specify the file path of the environment definition "
        "file you want to use."
    )

    p = sub_parsers.add_parser(
        "create",
        help=summary,
        description=summary + "\n\n" + description,
        epilog_factory=epilog,
        **kwargs,
    )
    p.add_argument(
        "-f",
        "--file",
        nargs="*",
        help=(
            "Environment definition file (default: environment.yml). Standard "
            "filenames registered by the installed format plugins are "
            "auto-detected. Custom filenames require --format."
        ),
        default=["environment.yml"],
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

    p.set_defaults(
        func="conda.cli.main_create.execute",
        clone=False,
        override_channels=False,
        use_local=NULL,
        packages=[],
        repodata_fns=None,
        yes=True,
    )
    return p
