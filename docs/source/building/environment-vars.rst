.. _env-vars:

Environment variables
=====================

Environment variables set during the build process
--------------------------------------------------

The following environment variables are set, both on Unix (build.sh) and on 
Windows (bld.bat) during the build process.
(By default, these are the only variables available to your build script --
unless otherwise noted, no variables are inherited from the shell environment
in which you invoked ``conda build``. See :ref:`inherited-env-vars` to
override this behavior.)

.. list-table::

  * - ``ARCH``
    - Either ``32`` or ``64``, to specify whether the build is 32-bit or
      64-bit.  The value depends on the ``ARCH`` environment variable, and
      defaults to the architecture the interpreter running conda was
      compiled with
  * - ``CMAKE_GENERATOR``
    - The CMake generator string for the current build environment. On Unix
      systems, this is always "Unix Makefiles". On Windows, it is generated
      according to the Visual Studio version activated at build time,
      e.g. "Visual Studio 9 2008 Win64"
  * - ``CONDA_BUILD=1``
    - Always set
  * - ``CPU_COUNT``
    - Number of CPUs on the system, as reported by
      ``multiprocessing.cpu_count()``
  * - ``DIRTY``
    - Set to 1 if `--dirty` flag passed to `conda build` command.  May be used to skip parts of
      build script conditionally (downloads, extraction, other things that need not be repeated
      for faster iteration time when developing recipes)
  * - ``HTTP_PROXY``
    - Inherited from your shell environment.
  * - ``HTTPS_PROXY``
    - Inherited from your shell environment.
  * - ``LANG``
    - Inherited from your shell environment.
  * - ``MAKEFLAGS``
    - Inherited from your shell environment. May be used to set additional
      arguments to make, such as `-j2`, which will use 2 CPU cores to build
      your recipe.
  * - ``NPY_VER``
    - Numpy version building against (Set via `--numpy` arg or via `CONDA_NPY` environment variable.)
  * - ``PATH``
    - Inherited from your shell environment, and augmented with ``$PREFIX/bin``
  * - ``PREFIX``
    - Build prefix where build script should install to
  * - ``PKG_BUILDNUM``
    - Build number of the package being built
  * - ``PKG_NAME``
    - Name of the package being built
  * - ``PKG_VERSION``
    - Version of the package being built
  * - ``PYTHON``
    - Path to Python executable in build prefix (note that Python is only
      installed in the build prefix when it is listed as a build requirement)
  * - ``PY3K``
    - ``1`` when Python 3 is installed in build prefix, else ``0``
  * - ``R``
    - Path to R executable in build prefix (note that R is only
      installed in the build prefix when it is listed as a build requirement).
  * - ``RECIPE_DIR``
    - Directory of recipe
  * - ``SP_DIR``
    - Python's site-packages location
  * - ``SRC_DIR``
    - Path to where source is unpacked (or cloned). If the source file is not
      a recognized file type (right now, ``.zip``, ``.tar``, ``.tar.bz2``,
      ``.tar.xz``, and ``.tar``), this is a directory containing a copy of the
      source file
  * - ``STDLIB_DIR``
    - Python standard library location

When building "Unix-style" packages on Windows, which are then usually
statically linked to executables, we do this in a special *Library* directory
under the build prefix.  The following environment variables are only
defined in Windows:

.. list-table::

  * - ``CYGWIN_PREFIX``
    - Same as ``PREFIX``, but as a Unix-style path, e.g. ``/cygdrive/c/path/to/prefix``
  * - ``LIBRARY_BIN``
    - ``<build prefix>\Library\bin``
  * - ``LIBRARY_INC``
    - ``<build prefix>\Library\include``
  * - ``LIBRARY_LIB``
    - ``<build prefix>\Library\lib``
  * - ``LIBRARY_PREFIX``
    - ``<build prefix>\Library``
  * - ``SCRIPTS``
    - ``<build prefix>\Scripts``
  * - ``VS_MAJOR``
    - The major version number of the Visual Studio version activated within the 
      build, e.g. ``9``
  * - ``VS_VERSION``
    - The version number of the Visual Studio version activated within the 
      build, e.g. ``9.0``
  * - ``VS_YEAR``
    - The release year of the Visual Studio version activated within the 
      build, e.g. ``2008``
 
