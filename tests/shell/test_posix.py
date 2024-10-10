# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from logging import getLogger
from pathlib import Path

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda import __version__ as CONDA_VERSION
from conda.base.context import context
from conda.common.compat import on_win

from . import (
    ACTIVATE_ARGS,
    DEACTIVATE_ARGS,
    DEV_ARG,
    HDF5_VERSION,
    INSTALL_ARGS,
    SKIPIF_ON_MAC,
    SKIPIF_ON_WIN,
    InteractiveShell,
)

log = getLogger(__name__)
pytestmark = pytest.mark.integration
PARAMETRIZE_POSIX = pytest.mark.parametrize(
    "shell",
    [
        pytest.param("ash", marks=[SKIPIF_ON_MAC, SKIPIF_ON_WIN]),
        "bash",
        pytest.param("dash", marks=SKIPIF_ON_WIN),
        pytest.param("zsh", marks=SKIPIF_ON_WIN),
    ],
    indirect=True,
)


@PARAMETRIZE_POSIX
def test_shell_available(shell: str) -> None:
    # the fixture does all the work
    pass


@PARAMETRIZE_POSIX
def test_basic_integration(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        case = str.lower if on_win else str

        prefix_p = interactive.path_conversion(prefix)
        prefix2_p = interactive.path_conversion(prefix2)
        interactive.path_conversion(prefix3)

        base_paths = len(tuple(interactive.activator._get_path_dirs(sys.prefix)))
        prefix_paths = len(tuple(interactive.activator._get_path_dirs(prefix)))
        prefix2_paths = len(tuple(interactive.activator._get_path_dirs(prefix2)))
        prefix3_paths = len(tuple(interactive.activator._get_path_dirs(prefix3)))

        PATH0 = interactive.get_env_var("PATH", "")
        assert any(path.endswith("condabin") for path in PATH0.split(":"))

        interactive.assert_env_var("CONDA_SHLVL", "0")
        # Remove sys.prefix from PATH. It interferes with path entry count tests.
        # We can no longer check this since we'll replace e.g. between 1 and N path
        # entries with N of them in _replace_prefix_in_path() now. It is debatable
        # whether it should be here at all too.
        if PATH0.startswith(interactive.path_conversion(sys.prefix) + ":"):
            PATH0 = PATH0[len(interactive.path_conversion(sys.prefix)) + 1 :]
            interactive.sendline(f'export PATH="{PATH0}"')
            PATH0 = interactive.get_env_var("PATH", "")
        interactive.sendline("type conda")
        interactive.expect(interactive.is_a_function)

        _CE_M = interactive.get_env_var("_CE_M")
        _CE_CONDA = interactive.get_env_var("_CE_CONDA")

        interactive.sendline("conda --version")
        interactive.expect_exact(f"conda {CONDA_VERSION}")

        interactive.sendline(f"conda {ACTIVATE_ARGS} base")

        interactive.sendline("type conda")
        interactive.expect(interactive.is_a_function)

        CONDA_EXE2 = case(interactive.get_env_var("CONDA_EXE"))
        _CE_M2 = interactive.get_env_var("_CE_M")

        interactive.assert_env_var("PS1", "(base).*")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        PATH1 = interactive.get_env_var("PATH", "")
        assert len(PATH0.split(":")) + base_paths == len(PATH1.split(":"))

        CONDA_EXE = case(interactive.get_env_var("CONDA_EXE"))
        _CE_M = interactive.get_env_var("_CE_M")
        _CE_CONDA = interactive.get_env_var("_CE_CONDA")

        log.debug("activating ..")
        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix_p}"')

        interactive.sendline("type conda")
        interactive.expect(interactive.is_a_function)

        CONDA_EXE2 = case(interactive.get_env_var("CONDA_EXE"))
        _CE_M2 = interactive.get_env_var("_CE_M")
        _CE_CONDA2 = interactive.get_env_var("_CE_CONDA")
        assert CONDA_EXE == CONDA_EXE2
        assert _CE_M == _CE_M2
        assert _CE_CONDA == _CE_CONDA2

        interactive.sendline("env | sort")
        # When CONDA_SHLVL==2 fails it usually means that conda activate failed. We that fails it is
        # usually because you forgot to pass `--dev` to the *previous* activate so CONDA_EXE changed
        # from python to conda, which is then found on PATH instead of using the dev sources. When it
        # goes to use this old conda to generate the activation script for the newly activated env.
        # it is running the old code (or at best, a mix of new code and old scripts).
        interactive.assert_env_var("CONDA_SHLVL", "2")
        CONDA_PREFIX = interactive.get_env_var("CONDA_PREFIX", "")
        # We get C: vs c: differences on Windows.
        # Also, self.prefix instead of prefix_p is deliberate (maybe unfortunate?)
        assert CONDA_PREFIX.lower() == prefix.lower()
        PATH2 = interactive.get_env_var("PATH", "")
        assert len(PATH0.split(":")) + prefix_paths == len(PATH2.split(":"))

        interactive.sendline("env | sort | grep CONDA")
        interactive.expect("CONDA_")
        interactive.sendline('echo "PATH=$PATH"')
        interactive.expect("PATH=")
        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix2_p}"')
        interactive.sendline("env | sort | grep CONDA")
        interactive.expect("CONDA_")
        interactive.sendline('echo "PATH=$PATH"')
        interactive.expect("PATH=")
        interactive.assert_env_var("PS1", "(charizard).*")
        interactive.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = interactive.get_env_var("PATH")
        assert len(PATH0.split(":")) + prefix2_paths == len(PATH3.split(":"))

        CONDA_EXE2 = case(interactive.get_env_var("CONDA_EXE"))
        _CE_M2 = interactive.get_env_var("_CE_M")
        _CE_CONDA2 = interactive.get_env_var("_CE_CONDA")
        assert CONDA_EXE == CONDA_EXE2
        assert _CE_M == _CE_M2
        assert _CE_CONDA == _CE_CONDA2

        interactive.sendline(f"conda {INSTALL_ARGS} -yq hdf5={HDF5_VERSION}")
        interactive.expect(
            r"Executing transaction: ...working... done.*\n", timeout=180
        )
        interactive.assert_env_var("?", "0", use_exact=True)

        interactive.sendline("h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # TODO: assert that reactivate worked correctly

        interactive.sendline("type conda")
        interactive.expect(interactive.is_a_function)

        interactive.sendline(f"conda run {DEV_ARG} h5stat --version")
        interactive.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # regression test for #6840
        interactive.sendline(f"conda {INSTALL_ARGS} --blah")
        interactive.assert_env_var("?", "2", use_exact=True)
        interactive.sendline("conda list --blah")
        interactive.assert_env_var("?", "2", use_exact=True)

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "2")
        PATH = interactive.get_env_var("PATH")
        assert len(PATH0.split(":")) + prefix_paths == len(PATH.split(":"))

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        PATH = interactive.get_env_var("PATH")
        assert len(PATH0.split(":")) + base_paths == len(PATH.split(":"))

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "0")
        PATH = interactive.get_env_var("PATH")
        assert len(PATH0.split(":")) == len(PATH.split(":"))
        # assert PATH0 == PATH  # cygpath may "resolve" paths

        interactive.sendline(interactive.print_env_var % "PS1")
        interactive.clear()
        assert "CONDA_PROMPT_MODIFIER" not in str(interactive.p.after)

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "0")

        # When fully deactivated, CONDA_EXE, _CE_M and _CE_CONDA must be retained
        # because the conda shell scripts use them and if they are unset activation
        # is not possible.
        CONDA_EXED = case(interactive.get_env_var("CONDA_EXE"))
        assert CONDA_EXED, (
            "A fully deactivated conda shell must retain CONDA_EXE (and _CE_M and _CE_CONDA in dev)\n"
            "  as the shell scripts refer to them."
        )

        PATH0 = interactive.get_env_var("PATH")

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix2_p}"')
        interactive.assert_env_var("CONDA_SHLVL", "1")
        PATH1 = interactive.get_env_var("PATH")
        assert len(PATH0.split(":")) + prefix2_paths == len(PATH1.split(":"))

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix3}" --stack')
        interactive.assert_env_var("CONDA_SHLVL", "2")
        PATH2 = interactive.get_env_var("PATH")
        assert "charizard" in PATH2
        assert "venusaur" in PATH2
        assert len(PATH0.split(":")) + prefix2_paths + prefix3_paths == len(
            PATH2.split(":")
        )

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix_p}"')
        interactive.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = interactive.get_env_var("PATH")
        assert "charizard" in PATH3
        assert "venusaur" not in PATH3
        assert len(PATH0.split(":")) + prefix2_paths + prefix_paths == len(
            PATH3.split(":")
        )

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "2")
        PATH4 = interactive.get_env_var("PATH")
        assert "charizard" in PATH4
        assert "venusaur" in PATH4
        assert len(PATH4.split(":")) == len(PATH2.split(":"))
        # assert PATH4 == PATH2  # cygpath may "resolve" paths

        interactive.sendline(f"conda {DEACTIVATE_ARGS}")
        interactive.assert_env_var("CONDA_SHLVL", "1")
        PATH5 = interactive.get_env_var("PATH")
        assert len(PATH1.split(":")) == len(PATH5.split(":"))
        # assert PATH1 == PATH5  # cygpath may "resolve" paths

        # Test auto_stack
        interactive.sendline(
            interactive.activator.export_var_tmpl % ("CONDA_AUTO_STACK", "1")
        )

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix3}"')
        interactive.assert_env_var("CONDA_SHLVL", "2")
        PATH2 = interactive.get_env_var("PATH")
        assert "charizard" in PATH2
        assert "venusaur" in PATH2
        assert len(PATH0.split(":")) + prefix2_paths + prefix3_paths == len(
            PATH2.split(":")
        )

        interactive.sendline(f'conda {ACTIVATE_ARGS} "{prefix_p}"')
        interactive.assert_env_var("CONDA_SHLVL", "3")
        PATH3 = interactive.get_env_var("PATH")
        assert "charizard" in PATH3
        assert "venusaur" not in PATH3
        assert len(PATH0.split(":")) + prefix2_paths + prefix_paths == len(
            PATH3.split(":")
        )


