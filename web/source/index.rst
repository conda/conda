.. Conda documentation master file, created by
   sphinx-quickstart on Fri Oct 25 16:40:03 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


=====
Conda
=====


Conda is a cross-platform, Python-agnostic binary package manager. It is the
package manager used by `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations, but it may be
used for other systems as well.  Conda makes environments first-class
citizens. `conda` is written entirely in Python, and is BSD licensed open
source.


Installation
------------

conda is a part of the Anaconda distribution which can be downloaded `here
<https://store.continuum.io/cshop/anaconda/>`_.  You can also download a
minimal installation that only includes conda and its dependencies, called
Miniconda, `here <http://repo.continuum.io/miniconda/index.html>`_.

It is also possible to `pip` install conda, by doing

.. code-block:: bash

   $ pip install conda
   $ conda init

However, there are several disadvantages to pip installing conda, and the
recommended way to obtain conda is to use Anaconda or Miniconda.

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

The default environment, which `conda` itself is installed into is called
`root`.  To create another environment, use the `conda create` command. For
instance, to create an environment with the IPython notebook and NumPy 1.6,
which is older than the version that comes with Anaconda by default, you would
run

.. code-block:: bash

   $ conda create -n numpy16 ipython-notebook numpy=1.6

This creates an environment called `numpy16` with the latest version of
the IPython notebook, NumPy 1.6, and their dependencies.

We can now activate this environment. On Linux and Mac OS X, use

.. code-block:: bash

   $ source activate numpy16

This puts the bin directory of the `numpy16` environment in the front of the
`PATH`, and sets it as the default environment for all subsequent conda commands.

To go back to the root environment, use

.. code-block:: bash

   $ source deactivate


Getting Help
------------

The documentation for conda is at http://docs.continuum.io/conda/. You can
subscribe to the `conda mailing list
<https://groups.google.com/a/continuum.io/forum/#!forum/conda>`_.  The source
code and issue tracker for conda is on `GitHub <https://github.com/pydata/conda>`_.

..
   Uncomment this when there is more than one page
      Contents:

      .. toctree::
         :maxdepth: 2
