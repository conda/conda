# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Common utilities for conda command line tools."""
import re
import sys
from logging import getLogger
from os.path import basename, dirname, isdir, isfile, join, normcase

from ..auxlib.ish import dals
from ..base.constants import ROOT_ENV_NAME
from ..base.context import context, env_name
from ..common.constants import NULL
from ..common.io import swallow_broken_pipe
from ..common.iterators import groupby_to_dict as groupby
from ..common.path import paths_equal
from ..common.serialize import json_dump
from ..core.prefix_data import PrefixData
from ..exceptions import (
    CondaError,
    DirectoryNotACondaEnvironmentError,
    EnvironmentLocationNotFound,
)
from ..history import History
from ..models.enums import PackageType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph


def confirm(message="Proceed", choices=("yes", "no"), default="yes", dry_run=NULL):
    assert default in choices, default
    if (dry_run is NULL and context.dry_run) or dry_run:
        from ..exceptions import DryRunExit

        raise DryRunExit()

    options = []
    for option in choices:
        if option == default:
            options.append("[%s]" % option[0])
        else:
            options.append(option[0])
    message = "{} ({})? ".format(message, "/".join(options))
    choices = {alt: choice for choice in choices for alt in [choice, choice[0]]}
    choices[""] = default
    while True:
        # raw_input has a bug and prints to stderr, not desirable
        sys.stdout.write(message)
        sys.stdout.flush()
        try:
            user_choice = sys.stdin.readline().strip().lower()
        except OSError as e:
            raise CondaError(f"cannot read from stdin: {e}")
        if user_choice not in choices:
            print("Invalid choice: %s" % user_choice)
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return choices[user_choice]


def confirm_yn(message="Proceed", default="yes", dry_run=NULL):
    if (dry_run is NULL and context.dry_run) or dry_run:
        from ..exceptions import DryRunExit

        raise DryRunExit()
    if context.always_yes:
        return True
    try:
        choice = confirm(
            message=message, choices=("yes", "no"), default=default, dry_run=dry_run
        )
    except KeyboardInterrupt:  # pragma: no cover
        from ..exceptions import CondaSystemExit

        raise CondaSystemExit("\nOperation aborted.  Exiting.")
    if choice == "no":
        from ..exceptions import CondaSystemExit

        raise CondaSystemExit("Exiting.")
    return True


def is_active_prefix(prefix: str) -> bool:
    """
    Determines whether the args we pass in are pointing to the active prefix.
    Can be used a validation step to make sure operations are not being
    performed on the active prefix.
    """
    if context.active_prefix is None:
        return False
    return (
        paths_equal(prefix, context.active_prefix)
        # normcasing our prefix check for Windows, for case insensitivity
        or normcase(prefix) == normcase(env_name(context.active_prefix))
    )


def arg2spec(arg, json=False, update=False):
    try:
        spec = MatchSpec(arg)
    except:
        from ..exceptions import CondaValueError

        raise CondaValueError("invalid package specification: %s" % arg)

    name = spec.name
    if not spec._is_simple() and update:
        from ..exceptions import CondaValueError

        raise CondaValueError(
            "version specifications not allowed with 'update'; use\n"
            f"    conda update  {name:<{len(arg)}}  or\n"
            f"    conda install {arg:<{len(name)}}"
        )

    return str(spec)


def specs_from_args(args, json=False):
    return [arg2spec(arg, json=json) for arg in args]


spec_pat = re.compile(
    r"""
    (?P<name>[^=<>!\s]+)                # package name
    \s*                                 # ignore spaces
    (
        (?P<cc>=[^=]+(=[^=]+)?)         # conda constraint
        |
        (?P<pc>(?:[=!]=|[><]=?|~=).+)   # new pip-style constraints
    )?$
    """,
    re.VERBOSE,
)


def strip_comment(line):
    return line.split("#")[0].rstrip()


def spec_from_line(line):
    m = spec_pat.match(strip_comment(line))
    if m is None:
        return None
    name, cc, pc = (m.group("name").lower(), m.group("cc"), m.group("pc"))
    if cc:
        return name + cc.replace("=", " ")
    elif pc:
        if pc.startswith("~= "):
            assert (
                pc.count("~=") == 1
            ), f"Overly complex 'Compatible release' spec not handled {line}"
            assert pc.count("."), f"No '.' in 'Compatible release' version {line}"
            ver = pc.replace("~= ", "")
            ver2 = ".".join(ver.split(".")[:-1]) + ".*"
            return name + " >=" + ver + ",==" + ver2
        else:
            return name + " " + pc.replace(" ", "")
    else:
        return name


