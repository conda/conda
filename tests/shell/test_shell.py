# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from shutil import which
from subprocess import check_output
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.base.context import context
from conda.common.compat import on_win
from conda.testing.integration import SPACER_CHARACTER

from . import InteractiveShell
from .test_posix import skip_unsupported_bash

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from pytest import TempPathFactory

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


log = getLogger(__name__)
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def prefix(tmp_path_factory: TempPathFactory) -> Iterator[Path]:
    name = f"{uuid4().hex[:4]}{SPACER_CHARACTER}{uuid4().hex[:4]}"
    root = tmp_path_factory.mktemp(name)

    (root / "conda-meta").mkdir(parents=True)
    (root / "conda-meta" / "history").touch()

    prefix = root / "envs" / "charizard"

    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "conda-meta" / "history").touch()

    yield prefix


@pytest.mark.parametrize(
    ["shell"],
    [
        pytest.param(
            "bash",
            marks=skip_unsupported_bash,
        ),
        pytest.param(
            "cmd.exe",
            marks=pytest.mark.skipif(
                not which("cmd.exe"), reason="cmd.exe not installed"
            ),
        ),
    ],
)
def test_activate_deactivate_modify_path(
    test_recipes_channel: Path,
    shell,
    prefix,
    conda_cli: CondaCLIFixture,
):
    original_path = os.environ.get("PATH")
    conda_cli(
        "install",
        *("--prefix", prefix),
        "activate_deactivate_package",
        "--yes",
    )

    with InteractiveShell(shell) as sh:
        sh.sendline(f'conda activate "{prefix}"')
        activated_env_path = sh.get_env_var("PATH")
        sh.sendline("conda deactivate")

    assert "teststringfromactivate/bin/test" in activated_env_path
    assert original_path == os.environ.get("PATH")


@pytest.fixture
def create_stackable_envs(
    tmp_env: TmpEnvFixture,
) -> Iterator[tuple[str, dict[str, Any]]]:
    # generate stackable environments, two with curl and one without curl
    which = f"{'where' if on_win else 'which -a'} curl"

    class Env:
        def __init__(self, prefix=None, paths=None):
            self.prefix = Path(prefix) if prefix else None

            if not paths:
                if on_win:
                    path = self.prefix / "Library" / "bin" / "curl.exe"
                else:
                    path = self.prefix / "bin" / "curl"

                paths = (path,) if path.exists() else ()
            self.paths = paths

    sys = _run_command(
        "conda config --set auto_activate_base false",
        which,
    )

    with tmp_env("curl") as base, tmp_env("curl") as haspkg, tmp_env() as notpkg:
        yield (
            which,
            {
                "sys": Env(paths=sys),
                "base": Env(prefix=base),
                "has": Env(prefix=haspkg),
                "not": Env(prefix=notpkg),
            },
        )


def _run_command(*lines):
    # create a custom run command since this is specific to the shell integration
    if on_win:
        join = " && ".join
        source = f"{Path(context.root_prefix, 'condabin', 'conda_hook.bat')}"
    else:
        join = "\n".join
        source = f". {Path(context.root_prefix, 'etc', 'profile.d', 'conda.sh')}"

    marker = uuid4().hex
    script = join((source, *(["conda deactivate"] * 5), f"echo {marker}", *lines))
    output = check_output(script, shell=True).decode().splitlines()
    output = list(map(str.strip, output))
    output = output[output.index(marker) + 1 :]  # trim setup output

    return [Path(path) for path in filter(None, output)]


# see https://github.com/conda/conda/pull/11257#issuecomment-1050531320
@pytest.mark.parametrize(
    ("auto_stack", "stack", "run", "expected"),
    [
        # no environments activated
        (0, "", "base", "base,sys"),
        (0, "", "has", "has,sys"),
        (0, "", "not", "sys"),
        # one environment activated, no stacking
        (0, "base", "base", "base,sys"),
        (0, "base", "has", "has,sys"),
        (0, "base", "not", "sys"),
        (0, "has", "base", "base,sys"),
        (0, "has", "has", "has,sys"),
        (0, "has", "not", "sys"),
        (0, "not", "base", "base,sys"),
        (0, "not", "has", "has,sys"),
        (0, "not", "not", "sys"),
        # one environment activated, stacking allowed
        (5, "base", "base", "base,sys"),
        (5, "base", "has", "has,base,sys"),
        (5, "base", "not", "base,sys"),
        (5, "has", "base", "base,has,sys"),
        (5, "has", "has", "has,sys"),
        (5, "has", "not", "has,sys"),
        (5, "not", "base", "base,sys"),
        (5, "not", "has", "has,sys"),
        (5, "not", "not", "sys"),
        # two environments activated, stacking allowed
        (5, "base,has", "base", "base,has,sys" if on_win else "base,has,base,sys"),
        (5, "base,has", "has", "has,base,sys"),
        (5, "base,has", "not", "has,base,sys"),
        (5, "base,not", "base", "base,sys" if on_win else "base,base,sys"),
        (5, "base,not", "has", "has,base,sys"),
        (5, "base,not", "not", "base,sys"),
    ],
)
def test_stacking(
    create_stackable_envs: tuple[str, dict[str, Any]],
    auto_stack: int,
    stack: str,
    run: str,
    expected: str,
) -> None:
    which, envs = create_stackable_envs
    assert _run_command(
        f"conda config --set auto_stack {auto_stack}",
        *(
            f'conda activate "{envs[env.strip()].prefix}"'
            for env in filter(None, stack.split(","))
        ),
        f'conda run -p "{envs[run.strip()].prefix}" {which}',
    ) == [
        path
        for env in filter(None, expected.split(","))
        for path in envs[env.strip()].paths
    ]
