=================================
Custom subcommand plugin tutorial
=================================

In this tutorial, we will create a new ``conda`` subcommand that can convert a string
into ASCII art.

To follow along with this guide, it is recommended that you create and activate a new ``conda``
environment with the following commands:

.. code-block:: bash

   $ conda create -n plugin-tutorial "python>=3"

   $ conda activate plugin-tutorial


Project directory structure
---------------------------

Set up your working directory and files as shown below:

.. code-block:: bash

    /string-art
    │── string_art.py
    └── pyproject.toml (or setup.py)


The custom subcommand module
----------------------------

The following module implements a function, ``conda_string_art`` (where a specified string gets
converted into ASCII art), into a plugin manager hook called ``conda_subcommands``.

The ``HookImplMarker`` decorator is initialized with the name of ``conda`` as the host
project in the ``conda/plugins/__init__.py`` file, and it is invoked via ``@conda.plugins.register``
in the example subcommand module below:

.. code-block:: python
   :caption: string-art/string_art.py

   from art import text2art
   from typing import Sequence


   import conda.plugins


   def conda_string_art(args: Sequence[str]):
       # if using a multi-word string with spaces, make sure to wrap it in quote marks
       output = "".join(args)
       string_art = text2art(output)

       print(string_art)


   @conda.plugins.register
   def conda_subcommands():
       yield conda.plugins.CondaSubcommand(
           name="string-art",
           summary="tutorial subcommand that prints a string as ASCII art",
           action=conda_string_art,
       )


Packaging the custom subcommand
-------------------------------

In order to run the ``conda string-art`` subcommand successfully, you will first need
to either package the subcommand (examples are shown in this section) or register it
locally (details for how to do that are discussed in the following section).

Below is a code snippet that shows how to set up the ``pyproject.toml`` file to package the
``string-art`` subcommand:

.. code-block::
   :caption: string-art/pyproject.toml

   [build-system]
   requires = ["setuptools>=61.0", "setuptools-scm"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "my-conda-subcommand"
   version = "1.0.0"
   description = "My string art subcommand plugin"
   requires-python = ">=3.7"
   dependencies = ["conda", "art"]

   [tools.setuptools]
   py_modules=["string_art"]

   [project.entry-points."conda"]
   my-conda-subcommand = "string_art"


.. note::

   Below is a list of explanations of the metadata that we are specifying in the ``pyproject.toml`` example above:

   ``[build-system]``

   * **requires** This is a list of requirement specifiers for build-time dependencies of a package.
   * **build-backend** Build backends have the ability to accept configuration settings, which can change the way that the package building is handled.

   ``[project]``

   * **name** (required) This is the name of the package that contains your subcommand. This is also how others will find your subcommand package if you choose to upload it to PyPI.
   * **version** (required) The version of the project; can be specified *either* statically or listed as dynamic.
   * **description** A brief description of the project.
   * **requires-python** The version(s) of Python required by your project.
   * **dependencies** These are all of the dependencies for your project. This specific subcommand example requires both ``conda`` and ``art``, which is why they are both listed here.


The custom ``string-art`` subcommand plugin can be installed via ``pyproject.toml`` as shown above
by running the following commands (from the same directory where the ``pyproject.toml`` is located):

**[Unix/MacOS]**

.. code-block:: bash

  # Make sure you have the latest version of pip installed
  $ python3 -m pip install --upgrade pip

  # Make sure you have the latest version of PyPA’s build installed
  $ python3 -m pip install --upgrade build

  # Run this command from the same directory where the pyproject.toml file is located
  $ python3 -m build

**[Windows]**

.. code-block:: bash

  # Make sure you have the latest version of pip installed
  $ py -m pip install --upgrade pip

  # Make sure you have the latest version of PyPA’s build installed
  $ py -m pip install --upgrade build

  # Run this command from the same directory where the pyproject.toml file is located
  $ py -m build


At this point, if the custom subcommand package was built successfully, there should be a
``dist`` directory inside of the ``string-art`` directory with the following contents:

.. code-block:: bash

    /dist
    │── my-conda-subcommand-1.0.0.tar.gz
    └── my_conda_subcommand-1.0.0-py3-none-any.whl

Run the following command in order to install the ``string-art`` subcommand package:

**[Unix/MacOS]**

.. code-block:: bash

  # Install the string-art package
  $ python3 -m pip install dist/my_conda_subcommand-1.0.0-py3-none-any.whl


**[Windows]**

.. code-block:: bash

  # Install the string-art package
  $ py -m pip install dist\my_conda_subcommand-1.0.0-py3-none-any.whl


.. note::

   For more information on ``pyproject.toml`` configuration, please read the related `PyPA documentation page`_.


------------

Another packaging option is to utilize a ``setup.py`` file, as shown below:

.. code-block:: python
   :caption: string-art/setup.py

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

.. note::

   Below is a list of explanations of the variables that we are passing to the ``setup`` function in the ``setup.py`` example above:

   * **name** This is the name of the package that contains your subcommand. This is also how others will find your subcommand package if you choose to upload it to PyPI.
   * **install_requires** These are all of the dependencies for your project. This should at a minimum always contain the version of ``conda`` for which your plugin is compatible with.
   * **entry_points** The entry point you list here is how ``conda`` will discover your plugin and should point to the file containing the ``conda.plugins.register`` hook. In our simple use case, it points to the ``string_art`` module contained within the ``string_art.py`` file. For more complex examples where your module is contained within a folder, it may look more like ``my_module.main`` or ``my_modules.plugin_hooks``.
   * **py_modules** The ``py_modules`` variables lets ``setup`` know exactly where to look for all of the modules which comprise your plugin source code.


The custom ``string-art`` subcommand plugin can be installed via the ``setup.py`` example shown above
by running the following from the directory where the ``setup.py`` file is located:

**[Unix/MacOS]**

.. code-block:: bash

   $ python3 -m pip install --editable .

**[Windows]**

.. code-block:: bash

   $ py -m pip install --editable .


.. note::

   For more information about entry points specification in general, please read `PyPA's entrypoints documentation`_.


An alternative option: registering a plugin locally
---------------------------------------------------

There is also a way to use ``setuptools`` entrypoints to automatically load plugins that
are registered through them, via the ``load_setup_tools_entrypoints()`` method inside of the
``get_plugin_manager()`` function. This option is particularly useful if you would like to
develop and utilize a custom subcommand locally via a cloned ``conda`` codebase on your
machine.

If you prefer not to package your subcommand, the code snippet below shows how to register the
``string_art.py`` subcommand plugin module in ``conda/base/context.py``:

.. code-block:: python
   :caption: conda/base/context.py

   @functools.lru_cache(maxsize=None)
   def get_plugin_manager():
       pm = pluggy.PluginManager("conda")
       pm.add_hookspecs(plugins)
       pm.register(string_art)  # <--- this line is registering the custom subcommand
       # inside of conda itself instead of using an external entrypoint namespace
       pm.load_setuptools_entrypoints("conda")
       return pm


.. note::

   For more information, check out the associated ``pluggy`` `documentation page`_.


The subcommand output
---------------------

Once the subcommand plugin is successfully installed or registered, the help text will display
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


Running ``conda string-art [string]`` will result in the following output:

.. code-block::

  $ conda string-art "testing 123"
    _               _    _                 _  ____   _____
   | |_   ___  ___ | |_ (_) _ __    __ _  / ||___ \ |___ /
   | __| / _ \/ __|| __|| || '_ \  / _` | | |  __) |  |_ \
   | |_ |  __/\__ \| |_ | || | | || (_| | | | / __/  ___) |
    \__| \___||___/ \__||_||_| |_| \__, | |_||_____||____/
                                   |___/

Congratulations, you've just implemented your first custom ``conda`` subcommand plugin!

.. note::

  Whenever you develop your own custom plugins, please be sure to apply
  the :ref:`appropriate license<A note on licensing>`.


.. _`PyPA documentation page`: https://packaging.python.org/en/latest/tutorials/packaging-projects/#creating-pyproject-toml
.. _`PyPA's entrypoints documentation`: https://packaging.python.org/en/latest/specifications/entry-points/
.. _`documentation page`: https://pluggy.readthedocs.io/en/stable/index.html#loading-setuptools-entry-points