def specs_from_url(url, json=False):
    from ..gateways.connection.download import TmpDownload

    explicit = False
    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line == "@EXPLICIT":
                    explicit = True
                if explicit:
                    specs.append(line)
                    continue
                spec = spec_from_line(line)
                if spec is None:
                    from ..exceptions import CondaValueError

                    raise CondaValueError(f"could not parse '{line}' in: {url}")
                specs.append(spec)
        except OSError as e:
            from ..exceptions import CondaFileIOError

            raise CondaFileIOError(path, e)
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def disp_features(features):
    if features:
        return "[%s]" % " ".join(features)
    else:
        return ""


@swallow_broken_pipe
def stdout_json(d):
    getLogger("conda.stdout").info(json_dump(d))


def stdout_json_success(success=True, **kwargs):
    result = {"success": success}
    actions = kwargs.pop("actions", None)
    if actions:
        if "LINK" in actions:
            actions["LINK"] = [prec.dist_fields_dump() for prec in actions["LINK"]]
        if "UNLINK" in actions:
            actions["UNLINK"] = [prec.dist_fields_dump() for prec in actions["UNLINK"]]
        result["actions"] = actions
    result.update(kwargs)
    stdout_json(result)


def print_envs_list(known_conda_prefixes, output=True):
    if output:
        print("# conda environments:")
        print("#")

    def disp_env(prefix):
        fmt = "%-20s  %s  %s"
        active = "*" if prefix == context.active_prefix else " "
        if prefix == context.root_prefix:
            name = ROOT_ENV_NAME
        elif any(
            paths_equal(envs_dir, dirname(prefix)) for envs_dir in context.envs_dirs
        ):
            name = basename(prefix)
        else:
            name = ""
        if output:
            print(fmt % (name, active, prefix))

    for prefix in known_conda_prefixes:
        disp_env(prefix)

    if output:
        print()


def check_non_admin():
    from ..common._os import is_admin

    if not context.non_admin_enabled and not is_admin():
        from ..exceptions import OperationNotAllowed

        raise OperationNotAllowed(
            dals(
                """
            The create, install, update, and remove operations have been disabled
            on your system for non-privileged users.
        """
            )
        )


def validate_prefix(prefix):
    """Verifies the prefix is a valid conda environment.

    :raises EnvironmentLocationNotFound: Non-existent path or not a directory.
    :raises DirectoryNotACondaEnvironmentError: Directory is not a conda environment.
    :returns: Valid prefix.
    :rtype: str
    """
    if isdir(prefix):
        if not isfile(join(prefix, "conda-meta", "history")):
            raise DirectoryNotACondaEnvironmentError(prefix)
    else:
        raise EnvironmentLocationNotFound(prefix)

    return prefix


def from_environment(
    name, prefix, no_builds=False, ignore_channels=False, from_history=False
):
    """
        Get ``Environment`` object from prefix
    Args:
        name: The name of environment
        prefix: The path of prefix
        no_builds: Whether has build requirement
        ignore_channels: whether ignore_channels
        from_history: Whether environment file should be based on explicit specs in history

    Returns:     Environment object
    """
    from ..env.env import Environment

    pd = PrefixData(prefix, pip_interop_enabled=True)
    variables = pd.get_environment_env_vars()

    if from_history:
        history = History(prefix).get_requested_specs_map()
        deps = [str(package) for package in history.values()]
        return Environment(
            name=name,
            dependencies=deps,
            channels=list(context.channels),
            prefix=prefix,
            variables=variables,
        )

    precs = tuple(PrefixGraph(pd.iter_records()).graph)
    grouped_precs = groupby(lambda x: x.package_type, precs)
    conda_precs = sorted(
        (
            *grouped_precs.get(None, ()),
            *grouped_precs.get(PackageType.NOARCH_GENERIC, ()),
            *grouped_precs.get(PackageType.NOARCH_PYTHON, ()),
        ),
        key=lambda x: x.name,
    )

    pip_precs = sorted(
        (
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_WHEEL, ()),
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE, ()),
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE, ()),
        ),
        key=lambda x: x.name,
    )

    if no_builds:
        dependencies = ["=".join((a.name, a.version)) for a in conda_precs]
    else:
        dependencies = ["=".join((a.name, a.version, a.build)) for a in conda_precs]
    if pip_precs:
        dependencies.append({"pip": [f"{a.name}=={a.version}" for a in pip_precs]})

    channels = list(context.channels)
    if not ignore_channels:
        for prec in conda_precs:
            canonical_name = prec.channel.canonical_name
            if canonical_name not in channels:
                channels.insert(0, canonical_name)
    return Environment(
        name=name,
        dependencies=dependencies,
        channels=channels,
        prefix=prefix,
        variables=variables,
    )
