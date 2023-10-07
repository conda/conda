==========================
Getting started with conda
==========================

.. _navigator-starting:

Conda is a powerful command line package and environment management tool that runs on Windows, macOS, and Linux.

This 20-minute guide to getting started with conda lets you try out
the major features of conda. You should understand the basics of how conda works when you finish this guide.

.. tip::
   
   Anaconda Navigator is a graphical desktop application that enables you to
   use conda without having to enter commands into the command line.
   See `Getting started with Anaconda Navigator <https://docs.anaconda.com/anaconda/navigator/getting-started>`_ 
   to learn more and see which approach to using conda you prefer.

Before you start
================

You should have already installed conda before beginning this getting 
started guide. Conda can be found in many distributions, like 
`Anaconda Distribution <https://docs.anaconda.com/anaconda/install/>`_ 
or `Miniconda <https://docs.conda.io/projects/miniconda/en/latest/>`_.

Contents
========

 - :ref:`Starting conda <starting-conda>` on Windows, macOS, or Linux. 2 MINUTES

 - :ref:`Managing conda <managing-conda>`. Verify that Anaconda is installed and check that conda is updated to the current version. 3 MINUTES

 - :ref:`Managing environments <managing-envs>`. Create :doc:`environments <../user-guide/concepts/environments>` and move easily between them.  5 MINUTES

 - :ref:`Managing Python <managing-python>`. Create an environment that has a different version of Python. 5 MINUTES

 - :ref:`Managing packages <managing-pkgs>`. Find packages available for you to install. Install packages. 5 MINUTES

TOTAL TIME: 20 MINUTES

.. _starting-conda:

Starting conda
==============

Conda is available on Windows, macOS, or Linux. Conda can be used with any terminal application in MacOS/Linux, while in Windows, we recommend using the Anaconda Prompt application provided by the Anaconda Distribution or Miniconda installations.

.. tab-set::

   .. tab-item:: Windows

      #. From the Start menu, search for "Anaconda Prompt".
      #. Open the Anaconda Prompt desktop app that appears in the search sidebar.

   .. tab-item:: MacOS

      #. Open Launchpad.
      #. Open the Other application folder.
      #. Open the Terminal application.
      
      iTerm2 can also be used with conda on macOS.

   .. tab-item:: Linux

      Open a terminal window.

.. _managing-conda:

Managing conda
===============

Verifying your installation
---------------------------

Verify that conda is installed and running on your system:

 .. code::

    conda --version

No matter where in you run this command from, conda displays the number of the version that you have installed.

.. code::

   conda 23.9.0

.. note::
   If you get an error message “command not found: conda”, close and reopen 
   your terminal window and verify that you are logged 
   into the same user account that you used to install Anaconda or Miniconda.

Updating your conda version
---------------------------

To update conda to the current version:

 .. code::

     conda activate
     conda update conda

Conda compares your version to the latest available version and then displays what is available to install.

If a newer version of conda is available, type ``y`` and press Enter to update:

 .. code::

    Proceed ([y]/n)? y

.. tip::
   We recommend that you always keep conda updated to the latest version.

.. _managing-envs:

Managing environments
=====================

Conda allows you to create separate environments, each containing their own files, packages,
and package dependencies. The contents of each environment do not interact with one another.

When you begin using conda, you already have a default environment named
``base``. **Don't install programs into your base environment.** Instead,
create separate environments for each project to keep your programs isolated from each other.

#. Create a new environment and install a package in it.

   We will name the environment ``snowflakes`` and install the package
   BioPython:

   .. code::

      conda create --name snowflakes biopython

   Conda checks to see what additional packages
   BioPython will need to run (BioPython's dependencies) and lists them for you.
   Type ``y`` and press Enter to proceed:

   .. code::

      Proceed ([y]/n)? y

#. To use, or "activate" the new environment:

   .. code::

      conda activate snowflakes

   Now that you are in your ``snowflakes`` environment, any conda
   commands you type will use and affect that environment until
   you deactivate it.

#. To see a list of all your environments:

   .. code::

      conda info --envs

   A list of environments appears, similar to the following:

   .. code::

      conda environments:

          base           /home/username/Anaconda3
          snowflakes   * /home/username/Anaconda3/envs/snowflakes

   .. tip::
      The active environment is the one with an asterisk (*).

   The active environment is also displayed in front of your prompt in
   (parentheses) or [brackets] like this:

   .. code::

     (snowflakes) $

#. Change your current environment back to the default ``base``:

   .. code::
      
      conda activate

   .. tip::
      When the environment is deactivated, its name is no
      longer shown in your prompt, and the asterisk (*) returns to ``base``.
      To verify, you can repeat the  ``conda info --envs`` command.

For more information on managing environments, see :doc:`<tasks/manage-environments>`.

.. _managing-python:

Managing Python
===============

When you create a new environment, conda installs the same Python version you
used when you downloaded and installed Anaconda. If you want to use a different
version of Python—for example, Python 3.9—simply create a new environment and
specify the version of Python that you want.

#. Create a new environment named ``snakes`` that contains Python 3.9:

   .. code::

      conda create --name snakes python=3.9

   When conda asks if you want to proceed, type ``y`` and press Enter.

#. Activate the new environment:

   .. code::

      conda activate snakes

#. Verify which version of Python is in your current
   environment:

   .. code::

      python --version

.. _managing-pkgs:

Managing packages
=================

In this section, you check which packages you have installed,
check which are available and look for a specific package and
install it.

#. To find a package you have already installed, first activate the environment
   you want to search. Look above for the commands to
   :ref:`activate your snakes environment <managing-envs>`.

#. Check to see if a package you have not installed named
   ``beautifulsoup4`` is available from the Anaconda repository
   (must be connected to the Internet):

   .. code::

      conda search beautifulsoup4

   Conda displays a list of all packages with that name on the Anaconda
   repository, so we know it is available.

#. Install this package into the current environment:

   .. code::

      conda install beautifulsoup4

#. Check to see if the newly installed program is in this environment:

   .. code::

      conda list

For more information on searching for and installing packages, see :doc:`<tasks/manage-pkgs>`.

More information
================

* :doc:`Conda cheat sheet <cheatsheet>`
* Full documentation--- https://conda.io/docs/
* Free community support--- https://groups.google.com/a/anaconda.com/forum/#!forum/anaconda
* Paid support options--- https://www.anaconda.com/support/
