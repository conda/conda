.. NOTE: This file serves both as the README on GitHub and the index.html for
   conda.pydata.org. If you update this file, be sure to cd to the web
   directory and run ``make html; make live``

=====
Conda
=====


Conda is a cross-platform, Python-agnostic binary package manager. It is the
package manager used by `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations, but it may be
used for other systems as well.  Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. Conda is written entirely in Python, and is BSD licensed open
source.


Installation
------------

Conda is a part of the `Anaconda distribution <https://store.continuum.io/cshop/anaconda/>`_.  You can also download a
minimal installation that only includes conda and its dependencies, called
:ref:`Miniconda`.


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

We can now activate this environment. On Linux and Mac OS X, use

.. code-block:: bash

   $ source activate numpy16

This puts the bin directory of the ``numpy16`` environment in the front of the
``PATH``, and sets it as the default environment for all subsequent conda commands.

To go back to the root environment, use

.. code-block:: bash

   $ source deactivate


Building Your Own Packages
--------------------------

You can easily build your own packages for conda, and upload them to `Binstar
<https://binstar.org>`_, a free service for hosting packages for conda, as
well as other package managers.  To build a package, create a recipe.  See
http://github.com/conda/conda-recipes for many example recipes, and
http://docs.continuum.io/conda/build.html for documentation on how to build
recipes.

To upload to Binstar, create an account on binstar.org.  Then, install the
binstar client and login

.. code-block:: bash

   $ conda install binstar
   $ binstar login

Then, after you build your recipe

.. code-block:: bash

   $ conda build <recipe-dir>

you will be prompted to upload to binstar.

To add your Binstar channel, or the channel of others to conda so that ``conda
install`` will find and install their packages, run

.. code-block:: bash

   $ conda config --add channels https://conda.binstar.org/username

(replacing ``username`` with the user name of the person whose channel you want
to add).

Getting Help
------------

The documentation for conda is at http://docs.continuum.io/conda/. You can
subscribe to the `conda mailing list
<https://groups.google.com/a/continuum.io/forum/#!forum/conda>`_.  The source
code and issue tracker for conda are on `GitHub <https://github.com/conda/conda>`_.

--------

Contents:

.. toctree::
   :maxdepth: 2

   miniconda.rst
