[conda-logo]: https://s3.amazonaws.com/conda-dev/conda_logo.svg
[tests-badge]: https://img.shields.io/github/actions/workflow/status/conda/conda/tests.yml?branch=main&event=schedule&logo=github&label=tests
[codecov-badge]: https://img.shields.io/codecov/c/github/conda/conda/main?logo=codecov
[codspeed-badge]: https://img.shields.io/endpoint?url=https://codspeed.io/badge.json
[release-badge]: https://img.shields.io/github/v/release/conda/conda?logo=github
[anaconda-badge]: https://img.shields.io/conda/vn/anaconda/conda?logo=anaconda
[conda-forge-badge]: https://img.shields.io/conda/vn/conda-forge/conda?logo=conda-forge
[calver-badge]: https://img.shields.io/badge/calver-YY.MM.MICRO-22bfda.svg
[gitpod]: https://gitpod.io/button/open-in-gitpod.svg

[![Conda Logo][conda-logo]](https://github.com/conda/conda)

[![GitHub Scheduled Tests][tests-badge]](https://github.com/conda/conda/actions/workflows/tests.yml?query=branch%3Amain+event%3Aschedule)
[![Codecov Status][codecov-badge]](https://codecov.io/gh/conda/conda/branch/main)
[![CodSpeed Performance Benchmarks][codspeed-badge]](https://codspeed.io/conda/conda)
[![CalVer Versioning][calver-badge]](https://calver.org)
<br>
[![GitHub Release][release-badge]](https://github.com/conda/conda/releases)
[![Anaconda Package][anaconda-badge]](https://anaconda.org/anaconda/conda)
[![conda-forge Package][conda-forge-badge]](https://anaconda.org/conda-forge/conda)

Conda is a cross-platform, language-agnostic binary package manager. It is a
package manager used in conda distributions like [Miniforge](https://github.com/conda-forge/miniforge)
and the [Anaconda Distribution](https://www.anaconda.com/distribution/), but it may be
used for other systems as well. Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. The conda command line interface is written entirely in Python,
and is BSD licensed open source.

Conda is enhanced by organizations, tools, and repositories created and managed by
the amazing members of the [conda community](https://conda.org/). Some of them
can be found [here](https://github.com/conda/conda/wiki/Conda-Community).


## Installation

To bootstrap a minimal distribution, use a minimal installer such as [Miniconda](https://docs.anaconda.com/free/miniconda/) or [Miniforge](https://conda-forge.org/download/).

Conda is also included in the [Anaconda Distribution](https://repo.anaconda.com).

## Updating conda

To update `conda` to the newest version, use the following command:

```
$ conda update -n base conda
```

> [!TIP]
> It is possible that `conda update` does not install the newest version
> if the existing `conda` version is far behind the current release.
> In this case, updating needs to be done in stages.
>
> For example, to update from `conda 4.12` to `conda 23.10.0`,
> `conda 22.11.1` needs to be installed first:
>
> ```
> $ conda install -n base conda=22.11.1
> $ conda update conda
> ```

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
