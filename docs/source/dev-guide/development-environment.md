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

Create a local development environment and activate it using the `dev/start` scripts:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
$ source ./dev/start
```

```{tab-item} cmd.exe (Windows)
```batch
> .\dev\start.bat
```

````

This command will create a project-specific base environment (see `devenv` in your repo directory after running this command). If the base environment already exists this command will simply activate the already-created `devenv` environment.

To be sure that the conda code being interpreted is the code in the project directory, look at the value of `conda location:` in the output of `conda info --all`.

### Choosing Your Installer

The `dev/start` script supports two different conda installers:

- **miniconda** (default): Uses the Anaconda defaults channel and official Miniconda installer
- **miniforge**: Uses the conda-forge channel and community-maintained Miniforge installer

#### Configuration Options

You can specify the installer type in several ways, in order of precedence:

1. **Command line flag** (highest priority)
2. **Configuration file** (`~/.condarc`)
3. **Interactive prompt** (lowest priority)

To avoid being prompted every time, you can set your preferred installer in your `~/.condarc` file:

```yaml
# ~/.condarc
installer_type: miniforge  # or miniconda
```

When you run the script for the first time without specifying an installer and no configuration file setting, you'll be prompted to choose:

```text
Choose conda installer:
  1) miniconda (default - Anaconda defaults channel)
  2) miniforge (conda-forge channel)
Enter choice [1]:
```

You can also specify the installer directly using the `-i` or `--installer` flag:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
# Use miniconda (default behavior)
$ source ./dev/start -i miniconda

# Use miniforge
$ source ./dev/start -i miniforge
```

```{tab-item} cmd.exe (Windows)
```batch
:: Use miniconda (default behavior)
> .\dev\start.bat -i miniconda

:: Use miniforge
> .\dev\start.bat -i miniforge
```

````

### Additional Options

The `dev/start` script supports several other options for customizing your development environment:

```bash
# See all available options
$ source ./dev/start --help

# Use a specific Python version
$ source ./dev/start -p 3.11

# Force update packages
$ source ./dev/start -u

# Preview what would be done without making changes
$ source ./dev/start -n
```

### Switching Between Installers

You can maintain separate development environments for different installers and switch between them:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
# Set up and activate miniconda-based environment
$ source ./dev/start -i miniconda

# Later, set up and activate miniforge-based environment
$ source ./dev/start -i miniforge
```

```{tab-item} cmd.exe (Windows)
```batch
:: Set up and activate miniconda-based environment
> .\dev\start.bat -i miniconda

:: Later, set up and activate miniforge-based environment
> .\dev\start.bat -i miniforge
```

````

Each installer creates its own isolated environment, so you can test conda behavior with both the defaults and conda-forge channels.

## Manual Setup

If you prefer to set up your development environment manually instead of using the automated scripts, follow these steps:

### Prerequisites

- Conda is already installed and initialized on your system
- (Optional) If using Option B in step 4, install conda-pypi canary version: `conda install -n base conda-canary/label/dev::conda-pypi`

1. Create the development directory:

   ```bash
   $ mkdir -p ./devenv
   ```

