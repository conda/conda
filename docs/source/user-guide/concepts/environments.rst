.. _concepts-conda-environments:

==================
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
:doc:`../tasks/manage-environments`.


Conda directory structure
=========================

``ROOT_DIR``
------------
The directory that Anaconda or Miniconda was installed into.

EXAMPLES:

.. code-block:: shell

   /opt/Anaconda  #Linux
   C:\Anaconda    #Windows

``/pkgs``
---------

Also referred to as PKGS_DIR. This directory contains
decompressed packages, ready to be linked in conda environments.
Each package resides in a subdirectory corresponding to its
canonical name.

``/envs``
---------

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

Virtual environments
====================

A virtual environment is a tool that helps to
keep dependencies required by different projects
separate by creating isolated spaces for them that
contain per-project dependencies for them.

Users can create virtual environments
using one of several tools such as
Pipenv or Poetry, or a conda virtual
environment. Pipenv and Poetry are based around Python's
built-in venv library, whereas conda has its own notion of virtual
environments that is lower-level (Python itself is a dependency provided
in conda environments).

Scroll to the right in the table below.

Some other traits are:

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * -
     - Python virtual environment
     - Conda virtual environment
   * - **Libraries**
     - Statically link, vendor libraries in wheels,
       or use apt/yum/brew/etc.
     - Install system-level libraries as conda dependencies.
   * - **System**
     - Depend on base system install of Python.
     - Python is independent from system.
   * - **Extending environment**
     - Extend environment with pip.
     - Extended environment with conda or pip.
   * - **Non-Python dependencies**
     -
     - Manages non-Python dependencies (R, Perl,
       arbitrary executables).
   * - **Tracking dependencies**
     -
     - Tracks binary dependencies explicitly.

|

Why use venv-based virtual environments
---------------------------------------

- You prefer their workflow or spec formats.
- You prefer to use the system Python and libraries.
- Your project maintainers only publish to PyPI, and
  you prefer packages that come more directly from the
  project maintainers, rather than someone else providing
  builds based on the same code.

Why use conda virtual environments?
-----------------------------------

- You want control over binary compatibility choices.
- You want to utilize newer language standards, such as C++ 17.
- You need libraries beyond what the system Python offers.
- You want to manage packages from languages other than Python
  in the same space.

Workflow differentiators
========================

Some questions to consider as you determine your preferred
workflow and virtual environment:

- Is your environment shared across multiple code projects?
- Does your environment live alongside your code or in a separate place?
- Do your install steps involve installing any external libraries?
- Do you want to ship your environment as an archive of some sort
  containing the actual files of the environment?

Package system differentiators
==============================

There are potential benefits for choosing PyPI or conda.

PyPI has one global namespace and distributed ownership of that namespace.
Because of this, it is easier within PyPI to have single sources for a package
directly from package maintainers.

Conda has unlimited namespaces (channels) and distributed ownership of a
given channel.
As such, it is easier to ensure binary compatibility within a channel using
conda.
