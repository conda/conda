=======
Plugins
=======

As of version ``22.11.0``, ``conda`` has support for user plugins, enabling extension and/or
alterations to some of its functionality.

An overview of ``pluggy``
-------------------------

Plugins in ``conda`` are implemented with the use of Pluggy_, a Python framework used by
other projects, such as ``pytest``, ``tox``, and ``devpi``. ``pluggy`` provides the ability to
extend and modify the behavior of ``conda`` via function hooking, which results in plugin
systems that are discoverable with the use of `Python package entrypoints`_.

At its core, creating and implementing custom plugins with the use of ``pluggy`` can
be broken down into two parts:

1. Define the hooks you want to register
2. Register your plugin under the ``conda`` entrypoint namespace

If you would like more information about ``pluggy``, please refer to their documentation_
for a full description of its features.


Basic hook and entry point examples
-----------------------------------

Hook
~~~~

Below is an example of a very basic plugin "hook":

.. code-block:: python
   :caption: my_plugin.py

   import conda.plugins


   @conda.plugins.hookimpl
   def conda_subcommands():
       ...


Packaging / entry point namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``pyproject.toml`` file shown below is an example of a way to define and build
a package out of the custom plugin hook shown above:

.. code-block::
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


The ``setup.py`` file below is an alternative to the ``pyproject.toml`` file shown
above; its main difference is the ``entry_points`` argument that is provided to the
``setup()`` function:

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

When licensing plugins, we recommend using licenses such as BSD-3_, MIT_, and
`Apache License 2.0`_. Some ``import`` statements may possibly require the GPLv3_
license, which ensures that the software being licensed is open source.

Ultimately, the authors of the plugins can decide which license is best for their particular
use case. Be sure to credit the original author of the plugin, and keep in mind that
licenses can be altered depending on the situation.

For more information on which license to use for your custom plugin, please reference
the `"Choose an Open Source License"`_ site.


API reference
-------------

.. autoattribute:: conda.plugins::hookimpl
   :no-value:

   Conda plugin hook implementation marker.

.. toctree::
   :maxdepth: 1

   manager
   on_exception
   post_command
   pre_command
   solvers
   subcommands
   virtual_packages


.. _Pluggy: https://pluggy.readthedocs.io/en/stable/
.. _documentation: https://pluggy.readthedocs.io/en/stable/
.. _`Python package entrypoints`: https://packaging.python.org/en/latest/specifications/entry-points/
.. _BSD-3: https://opensource.org/licenses/BSD-3-Clause
.. _MIT: https://opensource.org/licenses/MIT
.. _`Apache License 2.0`: https://www.apache.org/licenses/LICENSE-2.0
.. _GPLv3: https://www.gnu.org/licenses/gpl-3.0.en.html
.. _`"Choose an Open Source License"`: https://choosealicense.com/
