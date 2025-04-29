# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda solve`.

Solve a conda environment with the specified packages.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from ..notices import notices

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction
    from typing import MutableSet, Any

    from ..models.match_spec import MatchSpec
    from ..models.package_info import PackageRecord
    from ..base.context import Context


log = getLogger(__name__)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from ..common.constants import NULL
    from .helpers import (
        add_parser_channels,
        add_parser_default_packages,
        add_parser_networking,
        add_parser_platform,
        add_parser_solver,
        add_parser_solver_mode,
        add_parser_json,
        add_parser_show_channel_urls,
        _ValidatePackages,
    )

    summary = "Solve a conda environment from a list of specified packages. "
    description = dals(
        f"""
        {summary}

        The packages which make up this solved environment are displayed.
        """
    )
    epilog = dals(
        """
        Examples:

        Solve an environment containing the package 'python'::

            conda solve python

        """
    )
    p = sub_parsers.add_parser(
        "solve",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    channel_options = add_parser_channels(p)
    solver_mode_options = add_parser_solver_mode(p)
    add_parser_networking(p)
    add_parser_default_packages(solver_mode_options)
    add_parser_platform(channel_options)
    add_parser_solver(solver_mode_options)
    output_and_prompt_options = add_parser_json(p)
    add_parser_show_channel_urls(output_and_prompt_options)
    output_and_prompt_options.add_argument(
        "--no-builds",
        default=False,
        action="store_true",
        required=False,
        help="Remove build specification from dependencies",
    )
    output_and_prompt_options.add_argument(
        "--ignore-channels",
        default=False,
        action="store_true",
        required=False,
        help="Do not include channel names with package names.",
    )
    output_and_prompt_options.add_argument(
        "--canonical",
        action="store_true",
        help="Output canonical names of packages only.",
    )
    output_and_prompt_options.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Output explicit, machine-readable requirement strings instead of "
        "human-readable lists of packages. This output may be used by "
        "conda create --file.",
    )
    output_and_prompt_options.add_argument(
        "--explicit",
        action="store_true",
        help="List explicitly conda packages with URL "
        "(output may be used by conda create --file).",
    )
    output_and_prompt_options.add_argument(
        "--reverse",
        action="store_true",
        default=False,
        help="List packages in reverse order.",
    )
    output_and_prompt_options.add_argument(
        "--md5",
        action="store_true",
        help="Add MD5 hashsum when using --explicit.",
    )
    output_and_prompt_options.add_argument(
        "--sha256",
        action="store_true",
        help="Add SHA256 hashsum when using --explicit.",
    )
    output_and_prompt_options.add_argument(
        "--auth",
        action="store_false",
        default=True,
        dest="remove_auth",
        help="In explicit mode, leave authentication details in package URLs. "
        "They are removed by default otherwise.",
    )
    p.add_argument(
        "-f",
        "--file",
        default=[],
        action="append",
        help="Read package versions from the given file. Repeated file "
        "specifications can be passed (e.g. --file=file1 --file=file2).",
    )
    p.add_argument(
        "packages",
        metavar="package_spec",
        action=_ValidatePackages,
        nargs="*",
        help="List of packages to install or update in the conda environment.",
    )
    p.set_defaults(func="conda.cli.main_solve.execute")
    return p


def solve_env_given_specs(
    specs: list[MatchSpec],
    repodata_fns: list[str],
    index_args: dict[str, Any],
    context: Context,
) -> MutableSet[PackageRecord]:
    """Solve an environment given a set of specifications."""

    from ..exceptions import (
        UnsatisfiableError,
        SpecsConfigurationConflictError,
        CondaImportError,
    )
    from .install import Repodatas

    prefix = "/fake/fake/fake"

    for repodata_fn in Repodatas(
        repodata_fns,
        index_args,
        (UnsatisfiableError, SpecsConfigurationConflictError, SystemExit),
    ):
        with repodata_fn as repodata:
            solver_backend = context.plugin_manager.get_cached_solver_backend()
            solver = solver_backend(
                prefix,
                context.channels,
                context.subdirs,
                specs_to_add=specs,
                repodata_fn=repodata,
                command="create",
            )
            try:
                package_records: MutableSet[PackageRecord] = solver.solve_final_state(
                    deps_modifier=context.deps_modifier,
                    update_modifier=context.update_modifier,
                    should_retry_solve=(repodata_fn != repodata_fns[-1]),
                )
            except (UnsatisfiableError, SpecsConfigurationConflictError) as e:
                if not getattr(e, "allow_retry", True):
                    raise e
            except SystemExit as e:
                if not getattr(e, "allow_retry", True):
                    raise e
                if e.args and "could not import" in e.args[0]:
                    raise CondaImportError(str(e))
                raise e
    return package_records


