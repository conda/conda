==============
Managing conda
==============

Verifying that conda is installed
=================================

To verify that conda is installed, in your terminal window, run:

.. code::

   conda --version

Conda responds with the version number that you have installed,
such as ``conda 4.12.0``.

If you get an error message, make sure of the following:

* You are logged into the same user account that you used to
  install Anaconda or Miniconda.

* You are in a directory that Anaconda or Miniconda can find.

* You have closed and re-opened the terminal window after
  installing conda.


Determining your conda version
==============================

In addition to the ``conda --version`` command explained above,
you can determine what conda version is installed by running
one of the following commands in your terminal window:

.. code-block:: bash

   conda info

OR

.. code-block:: bash

   conda -V


Updating conda to the current version
=====================================

To update conda, in your terminal window, run:

.. code-block:: bash

   conda self update

This updates conda and its dependencies in the ``base`` environment.
To preview the changes without applying them, add ``--dry-run``.
To update every package in ``base`` (not just conda), run:

.. code-block:: bash

   conda self update --all

.. note::

   If ``conda self`` is not available (for example, on an older conda
   installation), update conda with:

   .. code-block:: bash

      conda update --name base conda

Conda compares versions and reports what is available to install.
It also tells you about other packages that will be automatically
updated or changed with the update. If conda reports that a newer
version is available, type ``y`` to update:

.. code::

   Proceed ([y]/n)? y


When to use ``conda self``
--------------------------

``conda self`` manages the conda installation in your ``base`` environment:
conda itself and (with ``--all``) the other packages in ``base``.
It always operates on ``base``, no matter which environment is active, and it
also works when ``base`` is protected (see :ref:`frozen-env`).

Use ``conda update`` and ``conda install`` for packages in all your other
environments.

.. note::

   ``conda self`` runs ``conda install --override-frozen`` on ``base`` for you.
   On an unprotected ``base``, ``conda update`` and ``conda self update`` both
   operate on the same environment. Once ``base`` is protected, ``conda update``
   is blocked and ``conda self`` is the way to make changes.

For details on all ``conda self`` subcommands (``install``, ``remove``,
``update``, and ``reset``), see the
`conda-self documentation <https://conda.github.io/conda-self/>`_,
in particular the `quickstart <https://conda.github.io/conda-self/quickstart/>`_
and the `CLI reference <https://conda.github.io/conda-self/reference/cli/>`_.


Suppressing warning message about updating conda
================================================

To suppress the following warning message when you do not want
to update conda to the latest version:

.. code-block::

    ==> WARNING: A newer version of conda exists. <==
    current version: 4.6.13
    latest version: 4.8.0

Update conda by running: ``conda self update`` (or, if ``conda self`` is
not available, ``conda update --name base conda``)

Run the following command from your terminal:
``conda config --set notify_outdated_conda false``

Or add the following line in your ``.condarc`` file:
``notify_outdated_conda: false``
