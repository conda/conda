================
Conda Plugin API
================

As of version ``X.Y``, ``conda`` has support for user plugins, enabling them to
extend and/or change some of its functionality.

What is ``pluggy``?
-------------------

Plugins in ``conda`` are implemented with the use of ``pluggy``, a Python framework used by
other projects such as ``pytest``, ``tox``, and ``devpi``. ``pluggy`` provides the ability to
extend and modify the behavior of ``conda`` via function hooking, which results in plugin
systems that are discoverable with the use of `Python package entrypoints`_.

At its core, creating and implementing custom plugins with the use of ``pluggy`` can
be broken down into two parts:

1. Define the hooks you want to register
2. Register your plugin under the ``conda`` entrypoint namespace

If you would like more information about ``pluggy``, please refer to their documentation_
for a full description of its features.


Hook and entrypoint examples
----------------------------

Hook
~~~~

Below is an example of a very basic plugin "hook":

.. code-block:: python
   :caption: my_plugin.py

   import conda.plugins


   @conda.plugins.hookimpl
   def conda_cli_register_subcommands():
       ...

Entrypoint namespace
~~~~~~~~~~~~~~~~~~~~

The codeblock below is an example of an entrypoint namespace for the custom plugin function
(shown above) that is decorated with the plugin hook:

.. code-block:: python
   :caption: setup.py

   from setuptools import setup

   setup(
       name="my-conda-plugin",
       install_requires="conda",
       entry_points={"conda": ["my-conda-plugin = my_plugin"]},
       py_modules=["my_plugin"],
   )


Custom subcommand plugin tutorial
---------------------------------

XYZ

.. Explain what this tutorial is going to be teaching

A custom subcommand
~~~~~~~~~~~~~~~~~~~

.. code-block:: python
 :caption: string_art.py

 # insert code here


Custom subcommand entrypoint namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
 :caption: setup.py

 # Update with the code from github gist

 from setuptools import setup

 setup(
     name="my-conda-plugin",
     install_requires="conda",
     entry_points={"conda": ["my-conda-plugin = my_plugin"]},
     py_modules=["my_plugin"],
 )


API reference
-------------

.. py:module:: conda.plugins


.. toctree::
   :maxdepth: 1

   subcommands

.. _documentation: https://pluggy.readthedocs.io/en/stable/
.. _`Python package entrypoints`: https://packaging.python.org/en/latest/specifications/entry-points/
