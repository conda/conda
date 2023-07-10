===================
Installing on macOS
===================

.. caution::
   If you use the .pkg installer for Miniconda, be aware that those installers may skip the which will cause the installation to fail. If the installer skips this page, click Change Install Location... on the Installation Type page and choose a location for your install, then click Continue.

#. Download the installer:

   * `Miniconda installer for macOS <https://conda.io/miniconda.html>`_.

   * `Anaconda installer for macOS <https://www.anaconda.com/download/>`_.

#. :ref:`Verify your installer hashes <hash-verification>`.

#. Install:

   * Miniconda---In your terminal window, run:

     .. code::

        bash Miniconda3-latest-MacOSX-x86_64.sh

   * Anaconda---Double-click the ``.pkg`` file.

#. Follow the prompts on the installer screens.

   If you are unsure about any setting, accept the defaults. You
   can change them later.

#. To make the changes take effect, close and then re-open your
   terminal window.

#. Test your installation. In your terminal window or
   Anaconda Prompt, run the command ``conda list``. A list of installed packages appears
   if it has been installed correctly.


.. _install-macos-silent:

Installing in silent mode
=========================

.. note::
   The following instructions are for Miniconda. For Anaconda,
   substitute ``Anaconda`` for ``Miniconda`` in all of the commands.

To run the :ref:`silent installation <silent-mode-glossary>` of
Miniconda for macOS or Linux, specify the -b and -p arguments of
the bash installer. The following arguments are supported:

* ``-b``: Batch mode with no PATH modifications to shell scripts.
  Assumes that you agree to the license agreement. Does not edit
  shell scripts such as ``.bashrc``, ``.bash_profile``, ``.zshrc``, etc.
* ``-p``: Installation prefix/path.
* ``-f``: Force installation even if prefix ``-p`` already exists.

EXAMPLE:

.. code-block:: bash

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda

The installer prompts “Do you wish the installer to initialize Miniconda3 by running ``conda init``?” We recommend “yes”.

.. note::
   If you enter “no”, then conda will not modify your shell scripts at all. In order to initialize after the installation process is done, first run ``source <path to conda>/bin/activate`` and then run ``conda init``.

   **macOS Catalina (and later)**

   If you are on macOS Catalina (or later versions), the default shell is zsh. You will instead need to run ``source <path to conda>/bin/activate`` followed by ``conda init zsh`` (to explicitly select the type of shell to initialize).

Updating Anaconda or Miniconda
==============================

#. Open a terminal window.

#. Navigate to the ``anaconda`` directory.

#. Run ``conda update conda``.


Uninstalling Anaconda or Miniconda
==================================

#. Open a terminal window.

#. Remove the entire Miniconda install directory with::

     rm -rf ~/miniconda

#. OPTIONAL: Edit ``~/.bash_profile`` to remove the Miniconda
   directory from your PATH environment variable.

#. Remove the following hidden file and folders that may have
   been created in the home directory:

   * ``.condarc`` file
   * ``.conda`` directory
   * ``.continuum`` directory

   By running::

     rm -rf ~/.condarc ~/.conda ~/.continuum
