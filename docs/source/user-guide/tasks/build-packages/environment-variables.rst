.. _env-vars:

=====================
Environment variables
=====================

.. contents::
   :local:
   :depth: 1

.. _build-state:

Dynamic behavior based on state of build process
=================================================

There are times when you may want to process a single file in
different ways at more than one step in the render-build-test
flow of conda build. Conda build sets the CONDA_BUILD_STATE
environment variable during each of these phases. The possible
values are:

* RENDER---Set during evaluation of the ``meta.yaml`` file.

* BUILD---Set during processing of the ``bld.bat`` or
  ``build.sh`` script files.

* TEST---Set during the running of any ``run_test`` scripts,
  which also includes any commands defined in ``meta.yaml`` in
  the ``test/commands`` section.

The CONDA_BUILD_STATE variable is undefined outside
of these locations.


Environment variables set during the build process
===================================================

During the build process, the following environment variables
are set, on Windows with ``bld.bat`` and on macOS and Linux with
``build.sh``. By default, these are the only variables available
to your build script. Unless otherwise noted, no variables are
inherited from the shell environment in which you invoke
``conda-build``. To override this behavior, see
:ref:`inherited-env-vars`.


.. list-table::
   :widths: 20 80

   * - ARCH
     - Either ``32`` or ``64``, to specify whether the build is
       32-bit or 64-bit.  The value depends on the ARCH
       environment variable and  defaults to the architecture the
       interpreter running conda was
       compiled with.
   * - CMAKE_GENERATOR
     - The CMake generator string for the current build
       environment. On Linux systems, this is always
       ``Unix Makefiles``. On Windows, it is generated according
       to the Visual Studio version activated at build time, for
       example, ``Visual Studio 9 2008 Win64``.
   * - CONDA_BUILD=1
     - Always set.
   * - CPU_COUNT
     - The number of CPUs on the system, as reported by
       ``multiprocessing.cpu_count()``.
   * - SHLIB_EXT
     - The shared library extension.
   * - DIRTY
     - Set to 1 if the ``--dirty`` flag is passed to the
       ``conda-build`` command. May be used to  skip parts of a
       build script conditionally for faster iteration time when
       developing recipes. For example, downloads, extraction and
       other things that need not be repeated.
   * - HTTP_PROXY
     - Inherited from your shell environment.
   * - HTTPS_PROXY
     - Inherited from your shell environment.
   * - LANG
     - Inherited from your shell environment.
   * - MAKEFLAGS
     - Inherited from your shell environment. May be used to set
       additional arguments to make, such as ``-j2``, which uses
       2 CPU cores to build your recipe.
   * - PY_VER
     - Python version building against. Set with the ``--python`` argument
       or with the CONDA_PY environment variable.
   * - NPY_VER
     - NumPy version to build against. Set with the ``--numpy``
       argument or with the CONDA_NPY environment variable.
   * - PATH
     - Inherited from your shell environment and augmented with
       ``$PREFIX/bin``.
   * - PREFIX
     - Build prefix to which the build script should install.
   * - PKG_BUILDNUM
     - Build number of the package being built.
   * - PKG_NAME
     - Name of the package being built.
   * - PKG_VERSION
     - Version of the package being built.
   * - ``PKG_BUILD_STRING``
     - Complete build string of the package being built, including hash.
       EXAMPLE: py27h21422ab_0 . Conda-build 3.0+.
   * - ``PKG_HASH``
     - Hash of the package being built, without leading h. EXAMPLE: 21422ab .
       Conda-build 3.0+.
   * - PYTHON
     - Path to the Python executable in the host prefix. Python
       is installed only in the host prefix when it is listed as
       a host requirement.
   * - PY3K
     - ``1`` when Python 3 is installed in the build prefix,
       otherwise ``0``.
   * - R
     - Path to the R executable in the build prefix. R is only
       installed in the build prefix when it is listed as a build
       requirement.
   * - RECIPE_DIR
     - Directory of the recipe.
   * - SP_DIR
     - Python's site-packages location.
   * - SRC_DIR
     - Path to where source is unpacked or cloned. If the source
       file is not a recognized file type---zip, tar, tar.bz2, or
       tar.xz---this is a directory containing a copy of the
       source file.
   * - STDLIB_DIR
     - Python standard library location.

Unix-style packages on Windows, which are usually statically
linked to executables, are built in a special ``Library``
directory under the build prefix. The environment variables
listed in the following table are defined only on Windows.

.. list-table::
   :widths: 20 80

   * - CYGWIN_PREFIX
     - Same as PREFIX, but as a Unix-style path, such as
       ``/cygdrive/c/path/to/prefix``.
   * - LIBRARY_BIN
     - ``<build prefix>\Library\bin``.
   * - LIBRARY_INC
     - ``<build prefix>\Library\include``.
   * - LIBRARY_LIB
     - ``<build prefix>\Library\lib``.
   * - LIBRARY_PREFIX
     - ``<build prefix>\Library``.
   * - SCRIPTS
     - ``<build prefix>\Scripts``.
   * - VS_MAJOR
     - The major version number of the Visual Studio version
       activated within the build, such as ``9``.
   * - VS_VERSION
     - The version number of the Visual Studio version activated
       within the build, such as ``9.0``.
   * - VS_YEAR
     - The release year of the Visual Studio version activated
       within the build, such as ``2008``.

