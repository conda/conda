# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from functools import cache
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as CONDA_VERSION
from conda.base.context import context
from conda.common.compat import on_mac, on_win
from conda.common.path import win_path_to_unix

from . import activate, deactivate, dev_arg, install

if TYPE_CHECKING:
    from . import InteractiveShell, Shell

log = getLogger(__name__)
pytestmark = pytest.mark.integration

PARAMETRIZE_POSIX = pytest.mark.parametrize(
    "shell",
    [
        pytest.param(
            "ash",
            marks=[
                pytest.mark.skipif(on_mac, reason="unavailable on macOS"),
                pytest.mark.skipif(on_win, reason="unavailable on Windows"),
            ],
        ),
        "bash",
        pytest.param(
            "dash",
            marks=pytest.mark.skipif(on_win, reason="unavailable on Windows"),
        ),
        pytest.param(
            "zsh",
            marks=pytest.mark.skipif(on_win, reason="unavailable on Windows"),
        ),
    ],
    indirect=True,
)


@PARAMETRIZE_POSIX
def test_shell_available(shell: Shell) -> None:
    # the `shell` fixture does all the work
    pass


@cache
def is_a_function(sh: InteractiveShell) -> str:
    if sh.shell_name in ("ash", "dash", "zsh"):
        return "conda is a shell function"
    return "conda is a function"


