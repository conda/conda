# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda info`.

Display information about current conda installation.
"""

from __future__ import annotations

import os
import re
import sys
from argparse import SUPPRESS, _StoreTrueAction
from logging import getLogger
from os.path import exists, expanduser, isfile, join
from textwrap import wrap
from typing import TYPE_CHECKING, Literal

from ..deprecations import deprecated

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction
    from collections.abc import Iterable
    from typing import Any

    from ..base.context import Context
    from ..models.records import PackageRecord

log = getLogger(__name__)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..common.constants import NULL
    from .helpers import add_parser_json

    summary = "Display information about current conda install."
    description = summary
    epilog = ""

    p = sub_parsers.add_parser(
        "info",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    add_parser_json(p)
    p.add_argument(
        "--offline",
        action="store_true",
        default=NULL,
        help=SUPPRESS,
    )
    p.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all information.",
    )
    p.add_argument(
        "--base",
        action="store_true",
        help="Display base environment path.",
    )
    p.add_argument(
        "-e",
        "--envs",
        action="store_true",
        help="List all known conda environments.",
    )
    p.add_argument(
        "-l",
        "--license",
        action=deprecated.action("25.9", "26.3", _StoreTrueAction),
        help=SUPPRESS,
    )
    p.add_argument(
        "-s",
        "--system",
        action="store_true",
        help="List environment variables.",
    )
    p.add_argument(
        "--root",
        action=deprecated.action(
            "25.9",
            "26.3",
            _StoreTrueAction,
            addendum="Use `--base` instead.",
        ),
        help=SUPPRESS,
        dest="base",
    )
    p.add_argument(
        "--unsafe-channels",
        action="store_true",
        help="Display list of channels with tokens exposed.",
    )

    p.set_defaults(func="conda.cli.main_info.execute")

    return p


def get_user_site() -> list[str]:  # pragma: no cover
    """
    Method used to populate ``site_dirs`` in ``conda info``.

    :returns: List of directories.
    """

    from ..common.compat import on_win

    site_dirs = []
    try:
        if not on_win:
            if exists(expanduser("~/.local/lib")):
                python_re = re.compile(r"python\d\.\d")
                for path in os.listdir(expanduser("~/.local/lib/")):
                    if python_re.match(path):
                        site_dirs.append(f"~/.local/lib/{path}")
        else:
            if "APPDATA" not in os.environ:
                return site_dirs
            APPDATA = os.environ["APPDATA"]
            if exists(join(APPDATA, "Python")):
                site_dirs = [
                    join(APPDATA, "Python", i)
                    for i in os.listdir(join(APPDATA, "PYTHON"))
                ]
    except OSError as e:
        log.debug("Error accessing user site directory.\n%r", e)
    return site_dirs


IGNORE_FIELDS: set[str] = {"files", "auth", "preferred_env", "priority"}

SKIP_FIELDS: set[str] = {
    *IGNORE_FIELDS,
    "name",
    "version",
    "build",
    "build_number",
    "channel",
    "schannel",
    "size",
    "fn",
    "depends",
}


def dump_record(prec: PackageRecord) -> dict[str, Any]:
    """
    Returns a dictionary of key/value pairs from ``prec``.  Keys included in ``IGNORE_FIELDS`` are not returned.

    :param prec: A ``PackageRecord`` object.
    :returns: A dictionary of elements dumped from ``prec``
    """
    return {k: v for k, v in prec.dump().items() if k not in IGNORE_FIELDS}


def pretty_package(prec: PackageRecord) -> None:
    """
    Pretty prints contents of a ``PackageRecord``

    :param prec: A ``PackageRecord``
    """

    from ..utils import human_bytes

    pkg = dump_record(prec)
    d = {
        "file name": prec.fn,
        "name": pkg["name"],
        "version": pkg["version"],
        "build string": pkg["build"],
        "build number": pkg["build_number"],
        "channel": str(prec.channel),
        "size": human_bytes(pkg["size"]),
    }
    for key in sorted(set(pkg.keys()) - SKIP_FIELDS):
        d[key] = pkg[key]

    print()
    header = "{} {} {}".format(d["name"], d["version"], d["build string"])
    print(header)
    print("-" * len(header))
    for key in d:
        print("%-12s: %s" % (key, d[key]))
    print("dependencies:")
    for dep in pkg["depends"]:
        print(f"    {dep}")


def get_info_dict() -> dict[str, Any]:
    """
    Returns a dictionary of contextual information.

    :returns:  Dictionary of conda information to be sent to stdout.
    """

    from .. import CONDA_PACKAGE_ROOT
    from .. import __version__ as conda_version
    from ..base.context import (
        DEFAULT_SOLVER,
        context,
        env_name,
        sys_rc_path,
        user_rc_path,
    )
    from ..common.compat import on_win
    from ..common.url import mask_anaconda_token
    from ..core.index import Index
    from ..models.channel import all_channel_urls, offline_keep

    try:
        from conda_build import __version__ as conda_build_version
    except ImportError as err:
        # ImportError: conda-build is not installed
        log.debug("Unable to import conda-build: %s", err)
        conda_build_version = "not installed"
    except Exception as err:
        log.error("Error importing conda-build: %s", err)
        conda_build_version = "error"

    virtual_pkg_index = Index().system_packages
    virtual_pkgs = [[p.name, p.version, p.build] for p in virtual_pkg_index.values()]

    channels = list(all_channel_urls(context.channels))
    if not context.json:
        channels = [c + ("" if offline_keep(c) else "  (offline)") for c in channels]
    channels = [mask_anaconda_token(c) for c in channels]

    netrc_file = os.environ.get("NETRC")
    if not netrc_file:
        user_netrc = expanduser("~/.netrc")
        if isfile(user_netrc):
            netrc_file = user_netrc

    active_prefix_name = env_name(context.active_prefix)

    solver = {
        "name": context.solver,
        "user_agent": context.solver_user_agent(),
        "default": context.solver == DEFAULT_SOLVER,
    }

    info_dict = dict(
        platform=context.subdir,
        conda_version=conda_version,
        conda_env_version=conda_version,
        conda_build_version=conda_build_version,
        root_prefix=context.root_prefix,
        conda_prefix=context.conda_prefix,
        av_data_dir=context.av_data_dir,
        av_metadata_url_base=context.signing_metadata_url_base,
        root_writable=context.root_writable,
        pkgs_dirs=context.pkgs_dirs,
        envs_dirs=context.envs_dirs,
        default_prefix=context.default_prefix,
        active_prefix=context.active_prefix,
        active_prefix_name=active_prefix_name,
        conda_shlvl=context.shlvl,
        channels=channels,
        user_rc_path=user_rc_path,
        rc_path=user_rc_path,
        sys_rc_path=sys_rc_path,
        # is_foreign=bool(foreign),
        offline=context.offline,
        envs=[],
        python_version=".".join(map(str, sys.version_info)),
        requests_version=context.requests_version,
        user_agent=context.user_agent,
        conda_location=CONDA_PACKAGE_ROOT,
        config_files=context.config_files,
        netrc_file=netrc_file,
        virtual_pkgs=virtual_pkgs,
        solver=solver,
    )
    if on_win:
        from ..common._os.windows import is_admin_on_windows

        info_dict["is_windows_admin"] = is_admin_on_windows()
    else:
        info_dict["UID"] = os.geteuid()
        info_dict["GID"] = os.getegid()

    env_var_keys = {
        "CIO_TEST",
        "CURL_CA_BUNDLE",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
        "LD_PRELOAD",
    }

    # add all relevant env vars, e.g. startswith('CONDA') or endswith('PATH')
    env_var_keys.update(v for v in os.environ if v.upper().startswith("CONDA"))
    env_var_keys.update(v for v in os.environ if v.upper().startswith("PYTHON"))
    env_var_keys.update(v for v in os.environ if v.upper().endswith("PATH"))
    env_var_keys.update(v for v in os.environ if v.upper().startswith("SUDO"))

    env_vars = {
        ev: os.getenv(ev, os.getenv(ev.lower(), "<not set>")) for ev in env_var_keys
    }

    proxy_keys = (v for v in os.environ if v.upper().endswith("PROXY"))
    env_vars.update({ev: "<set>" for ev in proxy_keys})

    info_dict.update(
        {
            "sys.version": sys.version,
            "sys.prefix": sys.prefix,
            "sys.executable": sys.executable,
            "site_dirs": get_user_site(),
            "env_vars": env_vars,
        }
    )

    return info_dict


def get_env_vars_str(info_dict: dict[str, Any]) -> str:
    """
    Returns a printable string representing environment variables from the dictionary returned by ``get_info_dict``.

    :param info_dict:  The returned dictionary from ``get_info_dict()``.
    :returns:  String to print.
    """

    builder = []
    builder.append("%23s:" % "environment variables")
    env_vars = info_dict.get("env_vars", {})
    for key in sorted(env_vars):
        value = wrap(env_vars[key])
        first_line = value[0] if len(value) else ""
        other_lines = value[1:] if len(value) > 1 else ()
        builder.append("%25s=%s" % (key, first_line))
        for val in other_lines:
            builder.append(" " * 26 + val)
    return "\n".join(builder)


def get_main_info_display(info_dict: dict[str, Any]) -> dict[str, str]:
    """
    Returns the data that can be used to display information for conda info
    """
    from ..common.compat import on_win

    def flatten(lines: Iterable[str]) -> str:
        return ("\n" + 26 * " ").join(map(str, lines))

    def builder():
        if info_dict["active_prefix_name"]:
            yield ("active environment", info_dict["active_prefix_name"])
            yield ("active env location", info_dict["active_prefix"])
        else:
            yield ("active environment", info_dict["active_prefix"])

        if info_dict["conda_shlvl"] >= 0:
            yield ("shell level", info_dict["conda_shlvl"])

        yield ("user config file", info_dict["user_rc_path"])
        yield ("populated config files", flatten(info_dict["config_files"]))
        yield ("conda version", info_dict["conda_version"])
        yield ("conda-build version", info_dict["conda_build_version"])
        yield ("python version", info_dict["python_version"])
        yield (
            "solver",
            f"{info_dict['solver']['name']}{' (default)' if info_dict['solver']['default'] else ''}",
        )
        yield (
            "virtual packages",
            flatten("=".join(pkg) for pkg in info_dict["virtual_pkgs"]),
        )
        writable = "writable" if info_dict["root_writable"] else "read only"
        yield ("base environment", f"{info_dict['root_prefix']}  ({writable})")
        yield ("conda av data dir", info_dict["av_data_dir"])
        yield ("conda av metadata url", info_dict["av_metadata_url_base"])
        yield ("channel URLs", flatten(info_dict["channels"]))
        yield ("package cache", flatten(info_dict["pkgs_dirs"]))
        yield ("envs directories", flatten(info_dict["envs_dirs"]))
        yield ("platform", info_dict["platform"])
        yield ("user-agent", info_dict["user_agent"])

        if on_win:
            yield ("administrator", info_dict["is_windows_admin"])
        else:
            yield ("UID:GID", f"{info_dict['UID']}:{info_dict['GID']}")

        yield ("netrc file", info_dict["netrc_file"])
        yield ("offline mode", info_dict["offline"])

    return {key: value for key, value in builder()}


def get_main_info_str(info_dict: dict[str, Any]) -> str:
    """
    Returns a printable string of the contents of ``info_dict``.

    :param info_dict:  The output of ``get_info_dict()``.
    :returns:  String to print.
    """
    display_info = get_main_info_display(info_dict)

    return "\n".join(
        ("", *(f"{key:>23} : {value}" for key, value in display_info.items()), "")
    )


#: Possible components for the info command to render
InfoComponents = Literal["base", "channels", "envs", "system", "detail", "json_all"]


class InfoRenderer:
    """
    Provides a ``render`` method for rendering ``InfoComponents``
    """

    def __init__(self, context):
        from ..core.envs_manager import list_all_known_prefixes

        self._context = context
        self._info_dict = get_info_dict()
        self._info_dict["envs"] = list_all_known_prefixes()
        self._component_style_map = {
            "base": None,
            "channels": None,
            "detail": "detail_view",
            "envs": "envs_list",
            "system": None,
            "json_all": None,
        }

    def render(self, components: Iterable[InfoComponents]):
        """
        Iterates through the registered components, obtains the data to render via a
        ``_<component>_component`` method and then renders it.
        """
        from ..reporters import render

        for component in components:
            style = self._component_style_map.get(component)
            data_func = getattr(self, f"_{component}_component", None)

            if not data_func:
                continue

            data = data_func()

            if data:
                render(data, style=style)

    def _base_component(self) -> str | dict:
        if self._context.json:
            return {"root_prefix": self._context.root_prefix}
        else:
            return f"{self._context.root_prefix}\n"

    def _channels_component(self) -> str | dict:
        if self._context.json:
            return {"channels": self._context.channels}
        else:
            channels_str = "\n".join(self._context.channels)
            return f"{channels_str}\n"

    def _detail_component(self) -> dict[str, str]:
        return get_main_info_display(self._info_dict)

    def _envs_component(self):
        if not self._context.json:
            return self._info_dict["envs"]

    def _system_component(self) -> str:
        from .find_commands import find_commands, find_executable

        output = [
            f"sys.version: {sys.version[:40]}...",
            f"sys.prefix: {sys.prefix}",
            f"sys.executable: {sys.executable}",
            "conda location: {}".format(self._info_dict["conda_location"]),
        ]

        for cmd in sorted(set(find_commands() + ("build",))):
            output.append("conda-{}: {}".format(cmd, find_executable("conda-" + cmd)))

        site_dirs = self._info_dict["site_dirs"]
        if site_dirs:
            output.append(f"user site dirs: {site_dirs[0]}")
        else:
            output.append("user site dirs:")

        for site_dir in site_dirs[1:]:
            output.append(f"                {site_dir}")

        output.append("")

        for name, value in sorted(self._info_dict["env_vars"].items()):
            output.append(f"{name}: {value}")

        output.append("")

        return "\n".join(output)

    def _json_all_component(self) -> dict[str, Any]:
        return self._info_dict


@deprecated(
    "25.9",
    "26.3",
    addendum="Use `conda.cli.main_info.iter_info_components` instead.",
)
def get_info_components(args: Namespace, context: Context) -> set[InfoComponents]:
    return set(iter_info_components(args, context))


def iter_info_components(args: Namespace, context: Context) -> Iterable[InfoComponents]:
    """
    Determine which components to display.

    :param args: The parsed command line arguments.
    :param context: The conda context.
    :returns: An iterable of components to display.
    """
    if args.base:
        yield "base"

    if args.unsafe_channels:
        yield "channels"

    if (
        (args.all or (not args.envs and not args.system))
        and not context.json
        and not args.base
        and not args.unsafe_channels
    ):
        yield "detail"

    if (args.envs or args.all) and not context.json:
        yield "envs"

    if (args.system or args.all) and not context.json:
        yield "system"

    if context.json and not args.base and not args.unsafe_channels:
        yield "json_all"


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """
    Implements ``conda info`` command.

     * ``conda info``
     * ``conda info --base``
     * ``conda info <package_spec> ...``
     * ``conda info --unsafe-channels``
     * ``conda info --envs``
     * ``conda info --system``
    """

    from ..base.context import context

    components = iter_info_components(args, context)
    renderer = InfoRenderer(context)
    renderer.render(components)

    return 0