# TODO: combine with .main_list::print_explicit
def print_explicit(
    package_records: MutableSet[PackageRecord],
    add_md5: bool = False,
    remove_auth: bool = True,
    add_sha256: bool = False,
) -> None:
    from .main_list import print_export_header
    from ..base.constants import UNKNOWN_CHANNEL
    from ..base.context import context
    from ..common import url as common_url

    if add_md5 and add_sha256:
        raise ValueError("Only one of add_md5 and add_sha256 can be chosen")
    print_export_header(context.subdir)
    print("@EXPLICIT")
    for package_record in package_records:
        url = package_record.get("url")
        if not url or url.startswith(UNKNOWN_CHANNEL):
            print("# no URL for: {}".format(package_record["fn"]))
            continue
        if remove_auth:
            url = common_url.remove_auth(common_url.split_anaconda_token(url)[0])
        if add_md5 or add_sha256:
            hash_key = "md5" if add_md5 else "sha256"
            hash_value = package_record.get(hash_key)
            print(url + (f"#{hash_value}" if hash_value else ""))
        else:
            print(url)


# TODO: combine with .main_list::list_packages
def list_packages(
    package_records: MutableSet[PackageRecord],
    regex: str | None = None,
    format: str = "human",
    reverse: bool = False,
    show_channel_urls: bool | None = None,
    reload_records: bool = True,
) -> tuple[int, str]:
    from .main_list import get_packages
    from ..base.constants import DEFAULTS_CHANNEL_NAME
    from ..base.context import context
    from .common import disp_features

    res = 0
    packages = []
    for prec in get_packages(package_records, regex) if regex else package_records:
        if format == "canonical":
            packages.append(
                prec.dist_fields_dump() if context.json else prec.dist_str()
            )
            continue
        if format == "export":
            packages.append("=".join((prec.name, prec.version, prec.build)))
            continue
        features = set(prec.get("features") or ())
        disp = "%(name)-25s %(version)-15s %(build)15s" % prec
        disp += f"  {disp_features(features)}"
        schannel = prec.get("schannel")
        show_channel_urls = show_channel_urls or context.show_channel_urls
        if (
            show_channel_urls
            or show_channel_urls is None
            and schannel != DEFAULTS_CHANNEL_NAME
        ):
            disp += f"  {schannel}"
        packages.append(disp)
    if reverse:
        packages = reversed(packages)
    result = []
    if format == "human":
        result = [
            f"# packages in solved environment:",
            "#",
            "# %-23s %-15s %15s  Channel" % ("Name", "Version", "Build"),
        ]
    result.extend(packages)
    return res, result


# TODO: combine with .main_list::print_packages
def print_packages(
    package_records: MutableSet[PackageRecord],
    regex: str | None = None,
    format: str = "human",
    reverse: bool = False,
    piplist: bool = False,
    json: bool = False,
    show_channel_urls: bool | None = None,
) -> int:
    from .main_list import print_export_header
    from ..base.context import context
    from .common import stdout_json

    if not json:
        if format == "export":
            print_export_header(context.subdir)
    exitcode, output = list_packages(
        package_records,
        regex,
        format=format,
        reverse=reverse,
        show_channel_urls=show_channel_urls,
    )
    if context.json:
        stdout_json(output)
    else:
        print("\n".join(map(str, output)))
    return exitcode


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from .common import stdout_json
    from ..exceptions import CondaError
    from ..models.match_spec import MatchSpec
    from . import common
    from .install import get_index_args
    from ..base.context import context, REPODATA_FN

    if args.md5 and args.sha256:
        from ..exceptions import ArgumentError

        raise ArgumentError(
            "Only one of --md5 and --sha256 can be specified at the same time"
        )
    # collect packages provided from the command line
    args_packages = [s.strip("\"'") for s in args.packages]
    if not args.no_default_packages:
        # Override defaults if they are specified at the command line
        names = [MatchSpec(pkg).name for pkg in args_packages]
        for default_package in context.create_default_packages:
            if MatchSpec(default_package).name not in names:
                args_packages.append(default_package)
    # collect specs provided by --file arguments
    specs = []
    if args.file:
        for fpath in args.file:
            try:
                specs.extend(common.specs_from_url(fpath, json=context.json))
            except UnicodeError:
                raise CondaError(
                    "Error reading file, file should be a text file containing"
                    " packages \nconda solve --help for details"
                )
        if "@EXPLICIT" in specs:
            raise CondaError("Explicit (.txt) files are not supported. ")
    specs.extend(common.specs_from_args(args_packages, json=context.json))

    # collect repodata filenames
    repodata_fns = args.repodata_fns
    if not repodata_fns:
        repodata_fns = context.repodata_fns
    if REPODATA_FN not in repodata_fns:
        repodata_fns.append(REPODATA_FN)

    index_args = get_index_args(args)

    if args.explicit:
        # disable solver output for explicit
        context.json = True

    package_records = solve_env_given_specs(specs, repodata_fns, index_args, context)

    if args.explicit:
        print_explicit(package_records, args.md5, args.remove_auth, args.sha256)
        return 0

    if args.json:
        # handle this case within this function to output the full PackageRecord data
        stdout_json([prec.dump() for prec in package_records])
        return 0

    if args.canonical:
        format = "canonical"
    elif args.export:
        format = "export"
    else:
        format = "human"

    return print_packages(
        package_records,
        regex=None,
        format=format,
        reverse=args.reverse,
        piplist=False,
        json=False,
        show_channel_urls=context.show_channel_urls,
    )
