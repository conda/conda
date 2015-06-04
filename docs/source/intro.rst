===============
Getting Started
===============

The `conda` command is the primary interface for managing installations
of various packages.  It can query and search the package index and current
installation, create new environments, and install and update packages
into existing conda environments.

------------------
Conda Overview
------------------

.. _package:
.. index::
    pair: terminology; package

.. _environment:
.. index::
    pair: terminology; environment

conda is an application for finding and installing software packages.
A conda `package` is a binary tarball containing system-level libraries,
Python modules, executable programs, or other components.
conda keeps track of dependencies between packages and platform
specifics, making it simple to create working environments from different
sets of packages.

A `conda environment` is a filesystem directory that contains a specific
collection of conda packages.  As a concrete example, you might want to
have one environment that provides NumPy 1.7, and another environment that
provides NumPy 1.6 for legacy testing.  conda makes this kind of mixing
and matching easy.  To begin using an environment, simply set
your **PATH** variable to point to its `bin` directory.

.. _channel:
.. index::
    pair: terminology; channel

.. _locally_available:
.. index::
    pair: terminology; locally available

.. _activated:
.. index::
    pair: terminology; activated

.. _deactivated:
.. index::
    pair: terminology; deactivated


Conda packages are downloaded from remote ``channels``, which are simply URLs
to directories containing conda packages.
The conda command starts with a default set of channels to search, but users may exert control over this list; for example, if they wish to maintain a private or internal channel (see :ref:`config` for details).

Continuum provides the following standard channels:
 * ``http://repo.continuum.io/pkgs/dev`` - Experimental or developmental versions of packages
 * ``http://repo.continuum.io/pkgs/gpl`` - GPL licensed packages
 * ``http://repo.continuum.io/pkgs/free`` - non GPL open source packages

To view all available packages, you can use ``conda search``.  See the :ref:`search command examples <search_example>` for more information.

.. _location:
.. index::
    pair: terminology; location

.. _known:
.. index::
    pair: terminology; known

Since conda environments are simply directories, they may be created
anywhere.  However, conda has a notion of `locations` which are also
simply directories that are known to conda, and contain environments
within.  Conda environments created in such locations are said to
be `known`, and can be displayed for easy reference.  Conda has a default
system location, but additional locations may be specified (see :doc:`build/dirs` 
and :ref:`config`, respectively, for more details).
