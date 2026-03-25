# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
from logging import getLogger
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda import CondaError, plugins
from conda.activate import (
    CmdExeActivator,
    CshActivator,
    FishActivator,
    PosixActivator,
    PowerShellActivator,
    XonshActivator,
    _build_activator_cls,
    activator_map,
)
from conda.base.constants import (
    CONDA_ENV_VARS_UNSET_VAR,
    PACKAGE_ENV_VARS_DIR,
    PREFIX_STATE_FILE,
    ROOT_ENV_NAME,
)
from conda.base.context import context, reset_context
from conda.cli.main import main_sourced
from conda.common.compat import on_win
from conda.common.path.windows import win_path_to_unix
from conda.exceptions import (
    ArgumentError,
    EnvironmentLocationNotFound,
    EnvironmentNameNotFound,
)
from conda.gateways.disk.delete import rm_rf
from conda.plugins.types import CondaPostCommand, CondaPreCommand

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.activate import _Activator
    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import TmpEnvFixture


log = getLogger(__name__)

# a unique prompt (makes it easy to know that our values are showing up correctly)
DEFAULT_PROMPT = " >>(testing)>> "

# a unique context.env_prompt (makes it easy to know that our values are showing up correctly)
DEFAULT_ENV_PROMPT = "-- ==({default_env})== --"

# unique environment variables to set via packages and state files
PKG_A_ENV = "pkg_a-" + uuid4().hex
PKG_B_ENV = "pkg_b-" + uuid4().hex
ENV_ONE = "one-" + uuid4().hex
ENV_TWO = "two-" + uuid4().hex
ENV_THREE = "three-" + uuid4().hex
ENV_WITH_SAME_VALUE = "with_same_value-" + uuid4().hex
ENV_FOUR = "four-" + uuid4().hex
ENV_FIVE = "five-" + uuid4().hex


skip_unsupported_posix_path = pytest.mark.skipif(
    on_win,
    reason=(
        "You are using Windows. These tests involve setting PATH to POSIX values\n"
        "but our Python is a Windows program and Windows doesn't understand POSIX values."
    ),
)


def get_prompt_modifier(default_env: str | os.PathLike | Path) -> str:
    return DEFAULT_ENV_PROMPT.format(default_env=default_env)


def get_prompt(default_env: str | os.PathLike | Path | None = None) -> str:
    if not default_env:
        return DEFAULT_PROMPT
    return get_prompt_modifier(default_env) + DEFAULT_PROMPT


@pytest.fixture(autouse=True)
def reset_environ(monkeypatch: MonkeyPatch) -> None:
    for name in (
        "CONDA_SHLVL",
        "CONDA_DEFAULT_ENV",
        "CONDA_PREFIX",
        "CONDA_PREFIX_0",
        "CONDA_PREFIX_1",
        "CONDA_PREFIX_2",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("PS1", DEFAULT_PROMPT)
    monkeypatch.setenv("prompt", DEFAULT_PROMPT)

    monkeypatch.setenv("CONDA_CHANGEPS1", "true")
    monkeypatch.setenv("CONDA_ENV_PROMPT", DEFAULT_ENV_PROMPT)
    reset_context()
    assert context.changeps1


def write_pkg_A(prefix: str | os.PathLike | Path) -> None:
    activate_pkg_env_vars = Path(prefix, PACKAGE_ENV_VARS_DIR)
    activate_pkg_env_vars.mkdir(exist_ok=True)
    (activate_pkg_env_vars / "pkg_a.json").write_text(
        json.dumps({"PKG_A_ENV": PKG_A_ENV})
    )


def write_pkg_B(prefix: str | os.PathLike | Path) -> None:
    activate_pkg_env_vars = Path(prefix, PACKAGE_ENV_VARS_DIR)
    activate_pkg_env_vars.mkdir(exist_ok=True)
    (activate_pkg_env_vars / "pkg_b.json").write_text(
        json.dumps({"PKG_B_ENV": PKG_B_ENV})
    )


def write_pkgs(prefix: str | os.PathLike | Path) -> None:
    write_pkg_A(prefix)
    write_pkg_B(prefix)


def write_state_file(
    prefix: str | os.PathLike | Path,
    **envvars,
) -> None:
    Path(prefix, PREFIX_STATE_FILE).write_text(
        json.dumps(
            {
                "version": 1,
                "env_vars": (
                    envvars
                    or {
                        "ENV_ONE": ENV_ONE,
                        "ENV_TWO": ENV_TWO,
                        "ENV_THREE": ENV_THREE,
                        "ENV_WITH_SAME_VALUE": ENV_WITH_SAME_VALUE,
                    }
                ),
            }
        )
    )


@pytest.fixture
def env_activate(tmp_env: TmpEnvFixture) -> tuple[str, str, str]:
    with tmp_env() as prefix:
        activate_d = prefix / "etc" / "conda" / "activate.d"
        activate_d.mkdir(parents=True)

        activate_sh = activate_d / "activate.sh"
        activate_sh.touch()

        activate_bat = activate_d / "activate.bat"
        activate_bat.touch()

        return str(prefix), str(activate_sh), str(activate_bat)


@pytest.fixture
def env_activate_deactivate(tmp_env: TmpEnvFixture) -> tuple[str, str, str, str, str]:
    with tmp_env() as prefix:
        activate_d = prefix / "etc" / "conda" / "activate.d"
        activate_d.mkdir(parents=True)

        activate_sh = activate_d / "activate.sh"
        activate_sh.touch()

        activate_bat = activate_d / "activate.bat"
        activate_bat.touch()

        deactivate_d = prefix / "etc" / "conda" / "deactivate.d"
        deactivate_d.mkdir(parents=True)

        deactivate_sh = deactivate_d / "deactivate.sh"
        deactivate_sh.touch()

        deactivate_bat = deactivate_d / "deactivate.bat"
        deactivate_bat.touch()

        return (
            str(prefix),
            str(activate_sh),
            str(activate_bat),
            str(deactivate_sh),
            str(deactivate_bat),
        )


@pytest.fixture
def env_deactivate(tmp_env: TmpEnvFixture) -> tuple[str, str, str]:
    with tmp_env() as prefix:
        deactivate_d = prefix / "etc" / "conda" / "deactivate.d"
        deactivate_d.mkdir(parents=True)

        deactivate_sh = deactivate_d / "deactivate.sh"
        deactivate_sh.touch()

        deactivate_bat = deactivate_d / "deactivate.bat"
        deactivate_bat.touch()

        return str(prefix), str(deactivate_sh), str(deactivate_bat)


def get_scripts_export_unset_vars(
    activator: _Activator,
    **kwargs: str,
) -> tuple[str, str]:
    export_vars, unset_vars = activator.get_export_unset_vars(**kwargs)
    return (
        activator.command_join.join(
            activator.export_var_tmpl % (k, v) for k, v in (export_vars or {}).items()
        ),
        activator.command_join.join(
            activator.unset_var_tmpl % (k) for k in (unset_vars or [])
        ),
    )


@pytest.mark.parametrize("envvars_force_uppercase", [True, False])
def test_get_export_unset_vars(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    envvars_force_uppercase: bool,
) -> None:
    vars_dict = {"conda_lower": "value", "CONDA_UPPER": "value"}
    kwargs = {"lower": "value", "UPPER": "value"}

    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", str(envvars_force_uppercase))
    reset_context()
    assert context.envvars_force_uppercase == envvars_force_uppercase
    mocker.patch(
        "conda.base.context.Context.conda_exe_vars_dict",
        new_callable=mocker.PropertyMock,
        return_value=vars_dict,
    )

    case = str.upper if envvars_force_uppercase else str
    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        export_metavars=True,
        **kwargs,
    )
    assert set(export_vars) == {*map(case, vars_dict), *map(case, kwargs)}
    assert not unset_vars

    export_vars, unset_vars = activator.get_export_unset_vars(
        export_metavars=False,
        **kwargs,
    )
    assert set(export_vars) == set(map(case, kwargs))
    assert set(unset_vars) == set(map(case, vars_dict))


