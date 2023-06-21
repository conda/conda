========
Plugins
========

As of version ``22.11.0``, ``conda`` has support for user plugins, enabling extension and/or
alterations to some of its functionality.

Quick start
-----------

This is an example of a minimal working conda plugin that defines a new subcommand:

.. code-block:: python
   :caption: example_plugin.py

   import conda.plugins
   from conda.base.context import context


   def command(arguments: list[str]):
       print("Conda subcommand!")


   @conda.plugins.hookimpl
   def conda_subcommands():
       yield plugins.CondaSubcommand(
           name="example", action=command, summary="Example of a conda subcommand"
       )


Let's break down what's going on here step-by-step:

1. First, we create the function ``command`` that serves as our subcommand. This function is passed a list of
   arguments which equal to ``sys.argv[2:]``.
2. Next, we register this subcommand by using the ``conda_subcommands`` plugin hook. We do this by creating a function
   called ``conda_subcommands`` and then decorating it with ``conda.plugins.hookimpl``.
3. The object we return from this function is ``conda.plugins.CondaSubcommand``, which does several things:

   1. **name** is what we use to call this subcommand via the command line (i.e. "conda example")
   2. **action** is the function that will be called when we invoke "conda example"
   3. **summary** is the description of the of the subcommand that appears when users call "conda --help"

In order to actually use conda plugins, they must be packaged as Python packages. Furthermore, we also need to take
advantage of a feature known as `Python package entrypoints`_. We can define our Python package and the entry points
by either using a ``pyproject.toml`` file (preferred) or a ``setup.py`` (legacy) for our project:

.. code-block::
   :caption: pyproject.toml

   [build-system]
   requires = ["setuptools", "setuptools-scm"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "conda-example-plugin"
   version = "1.0.0"
   description = "Example conda plugin"
   requires-python = ">=3.8"
   dependencies = ["conda"]

   [project.entry-points."conda"]
   conda-example-plugin = "example_plugin"

.. code-block:: python
   :caption: setup.py

   from setuptools import setup

   setup(
       name="conda-example-plugin",
       install_requires="conda",
       entry_points={"conda": ["conda-example-plugin = example_plugin"]},
       py_modules=["example_plugin"],
   )

In both examples shown above, we define an entry point for conda. It's important to make sure
that the entry point is for "conda" and that it points to the correct module in your plugin package.
Our package only consists a single Python module called ``example_plugin``. If you have a large project,
be sure to always point the entry point to the module containing the plugin hook declarations (i.e.
where ``conda.plugins.hookimpl`` is used). We recommend using the `plugin` submodule
in these cases, e.g. `large_project.plugin` (in `large_project/plugin.py`).

More examples
-------------

To see more examples of conda plugins, please visit the following resources:

- `conda-plugins-template`_: this is a repository with full examples that could be used a starting point for your plugin

Using other plugin hooks
------------------------

For examples of how to use other plugin hooks, please read their respective documentation pages:

.. toctree::
   :maxdepth: 1

   post_commands
   pre_commands
   solvers
   subcommands
   virtual_packages


More information about how plugins work
---------------------------------------

Plugins in ``conda`` are implemented with the use of Pluggy_, a Python framework used by
other projects, such as ``pytest``, ``tox``, and ``devpi``. ``pluggy`` provides the ability to
extend and modify the behavior of ``conda`` via function hooking, which results in plugin
systems that are discoverable with the use of `Python package entrypoints`_.

For more information about how it
works, we suggest heading over to their `documentation`_.

API
---

For even more detailed information about our plugin system, please the see the
:doc:`Plugin API </dev-guide/api/conda/plugins/index>`.


A note on licensing
-------------------

For more information on which license to use for your custom plugin, please reference
the `"Choose an Open Source License"`_ site. If you need help figuring out exactly
which one to use, we advise to seeking a qualified legal professional.


.. _Pluggy: https://pluggy.readthedocs.io/en/stable/
.. _documentation: https://pluggy.readthedocs.io/en/stable/
.. _`Python package entrypoints`: https://packaging.python.org/en/latest/specifications/entry-points/
.. _BSD-3: https://opensource.org/licenses/BSD-3-Clause
.. _MIT: https://opensource.org/licenses/MIT
.. _`Apache License 2.0`: https://www.apache.org/licenses/LICENSE-2.0
.. _GPLv3: https://www.gnu.org/licenses/gpl-3.0.en.html
.. _`"Choose an Open Source License"`: https://choosealicense.com/
.. _`conda-plugins-template`: https://github.com/conda/conda-plugin-template/tree/main/tutorials
.. _`plugins-api`: /dev-guide/api/conda/plugins
