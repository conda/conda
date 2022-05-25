Custom subcommand plugin tutorial
---------------------------------

[content coming soon]

.. Explain what this tutorial is going to be teaching

A custom subcommand module
~~~~~~~~~~~~~~~~~~~~~~~~~~

[content coming soon]

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

[content coming soon]

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


Running ``conda string-art [string]`` successfully will result in the following output:

.. code-block::

  $ conda string-art "testing 123"
    _               _    _                 _  ____   _____
   | |_   ___  ___ | |_ (_) _ __    __ _  / ||___ \ |___ /
   | __| / _ \/ __|| __|| || '_ \  / _` | | |  __) |  |_ \
   | |_ |  __/\__ \| |_ | || | | || (_| | | | / __/  ___) |
    \__| \___||___/ \__||_||_| |_| \__, | |_||_____||____/
                                   |___/

As with any custom plugin, be sure you are applying the :ref:`appropriate license<A note on licensing>`.
