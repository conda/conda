# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.common.compat import on_linux, on_mac, on_win
from conda.testing.integration import SPACER_CHARACTER

from .. import TEST_RECIPES_CHANNEL

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest import FixtureRequest, TempPathFactory

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture

    from . import Shell


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
    "shell",
    [
        pytest.param(
            "cmd.exe",
            marks=[
                pytest.mark.skipif(on_linux, reason="unavailable on Linux"),
                pytest.mark.skipif(on_mac, reason="unavailable on macOS"),
            ],
        ),
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
def test_activate_deactivate_modify_path(
    test_recipes_channel: Path,
    shell: Shell,
    prefix: Path,
    conda_cli: CondaCLIFixture,
):
    original_path = os.environ.get("PATH")
    conda_cli(
        "install",
        *("--prefix", prefix),
        "activate_deactivate_package",
        "--yes",
    )

    with shell.interactive() as sh:
        sh.sendline(f'conda activate "{prefix}"')
        activated_env_path = sh.get_env_var("PATH")
        sh.sendline("conda deactivate")

    assert "teststringfromactivate/bin/test" in activated_env_path
    assert original_path == os.environ.get("PATH")


@dataclass
class Env:
    name: str
    prefix: Path | None = None
    paths: tuple[Path, ...] | None = None

    def __post_init__(self):
        if self.paths is None:
            paths = [
                self.prefix / "Scripts" / "small.bat" if on_win else None,
                self.prefix / "bin" / "small",
            ]
            self.paths = filter(Path.exists, filter(None, paths))


@pytest.fixture(scope="module")
def stacking_envs(session_tmp_env: TmpEnvFixture) -> dict[str, Env]:
    # create envs using full path to avoid solver
    path = TEST_RECIPES_CHANNEL / "noarch" / "small-executable-1.0.0-0.tar.bz2"
    with (
        session_tmp_env(path) as base_env,
        session_tmp_env(path) as has_env,
        # use --offline for empty env to avoid HTTP hit
        session_tmp_env("--offline") as not_env,
    ):
        return {
            "sys": Env("sys", paths=()),
            "base": Env("base", prefix=base_env),
            "has": Env("has", prefix=has_env),
            "not": Env("not", prefix=not_env),
        }


@pytest.fixture
def stack(request: FixtureRequest, stacking_envs: dict[str, Env]) -> tuple[Env, ...]:
    envs = request.param.split(",") if request.param else ()
    return tuple(stacking_envs[env] for env in envs)


@pytest.fixture
def run(request: FixtureRequest, stacking_envs: dict[str, Env]) -> Env:
    return stacking_envs[request.param]


@pytest.fixture
def expected(request: FixtureRequest, stacking_envs: dict[str, Env]) -> tuple[Env, ...]:
    envs = request.param.split(",") if request.param else ()
    return tuple(stacking_envs[env] for env in envs)


# TODO: test stacking on all shells
# see https://github.com/conda/conda/pull/11257#issuecomment-1050531320
@pytest.mark.parametrize(
    "auto_stack,stack,run,expected",
    [
        # no environments activated
        (0, None, "base", "base,sys"),
        (0, None, "has", "has,sys"),
        (0, None, "not", "sys"),
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
    indirect=["stack", "run", "expected"],
)
def test_stacking(
    auto_stack: int,
    stack: tuple[Env, ...],
    run: Env,
    expected: tuple[Env, ...],
    shell: Shell,
) -> None:
    which = f"{'where' if on_win else 'which -a'} small"
    with shell.interactive() as sh:
        sh.sendline(sh.activator.set_var_tmpl % ("CONDA_AUTO_STACK", auto_stack))
        for env in stack:
            sh.sendline(f'conda activate "{env.prefix}"')

        sh.sendline(f'conda run --prefix="{run.prefix}" {which}')
        if not expected:
            sh.expect_exact(f"'conda run {which}' failed")
        else:
            for env in expected:
                for path in env.paths:
                    sh.expect_exact(str(path))
