===================
Installing on Linux
===================

#. Download the installer:

   * `Miniconda installer for Linux <https://conda.io/miniconda.html>`_.

   * `Anaconda installer for Linux <https://www.anaconda.com/download/>`_.

#. In your Terminal window, run:

   * Miniconda:

     .. code::

        bash Miniconda3-latest-Linux-x86_64.sh

   * Anaconda:

     .. code::

        bash Anaconda-latest-Linux-x86_64.sh

#. Follow the prompts on the installer screens.

   If you are unsure about any setting, accept the defaults. You
   can change them later.

#. To make the changes take effect, close and then re-open your
   Terminal window.

#. :doc:`Test your installation <test-installation>`.


.. _install-linux-silent:

Installing in silent mode
=========================

See the instructions for
:ref:`installing in silent mode on macOS <install-macos-silent>`.


Updating Anaconda or Miniconda
==============================

#. Open a Terminal window.

#. Run ``conda update conda``.


Uninstalling Anaconda or Miniconda
==================================

#. Open a Terminal window.

#. Remove the entire miniconda install directory with::

     rm -rf ~/miniconda

#. OPTIONAL: Edit ``~/.bash_profile`` to remove the Miniconda
   directory from your PATH environment variable.

#. OPTIONAL: Remove the following hidden file and folders that
   may have been created in the home directory:

   * ``.condarc`` file
   * ``.conda`` directory
   * ``.continuum`` directory

   By running::

     rm -rf ~/.condarc ~/.conda ~/.continuum
