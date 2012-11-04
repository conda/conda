
==================
Conda Introduction
==================

The conda command is the primary means of interacting with and manipulating Anaconda environments.


-----------------
Anaconda Overview
-----------------


--------------------------
Package Naming Conventions
--------------------------

**package name**
    The name of a package, without any reference to a particular version. Anaconda pacakge names may contain lowercase alpha characters, numeric digits, or "-".

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

Additionally, a **package specification** is package name, together with a version (which may be partial, or absent), joined by "=". Here are some examples:

* python=2.7.3
* python=2.7
* python


-------------------
Directory Structure
-------------------

*ROOT_DIR*
    The directory that Anaconda was installed into, for example */opt/anaconda* or *C:\\Anaconda*

    */pkgs*
        Also referred to as *PKGS_DIR*. This directory contains exploded packages, ready to be activated in Anaconda environments. Each package resides in a subdiretory corresponding to its canonical name.

    */envs*
        A default location for additional Anaconda environments to be created.

    */bin*

    */include*

    */lib*

    */share*
        These subdirectories comprise the default Anaconda environment.




