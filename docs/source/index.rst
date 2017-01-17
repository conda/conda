.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. =====
.. Conda
.. =====

.. figure::  images/conda_logo.svg
   :align:   center

**Package, dependency and environment management for any language: Python, R, Ruby, Lua, Scala, Java, Javascript, C/ C++, FORTRAN**

Conda is an open source package management system and environment management system for installing multiple
versions of software packages and their dependencies and switching easily between them. It works on
Linux, OS X and Windows, and was created for Python programs but can package and distribute any software.

Conda is included in Anaconda and Miniconda. Conda is also included in the Continuum `subscriptions <https://www.continuum.io/anaconda-subscriptions>`_
of Anaconda, which provide on-site enterprise package and environment management for Python, R, Node.js, Java, and other application
stacks. Conda is also available on pypi, although that approach may not be as up-to-date.

**Miniconda** is a small "bootstrap" version that includes only conda, Python, and the packages they depend on. Over 720
scientific packages and their dependencies can be installed individually from the Continuum repository with
the "conda install" command.

**Anaconda** includes conda, conda-build, Python, and over 150 automatically installed scientific packages and
their dependencies. As with Miniconda, over 250 additional scientific packages can be installed individually with
the "conda install" command.

**pip install conda** uses the released version on pypi.  This version allows you to create new conda environments using
any python installation, and a new version of Python will then be installed into those environments.  These environments
are still considered "Anaconda installations."

The `conda` command is the primary interface for managing `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations. It can query
and search the Anaconda package index and current Anaconda installation,
create new conda environments, and install and update packages into existing
conda environments.



.. toctree::
   :hidden:

   announcements
   get-started
   using/index
   building/build
   help/help
   get-involved

Presentations & Blog Posts
--------------------------

`Packaging and Deployment with conda - Travis Oliphant <https://speakerdeck.com/teoliphant/packaging-and-deployment-with-conda>`_

`Python 3 support in Anaconda - Ilan Schnell <https://www.continuum.io/content/python-3-support-anaconda>`_

`New Advances in conda - Ilan Schnell <https://www.continuum.io/blog/developer/new-advances-conda>`_

`Python Packages and Environments with conda - Bryan Van de Ven <https://www.continuum.io/content/python-packages-and-environments-conda>`_

`Advanced features of Conda, part 1 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-1>`_

`Advanced features of Conda, part 2 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-2>`_

Requirements
------------

* python 2.7, 3.4, or 3.5
* pycosat
* pyyaml
* requests

What's new in conda 4.3?
------------------------

This release contains many improvements to performance, warning and error
messages, and conda's disk access, download, and package caching behavior.
Also a noarch/universal type for python packages is now officially supported,
a Python API module has been added, and the 'r' channel is now a default
channel. The `changelog <https://github.com/conda/conda/releases/tag/4.3.4>`_
contains a complete list of changes.

* **Unlink and Link Packages in a Single Transaction**: This provides improved
  error recovery by ensuring that conda is safe, defensive and fault-tolerant
  whenever it changes data on disk.

* **Progressive Fetch and Extract Transactions**: If errors are encountered
  while downloading packages, conda now keeps the packages that downloaded
  correctly and only re-downloads those with errors.

* **Generic- and Python-Type Noarch/Universal Packages**: Along with conda-build 2.1.0, a
  noarch/universal type for python packages is now officially supported. These are much like universal
  python wheels. Files in a python noarch package are linked into a prefix just like any other
  conda package, with the following additional features:
  
  1. conda maps the ``site-packages`` directory to the correct location for the python version
     in the environment,
  2. conda maps the python-scripts directory to either ``$PREFIX/bin`` or ``$PREFIX/Scripts`` depending
     on platform,
  3. conda creates the python entry points specified in the conda-build recipe, and
  4. conda compiles pyc files at install time when prefix write permissions are guaranteed.

  Python noarch packages must be "fully universal."  They cannot have OS- or
  python version-specific dependencies.  They cannot have OS- or python version-specific "scripts"
  files. If these features are needed, traditional conda packages must be used.

* **Multi-User Package Caches**: Package cache handling has been improved while
  preserving the on-disk package cache structure. Both writable and read-only
  package caches are fully supported.

* **Python API Module**: The new ``conda.cli.python_api`` module allows using
  conda as a Python library without needing to "shell out" to another Python
  process. There is also a ``conda.exports`` module for longer-term use of
  conda as a library across conda releases, although conda's Python code is
  considered internal and private and is subject to change across releases. For
  now conda will not install itself into environments other than its original
  install environment.

* **Remove All Locks**: Locking in conda had bugs and often created a false
  sense of security, and has been removed. The multi-user package caches in
  this release have improved safety by hard-linking packages in read-only
  caches to the user's primary user package cache. However, undefined behavior
  can still result when conda is running in multiple processes and operating on
  the same package caches or the same environments.

* Conda can now refuse to clobber existing files that are not within the unlink
  instructions of the transaction. The `path_conflict` configuration option can
  be set to ``clobber``, ``warn``, and ``prevent``. The current behavior and
  default in 4.3 is ``clobber``. The default in 4.4 will be ``warn``. The
  default in 4.5 and beyond will be ``prevent``. This can be overridden with
  the ``--clobber`` command line flag.

* Conda signed packages were vulnerable and created a false sense of security
  and have now been removed. Work has begun to incorporate The Update Framework
  into conda as a replacement.

* Conda 4.4 will drop support for older versions of conda-build.

* To verify that a channel URL is a valid conda channel, conda now checks that
  ``noarch/repodata.json`` or ``noarch/repodata.json.bz2`` exist. The check
  does pass if one or both of these files exist but are empty.

* A new "trace" log level with extremely verbose output, enabled with the
  ``-v -v -v`` or ``-vvv`` command-line flags, the ``verbose: 3`` configuration
  parameter, or the ``CONDA_VERBOSE=3`` environment variable.

* Conda can now be installed with pip, but only when used as a library or dependency.

* The 'r' channel is now part of the default channels.

* ``conda info`` now shows user-agent, UID, and GID.

* HTTP timeouts are configurable.

* The conda home page is now updated to conda.io.

* Fetch and extract for explicit URLs are now separate passes.

* Vendor URLs are now parsed by urllib3.

* Use of the Cache-Control max-age header for repodata is now implemented.

* Conda now caches repodata locally without remote server calls and has a
  ``repodata_timeout_secs`` configuration parameter.

* Conda now has a ``pkgs_dirs`` configuration parameter, an ``always_softlink``
  option, ``local_repodata_ttl`` configurability, and ``path_conflict`` and
  ``clobber`` configuration options.

* Package resolution/solver hints have been improved with better messaging.

* Further bug fixes, performance improvements, and better error and warning messages.

See the `changelog <https://github.com/conda/conda/releases/tag/4.3.4>`_ for 
a complete list of changes. 