The environment variables listed in the following table are
defined only on macOS and Linux.

.. list-table::
   :widths: 20 80

   * - HOME
     - Standard $HOME environment variable.
   * - PKG_CONFIG_PATH
     - Path to ``pkgconfig`` directory.

The environment variables listed in the following table are
defined only on macOS.

.. list-table::
   :widths: 20 80

   * - CFLAGS
     - ``-arch`` flag.
   * - CXXFLAGS
     - Same as CFLAGS.
   * - LDFLAGS
     - Same as CFLAGS.
   * - MACOSX_DEPLOYMENT_TARGET
     - Same as the Anaconda Python macOS deployment target. Currently ``10.6``.
   * - OSX_ARCH
     - ``i386`` or ``x86_64``, depending on Python build.

The environment variable listed in the following table is
defined only on Linux.

.. list-table::
   :widths: 20 80

   * - LD_RUN_PATH
     - ``<build prefix>/lib``.


.. _git-env:

Git environment variables
==========================

The environment variables listed in the following table are
defined when the source is a git repository, specifying the
source either with git_url or path.

.. list-table::
   :widths: 20 80

   * - GIT_BUILD_STR
     - String that joins GIT_DESCRIBE_NUMBER and
       GIT_DESCRIBE_HASH by an underscore.
   * - GIT_DESCRIBE_HASH
     - The current commit short-hash as displayed from
       ``git describe --tags``.
   * - GIT_DESCRIBE_NUMBER
     - String denoting the number of commits since the most
       recent tag.
   * - GIT_DESCRIBE_TAG
     - String denoting the most recent tag from the current
       commit, based on the output of ``git describe --tags``.
   * - GIT_FULL_HASH
     - String with the full SHA1 of the current HEAD.

These can be used in conjunction with templated ``meta.yaml``
files to set things---such as the build string---based on the
state of the git repository.

.. _mercurial-env-vars:

Mercurial environment variables
=================================

The environment variables listed in the following table are
defined when the source is a mercurial repository.

.. list-table::
   :widths: 20 80

   * - HG_BRANCH
     - String denoting the presently active branch.
   * - HG_BUILD_STR
     - String that joins HG_NUM_ID and HG_SHORT_ID by an
       underscore.
   * - HG_LATEST_TAG
     - String denoting the most recent tag from the current
       commit.
   * - HG_LATEST_TAG_DISTANCE
     - String denoting number of commits since the most recent
       tag.
   * - HG_NUM_ID
     - String denoting the revision number.
   * - HG_SHORT_ID
     - String denoting the hash of the commit.


.. _inherited-env-vars:

Inherited environment variables
==================================

Other than those mentioned above, no variables are inherited from
the environment in which you invoke conda build. You can choose
to inherit additional environment variables by adding them to
``meta.yaml``:

.. code-block:: yaml

     build:
       script_env:
        - TMPDIR
        - LD_LIBRARY_PATH # [linux]
        - DYLD_LIBRARY_PATH # [osx]

If an inherited variable is missing from your shell environment,
it remains unassigned, but a warning is issued noting that it has
no value assigned.

NOTE: Inheriting environment variables can make it difficult for
others to reproduce binaries from source with your recipe. Use
this feature with caution or avoid it.

NOTE: If you split your build and test phases with ``--no-test`` and ``--test``,
you need to ensure that the environment variables present at build time and test
time match. If you do not, the package hashes may use different values, and your
package may not be testable, because the hashes will differ.


.. _build-envs:

Environment variables that affect the build process
=====================================================

.. list-table::
   :widths: 20 80

   * - CONDA_PY
     - The Python version used to build the package. Should
       be ``27``, ``34``, ``35`` or ``36``.
   * - CONDA_NPY
     - The NumPy version used to build the package, such as
       ``19``, ``110`` or ``111``.
   * - CONDA_PREFIX
     - The path to the conda environment used to build the
       package, such as ``/path/to/conda/env``. Useful to pass as
       the environment prefix parameter to various conda tools,
       usually labeled ``-p`` or ``--prefix``.


.. _build-features:

Environment variables to set build features
============================================

The environment variables listed in the following table are
inherited from the process running conda build. These variables
control :doc:`features`.

.. list-table::
   :widths: 15 43 42

   * - FEATURE_NOMKL
     - Adds the ``nomkl`` feature to the built package.
     - Accepts ``0`` for off and ``1`` for on.
   * - FEATURE_DEBUG
     - Adds the ``debug`` feature to the built package.
     - Accepts ``0`` for off and ``1`` for on.
   * - FEATURE_OPT
     - Adds the ``opt`` feature to the built package.
     - Accepts ``0`` for off and ``1`` for on.


.. _test-envs:

Environment variables that affect the test process
====================================================

All of the above environment variables are also set during the
test process, using the test prefix instead of the build
prefix.
