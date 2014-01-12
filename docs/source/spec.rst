Conda package specification
===========================

A conda package is a bzipped tar archive (``.tar.bz2``) which contains
metadata under the ``info/`` directory, and a collection of files which
are installed directly into an install prefix.
The format is identical across platforms and operating systems.
It is important to note that during the install process, all files are
basically just extracted into the install prefix, with the exception
of the ones in ``info/``.  Installing a conda into an environment, may
be roughly taught of as executing the following using command::

   $ cd <environment prefix>
   $ tar xjf some-package-1.0-0.tar.bz2

However, it should be noted that only files (which includes symbolic
links) are part of a conda package, and not directories.  Directories
are created and removed as needed, but you cannot create an empty directory
from the tar archive directly.
In the following, we want to describe the precise layout of the metadata
contained in the ``info/`` directory and how it relates to the repository
index (``repodata.json.bz``).

Package metadata
----------------

All metadata about a package is contained under ``info/``.  Any files
within this location are not installed under the install prefix, and even
though a package creator is free to add whatever file, conda will only
inspect the content of the following ones:

``info/index.json``: This file contains basic information about the
package, such as name, version, build string, dependencies.
The content of this file is what gets stored in the repository index file
``repodata.json`` (hence the name ``index.json``).  The json object is
a dictionary containing the following keys:

   ``name``: The (lowercase) name of the package.  Note that this string
             may contain the ``-`` character.

   ``version``: The package version, which may **not** contain ``-``.

   ``build``: The build string, which also may **not** contain ``-``.
              The filename of the conda package is composed from these
              three values, that is ``<name>-<version>-<build>.tar.bz2``.
              The build string is used to differentiate builds of packages
              with otherwise the same name and version, e.g. a package
              build with other dependencies (Python 3.3 instead of Python
              2.7), a bug fix in the build process, or some different
              optional dependencies (MKL vs. ATLAS linkage), etc. .
              Nothing in conda is actually inspecting the build string,
              strings such as ``np17py33_1`` are only designed for human
              readability, but are never parsed by conda.

    ``build_number``: A (non-negative) integer representing the build
                      number of the package.  Unlike the build sting, this
                      number is inspected by conda.  It is used to sort
                      package (with otherwise same name and version) to
                      determine the *latest* one.


Repository index
----------------

todo...