def test_activate_environment_not_found(tmp_path: Path):
    activator = PosixActivator()

    with pytest.raises(EnvironmentLocationNotFound):
        activator.build_activate(str(tmp_path))

    with pytest.raises(EnvironmentLocationNotFound):
        activator.build_activate("/not/an/environment")

    with pytest.raises(EnvironmentNameNotFound):
        activator.build_activate("wontfindmeIdontexist_abc123")


def test_PS1(tmp_path: Path):
    conda_prompt_modifier = get_prompt_modifier(ROOT_ENV_NAME)
    activator = PosixActivator()
    assert activator._prompt_modifier(tmp_path, ROOT_ENV_NAME) == conda_prompt_modifier

    instructions = activator.build_activate("base")
    assert instructions["export_vars"]["CONDA_PROMPT_MODIFIER"] == conda_prompt_modifier


def test_PS1_no_changeps1(monkeypatch: MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CONDA_CHANGEPS1", "false")
    reset_context()
    assert not context.changeps1

    activator = PosixActivator()
    assert activator._prompt_modifier(tmp_path, "root") == ""

    instructions = activator.build_activate("base")
    assert instructions["export_vars"]["CONDA_PROMPT_MODIFIER"] == ""


@pytest.mark.skipif(
    on_win and "PWD" not in os.environ,
    reason="This test cannot be run from the cmd.exe shell.",
)
def test_add_prefix_to_path_posix():
    activator = PosixActivator()

    path_dirs = activator.path_conversion(
        ["/path1/bin", "/path2/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    )
    assert len(path_dirs) == 5
    test_prefix = "/usr/mytest/prefix"
    added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))

    new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
    condabin_dir = activator.path_conversion(
        os.path.join(context.conda_prefix, "condabin")
    )
    assert new_path == (*added_paths, condabin_dir, *path_dirs)


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_add_prefix_to_path_cmdexe():
    activator = CmdExeActivator()

    path_dirs = activator.path_conversion(
        ["C:\\path1", "C:\\Program Files\\Git\\cmd", "C:\\WINDOWS\\system32"]
    )
    assert len(path_dirs) == 3
    test_prefix = "/usr/mytest/prefix"
    added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))

    new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
    assert new_path[: len(added_paths)] == added_paths
    assert new_path[-len(path_dirs) :] == path_dirs
    assert len(new_path) == len(added_paths) + len(path_dirs) + 1
    assert new_path[len(added_paths)].endswith("condabin")


def test_remove_prefix_from_path_1():
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path, *original_path)
    final_path = activator.path_conversion(final_path)

    test_prefix = join(os.getcwd(), "mytestpath")
    new_paths = tuple(activator._get_path_dirs(test_prefix))
    prefix_added_path = (keep_path, *new_paths, *original_path)
    new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)
    assert final_path == new_path


def test_remove_prefix_from_path_2():
    # this time prefix doesn't actually exist in path
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path, *original_path)
    final_path = activator.path_conversion(final_path)

    test_prefix = join(os.getcwd(), "mytestpath")
    prefix_added_path = (keep_path, *original_path)
    new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)

    assert final_path == new_path


def test_replace_prefix_in_path_1():
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    new_prefix = join(os.getcwd(), "mytestpath-new")
    new_paths = activator.path_conversion(activator._get_path_dirs(new_prefix))
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path, *new_paths, *original_path)
    final_path = activator.path_conversion(final_path)

    replace_prefix = join(os.getcwd(), "mytestpath")
    replace_paths = tuple(activator._get_path_dirs(replace_prefix))
    prefix_added_path = (keep_path, *replace_paths, *original_path)
    new_path = activator._replace_prefix_in_path(
        replace_prefix, new_prefix, prefix_added_path
    )

    assert final_path == new_path


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_replace_prefix_in_path_2(monkeypatch: MonkeyPatch):
    path1 = join("c:\\", "temp", "6663 31e0")
    path2 = join("c:\\", "temp", "6663 31e0", "envs", "charizard")
    one_more = join("d:\\", "one", "more")
    #   old_prefix: c:\users\builder\appdata\local\temp\6663 31e0
    #   new_prefix: c:\users\builder\appdata\local\temp\6663 31e0\envs\charizard
    activator = CmdExeActivator()
    old_path = activator.pathsep_join(activator._add_prefix_to_path(path1))
    old_path = one_more + ";" + old_path

    monkeypatch.setenv("PATH", old_path)
    activator = PosixActivator()
    path_elements = activator._replace_prefix_in_path(path1, path2)

    assert path_elements[0] == win_path_to_unix(one_more)
    assert path_elements[1] == win_path_to_unix(next(activator._get_path_dirs(path2)))
    assert len(path_elements) == len(old_path.split(";"))


def test_default_env(tmp_path: Path):
    activator = PosixActivator()
    assert ROOT_ENV_NAME == activator._default_env(context.root_prefix)

    assert str(tmp_path) == activator._default_env(str(tmp_path))

    (prefix := tmp_path / "envs" / "named-env").mkdir(parents=True)
    assert "named-env" == activator._default_env(str(prefix))


def test_build_activate_dont_use_PATH(
    env_activate: tuple[str, str, str],
):
    prefix, activate_sh, _ = env_activate

    write_state_file(
        prefix,
        PATH="something",
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=CONDA_ENV_VARS_UNSET_VAR,
    )

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=activator.pathsep_join(activator._add_prefix_to_path(prefix)),
        CONDA_PREFIX=prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(prefix),
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


def test_build_deactivate_dont_use_PATH(
    env_activate: tuple[str, str, str],
    monkeypatch: MonkeyPatch,
):
    prefix, activate_sh, _ = env_activate

    write_state_file(
        prefix,
        PATH="something",
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=CONDA_ENV_VARS_UNSET_VAR,
    )

    activator = PosixActivator()
    # Ensure that deactivating does not clobber PATH
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("CONDA_SHLVL", 1)

    deactivate = activator.build_deactivate()
    assert "PATH" not in deactivate["unset_vars"]


def test_build_activate_dont_activate_unset_var(env_activate: tuple[str, str, str]):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(
        prefix,
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=CONDA_ENV_VARS_UNSET_VAR,
    )

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=activator.pathsep_join(activator._add_prefix_to_path(prefix)),
        CONDA_PREFIX=prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(prefix),
        # write_pkgs
        PKG_A_ENV=PKG_A_ENV,
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


def test_build_activate_shlvl_warn_clobber_vars(env_activate: tuple[str, str, str]):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(
        prefix,
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        PKG_A_ENV=(overwrite_a := "overwrite_a"),
    )

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=activator.pathsep_join(activator._add_prefix_to_path(prefix)),
        CONDA_PREFIX=prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(prefix),
        # write_pkgs
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        PKG_A_ENV=overwrite_a,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


