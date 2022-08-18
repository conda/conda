[conda-logo]: https://s3.amazonaws.com/conda-dev/conda_logo.svg
[ci-tests-badge]: https://github.com/conda/conda/actions/workflows/ci.yml/badge.svg
[ci-images-badge]: https://github.com/conda/conda/actions/workflows/ci-images.yml/badge.svg
[codecov-badge]: https://img.shields.io/codecov/c/github/conda/conda/main.svg?label=coverage
[release-badge]: https://img.shields.io/github/release/conda/conda.svg
[gitpod]: https://gitpod.io/button/open-in-gitpod.svg

[![Conda Logo][conda-logo]](https://github.com/conda/conda)


[![CI Tests (GitHub Actions)][ci-tests-badge]](https://github.com/conda/conda/actions/workflows/ci.yml)
[![CI Images (GitHub Actions)][ci-images-badge]](https://github.com/conda/conda/actions/workflows/ci-images.yml)
[![Codecov Status][codecov-badge]](https://codecov.io/gh/conda/conda/branch/main)
[![latest release version][release-badge]](https://github.com/conda/conda/releases)

Conda is a cross-platform, language-agnostic binary package manager. It is the
package manager used by [Anaconda](https://www.anaconda.com/distribution/) installations, but it may be
used for other systems as well. Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. Conda is written entirely in Python, and is BSD licensed open
source.

Conda is enhanced by organizations, tools, and repositories created and managed by
the amazing members of the conda community. Some of them can be found
[here](https://github.com/conda/conda/wiki/Conda-Community).


## Installation

Conda is a part of the [Anaconda Distribution](https://repo.anaconda.com).
Use [Miniconda](https://docs.conda.io/en/latest/miniconda.html) to bootstrap a minimal installation
that only includes conda and its dependencies.


## Getting Started

If you install the Anaconda Distribution, you will already have hundreds of packages
installed. You can see what packages are installed by running

```bash
$ conda list
```

to see all the packages that are available, use

```bash
$ conda search
```

and to install a package, use

```bash
$ conda install <package-name>
```

The real power of conda comes from its ability to manage environments.
In conda, an environment can be thought of as a completely separate installation.
Conda installs packages into environments efficiently using [hard links](https://en.wikipedia.org/wiki/Hard_link) by default when it is possible, so
environments are space efficient, and take seconds to create.

The default environment, which `conda` itself is installed into is called
`base`. To create another environment, use the `conda create`
command. For instance, to create an environment with the IPython notebook and
NumPy 1.6, which is older than the version that comes with Anaconda by
default, you would run:

```bash
$ conda create -n numpy16 ipython-notebook numpy=1.6
```

This creates an environment called `numpy16` with the latest version of
the IPython notebook, NumPy 1.6, and their dependencies.

We can now activate this environment, use

```bash
$ conda activate numpy16
```

This puts the bin directory of the `numpy16` environment in the front of the
`PATH`, and sets it as the default environment for all subsequent conda commands.

To go back to the base environment, use

```bash
$ conda deactivate
```

## Building Your Own Packages

You can easily build your own packages for conda, and upload them
to [anaconda.org](https://anaconda.org), a free service for hosting
packages for conda, as well as other package managers.
To build a package, create a recipe. Package building documentation is available
[here](https://docs.conda.io/projects/conda-build/en/latest/).
See [AnacondaRecipes](https://github.com/AnacondaRecipes) for the recipes that make up the Anaconda Distribution and `defaults` channel.
[Conda-forge](https://conda-forge.org/feedstocks/) and [Bioconda](https://github.com/bioconda/bioconda-recipes) are community-driven conda-based distributions.

To upload to anaconda.org, create an account. Then, install the
anaconda-client and login

```bash
$ conda install anaconda-client
$ anaconda login
```

Then, after you build your recipe

```bash
$ conda build <recipe-dir>
```

you will be prompted to upload to anaconda.org.

To add your anaconda.org channel, or other's channels, to conda so
that `conda install` will find and install their packages, run

```bash
$ conda config --add channels https://conda.anaconda.org/username
```

(replacing `username` with the username of the person whose channel you want
to add).

## Getting Help

- [Documentation](https://docs.conda.io/projects/conda/en/latest)
- [Twitter](https://twitter.com/condaproject)
- [Slack](https://conda.slack.com)
- [Bug Reports/Feature Requests](https://github.com/conda/conda/issues)
- [Installer/Package Issues](https://github.com/ContinuumIO/anaconda-issues/issues)

## Contributing

[![open in gitpod for one-click development][gitpod]](https://gitpod.io/#https://github.com/conda/conda)

Contributions to conda are welcome. See the [contributing](CONTRIBUTING.md) documentation
for instructions on setting up a development environment.

## Conda Community
There are many organizations, tools, and repositories created and managed by the amazing members of the conda community.

### Organizations

- [conda-forge](https://conda-forge.org/)<br>
  A github organization containing repositories of conda recipes. Each repository, also known as a feedstock, knows how to build itself using freely available (to open source software) CI services.

- [Bioconda](https://bioconda.github.io/)<br>
  Bioconda is a distribution of bioinformatics software realized as a channel for the versatile Conda package manager.

### Projects

- [anaconda-list-distributions](https://github.com/pelson/anaconda-list-distributions)<br>
  Give a name of an anaconda channel, and it will print out all of the distributions available, ordered by upload date. This view is helpful for managing a complex channel.

- [conda-build-all](https://github.com/conda-tools/conda-build-all)<br>
  A conda subcommand which allows multiple distributions to be built (and uploaded) in a single command. It makes use of the underlying machinery developed for conda build, but has a number of advantages.

- [conda-execute](https://github.com/conda-tools/conda-execute)<br>
  Write a script, annotate it with some comment metadata about the execution environment required, and run it with conda-execute. conda-execute will use conda to resolve and create a unique temporary environment, then run the script within it.

- [conda-gitenv](https://github.com/SciTools/conda-gitenv)<br>
  Track environment specifications using a git repo. conda gitenv is a designed to simplify the deployment centrally managed conda environments. Rather than expecting a sysadimn to administer appropriate conda commands on a live system, it decouples the conda update phase from the actual deployment, giving users the ability to review and prepare for any forthcoming changes.

- [centrally-managed-conda](https://github.com/pelson/centrally-managed-conda)<br>
  Miscellaneous tools useful to manage air-gapped conda environments.

- [conda-smithy](https://github.com/conda-forge/conda-smithy)<br>
  A tool for combining a conda recipe with configurations to build using freely hosted CI services into a single repository.

- [conda-testenv](https://github.com/SciTools/conda-testenv)<br>
  Run the tests of all packages installed in a conda environment. Especially useful for catching cases of badly installed packages, particularly those which poorly define their dependencies (e.g. a package claims to run with "numpy", but actually only runs with "numpy >=1.9").

- [xonda](https://github.com/gforsyth/xonda)<br>
  A thin wrapper around conda for use with xonsh. It provides tab completion for most features and also will tab-complete activate/select calls for environments.

- [conda-devenv](https://github.com/ESSS/conda-devenv)
  Manage multiple `environment.yml`-like files, making it suitable to work with multiple projects in develop mode. Supports environment variables and Jinja 2 syntax.

### Notable Conda Recipe Repos

- [IOOS conda recipes](https://github.com/ioos/conda-recipes)
- [raspberrypi-conda-recipes](https://github.com/pelson/raspberrypi-conda-recipes)
