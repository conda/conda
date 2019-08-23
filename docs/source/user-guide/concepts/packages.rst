==============
Conda packages
==============

.. contents::
   :local:
   :depth: 2

.. _concept-conda-package:

What is a conda package?
========================

A conda package is a compressed tarball file (.tar.bz2) or
.conda file that contains:

* system-level libraries
* Python or other modules
* executable programs and other components
* metadata under the ``info/`` directory
* a collection of files that are installed directly into an ``install`` prefix

Conda keeps track of the dependencies between packages and platforms.
The conda package format is identical across platforms and
operating systems.

Only files, including symbolic links, are part of a conda
package. Directories are not included. Directories are created
and removed as needed, but you cannot create an empty directory
from the tar archive directly.

.conda file format
==================


The .conda file format was introduced in conda 4.7 as a more
compact, and thus faster, alternative to a tarball.

The .conda file format consists of an outer, uncompressed
ZIP-format container, with two inner compressed .tar files.

For the .conda format's initial internal compression format support,
we chose Zstandard (zstd). The actual compression format used does not
matter, as long as the format is supported by libarchive. The compression
format may change in the future as more advanced compression algorithms are
developed and no change to the .conda format is necessary. Only an updated
libarchive would be required to add a new compression format to .conda files.

These compressed files can be significantly smaller than their
bzip2 equivalents. In addition, they decompress much more quickly.
.conda is the preferred file format to use where available,
although we continue to provide .tar.bz2 files in tandem.

Read more about the `introduction of the .conda file format <https://www.anaconda.com/understanding-and-improving-condas-performance/>`_.

.. note::

  In conda 4.7 and later, you cannot use package names that
  end in “.conda” as they conflict with the .conda file format
  for packages.


Using packages
==============

* You may search for packages

.. code-block:: bash

  conda search scipy


* You may install a package

.. code-block:: bash

  conda install scipy


* You may build a package after `installing conda build <https://docs.conda.io/projects/conda-build/en/latest/index.html>`_

.. code-block:: bash

  conda build my_fun_package



Package structure
=================

.. code-block:: bash

  .
  ├── bin
  │   └── pyflakes
  ├── info
  │   ├── LICENSE.txt
  │   ├── files
  │   ├── index.json
  │   ├── paths.json
  │   └── recipe
  └── lib
      └── python3.5

* bin contains relevant binaries for the package

* lib contains the relevant library files (eg. the .py files)

* info contains package metadata

.. _noarch:

Noarch packages
===============
Noarch packages are packages that are not architecture specific
and therefore only have to be built once. Noarch packages are
either generic or Python. Noarch generic packages allow users to
distribute docs, datasets, and source code in conda packages.
Noarch Python packages are described below.

Declaring these packages as ``noarch`` in the ``build`` section of
the meta.yaml reduces shared CI resources. Therefore, all packages
that qualify to be noarch packages should be declared as such.

Noarch Python
-------------
The ``noarch: python`` directive in the build section
makes pure-Python packages that only need to be built once.

Noarch Python packages cut down on the overhead of building multiple
different pure Python packages on different architectures and Python
versions by sorting out platform and Python version-specific differences
at install time.

In order to qualify as a noarch Python package, all of the following
criteria must be fulfilled:

* No compiled extensions

* No post-link or pre-link or pre-unlink scripts

* No OS-specific build scripts

* No python version specific requirements

* No skips except for Python version. If the recipe is py3 only,
  remove skip statement and add version constraint on Python in host
  and run section.

* 2to3 is not used

* Scripts argument in setup.py is not used

* If ``console_script`` entrypoints are in setup.py,
  they are listed in meta.yaml

* No activate scripts

* Not a dependency of conda

.. note::
   While ``noarch: python`` does not work with selectors, it does
   work with version constraints. ``skip: True  # [py2k]`` can sometimes
   be replaced with a constrained Python version in the host and run
   subsections, for example: ``python >=3`` instead of just ``python``.

.. note::
   Only ``console_script`` entry points have to be listed in meta.yaml.
   Other entry points do not conflict with ``noarch`` and therefore do
   not require extra treatment.

Read more about `conda's noarch packages <https://www.anaconda.com/condas-new-noarch-packages/>`_.

.. _link_unlink:

Link and unlink scripts
=======================

You may optionally execute scripts before and after the link
and unlink steps. For more information, see `Adding pre-link, post-link, and pre-unlink scripts <https://docs.conda.io/projects/conda-build/en/latest/resources/link-scripts.html>`_.

.. _package_specs:

More information
================

Go deeper on how to :ref:`manage packages <managing-pkgs>`.
Learn more about package metadata, repository structure and index,
and package match specifications at :doc:`Package specifications <../concepts/pkg-specs>`.