On non-Windows (Linux and OS X), we have:

.. list-table::

  * - ``HOME``
    - Standard ``$HOME`` environment variable
  * - ``PKG_CONFIG_PATH``
    - Path to ``pkgconfig`` directory

On OS X, we have:

.. list-table::

  * - ``CFLAGS``
    - ``-arch`` flag
  * - ``CXXFLAGS``
    - Same as ``CFLAGS``
  * - ``LDFLAGS``
    - Same as ``CFLAGS``
  * - ``MACOSX_DEPLOYMENT_TARGET``
    - Same as the Anaconda Python. Currently ``10.6``
  * - ``OSX_ARCH``
    - ``i386`` or ``x86_64``, depending on Python build

On Linux, we have:

.. list-table::

  * - ``LD_RUN_PATH``
    - ``<build prefix>/lib``

.. _git-env:

Git Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

When the source is a git repository, specifying the source either with ``git_url``
or ``path``, the following variables are defined:

.. list-table::

   * - ``GIT_BUILD_STR``
     - a string that joins ``GIT_DESCRIBE_NUMBER`` and ``GIT_DESCRIBE_HASH``
       by an underscore
   * - ``GIT_DESCRIBE_HASH``
     - the current commit short-hash as displayed from ``git describe --tags``
   * - ``GIT_DESCRIBE_NUMBER``
     - string denoting the number of commits since the most recent tag
   * - ``GIT_DESCRIBE_TAG``
     - string denoting the most recent tag from the current commit (based on
       the output of ``git describe --tags``)
   * - ``GIT_FULL_HASH``
     - a string with the full SHA1 of the current HEAD

These can be used in conjunction with templated meta.yaml files to set things
like the build string based on the state of the git repository.

.. _mercurial-env-vars:

Mercurial Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the source is a mercurial repository, the following variables are defined:

.. list-table::

   * - ``HG_BRANCH``
     - string denoting the presently active branch
   * - ``HG_BUILD_STR``
     - a string that joins ``HG_NUM_ID`` and ``HG_SHORT_ID`` by an underscore
   * - ``HG_LATEST_TAG``
     - string denoting the most recent tag from the current commit
   * - ``HG_LATEST_TAG_DISTANCE``
     - string denoting number of commits since most recent tag
   * - ``HG_NUM_ID``
     - string denoting the revision number
   * - ``HG_SHORT_ID``
     - string denoting the hash of the commit

.. _inherited-env-vars:

Inherited Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Other than those mentioned above, no variables are inherited from the
environment in which you invoked ``conda build``. You can choose to inherit
additional environment variables by adding them to ``meta.yaml``:

.. code-block:: yaml

     build:
       script_env:
        - TMPDIR
        - LD_LIBRARY_PATH # [linux]
        - DYLD_LIBRARY_PATH # [osx]

If an inherited variable was missing from your shell environment, it will remain 
unassigned, but a warning will be issued noting that it has no value assigned.

NOTE: Inheriting environment variables like this can make it difficult for others
to reproduce binaries from source with your recipe. This feature should be 
used with caution or avoided altogether.

.. _build-envs:

Environment variables that affect the build process
---------------------------------------------------

.. list-table::

   * - ``CONDA_PY``
     - Should be ``27``, ``34``, or ``35``.  This is the Python version
       used to build the package.
   * - ``CONDA_NPY``
     - This is the NumPy version used to build the package, such as ``19``,
       ``110``, or ``111``.

.. _build-features:

Environment variables to set build features
-------------------------------------------

Three environment variables are inherited from the process running ``conda build``.
These three variables control :ref:`features` as defined in :doc:`meta-yaml`.

.. list-table::

   * - ``FEATURE_NOMKL``
     - Adds the ``nomkl`` feature to the built package.
     - Accepts ``0`` for off and ``1`` for on.
   * - ``FEATURE_DEBUG``
     - Adds the ``debug`` feature to the built package
     - Accepts ``0`` for off and ``1`` for on.
   * - ``FEATURE_OPT``
     - Adds the ``opt`` feature to the built package
     - Accepts ``0`` for off and ``1`` for on.

.. _test-envs:

Environment variables that affect the test process
--------------------------------------------------

All of the above environment variables are also set during the test process,
except with the test prefix instead of the build prefix everywhere.
