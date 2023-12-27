===================
Installing on Linux
===================

#. Download the installer:

   * `Miniconda installer for Linux <https://docs.conda.io/en/latest/miniconda.html#linux-installers>`_.

   * `Anaconda Distribution installer for Linux <https://www.anaconda.com/download/>`_.

   * `Miniforge installer for Linux <https://github.com/conda-forge/miniforge/>`_.

#. :ref:`Verify your installer hashes <hash-verification>`.

#. In your terminal window, run:

   .. code::

      bash <conda-installer-name>-latest-Linux-x86_64.sh

   ``conda-installer-name`` will be one of "Miniconda3", "Anaconda", or "Miniforge3".

#. Follow the prompts on the installer screens. If you are unsure about any setting, accept the defaults. You
   can change them later.

#. To make the changes take effect, close and then re-open your
   terminal window.

#.  Test your installation. In your terminal window, run the command ``conda list``.
    A list of installed packages appears if it has been installed correctly.


.. _install-linux-silent:

Using with fish shell
=====================

To use conda with fish shell, run the following in your terminal:

Add conda binary to $PATH, if not yet added::

      fish_add_path <conda-install-location>/condabin


Configure fish-shell::

      conda init fish

Installing in silent mode
=========================

See the instructions for
:ref:`installing in silent mode on macOS <install-macos-silent>`.


Updating conda
==============

#. Open a terminal window.

#. Run ``conda update conda``.


Uninstalling conda
==================

#. Open a terminal window.

#. Remove the entire conda install directory with (*this may differ*
   *depending on your installation location*) ::

     rm -rf ~/conda

#. *Optional*: run ``conda init --reverse --all`` to undo changes to shell initialization scripts

#. *Optional*: remove the following hidden file and folders that
   may have been created in the home directory:

   * ``.condarc`` file
   * ``.conda`` directory
   * ``.continuum`` directory

   By running::

     rm -rf ~/.condarc ~/.conda ~/.continuum
