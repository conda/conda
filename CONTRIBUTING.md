# Contributing to Conda

## New Issues

If your issue is a bug report or feature request for:

* **a specific conda package**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **anaconda.org**: please file it at <https://anaconda.org/contact/report>
* **repo.anaconda.com**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **commands under `conda build`**: please file it at <https://github.com/conda/conda-build/issues>
* **commands under `conda env`**: please file it here!
* **all other conda commands**: please file it here!

## Code of Conduct

The conda organization adheres to the [NumFOCUS Code of Conduct](https://www.numfocus.org/code-of-conduct).

## Development Environment

### Bash (e.g. macOS, Linux, Windows)

0. [Signup for a GitHub account][github signup] (if you haven't already)
   and [install Git on your system][install git].

1. Fork the conda/conda repository to your personal GitHub account by
   clicking the "Fork" button on https://github.com/conda/conda and then
   following the instructions GitHub provides.

2. Clone the conda repo you just forked on GitHub to your filesystem anywhere
   you choose. A special development environment will be set up within the
   git clone directory below.
   Set up a new `git remote` to point to both "upstream" (the main conda
   repo) and your fork repo. For detailed directions, see below.

   2a. Choose where you want the repository located (not a location of an
       existing conda installation though!), e.g.:

       CONDA_PROJECT_ROOT="$HOME/conda"

   2b. Clone the project, with `upstream` being the main repository.
       Please replace `your-username` with your actual GitHub username.

       GITHUB_USERNAME=your-username
       git clone git@github.com:$GITHUB_USERNAME/conda "$CONDA_PROJECT_ROOT"
       cd "$CONDA_PROJECT_ROOT"
       git remote add upstream git@github.com:conda/conda

3. Create a local development environment, and activate that environment

       source ./dev/start

   This command will create a project-specific base environment at `./devenv`.
   If the environment already exists, this command will just quickly activate
   the already-created `./devenv` environment.

   To be sure that the conda code being interpreted is the code in the project
   directory, look at the value of `conda location:` in the output of
   `conda info --all`.

4. Run conda's unit tests using GNU make

       make unit

   or alternately with pytest

       pytest -m "not integration" conda tests

   or you can use pytest to focus on one specific test

       pytest tests/test_create.py -k create_install_update_remove_smoketest

### cmd.exe shell (Windows)

0. [Signup for a GitHub account][github signup] (if you haven't already)
   and [install Git on your system][install git].

1. Fork the conda/conda repository to your personal GitHub account by
   clicking the "Fork" button on https://github.com/conda/conda and then
   following the instructions GitHub provides.

2. Clone the conda repo you just forked on GitHub to your filesystem anywhere
   you choose. A special development environment will be set up within the
   git clone directory below.
   Set up a new `git remote` to point to both "upstream" (the main conda
   repo) and your fork repo. For detailed directions, see below.

   2a. Choose where you want the repository located (not a location of an
       existing conda installation though!), e.g.:

       set "CONDA_PROJECT_ROOT=%HOMEPATH%\conda"

   2b. Clone the project, with `upstream` being the main repository.
       Please replace `your-username` with your actual GitHub username.

       set GITHUB_USERNAME=your-username
       git clone git@github.com:%GITHUB_USERNAME%/conda "%CONDA_PROJECT_ROOT%"
       cd "%CONDA_PROJECT_ROOT%"
       git remote add upstream git@github.com:%GITHUB_USERNAME%/conda

3. Create a local development environment, and activate that environment

       .\dev\start.bat

   This command will create a project-specific base environment at `.\devenv`.
   If the environment already exists, this command will just quickly activate
   the already-created `.\devenv` environment.

   To be sure that the conda code being interpreted is the code in the project
   directory, look at the value of `conda location:` in the output of
   `conda info --all`.

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
