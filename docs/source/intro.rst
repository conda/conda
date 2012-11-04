
==================
Conda Introduction
==================

The **conda** command is the primary interface for managing an Anaconda installations. It can query and search the Anaconda package index and current Anaconda installation, create new Anaconda environments, and install and upgrade packages into existing Anaconda environments.

-----------------
Anaconda Overview
-----------------

Anaconda is system for finding and installing software packages. An Anaconda **package** is a binary tarball containing system-level libraries, python modules, executable programs, or other components. Anaconda keeps track of dependencies between packages and platform specifics, making it simple to create working environments from different sets of packages. An Anaconda **environment** is a filesystem directory that contains a specfic collection of Anaconda packages. As a concrete example, you might want to have one environment that provides numpy 1.7, and another environment that provides numpy 1.6 for legacy testing. Anaconda makes this kind of mixing and matching easy.

Anaconda packages are downloaded from remote **repositories**. The conda command starts with a default set of repositories to search, but users may exert control over this list, for example if they wish to maintain a private or internal repository (see Configuration_ for details). Once and Anaconda package has been downloaded, it is said to be **locally available**. A locally available package that has been linked into an Anaconda environment is said to be **activated**. Conversely, unlinking a package from an environment causes it to be **deactivated**.

Since Anaconda environments are simply directories, they may be created anywhere. However, Anaconda has a notion of **locations** which are also simply directories that are known to conda, and contain environments within. Anaconda environments created in such locations are said to be **known**, and can be displayed for easy reference. Anaconda has a default system location, but additional locations may be specified (see `Directory Structure`_ and Configuration_, respectively, for more details).


--------------------------
Package Naming Conventions
--------------------------

Names and versions of software packages do not follow any prescribed rules.  In order to facilitate communication and documentation, Anaconda employs the following naming conventions with respect to packages:

**package name**
    The name of a package, without any reference to a particular version. Anaconda package names are normalized, and may contain only lowercase alpha characters, numeric digits, underscores, or hyphens. In usage documenation, these will be referred to by ``package_name``.

**package version**
    A version number or string, often similar to *X.Y* or *X.Y.Z*, but may take other forms as well.

**build string**
    An arbitrary string that identifies a particular build of a package for Anaconda. It may contain suggestive mnemonics but these are subject to change and should not be relied upon or attempted to be parsed for any specific information.

**canonical name**
    The canonical name consists of the package name, version, and build string joined together by hyphens: *name*-*version*-*buildstring*. In usage documenation, these will be referred to by ``canonical_name``.

**file name**
    Anaconda package filenames are canonical names, plus the suffix *.tar.bz2*.


These components are illustrated in the following figure:

.. figure::  images/conda_names.png
   :align:   center

   Different parts of Anaconda package names.

Additionally, a **package specification** is a package name, together with a package version (which may be partial, or absent), joined by "=". Here are some examples:

* *python=2.7.3*
* *python=2.7*
* *python*

In usage documenation, these will be referred to by ``package_spec``.

-------------------
Directory Structure
-------------------

The Anaconda installation has the following directory structure:

*ROOT_DIR*
    The directory that Anaconda was installed into, for example */opt/anaconda* or *C:\\Anaconda*

    */pkgs*
        Also referred to as *PKGS_DIR*. This directory contains exploded packages, ready to be activated in Anaconda environments. Each package resides in a subdiretory corresponding to its canonical name.

    */envs*
        The system location for additional Anaconda environments to be created.

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
