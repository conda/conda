# Benchmarks

Conda uses [pytest-benchmark](https://pytest-benchmark.readthedocs.io/en/stable/)
to measure performance and [Bencher](https://bencher.dev/perf/conda-tdj8rt90)
to track measurements across commits.

## Run locally

From the repository root, activate the
{doc}`development environment <../development-environment>` and install
pytest-benchmark. For Bash, use Python 3.14 and Miniconda to match the current CI
configuration:

```bash
source ./dev/start -p 3.14 -i miniconda
conda install --yes "pytest-benchmark>=5.1.0"
python -m pytest -m benchmark
```

Append a path or a pytest filter such as `-k test_generate_parser` to run a smaller
selection. Run without coverage or parallel workers, which can affect timings.

To export the measurements as JSON, use:

```bash
python -m pytest -m benchmark --benchmark-json benchmark_results.json
```

The JSON file is ignored by Git. Local runs do not upload results to Bencher.
Compare commits on the same machine with the same Python version, dependencies,
and cache state. Local timings and CI timings can differ even with the same
Python environment.

## Write benchmarks

Place benchmarks alongside the tests for the code they measure. Mark each test
with `@pytest.mark.benchmark` and pass the operation to the `benchmark` fixture.
For example, measure constructing a `MatchSpec` with warm caches, then check the
result after timing:

```python
import pytest

from conda.models.match_spec import MatchSpec


@pytest.mark.benchmark
def test_match_spec_warm_cache(benchmark):
    MatchSpec("numpy")
    spec = benchmark(MatchSpec, "numpy")
    assert spec.name == "numpy"
```

Keep fixture setup and assertions outside the timed callable unless they are part
of the operation being measured. Use fixed test data and stable test names and
parameter IDs so Bencher can compare the same workload across commits.

Define whether each cache-sensitive case measures a cold or warm cache. If an
operation mutates state, reset that state between iterations. Use
[`benchmark.pedantic`](https://pytest-benchmark.readthedocs.io/en/stable/pedantic.html)
when setup must run before each round, with one iteration per round when each
iteration requires fresh state. Ensure the benchmark checks the operation's
result so an unintended no-op does not appear as a performance improvement.

## Results and regression alerts

The `linux-benchmarks` job in the
[Tests workflow](https://github.com/conda/conda/actions/workflows/tests.yml) runs on
Ubuntu 22.04 with Python 3.14 when the workflow detects code changes. Its
`benchmark-results` artifact contains the JSON measurements and is retained for
seven days. A successful overall test run can have no benchmark results if that
job was skipped.

The separate
[Track Benchmarks workflow](https://github.com/conda/conda/actions/workflows/benchmarks.yml)
uploads available results to the [Bencher project](https://bencher.dev/perf/conda-tdj8rt90).
Select `main` for the main branch or `pr-<number>` for a pull request. PR results
use the measured head commit and compare against the base branch's history.

Each testbed identifies the producer's operating system, architecture, Python
major/minor version, and CPU model. Compare results within the same testbed.
A new testbed needs its own base-branch measurements before PR regressions can be
detected. Changing the Python version or CPU model starts a separate history.

Bencher records mean latency using the `python_pytest` adapter. The latency
threshold uses a t-test with an upper threshold of `0.99` and at most 64 historical
measurements. Detected regressions fail the reporting workflow and generate PR
feedback. Inspect the affected benchmark, its testbed, and its history before
changing a threshold. See Bencher's
[threshold documentation](https://bencher.dev/docs/explanation/thresholds/) for
the statistical model.
