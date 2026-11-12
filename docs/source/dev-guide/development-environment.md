# Development Environment

## Repository Setup

Clone the repo you just forked on GitHub to your local machine. Configure your repo to point to both "upstream" (the main conda repo) and your fork ("origin").

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
# choose the repository location
# warning: not the location of an existing conda installation!
$ CONDA_PROJECT_ROOT="$HOME/conda"

# clone the project
# replace `your-username` with your actual GitHub username
$ git clone git@github.com:your-username/conda "$CONDA_PROJECT_ROOT"
$ cd "$CONDA_PROJECT_ROOT"

# set the `upstream` as the the main repository
$ git remote add upstream git@github.com:conda/conda
```

```{tab-item} cmd.exe (Windows)
```batch
# choose the repository location
# warning: not the location of an existing conda installation!
> set "CONDA_PROJECT_ROOT=%HOMEPATH%\conda"

# clone the project
# replace `your-username` with your actual GitHub username
> git clone git@github.com:your-username/conda "%CONDA_PROJECT_ROOT%"
> cd "%CONDA_PROJECT_ROOT%"

# set the `upstream` as the main repository
> git remote add upstream git@github.com:conda/conda
```

````

## Development Environment Setup

Development and test environments are managed with
[conda-workspaces](https://conda-incubator.github.io/conda-workspaces/). The
workspace manifest lives in `pyproject.toml` under the `[tool.conda.*]` tables.

Install conda-workspaces once into your `base` environment (this requires an
existing conda installation, e.g. Miniconda or Miniforge):

```bash
$ conda install -n base conda-forge::conda-workspaces
```

Then, from the repository root, create the default development environment:

```bash
$ conda workspace install
```

This solves and installs the environment into `.conda/envs/default` inside your
repository and installs conda from your checkout in editable mode. Changes to the
source code are picked up immediately without reinstalling.

Run a command inside the environment, or open a shell with it activated:

```bash
# run a single command
$ conda workspace run -- python -m pytest tests/test_exports.py

# spawn a shell with the environment activated
$ conda workspace shell
```

To be sure that the conda code being interpreted is the code in the project
directory, look at the value of `conda location:` in the output of
`conda workspace run -- conda info --all`.

```{note}
The editable install builds conda from the git history (`hatch-vcs`), so make
sure your clone has its tags (`git fetch --tags upstream`) and is not a shallow
clone.
```

### Available Environments

List the environments defined by the workspace with `conda workspace envs`. Select
one with `-e <name>`:

| Environment | Purpose |
|---|---|
| `default` | Test dependencies on Python 3.14 |
| `py311`, `py312`, `py313`, `py314` | Test and S3 dependencies on a specific Python version |
| `s3` | Test and S3 dependencies (for tests that need `minio-server`) |
| `typing` | Test dependencies plus `mypy` |
| `docs` | Documentation build dependencies |
| `lint` | `pre-commit`, `doc8`, and `rstcheck` |

For example:

```bash
$ conda workspace install -e py312
$ conda workspace run -e py312 -- python -m pytest -m "not integration"
```

```{note}
Not every environment is available on every platform. Python 3.11 through 3.13
are not available for `win-arm64`, and the `docs`, `typing`, and `lint`
environments are not available on every platform because some of their
dependencies are not built for it (for example, `plantuml` on `linux-aarch64` and
`lxml` and `ukkonen` on `win-arm64`). `conda workspace install` reports an error
when you select an environment that is not defined for your platform.
```

### Channels

The workspace solves against the `conda-forge` channel, which provides every
dependency on every supported platform. The `defaults` channel is still exercised
by continuous integration, but it is not used by the workspace environments.

### Tasks

Common development commands are defined as tasks in the same manifest. List them
with `conda task list` and run one with `conda task run <name>`:

```bash
# run the unit tests (pytest -m "not integration")
$ conda task run unit

# run the integration tests
$ conda task run integration

# run a quick create/install/update/remove smoke test
$ conda task run smoketest

# type check with mypy (runs in the `typing` environment)
$ conda task run typing

# run pre-commit on all files (runs in the `lint` environment)
$ conda task run lint

# build the HTML documentation (runs in the `docs` environment)
$ conda task run docs
```

Tasks run in the `default` environment when it is installed. Use `-e <name>` to
select a different, already installed, environment.

### Lock File

`conda workspace install` also writes a `conda.lock` file at the repository root.
It is not committed (it is listed in `.gitignore`) so that new environments always
solve against the latest packages. Use `conda workspace install --locked` to
re-create an environment from your existing lock file without solving again.

### Deprecated: `dev/start`

The `dev/start` (macOS, Linux) and `dev\start.bat` (Windows) scripts are pending
deprecation and are scheduled for removal in conda 27.9. They continue to work, but
print a deprecation notice. The `devenv` and `installer_type` settings in
`~/.condarc` are only used by these scripts.

## Docker Alternative

For Linux development, the repository includes a
[Dev Container](https://containers.dev/) configuration in `.devcontainer/`. Open
the repository with a Dev Containers-aware editor (for example, VS Code) to get a
reproducible environment that is not affected by your host's conda configuration.
The container installs conda-workspaces and creates the `default`, `s3`, and `lint`
environments when it is created.

## Static Code Analysis

This project is configured with [pre-commit](https://pre-commit.com/) to
automatically run linting and other static code analysis on every commit.
Running these tools prior to the PR/code review process helps in two ways:

1. it helps *you* by automating the nitpicky process of identifying and
   correcting code style/quality issues
2. it helps *us* where during code review we can focus on the substance of
   your contribution

Feel free to read up on everything pre-commit related in their
[docs](https://pre-commit.com/#quick-start) but we've included the gist of
what you need to get started below:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
# create the `lint` environment, which provides pre-commit
$ cd "$CONDA_PROJECT_ROOT"
$ conda workspace install -e lint

# install pre-commit hooks for conda
$ conda workspace run -e lint -- pre-commit install

# manually running pre-commit on current changes
# note: by default pre-commit only runs on staged files
$ conda workspace run -e lint -- pre-commit run

# or run it on all files using the `lint` task
$ conda task run lint

# automatically running pre-commit during commit
$ git commit
```

```{tab-item} cmd.exe (Windows)
```batch
:: create the `lint` environment, which provides pre-commit
> cd "%CONDA_PROJECT_ROOT%"
> conda workspace install -e lint

:: install pre-commit hooks for conda
> conda workspace run -e lint -- pre-commit install

:: manually running pre-commit on current changes
:: note: by default pre-commit only runs on staged files
> conda workspace run -e lint -- pre-commit run

:: or run it on all files using the `lint` task
> conda task run lint

:: automatically running pre-commit during commit
> git commit
```

````

Beware that some of the tools run by pre-commit can potentially modify the
code (see [black](https://github.com/psf/black),
[blacken-docs](https://github.com/asottile/blacken-docs), and
[darker](https://github.com/akaihola/darker)). If pre-commit detects that any
files were modified it will terminate the commit giving you the opportunity to
review the code before committing again.

Strictly speaking using pre-commit on your local machine for commits is
optional (if you don't install pre-commit you will still be able to commit
normally). But once you open a PR to contribue your changes, pre-commit will
be automatically run at which point any errors that occur will need to be
addressed prior to proceeding.

## Testing

We use pytest to run our test suite. Please consult pytest's
[docs](https://docs.pytest.org/en/6.2.x/usage.html) for detailed instructions
but generally speaking all you need is the following:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
# run conda's unit tests using the workspace task
$ conda task run unit

# or alternately with pytest in the default environment
$ conda workspace run -- pytest --cov -m "not integration" conda tests

# or you can use pytest to focus on one specific test
$ conda workspace run -- pytest --cov tests/test_create.py -k test_create_install_update_remove
```

````

If you are not measuring code coverage, `pytest` can be run without the `--cov`
option.

See {doc}`writing-tests/benchmarks` for running and adding performance benchmarks,
exporting measurements, and reviewing Bencher results.

Note: Some integration tests require you build a package with conda-build beforehand:

```bash
$ conda install conda-build
$ conda-build tests/data/recipes/activate_deactivate_package tests/data/recipes/pre_link_messages_package
```
