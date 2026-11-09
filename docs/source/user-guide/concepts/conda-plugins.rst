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

.. tip::

   For plugins in the ``base`` environment, ``conda self install``,
   ``conda self update``, and ``conda self remove`` are the safer path: they
   always target ``base`` and also work when ``base`` is protected
   (see :ref:`frozen-env`). See the
   `conda-self documentation <https://conda.github.io/conda-self/>`_
   for details.

Installing plugins
------------------

Use ``conda plugins install`` to install a conda plugin package into an environment.
Select the environment containing the conda installation you want to extend with
``--name`` or ``--prefix``. Choose plugin packages from channels compatible with
the packages already installed there.

.. warning::

   Do not install conda-forge plugins into an Anaconda Distribution or Miniconda
   ``base`` environment using ``defaults``. Adding ``--channel conda-forge`` or
   ``--override-channels`` does not make mixing those packages safe. Use a separate
   conda-forge environment instead. See :ref:`channel-best-practices`.

Choose the example matching the package source of your conda installation:

.. tab-set::

   .. tab-item:: Anaconda Distribution / Miniconda
      :sync: anaconda

      Keep ``base`` on Anaconda's ``defaults`` channels. To try the conda-forge
      plugin ``conda-tree``, create a separate environment containing conda:

      .. code-block:: console

         conda create --name conda-forge-plugins --override-channels --channel conda-forge conda
         conda plugins install --name conda-forge-plugins --override-channels --channel conda-forge conda-tree

      These commands leave the packages in ``base`` unchanged. Run the separate
      environment's conda to use the plugin:

      .. code-block:: console

         conda run --name conda-forge-plugins python -m conda tree --help

   .. tab-item:: Miniforge
      :sync: conda-forge

      Miniforge uses conda-forge packages in ``base``. Install ``conda-tree`` there,
      explicitly restricting package sources to conda-forge:

      .. code-block:: console

         conda plugins install --name base --override-channels --channel conda-forge conda-tree

      This example assumes ``base`` still contains only compatible conda-forge
      packages. Do not use it for an Anaconda ``defaults`` environment.

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


Inspecting plugins
------------------

List the plugins available to the running conda installation:

.. code-block:: console

   conda plugins list

The table shows each plugin's distribution name, version, status, and registered
hooks. Hooks identify the capabilities the plugin provides, such as subcommands
or solvers. To inspect one plugin, replace ``NAME`` with a distribution name from
the table:

.. code-block:: console

   conda plugins info NAME

``info`` shows the plugin's canonical name, summary, license, homepage, and project
URLs in addition to its version, status, and hooks. It also accepts the canonical
plugin name. Metadata fields may be empty when the plugin does not provide them.

Both commands support JSON output for scripts:

.. code-block:: console

   conda plugins list --json
   conda plugins info NAME --json

Unlike install, update, and remove, these commands do not accept ``--name`` or
``--prefix`` to select another environment. Use that environment's Python as
shown above. ``list`` and ``info`` were available before conda 26.11.0.


Updating plugins
----------------

Update installed plugins using the same target environment and package sources
used to install them. Do not switch an Anaconda ``base`` environment to
conda-forge to update a plugin.

.. tab-set::

   .. tab-item:: Anaconda Distribution / Miniconda
      :sync: anaconda

      Update plugin packages in your ``defaults``-based ``base`` environment
      using only ``defaults``:

      .. code-block:: console

         conda plugins update --name base --override-channels --channel defaults --all

      For ``conda-tree``, use the separate conda-forge environment created in the
      installation example. Do not target ``base``:

      .. code-block:: console

         conda plugins update --name conda-forge-plugins --override-channels --channel conda-forge conda-tree

      To update all plugins in that separate environment:

      .. code-block:: console

         conda plugins update --name conda-forge-plugins --override-channels --channel conda-forge --all

   .. tab-item:: Miniforge
      :sync: conda-forge

      Update ``conda-tree`` in your conda-forge-based ``base`` environment:

      .. code-block:: console

         conda plugins update --name base --override-channels --channel conda-forge conda-tree

      To update all plugin packages in that environment:

      .. code-block:: console

         conda plugins update --name base --override-channels --channel conda-forge --all

``--all`` selects plugin packages rather than every package in the environment.
Plugin updates disable automatic conda upgrades, but the solver may still change
conda or other packages to satisfy plugin dependencies. Review the transaction
plan before confirming. ``--all`` cannot be combined with package names or
``--file``.

Use ``--dry-run`` with install or update to preview the package plan without
installing packages. Dry runs do not download new packages to check their entry
points, so a successful dry run does not guarantee that those packages provide
conda plugins.

Removing plugins
----------------

Remove a plugin by its conda package name from the same target environment:

.. tab-set::

   .. tab-item:: Anaconda Distribution / Miniconda
      :sync: anaconda

      Remove ``conda-tree`` from the separate conda-forge environment:

      .. code-block:: console

         conda plugins remove --name conda-forge-plugins --override-channels --channel conda-forge conda-tree

   .. tab-item:: Miniforge
      :sync: conda-forge

      Remove ``conda-tree`` from your conda-forge-based ``base`` environment:

      .. code-block:: console

         conda plugins remove --name base --override-channels --channel conda-forge conda-tree

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