2. Download and install miniforge:

   ````{tab-set}

   ```{tab-item} macOS
   ```bash
   $ curl -L "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-$(uname -m).sh" -o ./devenv/miniforge.sh
   $ bash ./devenv/miniforge.sh -bfp ./devenv
   $ rm ./devenv/miniforge.sh
   ```

   ```{tab-item} Linux
   ```bash
   $ curl -L "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh" -o ./devenv/miniforge.sh
   $ bash ./devenv/miniforge.sh -bfp ./devenv
   $ rm ./devenv/miniforge.sh
   ```

   ```{tab-item} Windows (PowerShell)
   ```powershell
   > (New-Object System.Net.WebClient).DownloadFile("https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe", "$env:TEMP\miniforge.exe")
   > Start-Process $env:TEMP\miniforge.exe -ArgumentList "/InstallationType=JustMe","/RegisterPython=0","/AddToPath=0","/NoRegistry=1","/NoShortcuts=1","/S","/D=$PWD\devenv" -Wait -NoNewWindow
   > rm $env:TEMP\miniforge.exe
   ```

   ````

3. Create and configure environment:

   ````{tab-set}

   ```{tab-item} Bash (macOS, Linux)
   ```bash
   # Install dependencies
   $ ./devenv/bin/conda install -y -p ./devenv --override-channels -c conda-forge --file ./tests/requirements.txt --file ./tests/requirements-ci.txt python=3.13
   ```


   ```{tab-item} PowerShell (Windows)
   ```powershell
   # Install dependencies
   > .\devenv\Scripts\conda.exe install -y -p .\devenv --override-channels -c conda-forge --file .\tests\requirements.txt --file .\tests\requirements-ci.txt python=3.13
   ```

   ````

4. Make conda source code available and activate environment:

   Choose one of the following options:

   **Option A: Set PYTHONPATH**

   Set PYTHONPATH to make the conda source code available, then activate the environment:

   ````{tab-set}

   ```{tab-item} Bash (macOS, Linux)
   ```bash
   # Set PYTHONPATH
   $ export PYTHONPATH=$(pwd):$PYTHONPATH

   # Activate environment
   $ conda activate ./devenv
   ```
   ```{tab-item} Fish (macOS, Linux)
   ```fish
   # Set PYTHONPATH
   $ set -gx PYTHONPATH (pwd) $PYTHONPATH

   # Activate environment
   $ conda activate ./devenv
   ```
   ```{tab-item} PowerShell (Windows)
   ```powershell
   # Set PYTHONPATH
   > $env:PYTHONPATH="$PWD;$env:PYTHONPATH"

   # Activate environment
   > conda activate .\devenv
   ```
   ````

   **Option B: Install conda in editable mode**

   Activate the environment first, then install conda in editable mode using conda-pypi:

   ````{tab-set}

   ```{tab-item} Bash (macOS, Linux)
   ```bash
   # Activate environment
   $ conda activate ./devenv

   # Install conda in editable mode
   $ conda pypi install -e .
   ```
   ```{tab-item} PowerShell (Windows)
   ```powershell
   # Activate environment
   > conda activate .\devenv

   # Install conda in editable mode
   > conda pypi install -e .
   ```
   ````

   This installs conda as an editable package in the environment, which can be more convenient for development.

## Docker Alternative

Alternatively, for Linux development only, you can use the same Docker image the CI pipelines use. Note that you can run this from all three operating systems! We are using `docker compose`, which provides three actions for you:

- `unit-tests`: Run all unit tests.
- `integration-tests`: Run all integration tests.
- `interactive`: You are dropped in a pre-initialized Bash session, where you can run all your `pytest` commands as required.

Use them with `docker compose run <action>`. For example:

```bash
$ docker compose run unit-tests
```

This builds the same Docker image as used in continuous integration from the [Github Container Registry](https://github.com/conda/conda/pkgs/container/conda-ci) and starts `bash` with the conda development mode already enabled.

By default, it will use Miniconda-based, Python 3.9 installation configured for the `defaults` channel. You can customize this with two environment variables:

- `CONDA_DOCKER_PYTHON`: `major.minor` value; e.g. `3.11`.
- `CONDA_DOCKER_DEFAULT_CHANNEL`: either `defaults` or `conda-forge`

For example, if you need a conda-forge based 3.12 image:

````{tab-set}

```{tab-item} Bash (macOS, Linux, Windows)
```bash
$ CONDA_DOCKER_PYTHON=3.12 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose build --no-cache
# --- in some systems you might also need to re-supply the same values as CLI flags:
# CONDA_DOCKER_PYTHON=3.12 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose build --no-cache --build-arg python_version=3.12 --build-arg default_channel=conda-forge
$ CONDA_DOCKER_PYTHON=3.12 CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge docker compose run interactive
```

```{tab-item} cmd.exe (Windows)
```batch
> set CONDA_DOCKER_PYTHON=3.12
> set CONDA_DOCKER_DEFAULT_CHANNEL=conda-forge
> docker compose build --no-cache
> docker compose run interactive
> set "CONDA_DOCKER_PYTHON="
> set "CONDA_DOCKER_DEFAULT_CHANNEL="
```

````

> The `conda` repository will be mounted to `/opt/conda-src`, so all changes done in your editor will be reflected live while the Docker container is running.

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

```{tab-item} cmd.exe (Windows)
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

````

If you are not measuring code coverage, `pytest` can be run without the `--cov`
option. The `docker compose` tests pass `--cov`.

Note: Some integration tests require you build a package with conda-build beforehand.
This is taking care of if you run `docker compose run integration-tests`, but you need
to do it manually in other modes:

```bash
$ conda install conda-build
$ conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package
```

Check `dev/linux/integration.sh` and `dev\windows\integration.bat` for more details.