@PARAMETRIZE_POSIX
def test_basic_integration(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
    test_recipes_channel: Path,
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with shell.interactive() as sh:
        case = str.lower if on_win else str

        prefix_p = sh.path_conversion(prefix)
        prefix2_p = sh.path_conversion(prefix2)
        sh.path_conversion(prefix3)

        nbase = len(tuple(sh.activator._get_path_dirs(sys.prefix)))
        nprefix = len(tuple(sh.activator._get_path_dirs(prefix)))
        nprefix2 = len(tuple(sh.activator._get_path_dirs(prefix2)))
        nprefix3 = len(tuple(sh.activator._get_path_dirs(prefix3)))

        PATH0 = sh.get_env_var("PATH", "")
        assert any(path.endswith("condabin") for path in PATH0.split(":"))

        sh.assert_env_var("CONDA_SHLVL", "0")
        # Remove sys.prefix from PATH. It interferes with path entry count tests.
        # We can no longer check this since we'll replace e.g. between 1 and N path
        # entries with N of them in _replace_prefix_in_path() now. It is debatable
        # whether it should be here at all too.
        if PATH0.startswith(sh.path_conversion(sys.prefix) + ":"):
            PATH0 = PATH0[len(sh.path_conversion(sys.prefix)) + 1 :]
            sh.sendline(f'export PATH="{PATH0}"')
            PATH0 = sh.get_env_var("PATH", "")
        sh.sendline("type conda")
        sh.expect(is_a_function(sh))

        _CE_M = sh.get_env_var("_CE_M")
        _CE_CONDA = sh.get_env_var("_CE_CONDA")

        sh.sendline("conda --version")
        sh.expect_exact(f"conda {CONDA_VERSION}")

        sh.sendline(f"conda {activate} base")

        sh.sendline("type conda")
        sh.expect(is_a_function(sh))

        CONDA_EXE2 = case(sh.get_env_var("CONDA_EXE"))
        _CE_M2 = sh.get_env_var("_CE_M")

        sh.assert_env_var("PS1", "(base).*")
        sh.assert_env_var("CONDA_SHLVL", "1")
        PATH1 = sh.get_env_var("PATH", "")
        assert len(PATH0.split(":")) + nbase == len(PATH1.split(":"))

        CONDA_EXE = case(sh.get_env_var("CONDA_EXE"))
        _CE_M = sh.get_env_var("_CE_M")
        _CE_CONDA = sh.get_env_var("_CE_CONDA")

        log.debug("activating ..")
        sh.sendline(f'conda {activate} "{prefix_p}"')

        sh.sendline("type conda")
        sh.expect(is_a_function(sh))

        CONDA_EXE2 = case(sh.get_env_var("CONDA_EXE"))
        _CE_M2 = sh.get_env_var("_CE_M")
        _CE_CONDA2 = sh.get_env_var("_CE_CONDA")
        assert CONDA_EXE == CONDA_EXE2
        assert _CE_M == _CE_M2
        assert _CE_CONDA == _CE_CONDA2

        sh.sendline("env | sort")
        # When CONDA_SHLVL==2 fails it usually means that conda activate failed. We that fails it is
        # usually because you forgot to pass `--dev` to the *previous* activate so CONDA_EXE changed
        # from python to conda, which is then found on PATH instead of using the dev sources. When it
        # goes to use this old conda to generate the activation script for the newly activated env.
        # it is running the old code (or at best, a mix of new code and old scripts).
        sh.assert_env_var("CONDA_SHLVL", "2")
        CONDA_PREFIX = sh.get_env_var("CONDA_PREFIX", "")
        # We get C: vs c: differences on Windows.
        # Also, self.prefix instead of prefix_p is deliberate (maybe unfortunate?)
        assert CONDA_PREFIX.lower() == prefix.lower()
        PATH2 = sh.get_env_var("PATH", "")
        assert len(PATH0.split(":")) + nprefix == len(PATH2.split(":"))

        sh.sendline("env | sort | grep CONDA")
        sh.expect("CONDA_")
        sh.sendline('echo "PATH=$PATH"')
        sh.expect("PATH=")
        sh.sendline(f'conda {activate} "{prefix2_p}"')
        sh.sendline("env | sort | grep CONDA")
        sh.expect("CONDA_")
        sh.sendline('echo "PATH=$PATH"')
        sh.expect("PATH=")
        sh.assert_env_var("PS1", "(charizard).*")
        sh.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = sh.get_env_var("PATH")
        assert len(PATH0.split(":")) + nprefix2 == len(PATH3.split(":"))

        CONDA_EXE2 = case(sh.get_env_var("CONDA_EXE"))
        _CE_M2 = sh.get_env_var("_CE_M")
        _CE_CONDA2 = sh.get_env_var("_CE_CONDA")
        assert CONDA_EXE == CONDA_EXE2
        assert _CE_M == _CE_M2
        assert _CE_CONDA == _CE_CONDA2

        # despite which OS we are on, channel path needs to be POSIX compliant
        if on_win:
            test_recipes_channel = win_path_to_unix(test_recipes_channel)

        # install local tests/test-recipes/small-executable
        sh.sendline(
            f"conda {install} "
            f"--yes "
            f"--quiet "
            f"--override-channels "
            f"--channel={test_recipes_channel} "
            f"small-executable"
        )
        sh.expect(r"Executing transaction: ...working... done.*\n")
        sh.assert_env_var("?", "0", use_exact=True)

        # see tests/test-recipes/small-executable
        sh.sendline("small")
        sh.expect_exact("Hello!")
        sh.assert_env_var("SMALL_EXE", "small-var-sh")

        # TODO: assert that reactivate worked correctly

        sh.sendline("type conda")
        sh.expect(is_a_function(sh))

        # see tests/test-recipes/small-executable
        sh.sendline(f"conda run {dev_arg} small")
        sh.expect_exact("Hello!")

        # regression test for #6840
        sh.sendline(f'conda {install} --blah || echo "exitcode=$?"')
        sh.expect_exact("error: unrecognized arguments: --blah")
        sh.expect_exact("exitcode=2")
        sh.sendline('conda list --blah || echo "exitcode=$?"')
        sh.expect_exact("error: unrecognized arguments: --blah")
        sh.expect_exact("exitcode=2")

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "2")
        PATH = sh.get_env_var("PATH")
        assert len(PATH0.split(":")) + nprefix == len(PATH.split(":"))

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "1")
        PATH = sh.get_env_var("PATH")
        assert len(PATH0.split(":")) + nbase == len(PATH.split(":"))

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")
        PATH = sh.get_env_var("PATH")
        assert len(PATH0.split(":")) == len(PATH.split(":"))
        # assert PATH0 == PATH  # cygpath may "resolve" paths

        sh.sendline(sh.print_env_var % "PS1")
        sh.clear()
        assert "CONDA_PROMPT_MODIFIER" not in str(sh.p.after)

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "0")

        # When fully deactivated, CONDA_EXE, _CE_M and _CE_CONDA must be retained
        # because the conda shell scripts use them and if they are unset activation
        # is not possible.
        CONDA_EXED = case(sh.get_env_var("CONDA_EXE"))
        assert CONDA_EXED, (
            "A fully deactivated conda shell must retain CONDA_EXE (and _CE_M and _CE_CONDA in dev)\n"
            "  as the shell scripts refer to them."
        )

        PATH0 = sh.get_env_var("PATH")

        sh.sendline(f'conda {activate} "{prefix2_p}"')
        sh.assert_env_var("CONDA_SHLVL", "1")
        PATH1 = sh.get_env_var("PATH")
        assert len(PATH0.split(":")) + nprefix2 == len(PATH1.split(":"))

        sh.sendline(f'conda {activate} "{prefix3}" --stack')
        sh.assert_env_var("CONDA_SHLVL", "2")
        PATH2 = sh.get_env_var("PATH")
        assert "charizard" in PATH2
        assert "venusaur" in PATH2
        assert len(PATH0.split(":")) + nprefix2 + nprefix3 == len(PATH2.split(":"))

        sh.sendline(f'conda {activate} "{prefix_p}"')
        sh.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = sh.get_env_var("PATH")
        assert "charizard" in PATH3
        assert "venusaur" not in PATH3
        assert len(PATH0.split(":")) + nprefix2 + nprefix == len(PATH3.split(":"))

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "2")
        PATH4 = sh.get_env_var("PATH")
        assert "charizard" in PATH4
        assert "venusaur" in PATH4
        assert len(PATH4.split(":")) == len(PATH2.split(":"))
        # assert PATH4 == PATH2  # cygpath may "resolve" paths

        sh.sendline(f"conda {deactivate}")
        sh.assert_env_var("CONDA_SHLVL", "1")
        PATH5 = sh.get_env_var("PATH")
        assert len(PATH1.split(":")) == len(PATH5.split(":"))
        # assert PATH1 == PATH5  # cygpath may "resolve" paths

        # Test auto_stack
        sh.sendline(sh.activator.export_var_tmpl % ("CONDA_AUTO_STACK", "1"))

        sh.sendline(f'conda {activate} "{prefix3}"')
        sh.assert_env_var("CONDA_SHLVL", "2")
        PATH2 = sh.get_env_var("PATH")
        assert "charizard" in PATH2
        assert "venusaur" in PATH2
        assert len(PATH0.split(":")) + nprefix2 + nprefix3 == len(PATH2.split(":"))

        sh.sendline(f'conda {activate} "{prefix_p}"')
        sh.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = sh.get_env_var("PATH")
        assert "charizard" in PATH3
        assert "venusaur" not in PATH3
        assert len(PATH0.split(":")) + nprefix2 + nprefix == len(PATH3.split(":"))


