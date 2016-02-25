==================
Using R with conda
==================

For Linux, OS X and Windows

If you have conda installed, you can easily install R and over 80 of the most used R packages for data science with one command. Conda helps you keep your packages and dependencies up to date. You can also easily create and share your own custom R packages.

R-Essentials works very much like Anaconda:

* Installs all of the most popular packages with all of their dependencies with one command: ``conda install -c r r-essentials``
* Update all of the packages and their dependencies with one command: ``conda update -c r r-essentials``
* Update a single package in R-Essentials (if a new version of  the package is available in the R channel) with the command ``conda update r-XXXX``

How to install "R Essentials"
=============================

1. `Download and install Anaconda <https://www.continuum.io/downloads>`_
2. Install the R Essentials package into the current environment: ``conda install -c r r-essentials``

Create and share your own custom R bundle
=========================================

Building and sharing your own custom R bundles with others is like building and sharing conda packages.

For example, create a simple custom R bundle meta-package named "Custom-R-Bundle" containing several popular programs and their dependencies with the command::

  conda metapackage custom-r-bundle 0.1.0 --dependencies r-irkernel jupyter r-ggplot2 r-dplyr --summary "My custom R bundle"

Now you can easily share your new meta-package with friends and colleagues by uploading it to your channel on `Anaconda Cloud <https://anaconda.org>`_::

  conda install anaconda-client
  anaconda login
  anaconda upload path/to/custom-r-bundle-0.1.0-0.tar.bz2

Your friends and colleagues now have access to your Custom-R-Bundle from any computer with the command::

  conda install -c <your anaconda.org username> custom-r-bundle

For more information, see Christine Doig's blog post `Jupyter and conda for R <https://www.continuum.io/blog/developer/jupyter-and-conda-r>`_.

Microsoft R Open
================

You can install `Microsoft R Open (MRO) <https://mran.revolutionanalytics.com/download/mro-for-mrs/>`_ with conda on 64-bit Windows, 64-bit OS X, and 64-bit Linux, from the Anaconda.org channel "mro".

There are two ways to install MRO and other R packages. The first is to add the "mro" channel to your :doc:`.condarc configuration file<config>` above the "r" channel, and then use ``conda install r`` and use conda to install other packages. The second is to specify the "mro" channel on the command line each time you use the conda install command: ``conda install -c mro r``

In addition to installing R packages from conda channels, it is possible to install R packages from the Comprehensive R Archive Network (CRAN) or the Microsoft R Application Network (MRAN). These R packages will install into the currently active conda environment. MRO includes the `checkpoint package <https://github.com/RevolutionAnalytics/checkpoint/>`_, which installs from MRAN and is designed to offer enhanced `reproducibility <https://mran.revolutionanalytics.com/documents/rro/reproducibility/>`_.

To use MRO or R packages, activate the conda environment where they are installed to set your environment variables properly. Executing the programs at the pathname in that environment without activating the environment may result in errors.

Each conda environment may have packages installed from the channel "r" or the channel "mro", but no conda environment should contain packages from both channels, which may result in errors. If this occurs, you may use ``conda remove`` to remove the packages that were installed incorrectly, or create a new environment and install the correct packages there.

Installing the Intel Math Kernel Library (MKL) with Microsoft R Open
====================================================================

The Intel Math Kernel Library (MKL) extensions are also available for MRO on Windows and Linux, while the Accelerate library is used instead on OS X. Just `download the MKL package for your platform <https://mran.revolutionanalytics.com/download/>`_ and install it according to the instructions.

NOTE: Installing the MKL package constitutes implicit agreement to the `MKL license <https://mran.revolutionanalytics.com/assets/text/mkl-eula.txt>`_.

When MKL is not installed, each time the R interpreter starts it will display a message saying so, such as "No performance acceleration libraries were detected. To take advantage of the available processing power, also install MKL for MRO 3.2.3. Visit http://go.microsoft.com/fwlink/?LinkID=698301 for more details." Once the MKL extensions are properly installed, each time the R interpreter starts it will display a message stating that MKL is enabled, such as "Multithreaded BLAS/LAPACK libraries detected." (BLAS/LAPACK libraries such as MKL are implementations of the Basic Linear Algebra Subprograms specification of the LAPACK Linear Algebra PACKage.)

MKL installation on Linux
-------------------------

1. Download and extract the proper MKL package to a temporary folder, which we will call $REVOMATH .

   NOTE: You must select the correct MKL package for your Linux distribution.

2. Determine where R is located. The path will have the form of ``/path/to/anaconda/envs/<r environment>`` , which we will call $PREFIX . Ensure that you have write permissions to $PREFIX.
3. Make backups of ``$PREFIX/R/lib/libRblas.so`` and ``$PREFIX/R/lib/libRlapack.so`` .
4. Copy all the .so files from ``$REVOMATH/mkl/libs/*.so`` to ``$PREFIX/R/lib`` . (This overwrites libRblas.so and libRlapack.so.)
5. Edit ``$PREFIX/R/etc/Rprofile.site`` and add the following two lines to the top::

     Sys.setenv("MKL_INTERFACE_LAYER"="GNU,LP64")
     Sys.setenv("MKL_THREADING_LAYER"="GNU")

6. Execute this: ``R CMD INSTALL $REVOMATH/RevoUtilsMath.tar.gz``


Next, let's take a look at :doc:`using/pkgs`.
