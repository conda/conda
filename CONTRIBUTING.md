# Contributing to Conda

## New Issues

If your issue is a bug report or feature request for:

* **a specific conda package**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **anaconda.org**: please file it at <https://anaconda.org/contact/report>
* **repo.anaconda.com**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **commands under `conda build`**: please file it at <https://github.com/conda/conda-build/issues>
* **commands under `conda env` and all other conda commands**: please file it at <https://github.com/conda/conda/issues>

## Code of Conduct

The conda organization adheres to the [NumFOCUS Code of Conduct](https://www.numfocus.org/code-of-conduct).

## Development Environment

0. [Signup for a GitHub account][github signup] (if you haven't already) and
   [install Git on your system][install git].
1. Fork the conda repository to your personal GitHub account by clicking the
   "Fork" button on https://github.com/conda/conda and follow GitHub's
   instructions.
2. Clone the repo you just forked on GitHub to your local machine. Configure
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

3. One option is to create a local development environment and activate that environment

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

4. Alternatively, for Linux development only, you can use the same Docker
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
   By default, it will use Python 3.9 installation.

   If you need a different Python version, set a `CONDA_DOCKER_PYTHON`
   environment variable like this to rebuild the image. You might need
   to add `--no-cache` to make sure the image is rebuilt.

   **Bash (macOS, Linux, Windows)**

   ```bash
   $ CONDA_DOCKER_PYTHON=3.8 docker compose build --no-cache unit-tests
   ```

   **cmd.exe (Windows)**

   ```batch
   > set CONDA_DOCKER_PYTHON=3.8 && docker compose build --no-cache unit-tests && set "CONDA_DOCKER_PYTHON="
   ```

   The next time you run `docker compose run <task>` you will use the new image.
   If you want to revert to the version you were previously using, you need to rebuild
   the image again.

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
$ pytest -m "not integration" conda tests

# or you can use pytest to focus on one specific test
$ pytest tests/test_create.py -k create_install_update_remove_smoketest
```

**cmd.exe (Windows)**

```batch
:: reuse the development environment created above
> .\dev\start.bat
:: or start the Docker image in interactive mode
:: > docker compose run interactive

:: run conda's unit tests with pytest
> pytest -m "not integration" conda tests

:: or you can use pytest to focus on one specific test
> pytest tests\test_create.py -k create_install_update_remove_smoketest
```

Note: Some integration tests require you build a package with conda-build beforehand.
This is taking care of if you run `docker compose run integration-tests`, but you need
to do it manually in other modes:

**Bash (macOS, Linux, Windows)**

```bash
$ conda install conda-build
$ conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package

```

Check `dev/linux/integration.sh` and `dev\windows\integration.bat` for more details.


## Conda Contributor License Agreement

In case you're new to CLAs, this is rather standard procedure for larger
projects. [Django](https://www.djangoproject.com/foundation/cla/) and
[Python](https://www.python.org/psf/contrib/contrib-form/) for example
both use similar agreements.

Note: New contributors are required to complete the [Conda Contributor License Agreement][1].

For pull requests to be merged, contributors to GitHub pull requests need to
have signed the [Conda Contributor License Agreement][1], so Anaconda, Inc.
has it on file. A record of prior signatories is kept in a [separate repo in
conda's GitHub][2] organization.

[1]: https://conda.io/en/latest/contributing.html#conda-contributor-license-agreement
[2]: https://github.com/conda/clabot-config/blob/master/.clabot
[install git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[github signup]: https://github.com/signup

## Releasing

Conda releases may be performed via the [rever command](https://regro.github.io/rever-docs/).
Rever is configured to perform the activities for a typical conda-build release.
To cut a release, simply run `rever <X.Y.Z>` where `<X.Y.Z>` is the
release number that you want bump to. For example, `rever 1.2.3`.

However, it is always good idea to make sure that the you have permissions
everywhere to actually perform the release. So it is customary to run
`rever check` before the release, just to make sure.

The standard workflow is thus:

```bash
$ rever check
$ rever 1.2.3
```

If for some reason a release fails partway through, or you want to claw back a
release that you have made, rever allows you to undo activities. If you find yourself
in this pickle, you can pass the `--undo` option a comma-separated list of
activities you'd like to undo. For example:

```bash
$ rever --undo tag,changelog,authors 1.2.3
```

Happy releasing!
