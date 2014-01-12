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

todo...


Repository index
----------------

todo...
