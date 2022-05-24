================
Conda Plugin API
================

As of version ``X.Y``, ``conda`` has support for user plugins, enabling them to
extend and/or change some of its functionality.

An overview of ``pluggy``
-------------------------

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


Basic hook and entrypoint examples
----------------------------------

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

The ``setup.py`` file below is an example of an entrypoint namespace for the
custom plugin function decorated with the plugin hook (shown above):

.. code-block:: python
   :caption: setup.py

   from setuptools import setup

   setup(
       name="my-conda-plugin",
       install_requires="conda",
       entry_points={"conda": ["my-conda-plugin = my_plugin"]},
       py_modules=["my_plugin"],
   )


A note on licensing
-------------------

XYZ

.. Brief info about licensing and different options here

Custom subcommand plugin tutorial
---------------------------------

XYZ

.. Explain what this tutorial is going to be teaching

A custom subcommand module
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. What does this module do?

.. code-block:: python
   :caption: string_art.py

   from art import *

   import conda.plugins


   def conda_string_art(args: str):
       # if using a multi-word string with spaces, make sure to wrap it in quote marks
       str = ""
       output = str.join(args)
       string_art = text2art(output)

       print(string_art)


   @conda.plugins.hookimpl
   def conda_cli_register_subcommands():
       yield conda.plugins.CondaSubcommand(
           name="string-art",
           summary="tutorial subcommand that prints a string as ASCII art",
           action=conda_string_art,
       )


Entrypoint namespace for the custom subcommand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. Include info about how to use entrypoints

.. code-block:: python
   :caption: setup.py

   from setuptools import setup

   install_requires = [
       "conda",
       "art",
   ]

   setup(
       name="my-conda-subcommand",
       install_requires=install_requires,
       entry_points={"conda": ["my-conda-subcommand = string_art"]},
       py_modules=["string_art"],
   )



The subcommand output
~~~~~~~~~~~~~~~~~~~~~

Once the subcommand plugin is successfully installed, the help text will display
it as an additional option available from other packages:

.. code-block:: bash

  $ conda --help
  usage: conda [-h] [-V] command ...

  conda is a tool for managing and deploying applications, environments and packages.

  Options:

  positional arguments:
   command
     clean        Remove unused packages and caches.

  [...output shortened...]

  conda commands available from other packages:
  string-art - tutorial subcommand that prints a string as ASCII art

  conda commands available from other packages (legacy):
   content-trust
   env


Running ``conda string-art [string]`` will result in output like the following:

.. code-block::

  $ conda string-art "testing 123"
    _               _    _                 _  ____   _____
   | |_   ___  ___ | |_ (_) _ __    __ _  / ||___ \ |___ /
   | __| / _ \/ __|| __|| || '_ \  / _` | | |  __) |  |_ \
   | |_ |  __/\__ \| |_ | || | | || (_| | | | / __/  ___) |
    \__| \___||___/ \__||_||_| |_| \__, | |_||_____||____/
                                   |___/

API reference
-------------

.. py:module:: conda.plugins


.. toctree::
   :maxdepth: 1

   subcommands

.. _documentation: https://pluggy.readthedocs.io/en/stable/
.. _`Python package entrypoints`: https://packaging.python.org/en/latest/specifications/entry-points/