def test_build_activate_shlvl_0(env_activate: tuple[str, str, str]):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(prefix)

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=activator.pathsep_join(activator._add_prefix_to_path(prefix)),
        CONDA_PREFIX=prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(prefix),
        # write_pkgs
        PKG_A_ENV=PKG_A_ENV,
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        ENV_WITH_SAME_VALUE=ENV_WITH_SAME_VALUE,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


@skip_unsupported_posix_path
def test_build_activate_shlvl_1(
    monkeypatch: MonkeyPatch,
    env_activate: tuple[str, str, str],
):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(prefix)

    activator = PosixActivator()

    old_prefix = "/old/prefix"
    old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("CONDA_PREFIX", old_prefix)
    monkeypatch.setenv("PATH", old_path)

    new_path = activator.pathsep_join(
        activator._replace_prefix_in_path(old_prefix, prefix)
    )
    assert activator.path_conversion(prefix) in new_path
    assert old_prefix not in new_path

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=new_path,
        CONDA_PREFIX=prefix,
        CONDA_PREFIX_1=old_prefix,
        CONDA_SHLVL=2,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=(conda_prompt_modifier := get_prompt_modifier(prefix)),
        # write_pkgs
        PKG_A_ENV=PKG_A_ENV,
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        ENV_WITH_SAME_VALUE=ENV_WITH_SAME_VALUE,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }

    monkeypatch.setenv("PATH", new_path)
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("CONDA_PREFIX_1", old_prefix)
    monkeypatch.setenv("CONDA_SHLVL", 2)
    monkeypatch.setenv("CONDA_DEFAULT_ENV", prefix)
    monkeypatch.setenv("CONDA_PROMPT_MODIFIER", conda_prompt_modifier)
    # write_pkgs
    monkeypatch.setenv("PKG_A_ENV", PKG_A_ENV)
    monkeypatch.setenv("PKG_B_ENV", PKG_B_ENV)
    # write_state_file
    monkeypatch.setenv("ENV_ONE", ENV_ONE)
    monkeypatch.setenv("ENV_TWO", ENV_TWO)
    monkeypatch.setenv("ENV_THREE", ENV_THREE)
    monkeypatch.setenv("ENV_WITH_SAME_VALUE", ENV_WITH_SAME_VALUE)

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=old_prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=old_prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(old_prefix),
        CONDA_PREFIX_1=None,
        # write_pkgs
        PKG_A_ENV=None,
        PKG_B_ENV=None,
        # write_state_file
        ENV_ONE=None,
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {"PATH": old_path},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(old_prefix)},
        "export_vars": export_vars,
        "activate_scripts": (),
    }


@skip_unsupported_posix_path
def test_build_stack_shlvl_1(
    monkeypatch: MonkeyPatch,
    env_activate: tuple[str, str, str],
):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(prefix)

    activator = PosixActivator()

    old_prefix = "/old/prefix"
    old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("CONDA_PREFIX", old_prefix)
    monkeypatch.setenv("PATH", old_path)

    new_path = activator.pathsep_join(activator._add_prefix_to_path(prefix))
    assert prefix in new_path
    assert old_prefix in new_path

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=new_path,
        CONDA_PREFIX=prefix,
        CONDA_PREFIX_1=old_prefix,
        CONDA_SHLVL=2,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=(conda_prompt_modifier := get_prompt_modifier(prefix)),
        CONDA_STACKED_2="true",
        # write_pkgs
        PKG_A_ENV=PKG_A_ENV,
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        ENV_WITH_SAME_VALUE=ENV_WITH_SAME_VALUE,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    stack = activator.build_stack(prefix)
    stack["unset_vars"].sort()
    assert stack == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }

    monkeypatch.setenv("PATH", new_path)
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("CONDA_PREFIX_1", old_prefix)
    monkeypatch.setenv("CONDA_SHLVL", 2)
    monkeypatch.setenv("CONDA_DEFAULT_ENV", prefix)
    monkeypatch.setenv("CONDA_PROMPT_MODIFIER", conda_prompt_modifier)
    monkeypatch.setenv("CONDA_STACKED_2", "true")
    # write_pkgs
    monkeypatch.setenv("PKG_A_ENV", PKG_A_ENV)
    monkeypatch.setenv("PKG_B_ENV", PKG_B_ENV)
    # write_state_file
    monkeypatch.setenv("ENV_ONE", ENV_ONE)
    monkeypatch.setenv("ENV_TWO", ENV_TWO)
    monkeypatch.setenv("ENV_THREE", ENV_THREE)

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=old_prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=old_prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(old_prefix),
        CONDA_PREFIX_1=None,
        CONDA_STACKED_2=None,
        # write_pkgs
        PKG_A_ENV=None,
        PKG_B_ENV=None,
        # write_state_file
        ENV_ONE=None,
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {"PATH": old_path},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(old_prefix)},
        "export_vars": export_vars,
        "activate_scripts": (),
    }


def test_activate_same_environment(
    monkeypatch: MonkeyPatch,
    env_activate_deactivate: tuple[str, str, str, str, str],
):
    prefix, activate_sh, _, deactivate_sh, _ = env_activate_deactivate

    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("CONDA_PREFIX", prefix)

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=activator.pathsep_join(activator._replace_prefix_in_path(prefix, prefix)),
        CONDA_SHLVL=1,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(prefix),
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": activator.path_conversion([deactivate_sh]),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


