========
Glossary
========

.. _condarc-glossary:

.condarc
========

The Conda Runtime Configuration file, an optional ``.yaml`` file
that allows you to configure many aspects of conda, such as which
channels it searches for packages, proxy settings, and environment
directories. A ``.condarc`` file is not included by default, but
it is automatically created in your home directory
when you use the ``conda config`` command. The ``.condarc`` file
can also be located in a root environment, in which case it
overrides any ``.condarc`` in the home directory. For more
information, see :doc:`user-guide/configuration/use-condarc`
and :doc:`user-guide/configuration/admin-multi-user-install`.
Pronounced "conda r-c".

.. _activate-deactivate-glossary:

Activate/Deactivate environment
===============================

Conda commands used to switch or move between installed
environments. The ``conda activate`` command prepends the path of your
current environment to the PATH environment variable so that you
do not need to type it each time. ``deactivate`` removes it.
Even when an environment is deactivated, you can still execute
programs in that environment by specifying their paths directly,
as in ``~/anaconda/envs/envname/bin/program_name``. When an
environment is activated, you can execute the program in that
environment with just ``program_name``.

.. note::
   Replace ``envname`` with the name of the environment and
   replace ``program_name`` with the name of the program.


.. _anaconda-glossary:

Anaconda
========

A downloadable, free, open-source, high-performance, and optimized
Python and R distribution. Anaconda includes
:ref:`conda <conda-glossary>`, conda-build, Python, and 250+
automatically installed, open-source scientific packages and
their dependencies that have been tested to work well together,
including SciPy, NumPy, and many others. Use the ``conda install`` command
to easily install 7,500+ popular open-source packages
for data science--including advanced and scientific
analytics--from the Anaconda repository. Use the ``conda``
command to install thousands more open-source packages.

Because Anaconda is a Python distribution, it can make
installing Python quick and easy even for new users.

Available for Windows, macOS, and Linux, all versions of
Anaconda are supported by the community.

See also :ref:`miniconda-glossary` and :ref:`conda-glossary`.


.. _anaconda-org-glossary:

Anaconda.org
============

A web-based, repository hosting service in the cloud. Packages
created locally can be published to the cloud to be shared with
others. `Anaconda.org`_ is a public version of Anaconda Repository
and was formerly known as Anaconda Cloud.


.. _navigator-glossary:

Anaconda Navigator
==================

A desktop graphical user interface (GUI) included in all versions
of Anaconda that allows you to easily manage conda packages,
environments, channels, and notebooks without a command line
interface (CLI). See more about `Navigator`_.

.. _channels-glossary:

Channels
========

The locations of the repositories where conda looks for packages.
Channels may point to a Cloud repository or a private
location on a remote or local repository that you or your organization
created. The ``conda channel`` command has a default set of channels to
search, beginning with https://repo.anaconda.com/pkgs/, which you may
override, for example, to maintain a private or internal channel.
These default channels are referred to in conda commands and in
the ``.condarc`` file by the channel name "defaults."


.. _conda-glossary:

conda
=====

The package and environment manager program bundled with Anaconda
that installs and updates conda packages and their dependencies.
Conda also lets you easily switch between conda environments on
your local computer.


.. _conda-environment-glossary:

conda environment
=================

A folder or directory that contains a specific collection of
conda packages and their dependencies, so they can be maintained
and run separately without interference from each other. For
example, you may use a conda environment for only Python 2 and
Python 2 packages, maintain another conda environment with only
Python 3 and Python 3 packages, and maintain another for R
language packages. Environments can be created from:

* The Navigator GUI
* The command line
* An environment specification file with the name
  ``your-environment-name.yml``


.. _conda-package-glossary:

conda package
=============

A compressed file that contains everything that a software
program needs in order to be installed and run, so that you do
not have to manually find and install each dependency separately.
A conda package includes system-level libraries, Python or R
language modules, executable programs, and other components. You
manage conda packages with conda.

.. _conda-repository-glossary:

conda repository
================

A cloud-based repository that contains 7,500+ open-source certified
packages that are easily installed locally with the
``conda install`` command. Anyone can access the repository from:

* The Navigator GUI

* A terminal using conda commands

*  https://repo.anaconda.com/pkgs/


.. _metapackage-glossary:

Metapackage
===========

A metapackage is a very simple package that has at least a name
and a version. It need not have any dependencies or build steps.
:ref:`meta-package` may list dependencies to several core,
low-level libraries and may contain links to software files
that are automatically downloaded when executed.

.. _miniconda-glossary:

Miniconda
=========

A free minimal installer for conda. `Miniconda`_
is a small, bootstrap version of Anaconda that includes only conda,
Python, the packages they depend on, and a small number of other useful
packages, including pip, zlib, and a few others. Use the
``conda install`` command to install 7,500+ additional conda
packages from the Anaconda repository.

Miniconda is a Python distribution that can make
installing Python quick and easy even for new users.

See also :ref:`anaconda-glossary` and :ref:`conda-glossary`.

.. _noarch-glossary:

Noarch package
==============

A conda package that contains nothing specific to any system
architecture, so it may be installed from any system. When conda
searches for packages on any system in a channel, conda checks
both the system-specific subdirectory, such as ``linux-64``, and
the ``noarch`` directory. Noarch is a contraction of "no architecture".

.. _package-manager-glossary:

Package manager
===============

A collection of software tools that automates the process of
installing, updating, configuring, and removing computer programs
for a computer's operating system. Also known as a package management
system. Conda is a package manager.

.. _packages-glossary:

Packages
========

Software files and information about the software, such as its
name, the specific version, and a description, bundled into a
file that can be installed and managed by a package manager.

.. _plugins-glossary:

Plugins
=======

Plugins, sometimes referred to as add-ons or extensions, are software or modules
that add new functions to a host program (*e.g.*, conda) without directly altering
the host program itself. Amongst other uses, plugins support is utilized to
enable third-party developers to extend an application, support easily adding new
features, and to reduce the size of an application by not loading unused features.

.. _repository-glossary:

Repository
==========

Any storage location from which software assets may be retrieved
and installed on a local computer. See also
:ref:`anaconda-org-glossary` and
:ref:`conda-repository-glossary`.

.. _silent-mode-glossary:

Silent mode installation
========================

When installing Miniconda or Anaconda in silent mode, screen
prompts are not shown on screen and default settings are
automatically accepted.

.. _`Anaconda.org`: https://docs.anaconda.com/anacondaorg/
.. _`Navigator`: https://docs.anaconda.com/navigator/
.. _`Miniconda`: https://docs.conda.io/en/latest/miniconda.html
