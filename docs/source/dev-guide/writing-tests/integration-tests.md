# Integration Tests

Integration tests in `conda` test the application from a high level where each test can
potentially cover large portions of the code. These tests may also use the local
file system and/or perform network calls. In the following sections, we cover
several examples of exactly how these tests look. When writing your own integration tests,
these should serve as a good starting point.

## `conda_cli` Fixture: Running CLI level tests

CLI level tests are the highest level integration tests you can write. This means that the
code in the test is executed as if you were running it from the command line. For example,
you may want to write a test to confirm that an environment is created after successfully
running `conda create`. A test like this would look like the following:

```{code-block} python
:linenos:
:name: test-conda-create-1
:caption: Integration test for `conda create`
import json
from pathlib import Path

from conda.testing.integration import CondaCLIFixture


def test_conda_create(conda_cli: CondaCLIFixture, tmp_path: Path):
    # setup, create environment
    out, err, code = conda_cli("create", "--prefix", tmp_path, "--yes")

    assert f"conda activate {tmp_path}" in out
    assert not err  # no errors
    assert not code  # success!

    # verify everything worked using the `conda env list` command
    out, err, code = conda_cli("env", "list", "--json")

    assert any(
        tmp_path.samefile(path)
        for path in json.loads(out).get("envs", [])
    )
    assert not err  # no errors
    assert not code  # success!

    # cleanup, remove environment
    out, err, code = conda_cli("remove", "--all", "--prefix", tmp_path)

    assert out
    assert not err  # no errors
    assert not code  # success!
```

Let's break down exactly what is going on in the code snippet above:

First, we rely on a fixture (`conda_cli`) that allows us to run a command using the
current running process. This is much more efficient and quicker than running CLI tests
via subprocesses.

In the test itself, we first create a new environment by effectively running
`conda create`. This function returns the standard out, standard error, and the exit
code of the command. This allows us to perform our inspections in order to determine
whether the command ran successfully.

The second part of the test again uses the `conda_cli` fixture to call `conda env list`.
This time, we pass the `--json` flag, which allows capturing JSON that we can better
parse and more easily inspect. We then assert whether the environment we just created is
actually in the list of environments available.

Finally, we destroy the environment we just created and ensure the standard error and
the exit code are what we expect them to be.

:::{warning}
It is preferred to use temporary directories (e.g., `tmp_path`) whenever possible for
automatic cleanup after tests are run. Otherwise, remember to remove anything created
during the test since it will be present when other tests are run and may result in
unexpected race conditions.
:::

## `tmp_env` Fixture: Creating a temporary environment

The `tmp_env` fixture is a convenient way to create a temporary environment for use in
tests:

```{code-block} python
:linenos:
:name: test-conda-environment-with-numpy
:caption: Integration test for creating an environment with `numpy`
from conda.testing.integration import CondaCLIFixture, TmpEnvFixture


def test_environment_with_numpy(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("numpy") as prefix:
        out, err, code = conda_cli("list", "--prefix", prefix)

        assert out
        assert not err  # no error
        assert not code  # success!
```

## `path_factory` Fixture: Creating a unique (non-existing) path

The `path_factory` fixture extends pytest's tmp_path fixture to provide unique, unused
paths. This makes it easier to generate new paths in tests:

```{code-block} python
:linenos:
:name: test-conda-rename
:caption: Integration test for renaming an environment
from conda.testing.integration import (
    CondaCLIFixture,
    PathFactoryFixture,
    TmpEnvFixture,
)


def test_conda_rename(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    # each call to `path_factory` returns a unique path
    assert path_factory() != path_factory()

    # each call to `path_factory` returns a path that is a child of `tmp_path`
    assert path_factory().parent == path_factory().parent == tmp_path

    with tmp_env() as prefix:
        out, err, code = conda_cli("rename", "--prefix", prefix, path_factory())

        assert out
        assert not err  # no error
        assert not code  # success!
```

## Tests with fixtures

Sometimes in integration tests, you may want to re-use the same type of environment more
than once. Copying and pasting this setup and teardown code into each individual test
can make these tests more difficult to read and harder to maintain.

To overcome this, `conda` tests make extensive use of `pytest` fixtures. Below is an
example of the previously-shown test, except that we now make the focus of the test the
`conda env list` command and move the creation and removal of the environment into a
fixture:

```{code-block} python
:linenos:
:name: test-conda-create-2
:caption: Integration test for `conda create`
import json
from pathlib import Path

from conda.testing.integration import CondaCLIFixture


@pytest.fixture
def env_one(tmp_env: TmpEnvFixture) -> Path:
    with tmp_env() as prefix:
        yield prefix


def test_conda_create(env_one: Path, conda_cli: CondaCLIFixture):
    # verify everything worked using the `conda env list` command
    out, err, code = conda_cli("env", "list", "--json")

    assert any(
        env_one.samefile(path)
        for path in json.loads(out).get("envs", [])
    )
    assert not err  # no errors
    assert not code  # success!
```

In the fixture named `env_one`, we create a new environment using the `tmp_env` fixture.
We yield to mark the end of the setup. Since the `tmp_env` fixture extends `tmp_path` no
additional teardown is needed.

This fixture will be run using the default scope in `pytest`, which is `function`. This
means that the setup and teardown will occur before and after each test that requests this
fixture. If you need to share an environment or other pieces of data between tests, just
remember to set the fixture scope appropriately. [Read here][pytest-scope] for more
information on `pytest` fixture scopes.

[pytest-scope]: https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