@skip_unsupported_posix_path
def test_build_deactivate_shlvl_2_from_stack(
    monkeypatch: MonkeyPatch,
    env_activate: tuple[str, str, str],
    env_deactivate: tuple[str, str, str],
):
    old_prefix, activate_sh, _ = env_activate

    write_pkg_B(old_prefix)
    write_state_file(
        old_prefix,
        ENV_FOUR=ENV_FOUR,
        ENV_FIVE=ENV_FIVE,
    )

    prefix, deactivate_sh, _ = env_deactivate

    write_pkg_A(prefix)
    write_state_file(prefix)

    activator = PosixActivator()
    original_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

    monkeypatch.setenv("PATH", original_path)

    starting_path = activator.pathsep_join(activator._add_prefix_to_path(prefix))

    monkeypatch.setenv("CONDA_SHLVL", "2")
    monkeypatch.setenv("CONDA_PREFIX_1", old_prefix)
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("CONDA_STACKED_2", "true")
    monkeypatch.setenv("PATH", starting_path)
    # write_pkg_B (old_prefix)
    monkeypatch.setenv("PKG_B_ENV", PKG_B_ENV)
    # write_state_file (old_prefix)
    monkeypatch.setenv("ENV_FOUR", ENV_FOUR)
    monkeypatch.setenv("ENV_FIVE", ENV_FIVE)
    # write_pkg_A (prefix)
    monkeypatch.setenv("PKG_A_ENV", PKG_A_ENV)
    # write_state_file (prefix)
    monkeypatch.setenv("ENV_ONE", ENV_ONE)
    monkeypatch.setenv("ENV_TWO", ENV_TWO)
    monkeypatch.setenv("ENV_THREE", ENV_THREE)
    monkeypatch.setenv("ENV_WITH_SAME_VALUE", ENV_WITH_SAME_VALUE)

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=old_prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=old_prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(old_prefix),
        CONDA_PREFIX_1=None,
        CONDA_STACKED_2=None,
        # write_pkg_B (old_prefix)
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file (old_prefix)
        ENV_FOUR=ENV_FOUR,
        ENV_FIVE=ENV_FIVE,
        # write_pkg_A (prefix)
        PKG_A_ENV=None,
        # write_state_file (prefix)
        ENV_ONE=None,
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {"PATH": original_path},
        "deactivate_scripts": activator.path_conversion([deactivate_sh]),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(old_prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


@skip_unsupported_posix_path
def test_build_deactivate_shlvl_2_from_activate(
    monkeypatch: MonkeyPatch,
    env_activate: tuple[str, str, str],
    env_deactivate: tuple[str, str, str],
):
    old_prefix, activate_sh, _ = env_activate

    write_pkg_B(old_prefix)
    write_state_file(
        old_prefix,
        ENV_FOUR=ENV_FOUR,
        ENV_FIVE=ENV_FIVE,
    )

    prefix, deactivate_sh, _ = env_deactivate

    write_pkg_A(prefix)
    write_state_file(prefix)

    activator = PosixActivator()

    original_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))
    new_path = activator.pathsep_join(activator._add_prefix_to_path(prefix))

    monkeypatch.setenv("CONDA_SHLVL", "2")
    monkeypatch.setenv("CONDA_PREFIX_1", old_prefix)
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("PATH", new_path)
    # write_pkg_A (prefix)
    monkeypatch.setenv("PKG_A_ENV", PKG_A_ENV)
    # write_state_file (prefix)
    monkeypatch.setenv("ENV_ONE", ENV_ONE)
    monkeypatch.setenv("ENV_TWO", ENV_TWO)
    monkeypatch.setenv("ENV_THREE", ENV_THREE)
    monkeypatch.setenv("ENV_WITH_SAME_VALUE", ENV_WITH_SAME_VALUE)

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=old_prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=old_prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(old_prefix),
        CONDA_PREFIX_1=None,
        # write_pkg_B (old_prefix)
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file (old_prefix)
        ENV_FOUR=ENV_FOUR,
        ENV_FIVE=ENV_FIVE,
        # write_pkg_A (prefix)
        PKG_A_ENV=None,
        # write_state_file (prefix)
        ENV_ONE=None,
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {"PATH": original_path},
        "deactivate_scripts": activator.path_conversion([deactivate_sh]),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(old_prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }


def test_build_deactivate_shlvl_1(
    monkeypatch: MonkeyPatch,
    env_deactivate: tuple[str, str, str],
):
    prefix, deactivate_sh, _ = env_deactivate

    write_pkgs(prefix)
    write_state_file(prefix)

    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("CONDA_PREFIX", prefix)

    activator = PosixActivator()

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_SHLVL=0,
        CONDA_PREFIX=None,
        CONDA_DEFAULT_ENV=None,
        CONDA_PROMPT_MODIFIER=None,
        # write_pkgs
        PKG_A_ENV=None,
        PKG_B_ENV=None,
        # write_state_file
        ENV_ONE=None,
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {
            "PATH": activator.pathsep_join(
                activator.path_conversion(activator._get_starting_path_list())
            )
        },
        "deactivate_scripts": activator.path_conversion([deactivate_sh]),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt()},
        "export_vars": export_vars,
        "activate_scripts": (),
    }


def test_get_env_vars_big_whitespace(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        write_state_file(prefix)

        activator = PosixActivator()
        env_vars = activator._get_environment_env_vars(prefix)
        assert env_vars == {
            "ENV_ONE": ENV_ONE,
            "ENV_TWO": ENV_TWO,
            "ENV_THREE": ENV_THREE,
            "ENV_WITH_SAME_VALUE": ENV_WITH_SAME_VALUE,
        }


def test_get_env_vars_empty_file(tmp_env: TmpEnvFixture):
    with tmp_env() as prefix:
        (prefix / "conda-meta" / "env_vars").touch()

        activator = PosixActivator()
        env_vars = activator._get_environment_env_vars(prefix)
        assert env_vars == {}


@skip_unsupported_posix_path
def test_build_activate_restore_unset_env_vars(
    monkeypatch: MonkeyPatch,
    env_activate: tuple[str, str, str],
):
    prefix, activate_sh, _ = env_activate

    write_pkgs(prefix)
    write_state_file(prefix)

    activator = PosixActivator()

    old_prefix = "/old/prefix"
    old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("CONDA_PREFIX", old_prefix)
    monkeypatch.setenv("PATH", old_path)
    monkeypatch.setenv("ENV_ONE", "already_set_env_var")
    monkeypatch.setenv("ENV_WITH_SAME_VALUE", ENV_WITH_SAME_VALUE)

    new_path = activator.pathsep_join(
        activator._replace_prefix_in_path(old_prefix, prefix)
    )
    assert activator.path_conversion(prefix) in new_path
    assert old_prefix not in new_path

    export_vars, unset_vars = activator.get_export_unset_vars(
        PATH=new_path,
        CONDA_PREFIX=prefix,
        CONDA_PREFIX_1=old_prefix,
        CONDA_SHLVL=2,
        CONDA_DEFAULT_ENV=prefix,
        CONDA_PROMPT_MODIFIER=(conda_prompt_modifier := get_prompt_modifier(prefix)),
        __CONDA_SHLVL_1_ENV_ONE="already_set_env_var",
        __CONDA_SHLVL_1_ENV_WITH_SAME_VALUE=ENV_WITH_SAME_VALUE,
        # write_pkgs
        PKG_A_ENV=PKG_A_ENV,
        PKG_B_ENV=PKG_B_ENV,
        # write_state_file
        ENV_ONE=ENV_ONE,
        ENV_TWO=ENV_TWO,
        ENV_THREE=ENV_THREE,
        ENV_WITH_SAME_VALUE=ENV_WITH_SAME_VALUE,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    activate = activator.build_activate(prefix)
    activate["unset_vars"].sort()
    assert activate == {
        # "export_path": {},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(prefix)},
        "export_vars": export_vars,
        "activate_scripts": activator.path_conversion([activate_sh]),
    }

    monkeypatch.setenv("PATH", new_path)
    monkeypatch.setenv("CONDA_PREFIX", prefix)
    monkeypatch.setenv("CONDA_PREFIX_1", old_prefix)
    monkeypatch.setenv("CONDA_SHLVL", 2)
    monkeypatch.setenv("CONDA_DEFAULT_ENV", prefix)
    monkeypatch.setenv("CONDA_PROMPT_MODIFIER", conda_prompt_modifier)
    monkeypatch.setenv("__CONDA_SHLVL_1_ENV_ONE", "already_set_env_var")
    # write_pkgs
    monkeypatch.setenv("PKG_A_ENV", PKG_A_ENV)
    monkeypatch.setenv("PKG_B_ENV", PKG_B_ENV)
    # write_state_file
    monkeypatch.setenv("ENV_ONE", ENV_ONE)
    monkeypatch.setenv("ENV_TWO", ENV_TWO)
    monkeypatch.setenv("ENV_THREE", ENV_THREE)
    monkeypatch.setenv("ENV_WITH_SAME_VALUE", ENV_WITH_SAME_VALUE)

    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=old_prefix,
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=old_prefix,
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(old_prefix),
        CONDA_PREFIX_1=None,
        # write_pkgs
        PKG_A_ENV=None,
        PKG_B_ENV=None,
        # write_state_file
        ENV_ONE="already_set_env_var",
        ENV_TWO=None,
        ENV_THREE=None,
        ENV_WITH_SAME_VALUE=None,
    )

    # TODO: refactor unset_vars into a set and avoid sorting
    deactivate = activator.build_deactivate()
    deactivate["unset_vars"].sort()
    assert deactivate == {
        "export_path": {"PATH": old_path},
        "deactivate_scripts": (),
        "unset_vars": sorted(unset_vars),
        "set_vars": {"PS1": get_prompt(old_prefix)},
        "export_vars": export_vars,
        "activate_scripts": (),
    }


def make_dot_d_files(prefix: str | os.PathLike, extension: str) -> None:
    (activated := Path(prefix, "etc", "conda", "activate.d")).mkdir(parents=True)
    (deactivated := Path(prefix, "etc", "conda", "deactivate.d")).mkdir(parents=True)

    (activated / "ignore.txt").touch()
    (deactivated / "ignore.txt").touch()

    (activated / f"activate1{extension}").touch()
    (deactivated / f"deactivate1{extension}").touch()


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_posix_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = PosixActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.posix", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)

    activate1 = activator.path_conversion(
        join(empty_env, "etc", "conda", "activate.d", "activate1.sh")
    )
    assert activate_data == (
        f"{unset_vars}\n"
        f"PS1='{get_prompt(empty_env)}'\n"
        f"export PATH='{activator.pathsep_join(new_path_parts)}'\n"
        f"export CONDA_PREFIX='{empty_env}'\n"
        "export CONDA_SHLVL='1'\n"
        f"export CONDA_DEFAULT_ENV='{empty_env}'\n"
        f"export CONDA_PROMPT_MODIFIER='{get_prompt_modifier(empty_env)}'\n"
        f"{conda_exe_export}\n"
        + (f". \"`cygpath '{activate1}'`\"\n" if on_win else f'. "{activate1}"\n')
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = PosixActivator()
    err = main_sourced("shell.posix", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(empty_env, "etc", "conda", "activate.d", "activate1.sh")
    )
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.sh",
        )
    )
    assert reactivate_data == (
        (f". \"`cygpath '{deactivate1}'`\"\n" if on_win else f'. "{deactivate1}"\n')
        + f"{unset_vars}\n"
        f"PS1='{get_prompt(empty_env)}'\n"
        f"export PATH='{activator.pathsep_join(new_path_parts)}'\n"
        f"export CONDA_SHLVL='1'\n"
        f"export CONDA_PROMPT_MODIFIER='{get_prompt_modifier(empty_env)}'\n"
        f"{conda_exe_export}\n"
        + (f". \"`cygpath '{activate1}'`\"\n" if on_win else f'. "{activate1}"\n')
    )

    err = main_sourced("shell.posix", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.sh",
        )
    )
    assert deactivate_data == (
        f"export PATH='{new_path}'\n"
        + (f". \"`cygpath '{deactivate1}'`\"\n" if on_win else f'. "{deactivate1}"\n')
        + f"export CONDA_PREFIX=''\n"
        f"export CONDA_DEFAULT_ENV=''\n"
        f"export CONDA_PROMPT_MODIFIER=''\n"
        f"{unset_vars}\n"
        f"PS1='{get_prompt()}'\n"
        f"export CONDA_SHLVL='0'\n"
        f"{conda_exe_export}\n"
    )


