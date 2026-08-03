========
Commands
========

The ``conda`` command is the primary command-line interface for managing
conda environments and packages. You can use conda commands to create
environments, install packages, update packages, remove packages, search for
packages, and inspect your current conda configuration.

Common commands
===============

Some of the most commonly used conda commands include:

``conda create``
    Creates a new conda environment.

    .. code-block:: bash

       $ conda create --name myenv python=3.12

``conda install``
    Installs packages into the active environment or into a specified
    environment.

    .. code-block:: bash

       $ conda install numpy pandas

``conda update``
    Updates packages in an environment.

    .. code-block:: bash

       $ conda update numpy

``conda remove``
    Removes packages from an environment.

    .. code-block:: bash

       $ conda remove numpy

Other commands are available for managing channels, listing environments,
searching for packages, cleaning package caches, and viewing conda
configuration.

.. tip::
   You can abbreviate many frequently used command options that are preceded
   by two dashes (``--``) to one dash and the first letter of the option. For
   example, ``--name`` and ``--envs`` can be written as ``-n`` and ``-e``.

Getting help for commands
=========================

Use ``--help`` or ``-h`` to see help for conda itself or for an individual
command.

To see top-level conda help:

.. code-block:: bash

   $ conda --help

To see help for a specific command:

.. code-block:: bash

   $ conda install --help

or:

.. code-block:: bash

   $ conda install -h

For full usage of each command, including abbreviations, see
:doc:`commands <../../commands/index>`. You can see the same information at the
command line by :doc:`viewing the command-line help
<../tasks/view-command-line-help>`.

Plugin commands
===============

Conda plugins can add their own commands or subcommands to the conda
command-line interface. For example, a plugin may add a command for a custom
workflow, package source, or environment management task.

Plugins that add conda commands must be installed in the ``base`` environment,
where conda itself is installed. Installing a plugin into another environment
does not make its command available to the main ``conda`` command.
