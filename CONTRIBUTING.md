# Contributing to Conda

## New Issues

If your issue is a bug report or feature request for:

* **a specific conda package**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **anaconda.org**: please file it at <https://github.com/Anaconda-Platform/support/issues>
* **repo.anaconda.com**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **commands under `conda build`**: please file it at <https://github.com/conda/conda-build/issues>
* **commands under `conda env`**: please file it here!
* **all other conda commands**: please file it here!


## Development Environment, Bash (including the msys2 shell on Windows)

To set up an environment to start developing on conda code, we recommend the followings steps

1. Choose where you want the project located

    CONDA_PROJECT_ROOT="$HOME/conda"

2. Clone the project, with `origin` being the main repository. Make sure to click the `Fork`
   button above so you have your own copy of this repo.

    GITHUB_USERNAME=kalefranz
    git clone git@github.com:conda/conda "$CONDA_PROJECT_ROOT"
    cd "$CONDA_PROJECT_ROOT"
    git remote --add $GITHUB_USERNAME git@github.com:$GITHUB_USERNAME/conda

3. Create a local development environment, and activate that environment

    source ./dev/start.sh

   This command will create a project-specific base environment at `./devenv`. If
   the environment already exists, this command will just quickly activate the
   already-created `./devenv` environment.

   To be sure that the conda code being interpreted is the code in the project directory,
   look at the value of `conda location:` in the output of `conda info --all`.

4. Run conda's unit tests using GNU make

    make unit

   or alternately with pytest

    py.test -m "not integration and not installed" conda tests

   or you can use pytest to focus on one specific test

    py.test tests/test_create.py -k create_install_update_remove_smoketest


## Development Environment, Windows cmd.exe shell

In these steps, we assume `git` is installed and available on `PATH`.

1. Choose where you want the project located

    set "CONDA_PROJECT_ROOT=%HOMEPATH%\conda"

2. Clone the project, with `origin` being the main repository. Make sure to click the `Fork`
   button above so you have your own copy of this repo.

    set GITHUB_USERNAME=kalefranz
    git clone git@github.com:conda/conda "%CONDA_PROJECT_ROOT%"
    cd "%CONDA_PROJECT_ROOT%"
    git remote --add %GITHUB_USERNAME% git@github.com:%GITHUB_USERNAME%/conda

   To be sure that the conda code being interpreted is the code in the project directory,
   look at the value of `conda location:` in the output of `conda info --all`.

3. Create a local development environment, and activate that environment

    .\dev\start.bat

   This command will create a project-specific base environment at `.\devenv`. If
   the environment already exists, this command will just quickly activate the
   already-created `.\devenv` environment.
