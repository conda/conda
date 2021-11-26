=====================
Installing with conda
=====================

.. image:: /img/installing-with-conda.png
    :align: right

.. _installing-with-conda:


To install conda packages, in the terminal or an Anaconda Prompt, run::

  conda install [packagename]


During the install process, files are extracted into the specified
environment, defaulting to the current environment if none is specified.
Installing the files of a conda package into an
environment can be thought of as changing the directory to an
environment, and then downloading and extracting the artifact
and its dependencies---all with the single
``conda install [packagename]`` command.

Read more about :doc:`conda environments and directory structure <../concepts/environments>`.

* When you ``conda install`` a package that exists in a channel and has no dependencies, conda:

  * Looks at your configured channels (in priority).

  * Reaches out to the repodata associated with your channels/platform.

  * Parses repodata to search for the package.

  * Once the package is found, conda pulls it down and installs.

Conda update versus conda install
=================================

``conda update`` is used to update to the latest compatible version.
``conda install`` can be used to install any version.

Example:

* If Python 2.7.0 is currently installed, and the latest version of Python 2 is 2.7.5, then ``conda update python`` installs Python 2.7.5. It does not install Python 3.

* If Python 3.7.0 is currently installed, and the latest version of Python is 3.9.0, then ``conda install python=3`` installs Python 3.9.0.

Conda uses the same rules for other packages. ``conda update`` always installs the highest version with the same major version number, whereas ``conda install`` always installs the highest version.


Installing conda packages offline
=================================

To install conda packages offline, run:
``conda install /path-to-package/package-filename.tar.bz2/``

If you prefer, you can create a /tar/ archive file containing
many conda packages and install them all with one command:
``conda install /packages-path/packages-filename.tar``

.. note::
   If an installed package does not work, it may be missing
   dependencies that need to be resolved manually.

Installing packages directly from the file does not resolve
dependencies.


Installing conda packages with a specific build number
======================================================

If you want to install conda packages with the correct package specification, try
``pkg_name=version=build_string``. Read more about `build strings and package naming conventions <https://docs.conda.io/projects/conda-build/en/latest/concepts/package-naming-conv.html#index-2>`_.
Learn more about `package specifications and metadata <https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-metadata>`_.

For example, if you want to install llvmlite 0.31.0dev0 on Python 3.7.8, you
would enter::

    conda install  -c numba/label/dev llvmlite=0.31.0dev0=py37_8
