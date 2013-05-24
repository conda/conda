.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====
Conda
=====


The conda command is the primary interface for managing Anaconda installations. It can query and search the Anaconda package index and current Anaconda installation, create new Anaconda environments, and install and update packages into existing Anaconda environments.

Getting Started
---------------

.. code-block:: bash

    # First, let's check our system NumPy version

    $ python
    Python 2.7.3 |Anaconda 1.2.1 (x86_64)| (default, Nov 20 2012, 22:44:26)
    [GCC 4.0.1 (Apple Inc. build 5493)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import numpy
    >>> numpy.version.full_version
    '1.7.0b2'

    # Now we'll create an anaconda environment using a different version of NumPy

    $ conda create -p ~/anaconda/envs/test numpy=1.6 anaconda

    Package plan for creating environment at /Users/maggie/anaconda/envs/test:

    The following packages will be downloaded:

    [      COMPLETE      ] |#################################################| 100%

    # Next, we adjust our PATH variable to point to the new environment

    $ export PATH=~/anaconda/envs/test/bin/:$PATH

    # Finally, we check the version again

    $ python
    Python 2.7.3 |AnacondaCE 1.3.0 (x86_64)| (unknown, Jan 10 2013, 12:19:03)
    [GCC 4.0.1 (Apple Inc. build 5493)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import numpy
    >>> numpy.version.full_version
    '1.6.2'


User Guide
----------
.. toctree::
   :maxdepth: 1

   intro
   examples

Reference Guide
---------------

.. toctree::
   :maxdepth: 2

   commands

Requirements
------------

* python 2.7
* pyyaml


License Agreement
-----------------

``conda`` is distributed under the `OpenBSD license <http://opensource.org/licenses/bsd-license.php>`_.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
