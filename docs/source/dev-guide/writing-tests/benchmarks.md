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
Ubuntu 24.04 with Python 3.14 when the workflow detects code changes. Its
`benchmark-results-v3` artifact contains the JSON measurements, workflow event,
dependency list, and runner diagnostics, retained for seven days. A successful
test run can have no benchmark results if that job was skipped.

The separate
[Track Benchmarks workflow](https://github.com/conda/conda/actions/workflows/benchmarks.yml)
uses the shared Bencher reporting action in
[`conda/actions`](https://github.com/conda/actions) to upload available results to the
[Bencher project](https://bencher.dev/perf/conda-tdj8rt90).
Select `main` for historical results, or the relevant feature or release branch.

PR measurements use the exact base and head commits on the same runner with
`PYTHONHASHSEED=0`, the head revision's resolved dependencies, benchmark tests,
and fixtures. Running both revisions roughly doubles the benchmark execution time.
Both results must contain the same benchmark names. If the base revision
cannot run the complete head benchmark suite, the head results remain available
and the `Benchmark measurements (informational)` check is neutral.

The reporting workflow creates a separate baseline for each PR workflow run and
attempt. Select `pr-<number>` for its comparison. This baseline never replaces the
`main` history. PR measurements are informational while the suite is stabilized.
Single-round and cache-sensitive cases, together with shared-runner noise, can
produce substantial timing changes without changes to the measured code.

The reporter disables alerts for every paired measurement and posts a neutral
`Benchmark measurements (informational)` check with links to the producer run and
Bencher. A neutral check does not establish that performance is unchanged. The
original JSON artifacts retain every measurement and benchmark name. Historical
branch alerts remain active.

Non-PR runs preserve the branch's history and use a t-test at `0.99`, with at least
10 and at most 64 historical measurements. The `0.99` value is a statistical
prediction level, not a 1% slowdown allowance. A new benchmark or testbed may have
too little history to produce an alert. Missing comparison warnings remain visible.

Testbeds include the producer's Ubuntu version, architecture, Python major/minor
version, and CPU model. Ubuntu 24.04 measurements start separate histories from
Ubuntu 22.04. Runner image versions are recorded in `runner_metadata.json` and
`bencher noise` diagnostics in `noise.txt`, alongside the raw results. Noise
measurements are diagnostic only and do not change timings or alert thresholds.

The same CPU model can still have different contention, cache state, or frequency.
Dependencies can change between workflow runs even though each base/head pair
shares an environment. Inspect the measurements and runner diagnostics before
changing a threshold. Give benchmarks new names when their timed work or fixtures
change so historical comparisons do not combine different workloads.

The versioned artifact name prevents the older reporting workflow from treating
Ubuntu 24.04 measurements as Ubuntu 22.04 results while this change is in review.
