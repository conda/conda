=========
Concepts
=========

.. contents::
   :local:
   :depth: 1


Conda directory structure
=========================

This section describes the conda system directory structure.

**ROOT_DIR**

The directory that Anaconda or Miniconda was installed into.

EXAMPLES:

.. code-block:: none

   /opt/Anaconda
   C:\Anaconda

*/pkgs*

Also referred to as PKGS_DIR. This directory contains
decompressed packages, ready to be linked in conda environments.
Each package resides in a subdirectory corresponding to its
canonical name.

*/envs*

The system location for additional conda environments to be
created.

The following subdirectories comprise the default Anaconda
environment:

| ``/bin``
| ``/include``
| ``/lib``
| ``/share``
|

Other conda environments usually contain the same subdirectories
as the default environment.

.. _concept-conda-env:

Conda environments
==================

A conda environment is a directory that contains a specific
collection of conda packages that you have installed. For
example, you may have one environment with NumPy 1.7 and its
dependencies, and another environment with NumPy 1.6 for legacy
testing. If you change one environment, your other environments
are not affected. You can easily activate or deactivate
environments, which is how you switch between them. You can also
share your environment with someone by giving them a copy of your
``environment.yaml`` file. For more information, see
:doc:`tasks/manage-environments`.


.. _concept-conda-package:

Conda packages
==============

A conda package is a compressed tarball file that contains
system-level libraries, Python or other modules, executable
programs and other components. Conda keeps track of the
dependencies between packages and platforms.

Conda packages are downloaded from remote channels, which are
URLs to directories containing conda packages. The ``conda``
command searches a default set of channels, and packages are
automatically downloaded and updated from
http://repo.continuum.io/pkgs/. You can modify what remote
channels are automatically searched. You might want to do this to
maintain a private or internal channel. For details, see
:ref:`config-channels`. See also :doc:`tasks/manage-pkgs`.

The conda package format is identical across platforms and
operating systems.

To install conda packages, in the Terminal or an Anaconda Prompt, run:: 

  conda install [packagename]

NOTE: Replace ``[packagename]`` with the desired package name.

A conda package includes a link to a tarball or bzipped tar
archive, with the extension ".tar.bz2", which contains metadata
under the ``info/`` directory and a collection of files that are
installed directly into an ``install`` prefix.

During the install process, files are extracted into the
``install`` prefix, except for files in the ``info/``
directory. Installing the files of a conda package into an
environment can be thought of as changing the directory to an
environment, and then downloading and extracting the .zip file
and its dependencies---all with the single
``conda install [packagename]`` command.
