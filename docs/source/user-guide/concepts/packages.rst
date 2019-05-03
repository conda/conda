==============
Conda packages
==============

.. contents::
   :local:
   :depth: 2

.. _concept-conda-package:

What is a conda package?
========================

A conda package is a compressed tarball file (.tar.bz2) that contains:

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

.. _link_unlink:

Link and unlink scripts
=======================

You may optionally execute scripts before and after the link
and unlink steps. For more information, see `Adding pre-link, post-link and pre-unlink scripts <https://docs.conda.io/projects/conda-build/en/latest/resources/link-scripts.html>`_.

.. _package_specs:

More information
================

Go deeper on how to :ref:`manage packages <managing-pkgs>`.
Learn more about package metadata, repository structure and index,
and package match specifications at :doc:`Package specifications <../concepts/pkg-specs>`. 

