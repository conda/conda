===========================================
Using the .condarc conda configuration file
===========================================

.. _config-overview:

Overview
========

The conda configuration file, ``.condarc``, is an optional
runtime configuration file that allows advanced users to
configure various aspects of conda, such as which channels it
searches for packages, proxy settings, and environment
directories. For all of the conda configuration options,
see the :doc:`configuration page <../../configuration>`.


.. note::

   A ``.condarc`` file can also be used in an
   administrator-controlled installation to override the users’
   configuration. See :doc:`admin-multi-user-install`.

The ``.condarc`` file can change many parameters, including:

* Where conda looks for packages.

* If and how conda uses a proxy server.

* Where conda lists known environments.

* Whether to update the Bash prompt with the currently activated
  environment name.

* Whether user-built packages should be uploaded to
  `Anaconda.org <http://anaconda.org>`_.

* What default packages or features to include in new environments.

Creating and editing
====================

The ``.condarc`` file is not included by default, but it is
automatically created in your home directory the first time you
run the ``conda config`` command. To create or modify a ``.condarc``
file, open a terminal and enter the ``conda config`` command.

The ``.condarc`` configuration file follows simple
`YAML syntax <https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html>`_.

**Example:**

.. code-block:: yaml

  conda config --add channels conda-forge

Alternatively, you can open a text editor such as Notepad
on Windows, TextEdit on macOS, or VS Code. Name the new file
``.condarc`` and save it to your user home directory or root
directory. To edit the ``.condarc`` file, open it from your
home or root directory and make edits in the same way you would
with any other text file. If the ``.condarc`` file is in the root
environment, it will override any in the home directory.

You can find information about your ``.condarc`` file by typing
``conda info`` in your terminal. This will give you information about
your ``.condarc`` file, including where it is located.

You can also download a :doc:`sample .condarc file
<sample-condarc>` to edit in your editor and save to your user
home directory or root directory.

To set configuration options, edit the ``.condarc`` file directly
or use the ``conda config --set`` command.

**Example:**

To set the ``auto_update_conda option`` to ``False``, run::

  conda config --set auto_update_conda False

For a complete list of conda config commands, see the
:doc:`command reference <../../commands/config>`. The same list
is available at the terminal by running
``conda config --help``. You can also see the `conda channel
configuration <https://conda.io/projects/conda/en/latest/configuration.html>`_ for more information.

.. tip::

   Conda supports :doc:`tab completion <enable-tab-completion>`
   with external packages instead of internal configuration.

Conda supports a wide range of configuration options. This page
gives a non-exhaustive list of the most frequently used options and
their usage. For a complete list of all available options for your
version of conda, use the ``conda config --describe`` command.

.. _condarc_search_precedence:

Searching for .condarc
======================

Conda looks in the following locations for a ``.condarc`` file:

.. code-block:: python

  if on_win:
      SEARCH_PATH = (
          "C:/ProgramData/conda/.condarc",
          "C:/ProgramData/conda/condarc",
          "C:/ProgramData/conda/condarc.d",
      )
  else:
      SEARCH_PATH = (
          "/etc/conda/.condarc",
          "/etc/conda/condarc",
          "/etc/conda/condarc.d/",
          "/var/lib/conda/.condarc",
          "/var/lib/conda/condarc",
          "/var/lib/conda/condarc.d/",
      )

  SEARCH_PATH += (
      "$CONDA_ROOT/.condarc",
      "$CONDA_ROOT/condarc",
      "$CONDA_ROOT/condarc.d/",
      "$XDG_CONFIG_HOME/conda/.condarc",
      "$XDG_CONFIG_HOME/conda/condarc",
      "$XDG_CONFIG_HOME/conda/condarc.d/",
      "~/.config/conda/.condarc",
      "~/.config/conda/condarc",
      "~/.config/conda/condarc.d/",
      "~/.conda/.condarc",
      "~/.conda/condarc",
      "~/.conda/condarc.d/",
      "~/.condarc",
      "$CONDA_PREFIX/.condarc",
      "$CONDA_PREFIX/condarc",
      "$CONDA_PREFIX/condarc.d/",
      "$CONDARC",
  )

``XDG_CONFIG_HOME`` is the path to where user-specific configuration files should
be stored defined following The XDG Base Directory Specification (XDGBDS). Default
to $HOME/.config should be used.
``CONDA_ROOT`` is the path for your base conda install.
``CONDA_PREFIX`` is the path to the current active environment.
``CONDARC`` must be a path to a file named ``.condarc``, ``condarc``, or end with a YAML suffix (``.yml`` or ``.yaml``).

.. note::
   Any condarc files that exist in any of these special search path
   directories need to end in a valid yaml extension (".yml" or ".yaml").


Conflict merging strategy
-------------------------
When conflicts between configurations arise, the following strategies are employed:

* Lists - merge
* Dictionaries - merge
* Primitive - clobber

Precedence
----------

The precedence by which the conda configuration is built out is shown below.
Each new arrow takes precedence over the ones before it. For example, config
files (by parse order) will be superseded by any of the other configuration
options. Configuration environment variables (formatted like ``CONDA_<CONFIG NAME>``)
will always take precedence over the other 3.

.. figure:: /img/config-precedence.png

   ..

Obtaining information from the .condarc file
============================================

You can use the following commands to get the effective settings for conda.
The effective settings are those that have merged settings from all the sources
mentioned above.

To get all keys and their values:

.. code-block:: bash

   conda config --get

To get the value of a specific key, such as channels:

.. code-block:: bash

   conda config --get channels

To show all the configuration file sources and their contents::

    conda config --show-sources


Saving settings to your .condarc file
=====================================

The ``.condarc`` file can also be modified via conda commands.
Below are several examples of how to do this.

To add a new value, such as
http://conda.anaconda.org/mutirri, to a specific key, such as
channels:

.. code-block:: bash

   conda config --add channels http://conda.anaconda.org/mutirri

To remove an existing value, such as
http://conda.anaconda.org/mutirri from a specific key, such as
channels:

.. code-block:: bash

   conda config --remove channels http://conda.anaconda.org/mutirri

To remove a key, such as channels, and all of its values:

.. code-block:: bash

   conda config --remove-key channels

To configure channels and their priority for a single
environment, make a ``.condarc`` file in the :ref:`root directory
of that environment <config-channels>`.

.. _sample-condarc:

Sample .condarc file
====================

Because the ``.condarc`` file is just a YAML file, it means that
it can be edited directly. Below is an example ``.condarc`` file:

.. code-block:: yaml

  # This is a sample .condarc file.
  # It adds the r Anaconda.org channel and enables
  # the show_channel_urls option.

  # channel locations. These override conda defaults, i.e., conda will
  # search *only* the channels listed here, in the order given.
  # Use "defaults" to automatically include all default channels.
  # Non-url channels will be interpreted as Anaconda.org usernames
  # (this can be changed by modifying the channel_alias key; see below).
  # The default is just 'defaults'.
  channels:
    - r
    - defaults

  # Show channel URLs when displaying what is going to be downloaded
  # and in 'conda list'. The default is False.
  show_channel_urls: True

  # For more information about this file see:
  # https://conda.io/docs/user-guide/configuration/use-condarc.html
