=======
Plugins
=======

.. _concept-plugins:


In order to enable customization and extra features that are compatible with and discoverable by conda
(but do not necessarily ship as a default part of the conda codebase), an official conda plugin mechanism
has been implemented as of version ``22.11.0``.

Managing plugin packages
========================

.. versionadded:: 26.11.0

   The ``conda plugins install``, ``conda plugins remove``, and
   ``conda plugins update`` commands.

These commands manage conda packages that provide plugins. Use
``conda plugins list`` and ``conda plugins info`` to inspect plugins loaded by
the running conda installation. See :doc:`the command reference
<../../commands/plugins>` for all subcommands and options.

Installing plugins
------------------

Use ``conda plugins install`` to install a conda plugin package into an environment.
Select the environment containing the conda installation you want to extend with
``--name`` or ``--prefix``. Choose plugin packages from channels compatible with
the packages already installed there.

For example, Miniforge uses conda-forge by default. With that channel configuration,
install ``conda-tree`` directly into its ``base`` environment:

.. code-block:: console

   conda plugins install --name base conda-tree

This command uses the configured channels.

If your environment uses Anaconda's ``defaults`` channels instead, install plugins
from those channels. To use a plugin from conda-forge, create a separate
environment containing conda and install the plugin there:

.. code-block:: console

   conda create --name conda-forge-plugins --override-channels --channel conda-forge conda
   conda run --name conda-forge-plugins python -m conda plugins install --override-channels --channel conda-forge conda-tree

Your existing conda installation can create and manage this separate environment.
The second command runs the conda installed in it to install the plugin.

``--channel`` (``-c``) selects a package source for this command. Repeat it to search
multiple compatible sources in the specified order. ``--override-channels``
excludes the configured channels from the search. It does not isolate packages
already installed in the target environment or migrate them to another channel.
See :ref:`channel-best-practices`.

These options do not create or modify channel configuration and can be used before
a ``.condarc`` exists. Use ``--override-channels --channel conda-forge`` again for
subsequent installs and updates in ``conda-forge-plugins``. Without
``--override-channels``, conda also searches the configured channels.

Channel aliases, authentication, network settings, and channel restrictions are
handled by conda in the same way as ``conda install``. Plugin packages are checked
for a conda entry point before the installation transaction is confirmed.
This check identifies plugin packages; it does not verify that their code is safe.
Only install plugins from sources you trust.

Conda loads plugins from the environment containing the Python interpreter that
runs it. ``conda plugins list`` and ``conda plugins info`` report plugins from that
same environment. Activating another environment does not change the conda
installation used by the shell's ``conda`` command.

To load a plugin installed in another environment, run that environment's Python.
The environment must also contain conda, as in the example above:

.. code-block:: console

   conda run --name conda-forge-plugins python -m conda tree --help
   conda run --name conda-forge-plugins python -m conda plugins list
   conda run --name conda-forge-plugins python -m conda plugins info conda-tree


Updating plugins
----------------

Update an installed plugin by its conda package name. For the Miniforge ``base``
environment used above:

.. code-block:: console

   conda plugins update --name base conda-tree

To update all conda plugin packages installed in that environment:

.. code-block:: console

   conda plugins update --name base --all

``--all`` selects plugin packages rather than every package in the environment.
Plugin updates disable automatic conda upgrades, but the solver may still change
conda or other packages to satisfy plugin dependencies. Review the transaction
plan before confirming. ``--all`` cannot be combined with package names or
``--file``.

For the separate conda-forge environment used above, select its channels again:

.. code-block:: console

   conda plugins update --name conda-forge-plugins --override-channels --channel conda-forge conda-tree

Use ``--dry-run`` with install or update to preview the package plan without
installing packages. Dry runs do not download new packages to check their entry
points, so a successful dry run does not guarantee that those packages provide
conda plugins.

Removing plugins
----------------

Remove a plugin by its conda package name from the same target environment:

.. code-block:: console

   conda plugins remove --name base conda-tree

Removal can also remove packages that depend on the plugin. Review the package
plan before confirming, particularly when removing a solver or another plugin
used by your configuration.

Both remove and named update require the requested packages to be installed as
conda plugin packages in the target environment. They do not manage plugins
installed with pip. Package names can differ from the plugin names shown by
``conda plugins list``; use ``conda list --name base`` to check package names.


Implementation
==============

Plugins in conda integrate the "hook + entry point" structure by utilizing the Pluggy_ Python framework.
This implementation can be broken down via the following two steps:

* Define the hook(s) to be registered
* Register the plugin under the conda entrypoint namespace

Hook
----

Below is an example of a very basic plugin "hook":

.. code-block:: python
   :caption: my_plugin.py

   import conda.plugins


   @conda.plugins.hookimpl
   def conda_subcommands(): ...


Packaging using a pyproject.toml file
-------------------------------------

Below is an example that configures ``setuptools`` using a ``pyproject.toml`` file (note that the
``setup.py`` file is optional if a ``pyproject.toml`` file is defined, and thus will not be discussed here):

.. code-block:: toml
   :caption: pyproject.toml

   [build-system]
   requires = ["setuptools", "setuptools-scm"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "my-conda-plugin"
   version = "1.0.0"
   description = "My conda plugin"
   requires-python = ">=3.11"
   dependencies = ["conda"]

   [project.entry-points."conda"]
   my-conda-plugin = "my_plugin"


Conda plugins use cases
=======================

The new conda plugin API ecosystem brings about many possibilities, including but not limited to:

* :doc:`Custom subcommands <../../dev-guide/plugins/subcommands>`
* Support for packaging-related topics (*e.g.*, :doc:`virtual packages <../../dev-guide/plugins/virtual_packages>`)
* Development environment integrations (*e.g.*, shells)
* Alternative dependency solver backends
* Network adapters
* Build system integrations
* Non-Python language support (*e.g.*, C, Rust)
* :doc:`Environment export formats <../../dev-guide/plugins/environment_exporters>`
* Experimental features that are not currently covered by conda


Benefits of conda plugins
=========================

A conda plugin ecosystem enables contributors across the conda community to develop and share new features,
thus bringing about more functionality and focus on the user experience. Though the list below is by no means
exhaustive, some of the benefits of conda plugins include:

* Support for a better distribution of maintenance in the conda community
* Enabling third party contributors to use official APIs instead of having to divert to workarounds and wrappers
* The ability to extend conda internals via official APIs
* Lowering the barrier for contributions from other stakeholders in the conda ecosystem
* ... and much more!

.. _Pluggy: https://pluggy.readthedocs.io/en/stable/
