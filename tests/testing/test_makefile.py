# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from pathlib import Path
from shutil import copyfile, which
from textwrap import indent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import Config, MonkeyPatch, Pytester

pytest_plugins = ["pytester"]


@pytest.mark.parametrize("target", ["unit", "integration"])
def test_makefile_selects_tests(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    pytestconfig: Config,
    target: str,
) -> None:
    """Run Makefile test targets against an isolated suite with strict markers."""
    make = which("make")
    if make is None or not Path("/bin/bash").is_file():
        pytest.skip("The Makefile requires make and /bin/bash.")

    copyfile(pytestconfig.rootpath / "Makefile", pytester.path / "Makefile")
    markers = indent("\n".join(pytestconfig.getini("markers")), "    ")
    pytester.makeini(
        f"[pytest]\naddopts = --strict-markers -v --color=no\nmarkers =\n{markers}\n"
    )
    pytester.makepyfile(
        test_selection="""
        import pytest

        def test_unit():
            pass

        @pytest.mark.integration
        def test_integration():
            pass
        """
    )
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent), prepend=os.pathsep)
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    result = pytester.run(make, target, timeout=30)

    assert result.ret == 0, result.stderr.str()
    result.assert_outcomes(passed=1, deselected=1)
    result.stdout.fnmatch_lines([f"*::test_{target} PASSED*"])
