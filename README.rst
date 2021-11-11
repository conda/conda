.. NOTE: This file serves both as the README on GitHub and the index.html for
   conda.pydata.org. If you update this file, be sure to cd to the web
   directory and run ``make html; make live``

.. image:: https://s3.amazonaws.com/conda-dev/conda_logo.svg
   :alt: Conda Logo

----------------------------------------

.. image:: https://github.com/conda/conda/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/conda/conda/actions/workflows/ci.yml
    :alt: CI Tests (GitHub Actions)

.. image:: https://github.com/conda/conda/actions/workflows/ci-images.yml/badge.svg
    :target: https://github.com/conda/conda/actions/workflows/ci-images.yml
    :alt: CI Images (GitHub Actions)

.. image:: https://img.shields.io/codecov/c/github/conda/conda/master.svg?label=coverage
   :alt: Codecov Status
   :target: https://codecov.io/gh/conda/conda/branch/master

.. image:: https://img.shields.io/github/release/conda/conda.svg
   :alt: latest release version
   :target: https://github.com/conda/conda/releases

Conda is a cross-platform, language-agnostic binary package manager. It is the
package manager used by `Anaconda
<https://www.anaconda.com/distribution/>`_ installations, but it may be
used for other systems as well.  Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. Conda is written entirely in Python, and is BSD licensed open
source.

Conda is enhanced by organizations, tools, and repositories created and managed by
the amazing members of the conda community.  Some of them can be found
`here <https://github.com/conda/conda/wiki/Conda-Community>`_.


Installation
------------

Conda is a part of the `Anaconda Distribution <https://repo.anaconda.com>`_.
Use `Miniconda <https://conda.io/en/latest/miniconda.html>`_ to bootstrap a minimal installation
that only includes conda and its dependencies.


Getting Started
---------------

If you install Anaconda, you will already have hundreds of packages
installed.  You can see what packages are installed by running

.. code-block:: bash

   $ conda list

to see all the packages that are available, use

.. code-block:: bash

   $ conda search

and to install a package, use

.. code-block:: bash

   $ conda install <package-name>


The real power of conda comes from its ability to manage environments. In
conda, an environment can be thought of as a completely separate installation.
Conda installs packages into environments efficiently using `hard links
<https://en.wikipedia.org/wiki/Hard_link>`_ by default when it is possible, so
environments are space efficient, and take seconds to create.

The default environment, which ``conda`` itself is installed into is called
``base``.  To create another environment, use the ``conda create``
command. For instance, to create an environment with the IPython notebook and
NumPy 1.6, which is older than the version that comes with Anaconda by
default, you would run

.. code-block:: bash

   $ conda create -n numpy16 ipython-notebook numpy=1.6

This creates an environment called ``numpy16`` with the latest version of
the IPython notebook, NumPy 1.6, and their dependencies.

We can now activate this environment, use

.. code-block:: bash

   # On Linux and Mac OS X
   $ source activate numpy16

   # On Windows
   > activate numpy16

This puts the bin directory of the ``numpy16`` environment in the front of the
``PATH``, and sets it as the default environment for all subsequent conda commands.

To go back to the base environment, use

.. code-block:: bash

   # On Linux and Mac OS X
   $ source deactivate

   # On Windows
   > deactivate


Building Your Own Packages
--------------------------

You can easily build your own packages for conda, and upload them
to `anaconda.org <https://anaconda.org>`_, a free service for hosting
packages for conda, as well as other package managers.
To build a package, create a recipe. Package building documentation is available
`here <https://conda.io/projects/conda-build/en/latest/>`_.
See https://github.com/AnacondaRecipes for the recipes that make up the Anaconda Distribution
and ``defaults`` channel. `Conda-forge <https://conda-forge.org/feedstocks/>`_ and
`Bioconda <https://github.com/bioconda/bioconda-recipes>`_ are community-driven
conda-based distributions.

To upload to anaconda.org, create an account.  Then, install the
anaconda-client and login

.. code-block:: bash

   $ conda install anaconda-client
   $ anaconda login

Then, after you build your recipe

.. code-block:: bash

   $ conda build <recipe-dir>

you will be prompted to upload to anaconda.org.

To add your anaconda.org channel, or the channel of others to conda so
that ``conda install`` will find and install their packages, run

.. code-block:: bash

   $ conda config --add channels https://conda.anaconda.org/username

(replacing ``username`` with the user name of the person whose channel you want
to add).

Getting Help
------------

The documentation for conda is at https://conda.io/en/latest/. You can
subscribe to the `conda mailing list
<https://groups.google.com/a/continuum.io/forum/#!forum/conda>`_.  The source
code and issue tracker for conda are on `GitHub <https://github.com/conda/conda>`_.

Contributing
------------

.. image:: https://gitpod.io/button/open-in-gitpod.svg
   :alt: open in gitpod for one-click development
   :target: https://gitpod.io/#https://github.com/conda/conda

Contributions to conda are welcome. See the `contributing <CONTRIBUTING.md>`_ documentation
for instructions on setting up a development environment.
