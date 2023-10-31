[conda-logo]: https://s3.amazonaws.com/conda-dev/conda_logo.svg
[tests-badge]: https://github.com/conda/conda/actions/workflows/tests.yml/badge.svg
[images-badge]: https://github.com/conda/conda/actions/workflows/images.yml/badge.svg
[codecov-badge]: https://img.shields.io/codecov/c/github/conda/conda/main.svg?label=coverage
[release-badge]: https://img.shields.io/github/release/conda/conda.svg
[gitpod]: https://gitpod.io/button/open-in-gitpod.svg

[![Conda Logo][conda-logo]](https://github.com/conda/conda)

[![Tests (GitHub Actions)][tests-badge]](https://github.com/conda/conda/actions/workflows/tests.yml)
[![Images (GitHub Actions)][images-badge]](https://github.com/conda/conda/actions/workflows/images.yml)
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
installed. You can see what packages are installed by running:

```bash
$ conda list
```

to see all the packages that are available, use:

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

The default environment, which `conda` itself is installed into, is called `base`.
To create another environment, use the `conda create` command.
For instance, to create an environment with PyTorch, you would run:

```bash
$ conda create --name ml-project pytorch
```

This creates an environment called `ml-project` with the latest version of PyTorch, and its dependencies.

We can now activate this environment:

```bash
$ conda activate ml-project
```

This puts the `bin` directory of the `ml-project` environment in the front of the `PATH`,
and sets it as the default environment for all subsequent conda commands.

To go back to the base environment, use:

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
anaconda-client and login:

```bash
$ conda install anaconda-client
$ anaconda login
```

Then, after you build your recipe:

```bash
$ conda build <recipe-dir>
```

you will be prompted to upload to anaconda.org.

To add your anaconda.org channel, or other's channels, to conda so
that `conda install` will find and install their packages, run:

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
- [Discourse](https://conda.discourse.group/)

## Contributing

[![open in gitpod for one-click development][gitpod]](https://gitpod.io/#https://github.com/conda/conda)

Contributions to conda are welcome. See the [contributing](CONTRIBUTING.md) documentation
for instructions on setting up a development environment.
