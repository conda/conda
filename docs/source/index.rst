.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====
Conda
=====

==============
Intro to Conda
==============

Conda is an open source package management system and environment management system for installing multiple
versions of binary software packages and their dependencies and switching easily between them. It works on
Windows, OS X, and Linux, and was created for Python programs but can package and distribute any software.

Conda is included in all versions of Anaconda, Anaconda Server, and Miniconda, and is not available separately. 

* Miniconda is a small “bootstrap” version that includes only conda and conda-build, and installs Python. About
  279 scientific packages and their dependencies can be installed individually from the Continuum repository with
  the “conda install” command.
* Anaconda includes conda, conda-build and Python, plus about 100 automatically installed scientific packages and
  their dependencies. Like Miniconda, the 279 scientific packages can be installed individually with
  the “conda install” command.
* Anaconda Server allows both system administrators and users to manage packages and environments on-site. Any
  software application stack can be managed, including Python, R, NodeJs, Java, and more. It is sold by
  Continuum Analytics.

The `conda` command is the primary interface for managing `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations. It can query
and search the Anaconda package index and current Anaconda installation,
create new conda environments, and install and update packages into existing
conda environments.


Getting Started
---------------

To demonstrate the ease of a typical conda workflow, we will create a conda environment
with a version of `NumPy <http://www.numpy.org>`_ different from the default version.

First, we will check our system's Numpy version

.. code-block:: bash

    $ python
    Python 2.7.5 |Anaconda 1.6.1 (x86_64)| (default, Jun 28 2013, 22:20:13)
    [GCC 4.0.1 (Apple Inc. build 5493)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import numpy
    >>> numpy.__version__
    '1.7.1'

Next we will create a conda environment using a different version of NumPy

.. code-block:: none

    $ conda create -p ~/anaconda/envs/test numpy=1.6 anaconda

    Package plan for creating environment at /Users/maggie/anaconda/envs/test:

    The following packages will be downloaded:

    [      COMPLETE      ] |#################################################| 100%

Now we change our **PATH** variable to point to the new environment

.. code-block:: bash

    $ export PATH=~/anaconda/envs/test/bin/:$PATH

Finally, we check the version of Numpy again

.. code-block:: python

    $ python
    Python 2.7.5 |Anaconda 1.6.1 (x86_64)| (unknown, Jan 10 2013, 12:19:03)
    [GCC 4.0.1 (Apple Inc. build 5493)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import numpy
    >>> numpy.__version__
    '1.6.2'


User Guide
----------
.. toctree::
   :maxdepth: 2

   intro
   quick-install
   installation
   test-drive
   examples
   faq
   troubleshooting
   glossary
   config
   build
   build_tutorials
   admin
   custom-channels


Reference Guide
---------------

.. toctree::
   :maxdepth: 2

   commands
   build-commands
   env-commands
   spec
   travis
   bdist_conda
   license

Presentations & Blog Posts
--------------------------

`Packaging and Deployment with conda - Travis Oliphant <https://speakerdeck.com/teoliphant/packaging-and-deployment-with-conda>`_

`Python 3 support in Anaconda - Ilan Schnell <http://continuum.io/blog/anaconda-python-3>`_

`New Advances in conda - Ilan Schnell <http://continuum.io/blog/new-advances-in-conda>`_

`Python Packages and Environments with conda - Bryan Van de Ven <http://continuum.io/blog/conda>`_

`Advanced features of Conda, part 1 - Aaron Meurer <http://continuum.io/blog/advanced-conda-part-1>`_

`Advanced features of Conda, part 2 - Aaron Meurer <http://continuum.io/blog/advanced-conda-part-2>`_

Requirements
------------

* python 2.7, 3.3, or 3.4
* pycosat
* pyyaml
* requests


License Agreement
-----------------

conda is distributed under the `BSD license <http://opensource.org/licenses/bsd-license.php>`_.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
