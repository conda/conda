# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Startup performance benchmarks tracked by CodSpeed.

Measures the cost of conda's startup phases.  Instrumented by CodSpeed in
CI (CPU instruction counting) and runnable locally with
``pytest --codspeed tests/cli/test_startup_benchmarks.py``.

Import benchmarks use ``benchmark.pedantic`` with a setup function that
scrubs cached modules between rounds so each iteration starts from a clean
``sys.modules``.  Function benchmarks measure repeatedly-callable startup
functions.  Module-count guardrails use a subprocess for a clean interpreter
and fail when a phase exceeds its module budget.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.cli.conda_argparse import generate_parser
from conda.cli.main import main

if TYPE_CHECKING:
    from typing import TypedDict

    from pytest_codspeed.plugin import BenchmarkFixture

    class _BudgetSpec(TypedDict):
        code: str
        max_modules: int


pytestmark = pytest.mark.benchmark

# Packages the test runner needs — never remove these from sys.modules.
_TEST_INFRA = frozenset(
    {
        "_pytest",
        "coverage",
        "iniconfig",
        "pluggy",
        "py",
        "pytest",
        "pytest_codspeed",
        "pytest_cov",
        "pytest_mock",
        "pytest_split",
        "pytest_timeout",
        "pytest_xprocess",
        "xprocess",
    }
)


def _clean_modules() -> None:
    """Remove all non-stdlib, non-test-infra modules from ``sys.modules``.

    Uses ``sys.stdlib_module_names`` (Python 3.10+) to identify stdlib
    packages, keeping those and the test runner intact.  Everything else
    — conda and all its transitive dependencies regardless of how they
    were installed — gets removed so import benchmarks start clean.
    """
    stdlib = sys.stdlib_module_names
    to_remove = [
        k
        for k in sys.modules
        if (top := k.split(".")[0]) not in stdlib and top not in _TEST_INFRA
    ]
    for k in to_remove:
        del sys.modules[k]


def _pedantic_setup() -> tuple[tuple[()], dict[str, object]]:
    _clean_modules()
    return (), {}


def test_import_cli_main(benchmark: BenchmarkFixture) -> None:
    """Cost of ``from conda.cli.main import main``."""

    def target() -> object:
        from conda.cli.main import main

        return main

    benchmark.pedantic(target, setup=_pedantic_setup, rounds=5, warmup_rounds=1)


def test_import_context(benchmark: BenchmarkFixture) -> None:
    """Cost of importing ``conda.base.context.context``."""

    def target() -> object:
        from conda.base.context import context

        return context

    benchmark.pedantic(target, setup=_pedantic_setup, rounds=5, warmup_rounds=1)


def test_import_conda_argparse(benchmark: BenchmarkFixture) -> None:
    """Cost of importing ``conda.cli.conda_argparse``."""

    def target() -> object:
        from conda.cli.conda_argparse import generate_parser

        return generate_parser

    benchmark.pedantic(target, setup=_pedantic_setup, rounds=5, warmup_rounds=1)


def test_context_init(benchmark: BenchmarkFixture) -> None:
    """Cost of ``context.__init__()`` (config loading)."""
    benchmark(context.__init__)


def test_generate_parser(benchmark: BenchmarkFixture) -> None:
    """Cost of building the full CLI argument parser."""
    context.__init__()
    benchmark(generate_parser, add_help=True)


def test_version_main(benchmark: BenchmarkFixture) -> None:
    """Cost of ``conda --version`` through ``main()``."""

    def run_version() -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                main("--version")
            except SystemExit:
                pass

    benchmark(run_version)


# Module-count budgets: these should ratchet *down* as startup is optimised.
# Headroom accounts for cross-platform differences (Linux CI with Python 3.14
# and full plugin set loads more modules than a local macOS devenv).
_MODULE_BUDGETS: dict[str, _BudgetSpec] = {
    "import_main": {
        "code": "from conda.cli.main import main",
        "max_modules": 450,
    },
    "import_context": {
        "code": (
            "from conda.cli.main import main\nfrom conda.base.context import context"
        ),
        "max_modules": 650,
    },
    "full_startup": {
        "code": (
            "import contextlib, io\n"
            "from conda.cli.main import main\n"
            "with contextlib.redirect_stdout(io.StringIO()):\n"
            "    try:\n"
            "        main('--version')\n"
            "    except SystemExit:\n"
            "        pass"
        ),
        "max_modules": 900,
    },
}


@pytest.mark.parametrize(
    ("phase", "spec"),
    _MODULE_BUDGETS.items(),
    ids=_MODULE_BUDGETS,
)
def test_module_count_budget(phase: str, spec: _BudgetSpec) -> None:
    """Guard against accidental dependency additions in the startup path."""
    snippet = f"import sys\n{spec['code']}\nprint(len(sys.modules))"
    result = subprocess.run(
        [sys.executable, "-Xfrozen_modules=on", "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    count = int(result.stdout.strip())
    assert count <= spec["max_modules"], (
        f"Phase '{phase}' loaded {count} modules, "
        f"budget is {spec['max_modules']}. "
        f"A new import was likely added to the startup path."
    )