@PARAMETRIZE_POSIX
@pytest.mark.skipif(on_win, reason="Temporary skip, larger refactor necessary")
def test_bash_activate_error(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    context.dev = True
    with shell.interactive() as sh:
        sh.sendline("export CONDA_SHLVL=unaffected")
        if on_win:
            sh.sendline("uname -o")
            sh.expect("(Msys|Cygwin)")
        sh.sendline("conda activate environment-not-found-doesnt-exist")
        sh.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        sh.assert_env_var("CONDA_SHLVL", "unaffected")

        sh.sendline("conda activate -h blah blah")
        sh.expect("usage: conda activate")


@pytest.mark.parametrize(
    "shell",
    [
        pytest.param("ash", marks=pytest.mark.skip("sourcing ignores arguments")),
        "bash",
        pytest.param("dash", marks=pytest.mark.skip("sourcing ignores arguments")),
        pytest.param(
            "zsh",
            marks=pytest.mark.skipif(on_win, reason="unavailable on Windows"),
        ),
    ],
    indirect=True,
)
def test_legacy_activate_deactivate_bash(
    shell_wrapper_integration: tuple[str, str, str],
    shell: Shell,
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with shell.interactive() as sh:
        CONDA_ROOT = Path(CONDA_PACKAGE_ROOT)
        activate = sh.path_conversion(CONDA_ROOT / "shell" / "bin" / "activate")
        deactivate = sh.path_conversion(CONDA_ROOT / "shell" / "bin" / "deactivate")
        prefix2_p = sh.path_conversion(prefix2)
        prefix3_p = sh.path_conversion(prefix3)
        sh.sendline(f"export _CONDA_ROOT='{CONDA_ROOT}/shell'")
        sh.sendline(f'. "{activate}" {dev_arg} "{prefix2_p}"')
        PATH0 = sh.get_env_var("PATH")
        assert "charizard" in PATH0

        sh.sendline("type conda")
        sh.expect(is_a_function(sh))

        sh.sendline("conda --version")
        sh.expect_exact(f"conda {CONDA_VERSION}")

        sh.sendline(f'. "{activate}" {dev_arg} "{prefix3_p}"')

        PATH1 = sh.get_env_var("PATH")
        assert "venusaur" in PATH1

        sh.sendline(f'. "{deactivate}"')
        PATH2 = sh.get_env_var("PATH")
        assert "charizard" in PATH2

        sh.sendline(f'. "{deactivate}"')
        sh.assert_env_var("CONDA_SHLVL", "0")


@PARAMETRIZE_POSIX
@pytest.mark.parametrize("force_uppercase", [True, False])
def test_envvars_force_uppercase_integration(
    shell: Shell,
    force_uppercase: bool,
    test_envvars_case,
):
    """
    Integration test for envvars_force_uppercase across POSIX shells.

    Regression test for: https://github.com/conda/conda/issues/14934
    Fixed in: https://github.com/conda/conda/pull/14942
    """
    test_envvars_case(shell, force_uppercase)
