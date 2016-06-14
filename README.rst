.. NOTE: This file serves both as the README on GitHub and the index.html for
   conda.pydata.org. If you update this file, be sure to cd to the web
   directory and run ``make html; make live``

.. image:: https://s3.amazonaws.com/conda-dev/conda_logo.svg
   :alt: Conda Logo

----------------------------------------

.. image:: https://travis-ci.org/conda/conda.svg?branch=master
   :alt: Travis-CI Build Status
   :target: https://travis-ci.org/conda/conda

.. image:: https://ci.appveyor.com/api/projects/status/9k80kxa9gra9cjr9/branch/master?svg=true
   :alt: Appveyor Build Status
   :target: https://ci.appveyor.com/project/ironmancio54716/conda/branch/master

.. image:: https://codecov.io/github/conda/conda/coverage.svg?branch=master
   :alt: Codecov Status
   :target: https://codecov.io/github/conda/conda?branch=master

.. image:: https://scrutinizer-ci.com/g/conda/conda/badges/quality-score.png?b=master
   :alt: Scrutinizer Code Quality
   :target: https://scrutinizer-ci.com/g/conda/conda/?branch=master

.. image:: https://www.quantifiedcode.com/api/v1/project/81377831ebe54def8b31c55a4b5b4cb0/badge.svg
   :alt: Quantified Code
   :target: https://www.quantifiedcode.com/app/project/81377831ebe54def8b31c55a4b5b4cb0

.. image:: https://badges.gitter.im/conda/conda.svg
   :alt: Join the chat at https://gitter.im/conda/conda
   :target: https://gitter.im/conda/conda?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

Conda is a cross-platform, Python-agnostic binary package manager. It is the
package manager used by `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations, but it may be
used for other systems as well.  Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. Conda is written entirely in Python, and is BSD licensed open
source.

Conda is enhanced by organizations, tools, and repositories created and managed by the amazing members of the conda community.  Some of them can be found `here <https://github.com/conda/conda/wiki/Conda-Community>`_.


Installation
------------

Conda is a part of the `Anaconda distribution <https://store.continuum.io/cshop/anaconda/>`_.  You can also download a
minimal installation that only includes conda and its dependencies, called
`Miniconda <http://conda.pydata.org/miniconda.html>`_.


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
<http://en.wikipedia.org/wiki/Hard_links>`_ by default when it is possible, so
environments are space efficient, and take seconds to create.

The default environment, which ``conda`` itself is installed into is called
``root``.  To create another environment, use the ``conda create``
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

To go back to the root environment, use

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
To build a package, create a recipe.
See http://github.com/conda/conda-recipes for many example recipes, and
http://docs.continuum.io/conda/build.html for documentation on how to build
recipes.

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

The documentation for conda is at http://conda.pydata.org/docs/. You can
subscribe to the `conda mailing list
<https://groups.google.com/a/continuum.io/forum/#!forum/conda>`_.  The source
code and issue tracker for conda are on `GitHub <https://github.com/conda/conda>`_.

Contributing
------------

Contributions to conda are welcome. Just fork the GitHub repository and send a
pull request.

To develop on conda, the easiest way is to use a development build. This can be
accomplished as follows:

* clone the conda git repository to a computer with conda already installed
* navigate to the root directory of the git clone
* run ``$CONDA/bin/python setup.py develop`` where ``$CONDA`` is the path to your
  miniconda installation

Note building a development file requires git to be installed.

To undo this, run ``$CONDA/bin/python setup.py develop -u``.  Note that if you
used a python other than ``$CONDA/bin/python`` to install, you may have to manually
delete the conda executable.  For example, on OS X, if you use a homebrew python
located at ``/usr/local/bin/python``, then you'll need to ``rm /usr/local/bin/conda``
so that ``which -a conda`` lists first your miniconda installation.

If you are worried about breaking your conda installation, you can install a
separate instance of `Miniconda <http://conda.pydata.org/miniconda.html>`_ and
work off it. This is also the only way to test conda in both Python 2 and
Python 3, as conda can only be installed into a root environment.

Run the conda tests by ``conda install pytest pytest-cov`` and then running ``py.test``
in the conda directory. The tests are also run by Travis CI when you make a
pull request.
