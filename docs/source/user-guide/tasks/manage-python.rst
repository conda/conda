===============
Managing Python
===============

Conda treats Python the same as any other package, so it is easy
to manage and update multiple installations.

Conda supports Python 3.8, 3.9, 3.10, and 3.11.

Viewing a list of available Python versions
===========================================

To list the versions of Python that are available to install,
in your terminal window or an Anaconda Prompt, run:

.. code::

   conda search python

This lists all packages whose names contain the text ``python``.

To list only the packages whose full name is exactly ``python``,
add the ``--full-name`` option. In your terminal window or an Anaconda Prompt,
run:

.. code::

   conda search --full-name python


Installing a different version of Python
=========================================

To install a different version of Python without overwriting the
current version, create a new environment and install the second
Python version into it:

#. Create the new environment:

   * To create the new environment for Python 3.9, in your terminal
     window or an Anaconda Prompt, run:

     .. code-block:: bash

        conda create -n py39 python=3.9 anaconda

     .. note::
        Replace ``py39`` with the name of the environment you
        want to create. ``anaconda`` is the metapackage that
        includes all of the Python packages comprising the Anaconda
        distribution. ``python=3.9`` is the package and version you
        want to install in this new environment. This could be any
        package, such as ``numpy=1.19``, or :ref:`multiple packages
        <installing multiple packages>`.

#. :ref:`Activate the new environment <activate-env>`.

#. Verify that the new environment is your :ref:`current
   environment <determine-current-env>`.

#. To verify that the current environment uses the new Python
   version, in your terminal window or an Anaconda Prompt, run:

   .. code::

      python --version

Installing PyPy
===============

To use the PyPy builds you can do the following::

    conda config --add channels conda-forge
    conda config --set channel_priority strict
    conda create -n pypy pypy
    conda activate pypy


Using a different version of Python
====================================

To switch to an environment that has different version of Python,
:ref:`activate the environment <activate-env>`.


Updating or upgrading Python
=============================

Use the terminal or an Anaconda Prompt for the following steps.

If you are in an environment with Python version 3.4.2, the
following command updates Python to the latest
version in the 3.4 branch:

.. code-block:: bash

    conda update python

The following command upgrades Python to another
branch---3.8---by installing that version of Python. It is not recommended,
rather it is preferable to create a new environment. The resolver has to work
very hard to determine exactly which packages to upgrade. But it is possible,
and the command is:

.. code-block:: bash

    conda install python=3.8
