===================
Installing on macOS
===================

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

.. note::
   These instructions are also written for Linux.

To run the :ref:`silent installation <silent-mode-glossary>` of
Miniconda for macOS or Linux, specify the -b and -p arguments of
the bash installer. The following arguments are supported:

* ``-b`` --- Batch mode with no PATH modifications to ``~/.bashrc``.
  Assumes that you agree to the license agreement. Does not edit
  the ``.bashrc`` or ``.bash_profile`` files.
* ``-p <prefix>`` --- Installation prefix/path.
* ``-f`` --- Force installation even if prefix ``-p`` already exists.

EXAMPLE:

.. code-block:: bash

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O /tmp/install_miniconda.sh
    bash /tmp/install_miniconda.sh -b -p $~/miniconda

    # You may want to put *only* the conda binary on your $PATH.
    ln -s ~/miniconda/bin/conda ~/.local/bin/

The installer prompts “Do you wish the installer to initialize Miniconda3 by running ``conda init``?” We recommend “yes” if you want it to modify
``~/.bashrc``.

.. note::
   If you enter “no”, then conda will not modify your login shell scripts
   (``~/.bashrc``, ``~/.bash_profile``) at all. In order to initialize after
   the installation process is done, first run
   ``source <path to conda>/bin/activate`` and then run ``conda init``.

.. note::
   If you want to control when ``conda`` affects your shell environment, you
   can also add the following ``bash`` function to your ``~/.bashrc``:

   .. code-block:: bash

      conda-setup() {
          # This assumes conda is on your PATH, and bash is your primary shell.
          eval "$(conda shell.bash hook)"
      }

    Then you can drop into the conda environment calling ``conda-setup``.

**MacOS Catalina**

If you are on macOS Catalina, the new default shell is zsh. You will instead need to run ``source <path to conda>/bin/activate`` followed by ``conda init zsh``.

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
