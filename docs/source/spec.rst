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

   ``name``:
      The (lowercase) name of the package.  Note that this string
      may contain the ``-`` character.

   ``version``:
      The package version, which may **not** contain ``-``.
      Conda acknowledges `PEP 386<http://www.python.org/dev/peps/pep-0386/>`_.

   ``build``:
      The build string, which also may **not** contain ``-``.
      The filename of the conda package is composed from these
      three values, that is ``<name>-<version>-<build>.tar.bz2``.

   ``build_number``:
      A (non-negative) integer representing the build
      number of the package.

   ``depends``:
      List of dependencies specifications, where each element is a string
      as outlined in the paragraph `Specifying versions in requirements`
      in `build`_.

   ``arch``: (optional)
      The architecture the package is build for, e.g. ``x86_64``.
      Conda is not doing anything with this key.

   ``platform``: (optional)
      The platform (OS) the package is build for, e.g. ``osx``.
      Conda is not doing anything with this key.  Packages for a specific
      architecture and platform are usually distinguished by the repository
      sub-directory they are contained in (see below).

The build string is used to differentiate builds of packages with otherwise
the same name and version, e.g. a package a build with other
dependencies (Python 3.3 instead of Python 2.7), a bug fix in the build
process, or some different optional
dependencies (MKL vs. ATLAS linkage), etc. .
Nothing in conda is actually inspecting the build string, strings such
as ``np17py33_1`` are only designed for human readability, but are never
parsed by conda.
Unlike the build sting, this number is inspected by conda.
It is used to sort packages (with otherwise same name and version) to
determine the *latest* one.
This is important, because new builds (bug fixes to the way a package is
build) may be added to a repository.


Repository structure and index
------------------------------

A conda repository is a directory tree, which may be served over HTTP,
which has platform sub-directories, which contain conda packages and a
repository index.  The index file ``repodata.json`` lists all conda
packages in the platform sub-directory.  The command ``conda index`` can
be used to create such an index from the conda packages within a directory.
It is simple mapping of the full conda package filename to the dictionary
object in ``info/index.json`` described in the previous section.
