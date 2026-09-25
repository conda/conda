=======
Plugins
=======

.. _concept-plugins:


In order to enable customization and extra features that are compatible with and discoverable by conda
(but do not necessarily ship as a default part of the conda codebase), an official conda plugin mechanism
has been implemented as of version ``22.11.0``.

Installing plugins
==================

Use ``conda plugins install`` to install a conda plugin package into an environment.
Select the environment containing the conda installation you want to extend with
``--name`` or ``--prefix``. For example, to install ``conda-tree`` into ``base``:

.. code-block:: console

   conda plugins install --name base --override-channels --channel conda-forge conda-tree

``--channel`` (``-c``) selects a package source for this command. Repeat it to search
multiple sources in the specified order. ``--override-channels`` excludes the
configured channels, so explicit sources can be used before a ``.condarc`` exists.
These options do not create or modify channel configuration. Without
``--override-channels``, conda also searches the configured channels.

Channel aliases, authentication, network settings, and channel restrictions are
handled by conda in the same way as ``conda install``. Plugin packages are checked
for a conda entry point before the installation transaction is confirmed.

Start a new conda process from the target environment to load an installed plugin.


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
   requires-python = ">=3.7"
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
