================
Conda Plugin API
================

As of X.Y, Conda has support for user plugins, enabling them to extend and/or
change some of its functionality.

Plugins are implemented via pluggy_ and discovered using
`Python package entrypoints`_. You may refeer to pluggy_'s documentation
for a full description of its features, but in summary, you will want to define
the hooks you want to register and register your plugin under the ``conda``
entrypoint namespace.

Example:


.. code-block:: python
   :caption: my_plugin.py

   import conda.plugins


   @conda.plugins.hookimpl
   def conda_cli_register_subcommands():
       ...


.. code-block:: python
   :caption: setup.py

   from setuptools import setup

   setup(
       name="my-conda-plugin",
       install_requires="conda",
       entry_points={"conda": ["my-conda-plugin = my_plugin"]},
       py_modules=["my_plugin"],
   )


API Reference
-------------

.. py:module:: conda.plugins


Hooks
~~~~~


.. toctree::
   :maxdepth: 1

   subcommands
   virtual_packages

.. _pluggy: https://pluggy.readthedocs.io/en/stable/
.. _`Python package entrypoints`: https://packaging.python.org/en/latest/specifications/entry-points/
