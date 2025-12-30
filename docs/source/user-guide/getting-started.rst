==========================
Getting started with conda
==========================

Conda is a powerful command line tool for package and environment management that runs on Windows, macOS, and Linux.

This guide to getting started with conda goes over the basics of starting up and using conda to create environments and install packages.

.. tip::

   Anaconda Navigator is a graphical desktop application that enables you to use conda without having to run commands at the command line.

   See `Getting started with Anaconda Navigator <https://docs.anaconda.com/navigator/getting-started/>`__ to learn more.

Before you start
================

To bootstrap a ``conda`` installation, use a minimal installer such as `Miniconda <https://docs.anaconda.com/miniconda/>`__ or `Miniforge <https://conda-forge.org/download>`__.

Conda is also included in the `Anaconda Distribution <https://docs.anaconda.com/anaconda/install/>`_.

.. note::

    Miniconda and Anaconda Distribution come preconfigured to use the `Anaconda
    Repository <https://repo.anaconda.com/>`__ and installing/using packages
    from that repository is governed by the `Anaconda Terms of Service
    <https://www.anaconda.com/terms-of-service>`__, which means that it *might*
    require a commercial fee license. There are exceptions for individuals,
    universities and companies with fewer than 200 employees (as of September
    2024).

    Please review the `terms of service <https://www.anaconda.com/terms-of-service>`__, Anaconda's most recent `Update on Anaconda’s Terms of Service for Academia
    and Research <https://www.anaconda.com/blog/update-on-anacondas-terms-of-service-for-academia-and-research>`__,
    and the `Anaconda Terms of Service FAQ
    <https://www.anaconda.com/pricing/terms-of-service-faqs>`__ to answer your questions.

Starting conda
==============

Conda is available on Windows, macOS, or Linux and can be used with any terminal application (or shell).

.. tab-set::

   .. tab-item:: Windows

      #. Open either the Anaconda or Miniforge Command Prompt (cmd.exe). A PowerShell prompt is also available with Anaconda Distribution or Miniconda.

   .. tab-item:: macOS

      #. Open Launchpad.
      #. Open the Other application folder.
      #. Open the Terminal application.

   .. tab-item:: Linux

      Open a terminal window.

Creating environments
=====================

Conda allows you to create separate environments, each containing their own files, packages, and package dependencies. The contents of each environment do not interact with each other.

The most basic way to create a new environment is with the following command::

   conda create --name <env-name>

To add packages while creating an environment, specify them after the environment name::

   conda create --name myenvironment python numpy pandas

For more information on working with environments, see :doc:`Managing environments <tasks/manage-environments>`.

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

To change your current environment back to the default one::

   conda activate

.. tip::
    When the environment is deactivated, its name is no longer shown in your prompt,
    and the asterisk (*) returns to the default env. To verify, you can repeat the
    ``conda info --envs`` command.

Installing packages
===================

You can also install packages into a previously created environment. To do this, you can either activate the environment you want to modify or specify the environment name on the command line::

   # via environment activation
   conda activate myenvironment
   conda install matplotlib

   # via command line option
   conda install --name myenvironment matplotlib

For more information on searching for and installing packages, see :doc:`Managing packages <tasks/manage-pkgs>`.

Specifying channels
===================

Channels are locations (on your own computer or elsewhere on the Internet) where packages are stored. By default, conda searches for packages in its :ref:`default channels <default-channels>`.

If a package you want is located in another channel, such as conda-forge, you can manually specify the channel when installing the package::

   conda install conda-forge::numpy

You can also override the default channels in your `.condarc` file. For a direct example, see :ref:`Channel locations (channels) <config-channels>` or read the entire :doc:`Using the .condarc conda configuration file <configuration/use-condarc>`.

.. tip::

   Find more packages and channels by searching `Anaconda.org <https://www.anaconda.org>`_.

Updating conda
==============

To see your conda version, use the following command::

   conda --version

No matter which environment you run this command in, conda displays its current version:

.. parsed-literal::

   conda |version|

.. note::
   If you get an error message ``command not found: conda``, close and reopen
   your terminal window and verify that you are logged
   into the same user account that you used to install conda.

First, change your current environment back to the default one::

   conda activate

Then update conda to the latest version::

   conda update conda

Conda compares your version to the latest available version and then displays what is available to install.

.. tip::
   We recommend that you always keep conda updated to the latest version.
   For conda's official version support policy, see `CEP 10 <https://github.com/conda-incubator/ceps/blob/main/cep-10.md>`_.

More information
================

* :doc:`Conda cheat sheet <cheatsheet>`
* `Full documentation <https://conda.io/docs/>`_
* `Free community support <https://docs.conda.io/en/latest/help-support.html>`_
