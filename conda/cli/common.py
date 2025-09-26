# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Common utilities for conda command line tools."""

from __future__ import annotations

import re
from logging import getLogger
from os.path import (
    dirname,
    exists,
    isdir,
    isfile,
    join,
    normcase,
)
from typing import TYPE_CHECKING

from ..auxlib.ish import dals
from ..base.constants import (
    CMD_LINE_SOURCE,
    CONFIGURATION_SOURCES,
    ENV_VARS_SOURCE,
    EXPLICIT_MARKER,
    PREFIX_MAGIC_FILE,
)
from ..base.context import context, env_name
from ..common.io import swallow_broken_pipe
from ..common.path import expand, paths_equal
from ..deprecations import deprecated
from ..exceptions import (
    DirectoryNotACondaEnvironmentError,
    EnvironmentFileNotFound,
    EnvironmentFileTypeMismatchError,
    EnvironmentLocationNotFound,
    EnvironmentNotWritableError,
    OperationNotAllowed,
)
from ..gateways.connection.session import CONDA_SESSION_SCHEMES
from ..gateways.disk.test import file_path_is_writable
from ..models.match_spec import MatchSpec
from ..reporters import render

if TYPE_CHECKING:
    from collections.abc import Iterable

log = getLogger(__name__)


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


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `spec = str(MatchSpec(arg))` instead",
)
def arg2spec(arg: str, update: bool = False) -> str:
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


@deprecated.argument("26.3", "26.9", "json")
def specs_from_args(args: Iterable[str]) -> list[str]:
    return [str(MatchSpec(arg)) for arg in args]


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


def strip_comment(line: str) -> str:
    return line.split("#")[0].rstrip()


def spec_from_line(line: str) -> str:
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


@deprecated.argument("26.3", "26.9", "json")
def specs_from_url(url: str) -> list[str]:
    from ..gateways.connection.download import TmpDownload

    explicit = False
    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line == EXPLICIT_MARKER:
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


@deprecated("25.9", "26.3", addendum="Use PrefixData.assert_environment()")
def validate_prefix(prefix) -> str:
    """Verifies the prefix is a valid conda environment.

    :raises EnvironmentLocationNotFound: Non-existent path or not a directory.
    :raises DirectoryNotACondaEnvironmentError: Directory is not a conda environment.
    :returns: Valid prefix.
    :rtype: str
    """
    if isdir(prefix):
        if not isfile(join(prefix, PREFIX_MAGIC_FILE)):
            raise DirectoryNotACondaEnvironmentError(prefix)
    else:
        raise EnvironmentLocationNotFound(prefix)

    return prefix


@deprecated("25.9", "26.3", addendum="Use PrefixData.assert_writable()")
def validate_prefix_is_writable(prefix: str) -> str:
    """Verifies the environment directory is writable by trying to access
    the conda-meta/history file. If this file is not writable then we assume
    the whole prefix is not writable and raise an exception.

    :raises EnvironmentNotWritableError: Conda does not have permission to write to the prefix
    :returns: Valid prefix.
    :rtype: str
    """
    test_path = join(prefix, PREFIX_MAGIC_FILE)
    if isdir(dirname(test_path)) and file_path_is_writable(test_path):
        return prefix
    raise EnvironmentNotWritableError(prefix)


def validate_subdir_config():
    """Validates that the configured subdir is ok. A subdir that is different from
    the native system is only allowed if it comes from the global configuration, or
    from an environment variable.

    :raises OperationNotAllowed: Active environment is not allowed to request
                                 non-native platform packages
    """
    if context.subdir != context._native_subdir():
        # We will only allow a different subdir if it's specified by global
        # configuration, environment variable or command line argument. IOW,
        # prevent a non-base env configured for a non-native subdir from leaking
        # its subdir to a newer env.
        context_sources = context.collect_all()
        if context_sources.get(CMD_LINE_SOURCE, {}).get("subdir") == context.subdir:
            pass  # this is ok
        elif context_sources.get(ENV_VARS_SOURCE, {}).get("subdir") == context.subdir:
            pass  # this is ok too
        # config does not come from envvars or cmd_line, it must be a file
        # that's ok as long as it's a base env or a global file
        elif not paths_equal(context.active_prefix, context.root_prefix):
            # this is only ok as long as it's NOT base environment
            active_env_config = next(
                (
                    config
                    for path, config in context_sources.items()
                    if path not in CONFIGURATION_SOURCES
                    and paths_equal(context.active_prefix, path.parent)
                ),
                {},
            )
            if active_env_config.get("subdir") == context.subdir:
                # In practice this never happens; the subdir info is not even
                # loaded from the active env for conda create :shrug:
                msg = dals(
                    f"""
                    Active environment configuration ({context.active_prefix}) is
                    implicitly requesting a non-native platform ({context.subdir}).
                    Please deactivate first or explicitly request the platform via
                    the --platform=[value] command line flag.
                    """
                )
                raise OperationNotAllowed(msg)


def print_activate(env_name_or_prefix):  # pragma: no cover
    if not context.quiet and not context.json:
        if " " in env_name_or_prefix:
            env_name_or_prefix = f'"{env_name_or_prefix}"'
        message = dals(
            f"""
            #
            # To activate this environment, use
            #
            #     $ conda activate {env_name_or_prefix}
            #
            # To deactivate an active environment, use
            #
            #     $ conda deactivate
            """
        )
        print(message)  # TODO: use logger


def validate_environment_files_consistency(files: list[str]) -> None:
    """Validates that all the provided environment files are of the same format type.

    This function checks if all provided environment files are of the same format type
    using the conda plugin system's environment specifiers. It prevents mixing different
    environment file formats (e.g., YAML, explicit package lists, requirements.txt).

    :raises EnvironmentFileTypeMismatchError: When files with different formats are found
    """
    if not files or len(files) <= 1:
        return  # Nothing to validate if there are 0 or 1 files

    # Get types for all files using the plugin manager
    file_types = {
        file: context.plugin_manager.get_environment_specifier(file).name
        for file in files
    }
    # If there's more than one unique type, raise an error
    if len(set(file_types.values())) > 1:
        raise EnvironmentFileTypeMismatchError(file_types)


def validate_file_exists(filename: str):
    """
    Validate the existence of an environment file.

    This function checks if the given ``filename`` exists as an environment file.
    If the `filename` has a URL scheme supported by ``CONDA_SESSION_SCHEMES``,
    it assumes the file is accessible and returns without further validation.
    Otherwise, it expands the given path and verifies its existence. If the file
    does not exist, an ``EnvironmentFileNotFound`` exception is raised.

    Parameters:
        filename (str): The path or URL of the environment file to validate.

    Raises:
        EnvironmentFileNotFound: If the file does not exist and is not a valid URL.
    """
    url_scheme = filename.split("://", 1)[0]
    if url_scheme == "file":
        filename = expand(filename.split("://", 1)[-1])
    elif url_scheme not in CONDA_SESSION_SCHEMES:
        filename = expand(filename)
    else:
        return

    if not exists(filename):
        raise EnvironmentFileNotFound(filename=filename)
