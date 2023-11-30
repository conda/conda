==========================
Getting started with conda
==========================

Conda is a powerful command line package and environment management tool that runs on Windows, macOS, and Linux.

This guide to getting started with conda goes over the basics of starting up and using conda to create environments and install packages.

.. tip::

   Anaconda Navigator is a graphical desktop application that enables you to use conda without having to enter commands into the command line.

   See `Getting started with Anaconda Navigator <https://docs.anaconda.com/anaconda/navigator/getting-started>`_ to learn more.

Before you start
================

You should have already installed conda before beginning this getting started guide. Conda can be found in many distributions, like `Anaconda Distribution <https://docs.anaconda.com/free/anaconda/install/>`_ or `Miniconda <https://docs.conda.io/projects/miniconda/en/latest/>`_.

Starting conda
==============

Conda is available on Windows, macOS, or Linux. Conda can be used with any terminal application (or shell) in MacOS/Linux, while in Windows, we recommend using the Anaconda Prompt application provided by the Anaconda Distribution or Miniconda installations.

.. tab-set::

   .. tab-item:: Windows

      #. From the Start menu, search for "Anaconda Prompt".
      #. Open the Anaconda Prompt desktop app that appears in the search sidebar.

   .. tab-item:: macOS

      #. Open Launchpad.
      #. Open the Other application folder.
      #. Open the Terminal application.

   .. tab-item:: Linux

      Open a terminal window.

Creating environments
=====================

Conda allows you to create separate environments, each containing their own files, packages, and package dependencies. The contents of each environment do not interact with one another.

The most basic way to create a new environment is with the following command::

   conda create -n <env-name>

To add packages while creating an environment, list them all behind the environment name::

   conda create -n myenvironment python numpy pandas

For more information on environments, see :doc:`Managing environments <tasks/manage-environments>`.

Listing environments
====================

To see a list of all your environments::

   conda info --envs

A list of environments appears, similar to the following::

   conda environments:

      base           /home/username/Anaconda3
      myenvironment   * /home/username/Anaconda3/envs/myenvironment

.. tip::
   The active environment is the one with an asterisk (*).

To change your current environment back to the default ``base``::

   conda activate

.. tip::
    When the environment is deactivated, its name is no longer shown in your prompt, and the asterisk (*) returns to ``base``. To verify, you can repeat the  ``conda info --envs`` command.

Installing packages
===================

You can also install packages into a previously created environment. To do this, you first need to activate the environment. This changes the environment shown in your shell from ``(base)`` to the name of the environment. **Don’t install packages into your base environment.**::

   conda activate myenvironment
   conda install matplotlib

For more information on searching for and installing packages, see :doc:`Managing packages <tasks/manage-pkgs>`.

Specifying channels
===================

Channels are locations (on your own computer or elsewhere on the Internet) where packages are stored. By default, conda searches for packages in its :ref:`default channels <default-channels>`.

If a package you want is somewhere else, such as conda-forge, you can manually specify the channel when installing the package::

   conda activate myenvironment
   conda install conda-forge::numpy

You can also override the default channels in your `.condarc` file. For a direct example, see :ref:`Channel locations (channels) <config-channels>` or read the entire :doc:`Using the .condarc conda configuration file <configuration/use-condarc>`.

Updating conda
==============

To see your conda version, use the following command::

   conda --version

No matter where in you run this command, conda displays the number of the version that you have installed::

   conda 23.10.0

.. note::
   If you get an error message ``command not found: conda``, close and reopen
   your terminal window and verify that you are logged
   into the same user account that you used to install Anaconda or Miniconda.

To update conda to the current version::

   conda activate
   conda update conda

Conda compares your version to the latest available version and then displays what is available to install.

If a newer version of conda is available, type ``y`` and press Enter to update::

   Proceed ([y]/n)? y

.. tip::
   We recommend that you always keep conda updated to the latest version.

More information
================

* :doc:`Conda cheat sheet <cheatsheet>`
* `Full documentation <https://conda.io/docs/>_`
* `Free community support <https://groups.google.com/a/anaconda.com/forum/#!forum/anaconda>`_
