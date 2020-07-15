==========================
Using conda with Travis CI
==========================

.. contents::
   :local:
   :depth: 1


If you are already using Travis CI, using conda is a preferable
alternative to using apt and pip to install packages. The
Debian repos provided by Travis may not include packages for all
versions of Python or may not be updated as quickly. Installing
such packages with pip may also be undesirable, as this can take
a long time, which can consume a large portion of the 50 minutes
that Travis allows for each build. Using conda also lets you test
the building of conda recipes on Travis.

This page describes how to use conda to test a Python package
on Travis CI. However, you can use conda with any language, not
just Python.


The .travis.yml file
====================

The following code sample shows how to modify the ``.travis.yml``
file to use `Miniconda <https://conda.io/miniconda.html>`_ for a
project that supports Python 2.7, 3.5, and 3.6:

.. code-block:: yaml

   language: python
   python:
     # We don't actually use the Travis Python, but this keeps it organized.
     - "2.7"
     - "3.5"
     - "3.6"
   install:
     - sudo apt update
     # We do this conditionally because it saves us some downloading if the
     # version is the same.
     - if [[ "$TRAVIS_PYTHON_VERSION" == "2.7" ]]; then
         wget https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh -O miniconda.sh;
       else
         wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh;
       fi
     - bash miniconda.sh -b -p $HOME/miniconda
     - source "$HOME/miniconda/etc/profile.d/conda.sh"
     - hash -r
     - conda config --set always_yes yes --set changeps1 no
     - conda update -q conda
     # Useful for debugging any issues with conda
     - conda info -a

     # Replace dep1 dep2 ... with your dependencies
     - conda create -q -n test-environment python=$TRAVIS_PYTHON_VERSION dep1 dep2 ...
     - conda activate test-environment
     - python setup.py install

   script:
     # Your test script goes here

.. note::
   For information about the basic configuration for Travis CI,
   see `Building a Python Project
   <http://docs.travis-ci.com/user/languages/python/#Examples>`_.


Supporting packages that do not have official builds
====================================================

To support a package that does not have official Anaconda builds:

#. Build the package yourself.

#. Add it to an `Anaconda.org <http://Anaconda.org>`_ channel.

#. Add the following line to the install steps in ``.travis.yml``
   so that it finds the packages on that channel:

   .. code-block:: yaml

      - conda config --add channels your_Anaconda_dot_org_username


   .. note::
      Replace ``your_Anaconda_dot_org_username`` with your
      user name.


Building a conda recipe
=======================

If you support official conda packages for your project, you may
want to use conda-build in Travis, so the building of your
recipe is tested as well.

#. Include the conda recipe in the same directory as your source
   code.

#. In your ``.travis.yml`` file, replace the following line:

   .. code-block:: yaml

      - python setup.py install

   with these lines:

   .. code-block:: yaml

      - conda build your-conda-recipe
      - conda install your-package --use-local


AppVeyor
========

`AppVeyor <http://www.appveyor.com/>`_ is a continuous build
service for Windows built on Azure and is an alternative to using
Travis CI with conda.

For an example project building conda packages on AppVeyor, see
https://github.com/rmcgibbo/python-appveyor-conda-example.

Bootstrap your environment
==========================

To bootstrap your environment, use the standalone conda
approach in your ``appveyor.yml``:

.. code-block:: yaml
   
   # Config file for automatic testing at travis-ci.org

   language: python
   python:
     - "2.7"
     - "3.7"

   install:
     - wget https://repo.anaconda.com/pkgs/misc/conda-execs/conda-latest-linux-64.exe -O conda.exe
     - chmod +x conda.exe
     - export CONDA_ALWAYS_YES=1
     # This is where you put any extra dependencies you may have.
     - ./conda.exe create -p $HOME/miniconda python=$TRAVIS_PYTHON_VERSION conda conda-build pytest six pytest-cov pytest-mock
     - export PATH="$HOME/miniconda/bin:$PATH"
     - hash -r
     # Install your code here.
   script:
     - pytest -v --color=yes --cov=cpr tests
   after_success:
     - conda install codecov
     - codecov
