=================================
Using Microsoft R Open with conda
=================================

.. contents::
   :local:
   :depth: 1

You can easily use conda to install the `Microsoft R Open (MRO)
<https://mran.revolutionanalytics.com/download/mro-for-mrs/>`_
distribution of the R language. The MRO R language package and
many more are available from the `Anaconda Cloud channel named
MRO <https://anaconda.org/mro/packages/>`_.


Supported operating systems
===========================

* 64-bit systems only for all operating systems---Windows, macOS
  and Linux.
* Windows 7.0 SP1, Windows 8.1, Windows 10, Windows Server 2008
  R2 SP1 and Windows Server 2012.
* macOS---Mavericks (10.9), Yosemite (10.10) and El Capitan
  (10.11).
* Linux---CentOS, Red Hat Enterprise Linux, Debian and Ubuntu.


Installing MRO and other R language packages
============================================

You can install MRO and other R language packages several ways:

* Add the MRO channel to your :doc:`.condarc configuration file
  <../configuration/use-condarc>` above the R
  channel, and then use ``conda install r``. Use conda to install
  other packages.

* Specify the MRO channel on the command line each time you use
  the ``conda install`` command: ``conda install -c mro r``.

* Install R packages from the Comprehensive R Archive Network
  (CRAN) or the Microsoft R Application Network (MRAN). These R
  packages install into the currently active conda environment.
  MRO includes the `checkpoint package
  <https://github.com/RevolutionAnalytics/checkpoint/>`_, which
  installs from MRAN and is designed to offer enhanced
  `reproducibility
  <https://mran.revolutionanalytics.com/documents/rro/reproducibility/>`_.
  

Using MRO or R language packages
================================

To use MRO or R language packages, first activate the conda
environment where they are installed to set your environment
variables properly.

NOTE: Errors may result if you try to execute a program at the
path name in that environment without first activating the
environment.

Each conda environment may have packages installed from the
channel "r" or the channel "mro," but no conda environment should
contain packages from both channels. Doing so may result in
errors.

Handle these errors in one of the following ways:

* Use the command ``conda remove`` to remove the packages that
  were installed incorrectly.

* Create a new environment, and then install the correct packages
  there.


Installing the Intel Math Kernel Library (MKL) with MRO
=======================================================

The Intel Math Kernel Library (MKL) extensions are available for
MRO on Windows and Linux, while the Accelerate library is used
instead on macOS.

To install MKL, `download the MKL package for your platform
<https://mran.revolutionanalytics.com/download/>`_, and then
install it according to the instructions below for
:ref:`Windows <win-mkl>` or :ref:`Linux <linux-mkl>`.

NOTE: By using our install process, you are certifying that you
have agreed to the `MKL license
<https://mran.revolutionanalytics.com/assets/text/mkl-eula.txt>`_.
Proceeding further is an implicit agreement to this license.

* When MKL is not installed, each time the R interpreter starts
  it displays a message such as::

    No performance acceleration libraries were detected.
    To take advantage of the available processing power,
    also install MKL for MRO 3.2.3. Visit
    http://go.microsoft.com/fwlink/?LinkID=698301 for more details.

* When the MKL extensions are properly installed, each time the R
  interpreter starts it displays a message such as::

    Multithreaded BLAS/LAPACK libraries detected.

  NOTE: BLAS/LAPACK libraries such as MKL are implementations of
  the Basic Linear Algebra Subprograms specification of the
  LAPACK Linear Algebra PACKage.


.. _win-mkl:

Installing Windows MKL
----------------------

#. Download the proper MKL installer file.

#. Find the directory where the R language is located. It is a
   directory called ``R`` in one of the following locations:

   * The current user's home directory.

   * The ``Anaconda`` or ``Miniconda`` directory.

   * The ``environments`` directory.

   * The directory for the current environment.

   EXAMPLE: An Anaconda user on Windows 8 with the user name
   ``jsmith`` and an environment named ``my_r_env`` might find
   ``C:\Users\jsmith\Anaconda\envs\my_r_env\R``.

#. Run the installer.

#. When prompted to "Enter a path to MRO," enter the path.

Starting the R language interpreter now displays the message
showing that MKL is enabled.

If you wish to uninstall MKL on Windows and continue using the R
language, uninstall MKL from the Windows Control Panel.


.. _linux-mkl:

Installing Linux MKL
--------------------

#. Download and extract the proper MKL package to a temporary
   folder with a name such as ``$REVOMATH``.

#. Find the ``R`` directory. The path has the form:
   ``/path/to/anaconda/envs/<r environment>``.

   In the remaining steps, the path to the ``R`` directory is
   represented by $PREFIX.

#. Ensure that you have write permissions to $PREFIX.

#. Make backups of ``$PREFIX/lib/R/lib/libRblas.so`` and
   ``$PREFIX/lib/R/lib/libRlapack.so``.

#. Copy all of the ``.so`` files from ``$REVOMATH/mkl/libs/*.so``
   to ``$PREFIX/lib/R/lib``. This may prompt you to overwrite
   ``libRblas.so`` and ``libRlapack.so``.

#. Edit ``$PREFIX/lib/R/etc/Rprofile.site`` to add the following
   2 lines to the top::

     Sys.setenv("MKL_INTERFACE_LAYER"="GNU,LP64")
     Sys.setenv("MKL_THREADING_LAYER"="GNU")

#. Run this command::

     R CMD INSTALL $REVOMATH/RevoUtilsMath.tar.gz


More information
================

For community help on using conda with MRO, join the `conda
<https://groups.google.com/a/anaconda.com/forum/#!forum/conda>`_
email group.
