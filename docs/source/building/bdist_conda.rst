===========
Bdist_conda
===========

You can use conda build to build packages for Python to install rather than 
conda, by using ``setup.py bdist_conda``. This is a “quick and dirty” way to 
build packages without using a recipe, but it has limitations. The script 
is limited to the Python version used in the build. And it is not as 
reproducible as using a recipe. We recommend using a recipe with conda 
build. 

NOTE: If you use Setuptools, you must first import Setuptools and then 
import ``distutils.command.bdist_conda``, because Setuptools monkeypatches 
``distutils.dist.Distribution``.

Example
=======

A minimal setup.py file using setup options name and version:

.. code::

   from distutils.core import setup, Extension
   import distutils.command.bdist_conda

  setup(
      name="foo",
      version="1.0",
      distclass=distutils.command.bdist_conda.CondaDistribution,
      conda_buildnum=1,
      conda_features=['mkl'],
  )


Setup options
=============

Options that can be passed to ``setup()`` (must include 
``distclass=distutils.command.bdist_conda.CondaDistribution)``:

Build number
--------------

The number of the build. Can be overridden on the command line with the ``--buildnum`` flag. 
Defaults to 0. 

.. code::

   conda_buildnum=1


Build string
-------------

The build string. Default is generated automatically from the Python version, NumPy version 
if relevant, and the build number, like ``py34_0``.

.. code::

   conda_buildstr=py34_0

Import tests
-------------

Whether to automatically run import tests. The default is True, which runs import tests for the all 
the modules in “packages”. Also allowed are False, which runs no tests, or a list of module names to 
be tested on import.

.. code::

   conda_import_tests=False

Command line tests
-------------------

Command line tests to run. Default is True, which runs ``command --help`` for each command in the 
``console_scripts`` and ``gui_scripts entry_points``. Also allowed are False, which doesn’t run any 
command tests, or a list of command tests to run.

.. code::

   conda_command_tests=False

Binary files relocatable
------------------------

Whether binary files should be made relocatable (using ``install_name_tool`` on OS X or ``patchelf`` on Linux). 
The default is True. 

.. code::

   conda_binary_relocation=False

SEE ALSO:  :ref:`relocatable`  section in the conda build documentation for more information.

Preserve egg directory
-----------------------

Whether to preserve the egg directory as installed by Setuptools. The default is True if the package depends 
on Setuptools or has Setuptools ``entry_points`` other than ``console_scripts`` and ``gui_scripts``.

.. code::

   conda_preserve_egg_dir=False

Features
-------------

List of features for the package. 

.. code::

   conda_features=['mkl'] 

SEE ALSO:  :ref:`features` section of the conda build documentation for more information about features in conda.


Track features
-----------------

List of features that this package should track (enable when installed). 

.. code::

   conda_track_features=['mkl'] 

SEE ALSO:  :ref:`features` section of the conda build documentation for more information about 
features in conda.

Command line options
====================

Build number
-------------

Set the build number. Defaults to the ``conda_buildnum`` passed to ``setup()``, or 0. Overrides any ``conda_buildnum`` passed to ``setup()``.

.. code::

   --buildnum=1

Notes
=====

- ``bdist_conda`` must be installed into a root conda environment, as it imports ``conda`` and ``conda_build``. It is included as part of the ``conda build`` package.

- All metadata is gathered from the standard metadata from the ``setup()`` function. Metadata that are not directly supported by ``setup()`` can be added using one of the options specified below.

- By default, import tests are run for each subpackage specified by packages, and command line tests ``command --help`` are run for each ``setuptools entry_points`` command. This is done to ensure that the package is built correctly. These can be disabled or changed using the ``conda_import_tests`` and ``conda_command_tests`` options specified below.

- The Python version used in the build must be the same as where conda is installed, as ``bdist_conda`` uses ``conda-build``.

- ``bdist_conda`` uses the metadata provided to the ``setup()`` function.

- If you want to pass any ``bdist_conda`` specific options to ``setup()``, in ``setup()`` you must set ``distclass=distutils.command.bdist_conda.CondaDistribution``.
