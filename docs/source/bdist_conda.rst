======================
 setup.py bdist_conda
======================

You can build a conda package for a Python library using ``python setup.py
bdist_conda``.   ``python`` in this case must be the Python where conda is
installed, as ``bdist_conda`` uses ``conda-build``.

``bdist_conda`` will use the metadata provided to the ``setup()`` function.

In addition, several options to ``setup()`` are supported.

If you want to pass any ``bdist_conda`` specific options to ``setup()``, you
must set ``distclass=distutils.command.bdist_conda.CondaDistribution`` in
``setup()``.

.. note::

   If you use ``setuptools``, you must import ``setuptools`` *before*
   importing ``distutils.commands.bdist_conda``, as ``setuptools``
   monkeypatches ``distutils.dist.Distribution``.

Notes
=====

- ``bdist_conda`` can only be installed into a root conda environment, as it
  imports ``conda`` and ``conda_build``.

- To build against different versions of Python or NumPy, set the ``CONDA_PY``
  or ``CONDA_NPY`` environment variables, e.g., ``CONDA_PY=33`` will build
  against Python 3.3.  See :ref:`build-envs` for more information.

- All metadata is gathered from the standard metadata from the ``setup()``
  function. Metadata that is not directly supported by ``setup()`` can be
  added using one of the options specified below.

- By default, import tests are run for each subpackage specified by
  ``packages``, and command line tests (``command --help``) are run for each
  setuptools ``entry_points`` command.  This is done to ensure that the
  package is built correctly. These can be disabled or changed using the
  ``conda_import_tests`` and ``conda_command_tests`` options specified below.

Options
=======

All of the following options are optional.

``setup()`` Options
-------------------

Options that can be passed to ``setup()`` (must include
``distclass=CondaDistribution``):

- ``conda_buildnum``: The build number. Defaults to 0. Can be overridden on
  the command line with the ``--buildnum`` flag.

- ``conda_buildstr``: The build string. Default is generated automatically
  from the Python version, NumPy version if relevant, and the build number,
  like ``py34_0``.

- ``conda_import_tests``: Whether to automatically run import tests. The
  default is ``True``, which runs import tests for the all the modules in
  "packages". Also allowed are ``False``, which runs no tests, or a list of
  module names to be tested on import.

- ``conda_command_tests``: Command line tests to run. Default is ``True``,
  which runs ``command --help`` for each ``command`` in the
  ``console_scripts`` and ``gui_scripts`` ``entry_points``. Also allowed are
  ``False``, which doesn't run any command tests, or a list of command tests
  to run.

- ``conda_binary_relocation``: Whether binary files should be made relocatable
  (using ``install_name_tool`` on OS X or ``patchelf`` on Linux). The default
  is ``True``. See the :ref:`relocatable` section in the conda build
  documentation for more information on this.

- ``conda_preserve_egg_dir``: Whether to preserve the egg directory as
  installed by setuptools.  The default is ``True`` if the package depends on
  setuptools or has a setuptools ``entry_points`` other than
  ``console_scripts`` and ``gui_scripts``.

- ``conda_features``: List of features for the package. See the
  :ref:`features` section of the conda build documentation for more
  information about features in conda.

- ``conda_track_features``: List of features that this package should track
  (enable when installed).  See the :ref:`features` section of the conda build
  documentation for more information about features in conda.

Command line options
--------------------

``--buildnum``: Set the build number. Defaults to the ``conda_buildnum``
  passed to ``setup()``, or 0. Overrides any ``conda_buildnum`` passed to
  ``setup()``.
