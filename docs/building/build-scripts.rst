Pre/Post link/unlink scripts
============================

.. TODO: Add post-unlink

You can add scripts `pre-link.sh`, `post-link.sh`, or `pre-unlink.sh` (or
`.bat` for Windows) to the recipe, which will be run before the package is
installed, after it is installed, and before it is removed, respectively. If
these scripts exit nonzero the installation/removal will fail.

Environment variables are set in these scripts:

.. list-table::

   * - ``PREFIX``
     - The install prefix.
   * - ``PKG_NAME``
     - The name of the package.
   * - ``PKG_VERSION``
     - The version of the package.
   * - ``PKG_BUILDNUM``
     - The build number of the package.
   * - ``RECIPE_DIR``
     - Path to the recipe files.

No output is shown from the build script, but it may write to
``$PREFIX/.messages.txt``, which is shown after conda completes all actions.
