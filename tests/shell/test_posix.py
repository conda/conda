# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from functools import cache
from logging import getLogger
from shutil import which
from subprocess import CalledProcessError, check_output
from typing import TYPE_CHECKING

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as conda_version
from conda.base.context import context
from conda.common.compat import on_win

from . import HDF5_VERSION, InteractiveShell, activate, deactivate, dev_arg, install

if TYPE_CHECKING:
    from typing import Callable

log = getLogger(__name__)
pytestmark = pytest.mark.integration


@cache
def bash_unsupported() -> str | None:
    if not (bash := which("bash")):
        return "bash: was not found on PATH"
    elif on_win:
        try:
            output = check_output(f'{bash} -c "uname -v"')
        except CalledProcessError as exc:
            return f"bash: something went wrong while running bash, output:\n{exc.output}\n"
        else:
            if b"Microsoft" in output:
                return "bash: WSL is not yet supported. Pull requests welcome."
            else:
                output = check_output(f"{bash} --version")
                if b"msys" not in output and b"cygwin" not in output:
                    return f"bash: Only MSYS2 and Cygwin bash are supported on Windows, found:\n{output!r}\n"
    return None


skip_unsupported_bash = pytest.mark.skipif(
    bool(bash_unsupported()),
    reason=bash_unsupported() or "bash: supported!",
)


def basic_posix(shell, prefix, prefix2, prefix3):
    if shell.shell_name in ("zsh", "dash"):
        conda_is_a_function = "conda is a shell function"
    else:
        conda_is_a_function = "conda is a function"

    case = str.lower if on_win else str

    num_paths_added = len(tuple(shell.activator._get_path_dirs(prefix)))
    prefix_p = shell.path_conversion(prefix)
    prefix2_p = shell.path_conversion(prefix2)
    shell.path_conversion(prefix3)

    PATH0 = shell.get_env_var("PATH", "")
    assert any(path.endswith("condabin") for path in PATH0.split(":"))

    shell.assert_env_var("CONDA_SHLVL", "0")
    # Remove sys.prefix from PATH. It interferes with path entry count tests.
    # We can no longer check this since we'll replace e.g. between 1 and N path
    # entries with N of them in _replace_prefix_in_path() now. It is debatable
    # whether it should be here at all too.
    if PATH0.startswith(shell.path_conversion(sys.prefix) + ":"):
        PATH0 = PATH0[len(shell.path_conversion(sys.prefix)) + 1 :]
        shell.sendline(f'export PATH="{PATH0}"')
        PATH0 = shell.get_env_var("PATH", "")
    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    _CE_M = shell.get_env_var("_CE_M")
    _CE_CONDA = shell.get_env_var("_CE_CONDA")

    shell.sendline("conda --version")
    shell.expect_exact("conda " + conda_version)

    shell.sendline(f"conda {activate} base")

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    CONDA_EXE2 = case(shell.get_env_var("CONDA_EXE"))
    _CE_M2 = shell.get_env_var("_CE_M")

    shell.assert_env_var("PS1", "(base).*")
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH1 = shell.get_env_var("PATH", "")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH1.split(":"))

    CONDA_EXE = case(shell.get_env_var("CONDA_EXE"))
    _CE_M = shell.get_env_var("_CE_M")
    _CE_CONDA = shell.get_env_var("_CE_CONDA")

    log.debug("activating ..")
    shell.sendline(f'conda {activate} "{prefix_p}"')

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    CONDA_EXE2 = case(shell.get_env_var("CONDA_EXE"))
    _CE_M2 = shell.get_env_var("_CE_M")
    _CE_CONDA2 = shell.get_env_var("_CE_CONDA")
    assert CONDA_EXE == CONDA_EXE2
    assert _CE_M == _CE_M2
    assert _CE_CONDA == _CE_CONDA2

    shell.sendline("env | sort")
    # When CONDA_SHLVL==2 fails it usually means that conda activate failed. We that fails it is
    # usually because you forgot to pass `--dev` to the *previous* activate so CONDA_EXE changed
    # from python to conda, which is then found on PATH instead of using the dev sources. When it
    # goes to use this old conda to generate the activation script for the newly activated env.
    # it is running the old code (or at best, a mix of new code and old scripts).
    shell.assert_env_var("CONDA_SHLVL", "2")
    CONDA_PREFIX = shell.get_env_var("CONDA_PREFIX", "")
    # We get C: vs c: differences on Windows.
    # Also, self.prefix instead of prefix_p is deliberate (maybe unfortunate?)
    assert CONDA_PREFIX.lower() == prefix.lower()
    PATH2 = shell.get_env_var("PATH", "")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH2.split(":"))

    shell.sendline("env | sort | grep CONDA")
    shell.expect("CONDA_")
    shell.sendline('echo "PATH=$PATH"')
    shell.expect("PATH=")
    shell.sendline(f'conda {activate} "{prefix2_p}"')
    shell.sendline("env | sort | grep CONDA")
    shell.expect("CONDA_")
    shell.sendline('echo "PATH=$PATH"')
    shell.expect("PATH=")
    shell.assert_env_var("PS1", "(charizard).*")
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH3.split(":"))

    CONDA_EXE2 = case(shell.get_env_var("CONDA_EXE"))
    _CE_M2 = shell.get_env_var("_CE_M")
    _CE_CONDA2 = shell.get_env_var("_CE_CONDA")
    assert CONDA_EXE == CONDA_EXE2
    assert _CE_M == _CE_M2
    assert _CE_CONDA == _CE_CONDA2

    shell.sendline(f"conda {install} -yq hdf5={HDF5_VERSION}")
    shell.expect(r"Executing transaction: ...working... done.*\n", timeout=180)
    shell.assert_env_var("?", "0", use_exact=True)

    shell.sendline("h5stat --version")
    shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

    # TODO: assert that reactivate worked correctly

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    shell.sendline(f"conda run {dev_arg} h5stat --version")
    shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

    # regression test for #6840
    shell.sendline(f"conda {install} --blah")
    shell.assert_env_var("?", "2", use_exact=True)
    shell.sendline("conda list --blah")
    shell.assert_env_var("?", "2", use_exact=True)

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH.split(":"))

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH.split(":"))

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "0")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) == len(PATH.split(":"))
    # assert PATH0 == PATH  # cygpath may "resolve" paths

    shell.sendline(shell.print_env_var % "PS1")
    shell.clear()
    assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "0")

    # When fully deactivated, CONDA_EXE, _CE_M and _CE_CONDA must be retained
    # because the conda shell scripts use them and if they are unset activation
    # is not possible.
    CONDA_EXED = case(shell.get_env_var("CONDA_EXE"))
    assert CONDA_EXED, (
        "A fully deactivated conda shell must retain CONDA_EXE (and _CE_M and _CE_CONDA in dev)\n"
        "  as the shell scripts refer to them."
    )

    PATH0 = shell.get_env_var("PATH")

    shell.sendline(f'conda {activate} "{prefix2_p}"')
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH1 = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH1.split(":"))

    shell.sendline(f'conda {activate} "{prefix3}" --stack')
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH2 = shell.get_env_var("PATH")
    assert "charizard" in PATH2
    assert "venusaur" in PATH2
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH2.split(":"))

    shell.sendline(f'conda {activate} "{prefix_p}"')
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert "charizard" in PATH3
    assert "venusaur" not in PATH3
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH3.split(":"))

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH4 = shell.get_env_var("PATH")
    assert "charizard" in PATH4
    assert "venusaur" in PATH4
    assert len(PATH4.split(":")) == len(PATH2.split(":"))
    # assert PATH4 == PATH2  # cygpath may "resolve" paths

    shell.sendline(f"conda {deactivate}")
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH5 = shell.get_env_var("PATH")
    assert len(PATH1.split(":")) == len(PATH5.split(":"))
    # assert PATH1 == PATH5  # cygpath may "resolve" paths

    # Test auto_stack
    shell.sendline(shell.activator.export_var_tmpl % ("CONDA_AUTO_STACK", "1"))

    shell.sendline(f'conda {activate} "{prefix3}"')
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH2 = shell.get_env_var("PATH")
    assert "charizard" in PATH2
    assert "venusaur" in PATH2
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH2.split(":"))

    shell.sendline(f'conda {activate} "{prefix_p}"')
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert "charizard" in PATH3
    assert "venusaur" not in PATH3
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH3.split(":"))


