===============
Managing Python
===============

.. contents::
   :local:
   :depth: 1


Conda treats Python the same as any other package, so it is easy
to manage and update multiple installations.

Anaconda supports Python 2.7, 3.4, 3.5 and 3.6. The default is Python
2.7 or 3.6, depending on which installer you used:

* For the installers "Anaconda" and "Miniconda," the default is
  2.7.

* For the installers "Anaconda3" or "Miniconda3," the default is
  3.6.


Viewing a list of available Python versions
===========================================

To list the versions of Python that are available to install,
in your Terminal window or an Anaconda Prompt, run:

.. code::

   conda search python

This lists all packages whose names contain the text ``python``.

To list only the packages whose full name is exactly ``python``,
add the ``--full-name`` option. In your Terminal window or an Anaconda Prompt,
run:

.. code::

   conda search --full-name python


Installing a different version of Python
=========================================

To install a different version of Python without overwriting the
current version, create a new environment and install the second
Python version into it:

#. Create the new environment:

   * To create the new environment for Python 3.6, in your Terminal
     window or an Anaconda Prompt, run:

     .. code-block:: bash

        conda create -n py36 python=3.6 anaconda

     NOTE: Replace ``py36`` with the name of the environment you
     want to create. ``anaconda`` is the metapackage that
     includes all of the Python packages comprising the Anaconda
     distribution. ``python=3.6`` is the package and version you
     want to install in this new environment. This could be any
     package, such as ``numpy=1.7``, or :ref:`multiple packages
     <installing multiple packages>`.

   * To create the new environment for Python 2.7, in your Terminal window
     or an Anaconda Prompt, run:

     .. code-block:: bash

        conda create -n py27 python=2.7 anaconda

#. :ref:`Activate the new environment <activate-env>`.

#. Verify that the new environment is your :ref:`current
   environment <determine-current-env>`.

#. To verify that the current environment uses the new Python
   version, in your Terminal window or an Anaconda Prompt, run:

   .. code::

      python --version


Using a different version of Python
====================================

To switch to an environment that has different version of Python,
:ref:`activate the environment <activate-env>`.


Updating or upgrading Python
=============================

Use the Terminal or an Anaconda Prompt for the following steps.

If you are in an environment with Python version 3.4.2, the
following command updates Python to the latest
version in the 3.4 branch:

.. code-block:: bash

    conda update python

The following command upgrades Python to another
branch---3.6---by installing that version of Python:

.. code-block:: bash

    conda install python=3.6
