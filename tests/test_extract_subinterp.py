"""
Test how well subinterpreters work for package extraction.
"""

from __future__ import annotations

from concurrent.futures import as_completed
from concurrent.futures.interpreter import InterpreterPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from random import Random
from typing import TYPE_CHECKING

import pytest
from conda_package_streaming.extract import extract

if TYPE_CHECKING:
    from concurrent.futures import Executor

    import pytest_benchmark.fixture

SEED = 1
PACKAGES = [
    p
    for p in Path("~/miniconda3/pkgs").expanduser().glob("*")
    if str(p).endswith((".tar.bz2", ".conda"))
]
CONDA_PACKAGES = 10
TARBZ2_PACKAGES = 10


@pytest.mark.parametrize("Executor", [ThreadPoolExecutor, InterpreterPoolExecutor])
@pytest.mark.parametrize("threads", [1, 2, 3, 6, 12])
@pytest.mark.parametrize("format", [(".tar.bz2", ".conda"), (".conda",)])
@pytest.mark.benchmark(min_rounds=1)
def test_subinterpreter(
    tmp_path,
    benchmark: pytest_benchmark.fixture.BenchmarkFixture,
    Executor: Executor,
    threads,
    format,
):
    random = Random(SEED)
    to_extract = random.choices([p for p in PACKAGES if p.name.endswith(format)], k=20)
    import pprint

    pprint.pprint(to_extract)
    print("Size", sum(p.stat().st_size for p in to_extract))

    def run():
        futures = {}
        with Executor(threads) as executor:
            for package in to_extract:
                futures[
                    executor.submit(extract, str(package), str(tmp_path / package.name))
                ] = package.name

            for future in as_completed(futures):
                try:
                    assert future.result() is None
                    print("Extracted", futures[future])
                except Exception as e:
                    print("Error", futures[future], e)
    benchmark(run)