@pytest.mark.parametrize(
    "shell_name,script",
    [
        pytest.param(
            "bash",
            basic_posix,
            marks=[
                skip_unsupported_bash,
                pytest.mark.skipif(
                    on_win, reason="Temporary skip, larger refactor necessary"
                ),
            ],
        ),
        pytest.param(
            "dash",
            basic_posix,
            marks=[
                pytest.mark.skipif(
                    not which("dash") or on_win, reason="dash not installed"
                )
            ],
        ),
        pytest.param(
            "zsh",
            basic_posix,
            marks=[pytest.mark.skipif(not which("zsh"), reason="zsh not installed")],
        ),
    ],
)
def test_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell_name: str,
    script: Callable[[InteractiveShell, str, str, str], None],
):
    with InteractiveShell(shell_name) as shell:
        script(shell, *shell_wrapper_integration)


@skip_unsupported_bash
@pytest.mark.skipif(on_win, reason="Temporary skip, larger refactor necessary")
def test_bash_activate_error(shell_wrapper_integration: tuple[str, str, str]):
    context.dev = True
    with InteractiveShell("bash") as shell:
        shell.sendline("export CONDA_SHLVL=unaffected")
        if on_win:
            shell.sendline("uname -o")
            shell.expect("(Msys|Cygwin)")
        shell.sendline("conda activate environment-not-found-doesnt-exist")
        shell.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        shell.assert_env_var("CONDA_SHLVL", "unaffected")

        shell.sendline("conda activate -h blah blah")
        shell.expect("usage: conda activate")


@skip_unsupported_bash
def test_legacy_activate_deactivate_bash(
    shell_wrapper_integration: tuple[str, str, str],
):
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell("bash") as shell:
        CONDA_PACKAGE_ROOT_p = shell.path_conversion(CONDA_PACKAGE_ROOT)
        prefix2_p = shell.path_conversion(prefix2)
        prefix3_p = shell.path_conversion(prefix3)
        shell.sendline(f"export _CONDA_ROOT='{CONDA_PACKAGE_ROOT_p}/shell'")
        shell.sendline(
            f'source "${{_CONDA_ROOT}}/bin/activate" {dev_arg} "{prefix2_p}"'
        )
        PATH0 = shell.get_env_var("PATH")
        assert "charizard" in PATH0

        shell.sendline("type conda")
        shell.expect("conda is a function")

        shell.sendline("conda --version")
        shell.expect_exact("conda " + conda_version)

        shell.sendline(
            f'source "${{_CONDA_ROOT}}/bin/activate" {dev_arg} "{prefix3_p}"'
        )

        PATH1 = shell.get_env_var("PATH")
        assert "venusaur" in PATH1

        shell.sendline('source "${_CONDA_ROOT}/bin/deactivate"')
        PATH2 = shell.get_env_var("PATH")
        assert "charizard" in PATH2

        shell.sendline('source "${_CONDA_ROOT}/bin/deactivate"')
        shell.assert_env_var("CONDA_SHLVL", "0")
