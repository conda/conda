============================
 Using conda with Travis CI
============================

If you are already using Travis CI, using conda is a preferable alternative
to using apt-get and pip to install packages. The Debian repos provided
by Travis may not include versions of Python packages for all versions
of Python, or may not be updated as quickly. Pip installing such packages
may also be undesirable, as this can take a while, eating up a large chunk
of the 50 minutes that Travis allows for each build. Using conda also lets
you test the building of conda recipes on Travis.

Conda is language-agnostic, so it can be used for anything, not just Python, but
the following guide shows how to use it to test a Python package on Travis CI.

The .travis.yml file
====================

The
following shows how to modify the ``.travis.yml`` file to use `Miniconda
<http://conda.pydata.org/miniconda.html>`_ for a project that supports Python
2.6, 2.7, 3.3, and 3.4.

NOTE: Please see the Travis CI website for information about the `basic configuration for
Travis <http://docs.travis-ci.com/user/languages/python/#Examples>`_.

.. code-block:: yaml

   language: python
   python:
     # We don't actually use the Travis Python, but this keeps it organized.
     - "2.6"
     - "2.7"
     - "3.3"
     - "3.4"
   install:
     - sudo apt-get update
     # We do this conditionally because it saves us some downloading if the
     # version is the same.
     - if [[ "$TRAVIS_PYTHON_VERSION" == "2.7" ]]; then
         wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh -O miniconda.sh;
       else
         wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh;
       fi
     - bash miniconda.sh -b -p $HOME/miniconda
     - export PATH="$HOME/miniconda/bin:$PATH"
     - hash -r
     - conda config --set always_yes yes --set changeps1 no
     - conda update -q conda
     # Useful for debugging any issues with conda
     - conda info -a

     # Replace dep1 dep2 ... with your dependencies
     - conda create -q -n test-environment python=$TRAVIS_PYTHON_VERSION dep1 dep2 ...
     - source activate test-environment
     - python setup.py install

   script:
     # Your test script goes here

Additional Steps
================

If you wish to support a package that doesn't have official Continuum builds,
you can build it yourself, and add it to a Anaconda.org channel. You can
then add

.. code-block:: yaml

   - conda config --add channels your_Anaconda_dot_org_username

to the install steps in ``.travis.yml`` so that it finds the packages on that
channel.


Building a Conda Recipe
=======================

If you support official conda packages for your project, you may want to use
``conda build`` in Travis, so the building of your recipe is tested as
well.  We recommend that you include the conda recipe in the same directory
as your source code. Then replace the following:

.. code-block:: yaml

   - python setup.py install

with

.. code-block:: yaml

   - conda build your-conda-recipe
   - conda install your-package --use-local
   
For more information on building conda packages, see the `conda build <http://conda.pydata.org/docs/build.html>`_ section
and the example recipes in the `conda-recipes repo <https://github.com/conda/conda-recipes>`_.


AppVeyor
========

An alternative to using Travis CI with conda is `AppVeyor <http://www.appveyor.com/>`_, a continuous build
service for Windows built on Azure.

You can see an example project for building conda packages on AppVeyor located at
https://github.com/rmcgibbo/python-appveyor-conda-example.
