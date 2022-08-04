=================================
Custom subcommand plugin tutorial
=================================

In this tutorial, we will create a new ``conda`` subcommand that can convert a string
into ASCII art. We will also show you how to use ``click`` to build a CLI interface
for this command. This example can be used as starting point when developing your
own ``conda`` subcommands.

To follow along with this guide, it is recommended that you create and activate a new ``conda``
environment with the following commands:

.. code-block:: bash

   $ conda create -n plugin-tutorial "python>=3"

   $ conda activate plugin-tutorial


Project directory structure
---------------------------

Set up your working directory and files as shown below:

.. code-block:: bash

    string-art
    │── string_art.py
    └── setup.py


The custom subcommand module
----------------------------

In our simple program, we define a CLI interface using ``click`` and a function that
is able to print our ASCII art. Below is the program in its entirety:

.. code-block:: python
   :caption: string-art/string_art.py

   import click
   import conda.plugins
   from art import text2art

   COMMAND_NAME = "string-art"
   __version__ = "0.1.0"


   @click.group()
   def cli():
       pass


   @cli.command(COMMAND_NAME)
   @click.version_option(__version__, prog_name=COMMAND_NAME)
   @click.argument("message")
   @click.option("-n", "--normal", is_flag=True, help="No art, just print it normally")
   def command(message, normal):
       if normal:
           print(message)
       else:
           print(text2art(message))


   @conda.plugins.register
   def conda_subcommands():
       yield conda.plugins.CondaSubcommand(
           name=COMMAND_NAME,
           summary="tutorial subcommand that prints a string as ASCII art",
           action=cli,
       )


Let's break down exactly what's going on above:

First, we import all the necessary modules we need. For this program we import ``click``
to define our command line interface, ``art`` so we can render our message as ASCII art and
``conda.plugins`` so that we can register our subcommand with ``conda``. We additionally
define a version and the name of the command.

After that, we use several decorators from ``click`` to define the actual CLI interface.
We first use the ``click.group`` decorator to define a ``cli`` object. This is necessary
because our command is being embedded as a subcommand in ``conda``. Without doing this,
we would be one level off, and the commands would not work correctly.

Once we have defined this ``cli`` object, we can then register subcommands on it by using
the ``cli.command`` decorator. At this point, we also have all the available decorators one
would normally use to define a ``click`` command, including ``click.argument`` and ``click.option``.

Finally, we register this subcommand with ``conda`` by using the ``conda.plugins.register`` decorator.
Some important things to note here are:

- The decorated function must be named ``conda_subcommands``; otherwise, it will not be found.
- It must also yield at least one ``conda.plugins.CondaSubcommand`` object.

The ``CondaSubcommand`` object must include a ``name`` and ``summary``. These are the details that
will be listed on the help page (i.e. ``conda --help``). Additionally, you must include an ``action``
function. For the click tutorial, this will be the ``cli`` object we defined earlier, but technically,
it can be any ``callable`` object. This means you have quite a bit of flexibility in defining your CLI
interface (i.e. you do not have to use ``click`` and could use whatever you would like).

Entrypoint namespace for the custom subcommand
----------------------------------------------

In order to run the ``conda string-art`` subcommand successfully, you will need to make sure
that the ``art`` and ``click`` packages are available, which is why they are listed in the ``install_requires``
section of the ``setup.py`` file shown below:

.. code-block:: python
   :caption: string-art/setup.py

   from setuptools import setup

   install_requires = ["conda", "art", "click"]

   setup(
       name="my-conda-subcommand",
       install_requires=install_requires,
       entry_points={"conda": ["my-conda-subcommand = string_art"]},
       py_modules=["string_art"],
   )


The custom ``string-art`` subcommand plugin can be installed via the ``setup.py`` entrypoint shown above
by running the following ``pip`` command:

.. code-block:: bash

   $ pip install --editable [path to project]/string_art


The subcommand output
---------------------

Once the subcommand plugin is successfully installed, the help text will display
it as an additional command available from other packages:

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
