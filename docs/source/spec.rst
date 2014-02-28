Conda package specification
===========================

A conda package is a bzipped tar archive (``.tar.bz2``) which contains
metadata under the ``info/`` directory, and a collection of files which are
installed directly into an install prefix.  The format is identical across
platforms and operating systems.  It is important to note that during the
install process, all files are basically just extracted into the install
prefix, with the exception of the ones in ``info/``.  Installing a conda
package into an environment may be roughly thought of as executing the
following using command::

   $ cd <environment prefix>
   $ tar xjf some-package-1.0-0.tar.bz2

However, it should be noted that only files (which includes symbolic
links) are part of a conda package, and not directories.  Directories
are created and removed as needed, but you cannot create an empty directory
from the tar archive directly.

In the following, we describe the precise layout of the metadata contained in
the ``info/`` directory and how it relates to the repository index
(``repodata.json.bz``).

Package metadata
----------------

All metadata about a package is contained under ``info/``.  Any files within
this location are not installed under the install prefix, and even though a
package creator is free to add any file, conda will only inspect the content
of the following ones:

``info/index.json``: This file contains basic information about the package,
such as name, version, build string, and dependencies.  The content of this
file is what gets stored in the repository index file ``repodata.json`` (hence
the name ``index.json``).  The json object is a dictionary containing the
following keys:

   ``name``: string
      The (lowercase) name of the package.  Note that this string
      may contain the ``-`` character.

   ``version``: string
      The package version, which may not contain ``-``.
      Conda acknowledges `PEP 386 <http://www.python.org/dev/peps/pep-0386/>`_.

   ``build``: string
      The build string, which also may not contain ``-``.
      The filename of the conda package is composed from these
      three values, that is ``<name>-<version>-<build>.tar.bz2``.

   ``build_number``: integer
      A (non-negative) integer representing the build
      number of the package.

   ``depends``: list of strings
      List of dependency specifications, where each element is a string
      as outlined in :ref:`build-version-spec`.

   ``arch``: string (optional)
      The architecture the package is built for, e.g. ``x86_64``.
      Conda currently does not do anything with this key.

   ``platform``: string (optional)
      The platform (OS) the package is built for, e.g. ``osx``.
      Conda currently does not do anything with this key.  Packages for a
      specific architecture and platform are usually distinguished by the
      repository sub-directory they are contained in (see below).

The build string is used to differentiate builds of packages with otherwise
the same name and version, e.g. a build with other dependencies (like Python
3.3 instead of Python 2.7), a bug fix in the build process, or some different
optional dependencies (MKL vs. ATLAS linkage), etc.  Nothing in conda actually
inspects the build string---strings such as ``np17py33_1`` are only
designed for human readability, but are never parsed by conda.

Unlike the build sting, the build number is inspected by conda.
It is used to sort packages (with otherwise same name and version) to
determine the latest one.
This is important, because new builds (bug fixes to the way a package is
build) may be added to a repository.

``info/files``: This file lists all files which are part of the package
itself (one per line), i.e. all files which need to get linked into the
environment.  Any files in the package not listed in this file will not be
linked when the package is installed.

``info/has_prefix``: This optional file lists all files that contain a
placeholder, ``/opt/anaconda1anaconda2anaconda3``, for the install prefix,
which upon install is replaced by the real install prefix.

``info/no_softlink``: This optional file lists all files which cannot
be soft-linked into environments (and are copied instead).


Link and unlink scripts:
------------------------

A couple of scripts may optionally be executed before and after the link
and unlink step.  These scripts are executed in a subprocess by conda,
using ``/bin/bash <script>`` on Unix and ``%COMSPEC% /c <script>`` on
Windows.  For this to work, there needs to be a convention for the path and
filenames of these scripts.  On Unix we have ``bin/.<name>-<action>.sh``,
and on Windows ``Scripts/.<name>-<action>.bat``, where ``<name>`` is the
package name, and ``<action>`` is one of the following:

``pre-link``: executed prior to linking, an error causes conda to stop.

``post-link``: executed after linking, when the post-link step fails,
we don't write any package metadata and return here.  This way the package
is not considered installed.

``pre-unlink``: executed prior to unlinking, errors are ignored.

For example, when where is a script named ``/bin/.foo-post-link.sh`` in the
package ``foo-1.0-0.tar.bz2``, it is executed after the linking is completed.
Moreover, the following environment variables are set while the script is
being executed: ``PREFIX``, ``PKG_NAME``, ``PKG_VERSION``


Repository structure and index
------------------------------

A conda repository (or channel) is a directory tree, usually served over
HTTPS, which has platform sub-directories, each of which contain conda
packages and a repository index.  The index file ``repodata.json`` lists all
conda packages in the platform sub-directory.  The command ``conda index`` can
be used to create such an index from the conda packages within a directory.
It is simple mapping of the full conda package filename to the dictionary
object in ``info/index.json`` described in the previous section.

In the following example, a repository provides the conda package
``misc-1.0-np17py27_0.tar.bz2`` on 64-bit Linux and 32-bit Windows::

   <some path>/linux-64/repodata.json
                        repodata.json.bz2
                        misc-1.0-np17py27_0.tar.bz2
              /win-32/repodata.json
                      repodata.json.bz2
                      misc-1.0-np17py27_0.tar.bz2

Note that both conda packages have identical filenames, and are only
distinguished by the repository sub-directory they are contained in.
