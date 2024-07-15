===================
Installing on macOS
===================

.. caution::
    If you use the ``.pkg`` installer for Miniconda, beware that those installers may skip
    the "Destination Select" page which will cause the installation to fail. If the installer
    skips this page, click "Change Install Location..." on the "Installation Type" page,
    choose a location for your install, and then click Continue.

#. Download the installer:

   * `Miniconda installer for macOS <https://docs.anaconda.com/free/miniconda/>`_.

   * `Anaconda installer for macOS <https://www.anaconda.com/download/>`_.

   * `Miniforge installer for macOS <https://github.com/conda-forge/miniforge/>`_.

#. :ref:`Verify your installer hashes <hash-verification>`.

#. Install:

   * Miniconda or Miniforge: in your terminal window, run:

     .. code::

        bash <conda-installer-name>-latest-MacOSX-x86_64.sh

   * Anaconda Distribution: double-click the ``.pkg`` file.

#. Follow the prompts on the installer screens. If you are unsure about any setting, accept the defaults. You
   can change them later.

#. To make the changes take effect, close and then re-open your
   terminal window.

#. To verify your installation, in your terminal window, run the command ``conda list``.
   A list of installed packages appears if it has been installed correctly.


.. _install-macos-silent:

Installing in silent mode
=========================

.. note::
   The following instructions are for Miniconda but should also work
   for the Anaconda Distribution or Miniforge installers.

To run the :ref:`silent installation <silent-mode-glossary>` of
Miniconda for macOS or Linux, specify the -b and -p arguments of
the bash installer. The following arguments are supported:

* ``-b``: Batch mode with no PATH modifications to shell scripts.
  Assumes that you agree to the license agreement. Does not edit
  shell scripts such as ``.bashrc``, ``.bash_profile``, ``.zshrc``, etc.
* ``-p``: Installation prefix/path.
* ``-f``: Force installation even if prefix ``-p`` already exists.

**Example**

.. code-block:: bash

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda

.. note::
   In order to initialize after the installation process is done, first run
   ``source <path to conda>/bin/activate`` and then run ``conda init --all``.


Updating Anaconda or Miniconda
==============================

#. Open a terminal window.

#. Run ``conda update conda``.


Uninstalling Anaconda or Miniconda
==================================

#. Open a terminal window.

#. Remove the entire Miniconda install directory with (*this may differ*
   *depending on your installation location*) ::

     rm -rf ~/miniconda

#. *Optional*: run ``conda init --reverse --all`` to undo changes to shell initialization scripts

#. *Optional*: remove the following hidden file and folders that may have
   been created in the home directory:

   * ``.condarc`` file
   * ``.conda`` directory
   * ``.continuum`` directory

   By running::

     rm -rf ~/.condarc ~/.conda ~/.continuum
