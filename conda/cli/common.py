# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Common utilities for conda command line tools."""

import re
import sys
from os.path import isdir, isfile, join, normcase

from ..auxlib.ish import dals
from ..base.context import context, env_name
from ..common.constants import NULL
from ..common.io import swallow_broken_pipe
from ..common.path import paths_equal
from ..deprecations import deprecated
from ..exceptions import (
    CondaError,
    DirectoryNotACondaEnvironmentError,
    EnvironmentLocationNotFound,
)
from ..models.match_spec import MatchSpec
from ..reporters import render


@deprecated(
    "25.3",
    "25.9",
    addendum="Use `conda.reporters.confirm_yn` instead.",
)
def confirm(message="Proceed", choices=("yes", "no"), default="yes", dry_run=NULL):
    assert default in choices, default
    if (dry_run is NULL and context.dry_run) or dry_run:
        from ..exceptions import DryRunExit

        raise DryRunExit()

    options = []
    for option in choices:
        if option == default:
            options.append(f"[{option[0]}]")
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
            print(f"Invalid choice: {user_choice}")
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return choices[user_choice]


@deprecated(
    "25.3",
    "25.9",
    addendum="Use `conda.reporters.confirm_yn` instead.",
)
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

        raise CondaValueError(f"invalid package specification: {arg}")

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
            assert pc.count("~=") == 1, (
                f"Overly complex 'Compatible release' spec not handled {line}"
            )
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
        return "[{}]".format(" ".join(features))
    else:
        return ""


@swallow_broken_pipe
def stdout_json(d):
    render(d)


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


@deprecated(
    "25.3",
    "25.9",
    addendum="Use `conda.reporters.render(style='env_list')` instead.",
)
def print_envs_list(known_conda_prefixes, output=True):
    render(known_conda_prefixes, style="envs_list", output=output)


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
