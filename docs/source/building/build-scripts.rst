Pre/Post link/unlink scripts
============================

.. TODO: Add post-unlink

You can add scripts `pre-link.sh`, `post-link.sh`, or `pre-unlink.sh` (or
`.bat` for Windows) to the recipe, which will be run before the package is
installed, after it is installed, and before it is removed, respectively. If
these scripts exit nonzero the installation/removal will fail.

We strongly recommend that post-link (and pre-unlink) scripts should:

1. be avoided whenever possible,
2. not touch anything other than the files being installed,
3. not write anything to stdout (or stderr), unless an error occurs,
4. not depend on any installed (or to be installed) conda packages, and
5. only depend on simple system tools such as ``rm``, ``cp``, ``mv``, ``ln``,
   and so on.

The scripts should not write to stdout or stderr unless an error occurs, but
they may write to ``$PREFIX/.messages.txt``, which is shown after conda
completes all actions.

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
