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
      compiled with.
  * - ``CONDA_BUILD=1``
    - Always set.
  * - ``SRC_DIR``
    - Path to where source is unpacked (or cloned). If the source file is not
      a recognized file type (right now, ``.zip``, ``.tar``, ``.tar.bz2``,
      ``.tar.xz``, and ``.tar``), this is a directory containing a copy of the
      source file.
  * - ``PREFIX``
    - Build prefix where build script should install to.
  * - ``RECIPE_DIR``
    - Directory of recipe.
  * - ``PKG_NAME``
    - Name of the package being built.
  * - ``PKG_VERSION``
    - Version of the package being built.
  * - ``PKG_BUILDNUM``
    - Build number of the package being built.
  * - ``PATH``
    - Prepended by the build prefix bin directory.
  * - ``PYTHON``
    - Path to Python executable in build prefix (note that Python is only
      installed in the build prefix when it is listed as a build requirement).
  * - ``PY3K``
    - ``1`` when Python 3 is installed in build prefix, else ``0``.
  * - ``STDLIB_DIR``
    - Python standard library location
  * - ``SP_DIR``
    - Python's site-packages location
  * - ``PY_VER``
    - Python version building against
  * - ``R``
    - Path to R executable in build prefix (note that R is only
      installed in the build prefix when it is listed as a build requirement).
  * - ``CPU_COUNT``
    - Number of CPUs on the system, as reported by
      ``multiprocessing.cpu_count()``
  * - ``LANG``
    - Inherited from your shell environment.
  * - ``HTTP_PROXY``
    - Inherited from your shell environment.
  * - ``HTTPS_PROXY``
    - Inherited from your shell environment.
  * - ``PATH``
    - Inherited from your shell environment, and augmented with ``$PREFIX/bin``

When building "Unix-style" packages on Windows, which are then usually
statically linked to executables, we do this in a special *Library* directory
under the build prefix.  The following environment variables are only
defined in Windows:

.. list-table::

  * - ``LIBRARY_PREFIX``
    - ``<build prefix>\Library``
  * - ``LIBRARY_BIN``
    - ``<build prefix>\Library\bin``
  * - ``LIBRARY_INC``
    - ``<build prefix>\Library\include``
  * - ``LIBRARY_LIB``
    - ``<build prefix>\Library\lib``
  * - ``SCRIPTS``
    - ``<build prefix>\Scripts``
  * - ``CYGWIN_PREFIX``
    - Same as ``PREFIX``, but as a Unix-style path, e.g. ``/cygdrive/c/path/to/prefix``

On non-Windows (Linux and OS X), we have:

.. list-table::

  * - ``PKG_CONFIG_PATH``
    - Path to ``pkgconfig`` directory.
  * - ``HOME``
    - Standard ``$HOME`` environment variable.

On OS X, we have:

.. list-table::

  * - ``OSX_ARCH``
    - ``i386`` or ``x86_64``, depending on Python build
  * - ``CFLAGS``
    - ``-arch`` flag.
  * - ``CXXFLAGS``
    - Same as ``CFLAGS``.
  * - ``LDFLAGS``
    - Same as ``CFLAGS``.
  * - ``MACOSX_DEPLOYMENT_TARGET``
    - Same as the Anaconda Python. Currently ``10.6``.

On Linux, we have:

.. list-table::

  * - ``LD_RUN_PATH``
    - ``<build prefix>/lib``

Git Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~

When the source is a git repository, the following variables are defined:

.. list-table::

   * - ``GIT_DESCRIBE_TAG``
     - string denoting the most recent tag from the current commit (based on
       the output of ``git describe --tags``)
   * - ``GIT_DESCRIBE_NUMBER``
     - string denoting the number of commits since the most recent tag
   * - ``GIT_DESCRIBE_HASH``
     - the current commit short-hash as displayed from ``git describe --tags``
   * - ``GIT_BUILD_STR``
     - a string that joins ``GIT_DESCRIBE_NUMBER`` and ``GIT_DESCRIBE_HASH``
       by an underscore.
   * - ``GIT_FULL_HASH``
     - a string with the full SHA1 of the current HEAD

These can be used in conjunction with templated meta.yaml files to set things
like the build string based on the state of the git repository.

For example, here's a meta.yaml that would work with these values. In this
example, the recipe is included at the base directory of the git repository,
so the ``git_url`` is ``../``:

.. code-block:: yaml

     package:
       name: mypkg
       version: {{ environ.get('GIT_DESCRIBE_TAG', '') }}

     build:
       number: {{ environ.get('GIT_DESCRIBE_NUMBER', 0) }}

       # Note that this will override the default build string with the Python
       # and NumPy versions
       string: {{ environ.get('GIT_BUILD_STR', '') }}

     source:
       git_url: ../

All of the above environment variables are also set during the test process,
except with the test prefix instead of the build prefix everywhere.

Note that build.sh is run with ``bash -x -e`` (the ``-x`` makes it echo each
command that is run, and the ``-e`` makes it exit whenever a command in the
script returns nonzero exit status).  You can revert this in the script if you
need to by using the ``set`` command.

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

If an inherited variable was missing from your shell environment, it will be 
assigned the value ``<UNDEFINED>``.

NOTE: Inheriting environment variables like this can make it difficult for others
to reproduce binaries from source with your recipe. This feature should be 
used with caution or avoided altogether.

.. _build-envs:

Environment variables that affect the build process
---------------------------------------------------

.. list-table::

   * - ``CONDA_PY``
     - Should be ``26``, ``27``, ``33``, or ``34``.  This is the Python version
       used to build the package.
   * - ``CONDA_NPY``
     - Should be either ``16`` or ``17``.  This is the NumPy version used to
       build the package.
