# Development Environment

1. Clone the repo you just forked on GitHub to your local machine. Configure
   your repo to point to both "upstream" (the main conda repo) and your fork
   ("origin"). For detailed directions, see below:

   **Bash (macOS, Linux, Windows)**

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

   **cmd.exe (Windows)**

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

2. One option is to create a local development environment and activate that environment

   **Bash (macOS, Linux, Windows)**

   ```bash
   $ source ./dev/start
   ```

   **cmd.exe (Windows)**

   ```batch
   > .\dev\start.bat
   ```

   This command will create a project-specific base environment (see `devenv`
   in your repo directory after running this command). If the base environment
   already exists this command will simply activate the already-created
   `devenv` environment.

   To be sure that the conda code being interpreted is the code in the project
   directory, look at the value of `conda location:` in the output of
   `conda info --all`.

3. Alternatively, for Linux development only, you can use the same Docker
   image the CI pipelines use. Note that you can run this from all three
   operating systems! We are using `docker compose`, which provides three
   actions for you:

   - `unit-tests`: Run all unit tests.
   - `integration-tests`: Run all integration tests.
   - `interactive`: You are dropped in a pre-initialized Bash session,
     where you can run all your `pytest` commands as required.

   Use them with `docker compose run <action>`. For example:


   **Any shell (macOS, Linux, Windows)**

   ```bash
   $ docker compose run unit-tests
   ```

   This builds the same Docker image as used in continuous
   integration from the [Github Container Registry](https://github.com/conda/conda/pkgs/container/conda-ci)
   and starts `bash` with the conda development mode already enabled.

   By default, it will use Miniconda-based, Python 3.9 installation configured for
   the `defaults` channel. You can customize this with two environment variables:

   - `CONDA_DOCKER_PYTHON`: `major.minor` value; e.g. `3.11`.
   - `CONDA_DOCKER_DEFAULT_CHANNEL`: either `defaults` or `conda-forge`

   For example, if you need a conda-forge based 3.11 image:

   **Bash (macOS, Linux, Windows)**

   ```bash
   $ CONDA_DOCKER_PYTHON=3.11 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose build --no-cache
   # --- in some systems you might also need to re-supply the same values as CLI flags:
   # CONDA_DOCKER_PYTHON=3.11 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose build --no-cache --build-arg python_version=3.11 --build-arg default_channel=conda-forge
   $ CONDA_DOCKER_PYTHON=3.11 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose run interactive
   ```

   **cmd.exe (Windows)**

   ```batch
   > set CONDA_DOCKER_PYTHON=3.11
   > set CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge
   > docker compose build --no-cache
   > docker compose run interactive
   > set "CONDA_DOCKER_PYTHON="
   > set "CONDA_DOCKER_DEFAULT_CHANNEL="
   ```

>  The `conda` repository will be mounted to `/opt/conda-src`, so all changes
   done in your editor will be reflected live while the Docker container is
   running.

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

**Bash (macOS, Linux, Windows)**

```bash
# reuse the development environment created above
$ source ./dev/start
# or start the Docker image in interactive mode
# $ docker compose run interactive

# install pre-commit hooks for conda
$ cd "$CONDA_PROJECT_ROOT"
$ pre-commit install

# manually running pre-commit on current changes
# note: by default pre-commit only runs on staged files
$ pre-commit run

# automatically running pre-commit during commit
$ git commit
```

**cmd.exe (Windows)**

```batch
:: reuse the development environment created above
> .\dev\start.bat
:: or start the Docker image in interactive mode
:: > docker compose run interactive

:: install pre-commit hooks for conda
> cd "%CONDA_PROJECT_ROOT%"
> pre-commit install

:: manually running pre-commit on current changes
:: note: by default pre-commit only runs on staged files
> pre-commit run

:: automatically running pre-commit during commit
> git commit
```

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

**Bash (macOS, Linux, Windows)**

```bash
# reuse the development environment created above
$ source ./dev/start
# or start the Docker image in interactive mode
# $ docker compose run interactive

# run conda's unit tests using GNU make
$ make unit

# or alternately with pytest
$ pytest --cov -m "not integration" conda tests

# or you can use pytest to focus on one specific test
$ pytest --cov tests/test_create.py -k create_install_update_remove_smoketest
```

**cmd.exe (Windows)**

```batch
:: reuse the development environment created above
> .\dev\start.bat
:: or start the Docker image in interactive mode
:: > docker compose run interactive

:: run conda's unit tests with pytest
> pytest --cov -m "not integration" conda tests

:: or you can use pytest to focus on one specific test
> pytest --cov tests\test_create.py -k create_install_update_remove_smoketest
```

If you are not measuring code coverage, `pytest` can be run without the `--cov`
option. The `docker compose` tests pass `--cov`.

Note: Some integration tests require you build a package with conda-build beforehand.
This is taking care of if you run `docker compose run integration-tests`, but you need
to do it manually in other modes:

**Bash (macOS, Linux, Windows)**

```bash
$ conda install conda-build
$ conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package

```

Check `dev/linux/integration.sh` and `dev\windows\integration.bat` for more details.
