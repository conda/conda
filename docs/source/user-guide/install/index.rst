============
Installation
============

.. contents::
   :local:
   :depth: 1

The fastest way to obtain conda is to install
:ref:`Miniconda <miniconda-glossary>`, a mini version of
:ref:`Anaconda <anaconda-glossary>` that includes only conda and
its dependencies. If you prefer to have conda plus over 720 open
source packages, install Anaconda.

We recommend you install Anaconda for the local user, which does
not require administrator permissions and is the most robust
type of installation. You can also install Anaconda system wide,
which does require administrator permissions.

TIP: For information on using our graphical installers for
Windows or macOS, see the instructions for
`installing Anaconda <http://docs.continuum.io/anaconda/install.html>`_.


System requirements
===================

* 32- or 64-bit computer.

* For Miniconda---400 MB disk space.

* For Anaconda---Minimum 3 GB disk space to download and install.


* Windows, macOS or Linux.

* Python 2.7, 3.4, 3.5 or 3.6.
* pycosat.
* PyYaml.
* Requests.

NOTE: You do not need administrative or root permissions to
install Anaconda if you select a user-writable install location.


Installing in silent mode
=========================

You can use :ref:`silent installation <silent-mode-glossary>` of
Miniconda or Anaconda for deployment or testing or building
services such as Travis CI and AppVeyor.

Follow the silent-mode instructions for your operating system:

* :ref:`Windows <install-win-silent>`.
* :ref:`macOS <install-macos-silent>`.
* :ref:`Linux <install-linux-silent>`.


Installing conda on a system that has other Python installations or packages
============================================================================

You do not need to uninstall other Python installations or
packages in order to use conda. Even if you already have a
system Python, another Python installation from a source such as
the macOS Homebrew package manager and globally installed
packages from pip such as pandas and NumPy, you do not need to
uninstall, remove, or change any of them before using conda.

Install Anaconda or Miniconda normally, and let the installer
add the conda installation of Python to your PATH environment
variable. There is no need to set the PYTHONPATH environment
variable.

To see if the conda installation of Python is in your PATH
variable, run one of the following commands:

* macOS and Linux---``echo $PATH``.

* Windows---``echo %PATH%``.

To see which Python installation is currently set as the default,
run one of the following commands:

* macOS and Linux---``which python``.

* Windows---``where python``.

To see which packages are installed in your current conda
environment and their version numbers, run ``conda list``.

.. toctree::
   :maxdepth: 1
   :hidden:

   download
   windows
   macos
   linux
   test-installation
