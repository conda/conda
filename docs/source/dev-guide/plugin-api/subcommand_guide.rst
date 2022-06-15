=================================
Custom subcommand plugin tutorial
=================================

In this tutorial, we will create a new ``conda`` subcommand that can convert a string
into ASCII art.

This guide requires the use of a ``conda`` environment with Python 3.X and ``pip``
installed.


Project directory structure
---------------------------

Set up your working directory and files as shown below:

.. code-block:: bash

    string-art
    │── string_art.py
    ├── setup.py


The custom subcommand module
----------------------------

The following module implements a function, ``conda_string_art`` (where a specified string gets
converted into ASCII art), into a plugin manager hook called ``conda_cli_register_subcommands``.

The ``HookImplMarker`` decorator is initialized with the name of ``conda`` as the host
project in the ``conda/plugins/__init__.py`` file, and it is invoked via ``@conda.plugins.hookimpl``
in the example subcommand module below:

.. code-block:: python
   :caption: string-art/string_art.py

   from art import text2art

   import conda.plugins


   def conda_string_art(args: str):
       # if using a multi-word string with spaces, make sure to wrap it in quote marks
       output = "".join(args)
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
----------------------------------------------

In order to run the ``conda string-art`` subcommand successfully, you will need to make sure
that the ``art`` package is available, which is why it is listed in the ``install_requires``
section of the ``setup.py`` file shown below:

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


The custom ``string-art`` subcommand plugin can be installed via the ``setup.py`` entrypoint shown above
by running the following:

.. code-block:: bash

   $ pip install --editable [path to project]/string_art


An alternative option: registering a plugin locally
---------------------------------------------------

There is also a way to use ``setuptools`` entrypoints to automatically load plugins that
are registered through them, via the ``load_setup_tools_entrypoints()`` method inside of the
``get_plugin_manager()`` function. This option is particularly useful if you would like to
develop and utilize a custom subcommand locally via a cloned ``conda`` codebase on your
machine.

The example below shows how to register the ``string_art.py`` subcommand plugin module in
``conda/base/context.py``:

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


.. _`documentation page`: https://pluggy.readthedocs.io/en/stable/index.html#loading-setuptools-entry-points