@pytest.mark.skipif(not on_win, reason="cmd.exe only on Windows")
@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_cmd_exe_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = CmdExeActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.cmd.exe", "activate", str(empty_env))
    activate_result, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    activate_data = Path(activate_result).read_text()
    rm_rf(activate_result)

    new_path_parts = activator._add_prefix_to_path(empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(empty_env, "etc", "conda", "activate.d", "activate1.bat")
    )
    assert activate_data == (
        f"{unset_vars}\n"
        f"PROMPT={get_prompt(empty_env)}\n"
        f"PATH={activator.pathsep_join(new_path_parts)}\n"
        f"CONDA_PREFIX={activator.path_conversion(empty_env)}\n"
        f"CONDA_SHLVL=1\n"
        f"CONDA_DEFAULT_ENV={empty_env}\n"
        f"CONDA_PROMPT_MODIFIER={get_prompt_modifier(empty_env)}\n"
        f"{conda_exe_export}\n"
        f"_CONDA_SCRIPT={activate1}\n"
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = CmdExeActivator()
    err = main_sourced("shell.cmd.exe", "reactivate")
    reactivate_result, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    reactivate_data = Path(reactivate_result).read_text()
    rm_rf(reactivate_result)

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "activate.d",
            "activate1.bat",
        )
    )
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.bat",
        )
    )
    assert reactivate_data == (
        f"_CONDA_SCRIPT={deactivate1}\n"
        f"{unset_vars}\n"
        f"PROMPT={get_prompt(empty_env)}\n"
        f"PATH={activator.pathsep_join(new_path_parts)}\n"
        f"CONDA_SHLVL=1\n"
        f"CONDA_PROMPT_MODIFIER={get_prompt_modifier(empty_env)}\n"
        f"{conda_exe_export}\n"
        f"_CONDA_SCRIPT={activate1}\n"
    )

    err = main_sourced("shell.cmd.exe", "deactivate")
    deactivate_result, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    deactivate_data = Path(deactivate_result).read_text()
    rm_rf(deactivate_result)

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.bat",
        )
    )
    assert deactivate_data == (
        f"PATH={new_path}\n"
        f"_CONDA_SCRIPT={deactivate1}\n"
        f"CONDA_PREFIX=\n"
        f"CONDA_DEFAULT_ENV=\n"
        f"CONDA_PROMPT_MODIFIER=\n"
        f"{unset_vars}\n"
        f"PROMPT={get_prompt()}\n"
        f"CONDA_SHLVL=0\n"
        f"{conda_exe_export}\n"
    )


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_csh_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = CshActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.csh", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(empty_env, "etc", "conda", "activate.d", "activate1.csh")
    )
    assert activate_data == (
        f"{unset_vars};\n"
        f"set prompt='{get_prompt(empty_env)}';\n"
        f'setenv PATH "{activator.pathsep_join(new_path_parts)}";\n'
        f'setenv CONDA_PREFIX "{empty_env}";\n'
        'setenv CONDA_SHLVL "1";\n'
        f'setenv CONDA_DEFAULT_ENV "{empty_env}";\n'
        f'setenv CONDA_PROMPT_MODIFIER "{get_prompt_modifier(empty_env)}";\n'
        f"{conda_exe_export};\n"
        + (
            f"source \"`cygpath '{activate1}'`\";\n"
            if on_win
            else f'source "{activate1}";\n'
        )
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = CshActivator()
    err = main_sourced("shell.csh", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "activate.d",
            "activate1.csh",
        )
    )
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.csh",
        )
    )
    assert reactivate_data == (
        (
            f"source \"`cygpath '{deactivate1}'`\";\n"
            if on_win
            else f'source "{deactivate1}";\n'
        )
        + f"{unset_vars};\n"
        f"set prompt='{get_prompt(empty_env)}';\n"
        f'setenv PATH "{activator.pathsep_join(new_path_parts)}";\n'
        f'setenv CONDA_SHLVL "1";\n'
        f'setenv CONDA_PROMPT_MODIFIER "{get_prompt_modifier(empty_env)}";\n'
        f"{conda_exe_export};\n"
        + (
            f"source \"`cygpath '{activate1}'`\";\n"
            if on_win
            else f'source "{activate1}";\n'
        )
    )

    err = main_sourced("shell.csh", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.csh",
        )
    )
    assert deactivate_data == (
        f'setenv PATH "{new_path}";\n'
        + (
            f"source \"`cygpath '{deactivate1}'`\";\n"
            if on_win
            else f'source "{deactivate1}";\n'
        )
        + f"unsetenv CONDA_PREFIX;\n"
        f"unsetenv CONDA_DEFAULT_ENV;\n"
        f"unsetenv CONDA_PROMPT_MODIFIER;\n"
        f"{unset_vars};\n"
        f"set prompt='{get_prompt()}';\n"
        f'setenv CONDA_SHLVL "0";\n'
        f"{conda_exe_export};\n"
    )


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_xonsh_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = XonshActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.xonsh", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(str(empty_env))
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    if on_win:
        sourcer = "source-cmd --suppress-skip-message"
    else:
        sourcer = "source-bash --suppress-skip-message -n"
    activate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "activate.d",
            "activate1.bat" if on_win else "activate1.sh",
        )
    )
    assert activate_data == (
        f"{unset_vars}\n"
        f"$PATH = '{activator.pathsep_join(new_path_parts)}'\n"
        f"$CONDA_PREFIX = '{empty_env}'\n"
        f"$CONDA_SHLVL = '1'\n"
        f"$CONDA_DEFAULT_ENV = '{empty_env}'\n"
        f"$CONDA_PROMPT_MODIFIER = '{get_prompt_modifier(empty_env)}'\n"
        f"{conda_exe_export}\n"
        f'{sourcer} "{activate1}"\n'
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = XonshActivator()
    err = main_sourced("shell.xonsh", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(str(empty_env), str(empty_env))
    if on_win:
        sourcer = "source-cmd --suppress-skip-message"
    else:
        sourcer = "source-bash --suppress-skip-message -n"
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "activate.d",
            "activate1.bat" if on_win else "activate1.sh",
        )
    )
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.bat" if on_win else "deactivate1.sh",
        )
    )
    assert reactivate_data == (
        f'{sourcer} "{deactivate1}"\n'
        f"{unset_vars}\n"
        f"$PATH = '{activator.pathsep_join(new_path_parts)}'\n"
        f"$CONDA_SHLVL = '1'\n"
        f"$CONDA_PROMPT_MODIFIER = '{get_prompt_modifier(empty_env)}'\n"
        f"{conda_exe_export}\n"
        f'{sourcer} "{activate1}"\n'
    )

    err = main_sourced("shell.xonsh", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(
        activator._remove_prefix_from_path(str(empty_env))
    )
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    if on_win:
        sourcer = "source-cmd --suppress-skip-message"
        deactivate1 = activator.path_conversion(
            join(
                empty_env,
                "etc",
                "conda",
                "deactivate.d",
                "deactivate1.bat",
            )
        )
    else:
        sourcer = "source-bash --suppress-skip-message -n"
        deactivate1 = activator.path_conversion(
            join(empty_env, "etc", "conda", "deactivate.d", "deactivate1.sh")
        )
    assert deactivate_data == (
        f"$PATH = '{new_path}'\n"
        f'{sourcer} "{deactivate1}"\n'
        f"try:\n"
        f"    del $CONDA_PREFIX\n"
        f"except KeyError:\n"
        f"    pass\n"
        f"try:\n"
        f"    del $CONDA_DEFAULT_ENV\n"
        f"except KeyError:\n"
        f"    pass\n"
        f"try:\n"
        f"    del $CONDA_PROMPT_MODIFIER\n"
        f"except KeyError:\n"
        f"    pass\n"
        f"{unset_vars}\n"
        f"$CONDA_SHLVL = '0'\n"
        f"{conda_exe_export}\n"
    )


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_fish_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = FishActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.fish", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(empty_env, "etc", "conda", "activate.d", "activate1.fish")
    )
    assert activate_data == (
        f"{unset_vars};\n"
        f'set -gx PATH "{activator.pathsep_join(new_path_parts)}";\n'
        f'set -gx CONDA_PREFIX "{empty_env}";\n'
        f'set -gx CONDA_SHLVL "1";\n'
        f'set -gx CONDA_DEFAULT_ENV "{empty_env}";\n'
        f'set -gx CONDA_PROMPT_MODIFIER "{get_prompt_modifier(empty_env)}";\n'
        f"{conda_exe_export};\n"
        f'source "{activate1}";\n'
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = FishActivator()
    err = main_sourced("shell.fish", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "activate.d",
            "activate1.fish",
        )
    )
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.fish",
        )
    )
    assert reactivate_data == (
        f'source "{deactivate1}";\n'
        f"{unset_vars};\n"
        f'set -gx PATH "{activator.pathsep_join(new_path_parts)}";\n'
        f'set -gx CONDA_SHLVL "1";\n'
        f'set -gx CONDA_PROMPT_MODIFIER "{get_prompt_modifier(empty_env)}";\n'
        f"{conda_exe_export};\n"
        f'source "{activate1}";\n'
    )

    err = main_sourced("shell.fish", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    deactivate1 = activator.path_conversion(
        join(
            empty_env,
            "etc",
            "conda",
            "deactivate.d",
            "deactivate1.fish",
        )
    )
    assert deactivate_data == (
        f'set -gx PATH "{new_path}";\n'
        f'source "{deactivate1}";\n'
        f"set -e CONDA_PREFIX || true;\n"
        f"set -e CONDA_DEFAULT_ENV || true;\n"
        f"set -e CONDA_PROMPT_MODIFIER || true;\n"
        f"{unset_vars};\n"
        f'set -gx CONDA_SHLVL "0";\n'
        f"{conda_exe_export};\n"
    )


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_powershell_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = PowerShellActivator()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.powershell", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = join(empty_env, "etc", "conda", "activate.d", "activate1.ps1")
    assert activate_data == (
        f"{unset_vars}\n"
        f'$Env:PATH = "{activator.pathsep_join(new_path_parts)}"\n'
        f'$Env:CONDA_PREFIX = "{empty_env}"\n'
        f'$Env:CONDA_SHLVL = "1"\n'
        f'$Env:CONDA_DEFAULT_ENV = "{empty_env}"\n'
        f'$Env:CONDA_PROMPT_MODIFIER = "{get_prompt_modifier(empty_env)}"\n'
        f"{conda_exe_export}\n"
        f'. "{activate1}"\n'
    )

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = PowerShellActivator()
    err = main_sourced("shell.powershell", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    conda_exe_export, unset_vars = get_scripts_export_unset_vars(activator)
    activate1 = join(empty_env, "etc", "conda", "activate.d", "activate1.ps1")
    deactivate1 = join(
        empty_env,
        "etc",
        "conda",
        "deactivate.d",
        "deactivate1.ps1",
    )
    assert reactivate_data == (
        f'. "{deactivate1}"\n'
        f"{unset_vars}\n"
        f'$Env:PATH = "{activator.pathsep_join(new_path_parts)}"\n'
        f'$Env:CONDA_SHLVL = "1"\n'
        f'$Env:CONDA_PROMPT_MODIFIER = "{get_prompt_modifier(empty_env)}"\n'
        f"{conda_exe_export}\n"
        f'. "{activate1}"\n'
    )

    err = main_sourced("shell.powershell", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    deactivate1 = join(
        empty_env,
        "etc",
        "conda",
        "deactivate.d",
        "deactivate1.ps1",
    )
    assert deactivate_data == (
        f'$Env:PATH = "{new_path}"\n'
        f'. "{deactivate1}"\n'
        f"$Env:CONDA_PREFIX = $null\n"
        f"$Env:CONDA_DEFAULT_ENV = $null\n"
        f"$Env:CONDA_PROMPT_MODIFIER = $null\n"
        f"{unset_vars}\n"
        f'$Env:CONDA_SHLVL = "0"\n'
        f"{conda_exe_export}\n"
    )


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_json_basic(
    empty_env: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
    force_uppercase_boolean: bool,
) -> None:
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase == force_uppercase_boolean

    activator = _build_activator_cls("posix+json")()
    make_dot_d_files(empty_env, activator.script_extension)

    err = main_sourced("shell.posix+json", "activate", str(empty_env))
    activate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._add_prefix_to_path(empty_env)
    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_PREFIX=str(empty_env),
        CONDA_SHLVL=1,
        CONDA_DEFAULT_ENV=str(empty_env),
        CONDA_PROMPT_MODIFIER=get_prompt_modifier(empty_env),
    )
    assert json.loads(activate_data) == {
        "path": {"PATH": list(new_path_parts)},
        "vars": {
            "export": export_vars,
            "set": {"PS1": get_prompt(empty_env)},
            "unset": unset_vars,
        },
        "scripts": {
            "activate": [
                activator.path_conversion(
                    join(empty_env, "etc", "conda", "activate.d", "activate1.sh")
                ),
            ],
            "deactivate": [],
        },
    }

    monkeypatch.setenv("CONDA_PREFIX", empty_env)
    monkeypatch.setenv("CONDA_SHLVL", "1")
    monkeypatch.setenv("PATH", os.pathsep.join((*new_path_parts, os.environ["PATH"])))

    activator = _build_activator_cls("posix+json")()
    err = main_sourced("shell.posix+json", "reactivate")
    reactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path_parts = activator._replace_prefix_in_path(empty_env, empty_env)
    export_vars, unset_vars = activator.get_export_unset_vars()
    assert json.loads(reactivate_data) == {
        "path": {"PATH": list(new_path_parts)},
        "vars": {
            "export": {
                "CONDA_SHLVL": 1,
                "CONDA_PROMPT_MODIFIER": get_prompt_modifier(empty_env),
                **export_vars,
            },
            "set": {"PS1": get_prompt(empty_env)},
            "unset": unset_vars,
        },
        "scripts": {
            "activate": [
                activator.path_conversion(
                    join(
                        empty_env,
                        "etc",
                        "conda",
                        "activate.d",
                        "activate1.sh",
                    )
                ),
            ],
            "deactivate": [
                activator.path_conversion(
                    join(
                        empty_env,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.sh",
                    )
                ),
            ],
        },
    }

    err = main_sourced("shell.posix+json", "deactivate")
    deactivate_data, stderr = capsys.readouterr()
    assert not stderr
    assert not err

    new_path = activator.pathsep_join(activator._remove_prefix_from_path(empty_env))
    export_vars, unset_vars = activator.get_export_unset_vars(
        CONDA_SHLVL=0,
        CONDA_PREFIX=None,
        CONDA_DEFAULT_ENV=None,
        CONDA_PROMPT_MODIFIER=None,
    )
    assert json.loads(deactivate_data) == {
        "path": {"PATH": list(new_path)},
        "vars": {
            "export": export_vars,
            "set": {"PS1": get_prompt()},
            "unset": unset_vars,
        },
        "scripts": {
            "activate": [],
            "deactivate": [
                activator.path_conversion(
                    join(
                        empty_env,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.sh",
                    )
                ),
            ],
        },
    }


def test_activate_and_deactivate_for_uninitialized_env(conda_cli):
    # Call activate (with and without env argument) and check that the proper error shows up
    with pytest.raises(CondaError) as conda_error:
        conda_cli("activate")
    assert conda_error.value.message.startswith(
        "Run 'conda init' before 'conda activate'"
    )
    with pytest.raises(CondaError) as conda_error:
        conda_cli("activate", "env")
    assert conda_error.value.message.startswith(
        "Run 'conda init' before 'conda activate'"
    )

    # Call deactivate and check that the proper error shows up
    with pytest.raises(CondaError) as conda_error:
        conda_cli("deactivate")
    assert conda_error.value.message.startswith(
        "Run 'conda init' before 'conda deactivate'"
    )


# The MSYS2_PATH tests are slightly unusual in two regards: firstly
# they stat(2) for potential directories which indicate which (of
# several) possible MSYS2 environments have been installed; secondly,
# conda will pass a Windows pathname prefix but conda-build will pass
# a Unix pathname prefix (in particular, an MSYS2 pathname).
MINGW_W64 = ["mingw-w64"]
UCRT64 = ["ucrt64"]
CLANG64 = ["clang64"]
MINGW64 = ["mingw64"]


@pytest.mark.skipif(not on_win, reason="windows-specific test")
@pytest.mark.parametrize(
    "create,expected,unexpected",
    [
        # No Library/* => Library/mingw-w64/bin
        pytest.param([], MINGW_W64, UCRT64, id="nothing"),
        # Library/mingw-w64 => Library/mingw-w64/bin
        pytest.param(MINGW_W64, MINGW_W64, UCRT64, id="legacy"),
        # Library/ucrt64 => Library/ucrt64/bin
        pytest.param(UCRT64, UCRT64 + MINGW_W64, CLANG64, id="ucrt64"),
        # Library/ucrt64 and Library/mingw-w64 => Library/ucrt64/bin
        pytest.param(
            UCRT64 + MINGW_W64,
            UCRT64 + MINGW_W64,
            CLANG64,
            id="ucrt64 legacy",
        ),
        # Library/clang64 and Library/mingw-w64 => Library/clang64/bin
        pytest.param(
            CLANG64 + MINGW_W64,
            CLANG64 + MINGW_W64,
            UCRT64,
            id="clang64 legacy",
        ),
        # Library/ucrt64 and Library/clang64 => Library/ucrt64/bin
        pytest.param(
            UCRT64 + CLANG64,
            UCRT64 + MINGW_W64,
            CLANG64,
            id="ucrt64 clang64",
        ),
        # Library/clang64 and Library/mingw64 => Library/clang64/bin
        pytest.param(
            CLANG64 + MINGW64,
            CLANG64 + MINGW_W64,
            MINGW64,
            id="clang64 mingw64",
        ),
        # Library/mingw64 and Library/mingw-w64 => Library/mingw64/bin
        pytest.param(
            MINGW64 + MINGW_W64,
            MINGW64 + MINGW_W64,
            UCRT64,
            id="mingw64 legacy",
        ),
    ],
)
@pytest.mark.parametrize("activator_cls", [CmdExeActivator, PowerShellActivator])
def test_MSYS2_PATH(
    tmp_env: TmpEnvFixture,
    create: list[str],
    expected: list[str],
    unexpected: list[str],
    activator_cls: type[_Activator],
) -> None:
    with tmp_env() as prefix:
        # create MSYS2 directories
        (library := prefix / "Library").mkdir()
        for path in create:
            (library / path / "bin").mkdir(parents=True)

        activator = activator_cls()
        paths = activator._replace_prefix_in_path(str(prefix), str(prefix))

        # ensure expected bin directories are included in %PATH%/$env:PATH
        for path in expected:
            assert activator.path_conversion(str(library / path / "bin")) in paths

        # ensure unexpected bin directories are not included in %PATH%/$env:PATH
        for path in unexpected:
            assert activator.path_conversion(str(library / path / "bin")) not in paths


@pytest.mark.skipif(
    not on_win, reason="MSYS2 shells line ending fix only applies on Windows"
)
@pytest.mark.parametrize("shell", ["zsh", "bash", "posix", "ash", "dash"])
def test_msys2_shell_line_endings(shell: str, capsys) -> None:
    """Test that MSYS2/zsh shell hooks don't contain Windows line endings."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out
    assert "\r" not in output
    assert "export" in output


@pytest.mark.skipif(
    not on_win, reason="MSYS2 shells line ending fix only applies on Windows"
)
def test_msys2_shell_stdout_reconfiguration(capsys) -> None:
    """Test that stdout is properly reconfigured for MSYS2 shells."""
    assert main_sourced("zsh", "hook") == 0
    assert "\r" not in capsys.readouterr().out


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_force_uppercase(monkeypatch: MonkeyPatch, force_uppercase_boolean):
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase is force_uppercase_boolean

    activator = PosixActivator()
    export_vars, unset_vars = activator.get_export_unset_vars(
        one=1,
        TWO=2,
        three=None,
        FOUR=None,
    )

    # preserved case vars present if  keep_case is True
    assert ("one" in export_vars) is not force_uppercase_boolean
    assert ("three" in unset_vars) is not force_uppercase_boolean

    # vars uppercased when keep_case is False
    assert ("ONE" in export_vars) is force_uppercase_boolean
    assert ("THREE" in unset_vars) is force_uppercase_boolean

    # original uppercase
    assert "TWO" in export_vars
    assert "FOUR" in unset_vars


@pytest.mark.parametrize("force_uppercase_boolean", [True, False])
def test_metavars_force_uppercase(
    mocker: MockerFixture, monkeypatch: MonkeyPatch, force_uppercase_boolean: bool
):
    monkeypatch.setenv("CONDA_ENVVARS_FORCE_UPPERCASE", force_uppercase_boolean)
    reset_context()
    assert context.envvars_force_uppercase is force_uppercase_boolean

    returned_dict = {
        "ONE": "1",
        "two": "2",
        "three": None,
        "FOUR": None,
        "five": "a/path/to/something",
        "SIX": "a\\path",
    }
    mocker.patch(
        "conda.base.context.Context.conda_exe_vars_dict",
        new_callable=mocker.PropertyMock,
        return_value=returned_dict,
    )
    assert context.conda_exe_vars_dict == returned_dict

    activator = PosixActivator()
    export_vars, unset_vars = activator.get_export_unset_vars()

    # preserved case vars present if keep_case is True
    assert ("two" in export_vars) is not force_uppercase_boolean
    assert ("three" in unset_vars) is not force_uppercase_boolean
    assert ("five" in export_vars) is not force_uppercase_boolean

    # vars uppercased when keep_case is False
    assert ("TWO" in export_vars) is force_uppercase_boolean
    assert ("THREE" in unset_vars) is force_uppercase_boolean

    # original uppercase
    assert "ONE" in export_vars
    assert "FOUR" in unset_vars
    assert "SIX" in export_vars


class PrePostCommandPlugin:
    def pre_command_action(self, command: str) -> None:
        pass

    @plugins.hookimpl
    def conda_pre_commands(self):
        yield CondaPreCommand(
            name="custom-pre-command",
            action=self.pre_command_action,
            run_for={"activate", "deactivate", "reactivate", "hook"},
        )

    def post_command_action(self, command: str) -> None:
        pass

    @plugins.hookimpl
    def conda_post_commands(self):
        yield CondaPostCommand(
            name="custom-post-command",
            action=self.post_command_action,
            run_for={"activate", "deactivate", "reactivate", "hook"},
        )


@pytest.fixture
def plugin(
    mocker: MockerFixture,
    plugin_manager: CondaPluginManager,
) -> PrePostCommandPlugin:
    mocker.patch.object(PrePostCommandPlugin, "pre_command_action")
    mocker.patch.object(PrePostCommandPlugin, "post_command_action")

    plugin = PrePostCommandPlugin()
    plugin_manager.register(plugin)

    return plugin


@pytest.mark.parametrize(
    "command",
    ["activate", "deactivate", "reactivate", "hook"],
)
def test_pre_post_command_invoked(plugin: PrePostCommandPlugin, command: str) -> None:
    activator = PosixActivator([command])
    activator.execute()

    assert len(plugin.pre_command_action.mock_calls) == 1
    assert len(plugin.post_command_action.mock_calls) == 1


@pytest.mark.parametrize(
    "command",
    ["activate", "deactivate", "reactivate", "hook"],
)
def test_pre_post_command_raises(plugin: PrePostCommandPlugin, command: str) -> None:
    exc_message = "💥"

    # first test post-command exceptions (sine they happen last)
    plugin.post_command_action.side_effect = Exception(exc_message)

    activator = PosixActivator([command])
    with pytest.raises(Exception, match=exc_message):
        activator.execute()

    assert len(plugin.pre_command_action.mock_calls) == 1
    assert len(plugin.post_command_action.mock_calls) == 1

    # now test pre-command exceptions
    plugin.pre_command_action.side_effect = Exception(exc_message)

    activator = PosixActivator([command])
    with pytest.raises(Exception, match=exc_message):
        activator.execute()

    assert len(plugin.pre_command_action.mock_calls) == 2
    assert len(plugin.post_command_action.mock_calls) == 1


@pytest.mark.parametrize(
    "command_args,expected_error_message",
    (
        (
            ["invalid-command"],
            "'activate', 'deactivate', 'hook', 'commands', or 'reactivate' command must be given.",
        ),
        (
            ["activate", "--stack", "--no-stack"],
            "cannot specify both --stack and --no-stack to activate",
        ),
        (
            ["activate", "env-one", "env-two"],
            "activate does not accept more than one argument:\n\\['env-one', 'env-two'\\]\n",
        ),
        (
            ["deactivate", "env-one"],
            "deactivate does not accept arguments\nremainder_args: \\['env-one']\n",
        ),
    ),
)
def test_activator_invalid_command_arguments(command_args, expected_error_message):
    """
    Ensure that the appropriate error is raised when invalid command arguments are passed
    """
    activator = PosixActivator(command_args)

    with pytest.raises(ArgumentError, match=expected_error_message):
        activator.execute()


@pytest.mark.parametrize("activator_cls", list(dict.fromkeys(activator_map.values())))
def test_activate_default_env(activator_cls, monkeypatch, conda_cli, tmp_path):
    # Make sure local config does not affect the test; empty string -> base
    monkeypatch.setenv("CONDA_DEFAULT_ACTIVATION_ENV", "")
    reset_context()

    output = activator_cls(["activate"]).execute()
    if activator_cls == CmdExeActivator:
        output = Path(output.strip()).read_text()
    assert "(base)" in output

    monkeypatch.setenv("CONDA_DEFAULT_ACTIVATION_ENV", str(tmp_path))
    reset_context()

    conda_cli("create", "-p", tmp_path, "--yes", "--offline")

    output = activator_cls(["activate"]).execute()
    if activator_cls == CmdExeActivator:
        output = Path(output.strip()).read_text()
    assert str(tmp_path) in output
