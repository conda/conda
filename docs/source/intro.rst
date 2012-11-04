
==================
Conda Introduction
==================

The conda command is the primary means of interacting with and manipulating Anaconda environments.


-----------------
Anaconda Overview
-----------------

Anaconda is system for finding and installing software. An Anaconda **package** is a binary tarball containing system-level libraries, python modules, programs, or other components. Anaconda keeps track of dependencies between packages and platform specifics, making it simple to create working environments from different sets of packages. An **environment** is a filesystem directory that contains a specfic collection of packages. As a concrete example, you might want to have one environment that provides numpy 1.7, and another environment that provides numpy 1.6 for legacy testing. Anacond makes this kind of mixing and matching easy.

The primary interface to Anaconda package manangement is the **conda** command.

--------------------------
Package Naming Conventions
--------------------------

**package name**
    The name of a package, without any reference to a particular version. Anaconda package names may contain lowercase alpha characters, numeric digits, or "-".

**package version**
    A version, often similar to *X.Y* or *X.Y.Z*, but may take other forms as well.

**build string**
    An arbitrary string that identifies a particular build of a package. It may contain suggestive mnemonics but these are subject to change and should not be relied upon or attempted to be parsed.

**canonical name**
    The canonical name consists of the package name, version, and build string joined together by hyphens: *name*-*version*-*buildstring*

**file name**
    Anaconda package filenames are canonical names, plus the suffix *.tar.bz2*.


These components are illustrated in the following figure:

.. figure::  images/conda_names.png
   :align:   center

   Different parts of Anaconda package names.

Additionally, a **package specification** is a package name, together with a package version (which may be partial, or absent), joined by "=". Here are some examples:

* python=2.7.3
* python=2.7
* python


-------------------
Directory Structure
-------------------

The Anaconda installation has the following directory structure:

*ROOT_DIR*
    The directory that Anaconda was installed into, for example */opt/anaconda* or *C:\\Anaconda*

    */pkgs*
        Also referred to as *PKGS_DIR*. This directory contains exploded packages, ready to be activated in Anaconda environments. Each package resides in a subdiretory corresponding to its canonical name.

    */envs*
        A default location for additional Anaconda environments to be created.

    |   */bin*
    |   */include*
    |   */lib*
    |   */share*
    |       These subdirectories comprise the default Anaconda environment.

Other Anaconda environments contain the same subdirectories as the default environment, and may be located anywhere on the same filesystem as *PKGS_DIR*.

-------------
Configuration
-------------
There is very little user configuration that conda requires, however conda will read minimal configuration from a *$HOME/.condarc* file, if it is present. The *.condarc* file follows simple `YAML syntax`_, here is an example:

.. code-block:: bash

    # This is a conda run configuration

    # repository locations. These override conda defaults, i.e., conda will
    # search *only* the repositories listed here, in the order given.
    repositories:
      - http://repo.continuum.io/pkgs
      - http://acme.com/internal/packages

    # environment locations. These locations are in *addition* to the system
    # location at $ROOT_DIR/envs.
    locations:
      - ~/envs


.. _YAML syntax: http://en.wikipedia.org/wiki/YAML