@PARAMETRIZE_POSIX
@pytest.mark.skipif(on_win, reason="Temporary skip, larger refactor necessary")
def test_bash_activate_error(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    context.dev = True
    with InteractiveShell(shell) as interactive:
        interactive.sendline("export CONDA_SHLVL=unaffected")
        if on_win:
            interactive.sendline("uname -o")
            interactive.expect("(Msys|Cygwin)")
        interactive.sendline("conda activate environment-not-found-doesnt-exist")
        interactive.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        interactive.assert_env_var("CONDA_SHLVL", "unaffected")

        interactive.sendline("conda activate -h blah blah")
        interactive.expect("usage: conda activate")


@pytest.mark.parametrize(
    "shell",
    [
        pytest.param("ash", marks=pytest.mark.skip("sourcing ignores arguments")),
        "bash",
        pytest.param("dash", marks=pytest.mark.skip("sourcing ignores arguments")),
        pytest.param("zsh", marks=SKIPIF_ON_WIN),
    ],
    indirect=True,
)
def test_legacy_activate_deactivate_bash(
    shell_wrapper_integration: tuple[str, str, str], shell: str
) -> None:
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell(shell) as interactive:
        CONDA_ROOT = Path(CONDA_PACKAGE_ROOT)
        activate = interactive.path_conversion(
            CONDA_ROOT / "shell" / "bin" / "activate"
        )
        deactivate = interactive.path_conversion(
            CONDA_ROOT / "shell" / "bin" / "deactivate"
        )

        prefix2_p = interactive.path_conversion(prefix2)
        prefix3_p = interactive.path_conversion(prefix3)

        interactive.sendline(f"export _CONDA_ROOT='{CONDA_ROOT}/shell'")
        interactive.sendline(f'. "{activate}" {DEV_ARG} "{prefix2_p}"')
        PATH0 = interactive.get_env_var("PATH")
        assert "charizard" in PATH0

        interactive.sendline("type conda")
        interactive.expect(interactive.is_a_function)

        interactive.sendline("conda --version")
        interactive.expect_exact(f"conda {CONDA_VERSION}")

        interactive.sendline(f'. "{activate}" {DEV_ARG} "{prefix3_p}"')

        PATH1 = interactive.get_env_var("PATH")
        assert "venusaur" in PATH1

        interactive.sendline(f'. "{deactivate}"')
        PATH2 = interactive.get_env_var("PATH")
        assert "charizard" in PATH2

        interactive.sendline(f'. "{deactivate}"')
        interactive.assert_env_var("CONDA_SHLVL", "0")
