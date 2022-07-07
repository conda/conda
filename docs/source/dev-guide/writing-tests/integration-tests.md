# Integration Tests

Integration tests in `conda` test the application from a high level where each test can
potentially cover large portions of the code. These tests may also use the local
file system and/or perform network calls. In the following sections, we cover
several examples of exactly how these tests look. When writing your own integration tests,
these should serve as a good starting point.

## Running CLI level tests

CLI level tests are the highest level integration tests you can write. This means that the code in
the test is executed as if you were running it from the command line. For example,
you may want to write a test to confirm that an environment is created after successfully
running `conda create`. A test like this would look like the following:

```python
import os.path
import json

from conda.testing.helpers import run_inprocess_conda_command as run

TEST_ENV_NAME_1 = "test-env-1"


def test_creates_new_environment():
    out, err, exit_code = run(f"conda create -n {TEST_ENV_NAME_1} -y")

    assert "conda activate test" in out  # ensure activation message is present
    assert err == ""  # no error messages
    assert exit_code == 0  # successful exit code

    # Perform a separate verification that everything works using the "conda env list" command
    out, err, exit_code = run("conda env list --json")
    json_out = json.loads(out)
    env_names = {os.path.basename(path) for path in json_out.get("envs", tuple())}

    assert TEST_ENV_NAME_1 in env_names

    out, err, exit_code = run(f"conda remove --all -n {TEST_ENV_NAME_1}")

    assert err == ""
    assert exit_code == 0
```

Let's break down exactly what is going on in the code snippet above:

First, we import a function called `run_inprocess_conda_command` (aliased to `run` here) that allows
us to run a command using the current running process. This ends up being much more efficient and quicker than
running this test as a subprocess.

In the test itself, we first use our `run` function to create a new environment. This function
returns the standard out, standard error, and the exit code of the command. This allows us to
perform our inspections in order to determine whether the command successfully ran.

The second part of the test again uses the `run` command to call `conda env list`. This time,
we pass the `--json` flag, which allows capturing JSON that we can better parse and more easily
inspect. We then assert whether the environment we just created is actually in the list of all
environments currently available.

Finally, we destroy the environment we just created and ensure the standard error and the exit
code are what we expect them to be. It is important to remember to remove anything you create,
as it will be present when other tests are run.

## Tests with fixtures

Sometimes in integration tests, you may want to re-use the same type of environment more than once.
Copying and pasting this setup and teardown code into each individual test can make these tests more
difficult to read and harder to maintain.

To overcome this, `conda` tests make extensive use of `pytest` fixtures. Below is an example of the
previously-shown test, except that we now make the focus of the test the `conda env list` command and move
the creation and removal of the environment into a fixture:

```python
# Writing a test for `conda env list`

import os.path
import json

import pytest

from conda.testing.helpers import run_inprocess_conda_command as run

TEST_ENV_NAME_1 = "test-env-1"


@pytest.fixture()
def env_one():
    out, err, exit_code = run(f"conda create -n {TEST_ENV_NAME_1} -y")

    assert exit_code == 0

    yield

    out, err, exit_code = run(f"conda remove --all -n {TEST_ENV_NAME_1}")

    assert exit_code == 0


def test_env_list_finds_existing_environment(env_one):
    # Because we're using fixtures, we can immediately run the `conda env list` command
    # and our test assertions
    out, err, exit_code = run("conda env list --json")
    json_out = json.loads(out)
    env_names = {os.path.basename(path) for path in json_out.get("envs", tuple())}

    assert TEST_ENV_NAME_1 in env_names
    assert err == ""
    assert exit_code == 0
```

In the fixture named `env_one`, we first create a new environment in exactly the same way as we
did in our previous test. We make an assertion to ensure that it ran correctly and
yield to mark the end of the setup. In the teardown section after the `yield` statement,
we run the `conda remove` command and also make an assertion to determine it ran correctly.

This fixture will be run using the default scope in `pytest`, which is `function`. This means
that the setup and teardown will be run before and after each test. If you need to share
an environment or other pieces of data between tests, just remember to set the fixture
scope appropriately. [Read here][pytest-scope]
for more information on `pytest` fixture scopes.

[pytest-scope]: https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
