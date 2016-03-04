======================
Using Microsoft R Open
======================

You can install `Microsoft R Open (MRO) <https://mran.revolutionanalytics.com/download/mro-for-mrs/>`_ with conda on 64-bit Windows, 64-bit OS X, and 64-bit Linux, from the Anaconda.org channel "mro". The supported Windows versions are Windows® 7.0 (SP1), 8.1, 10, and Windows Server® 2008 R2 (SP1) and 2012, and the supported OS X versions are Mavericks (10.9), Yosemite (10.10), and El Capitan (10.11). Microsoft R Open is supported on all the same versions of Linux as Anaconda, including CentOS, Red Hat Enterprise Linux, Debian, and Ubuntu.

There are two ways to install MRO and other R packages. The first is to add the "mro" channel to your :doc:`.condarc configuration file<config>` above the "r" channel, and then use ``conda install r`` and use conda to install other packages. The second is to specify the "mro" channel on the command line each time you use the conda install command: ``conda install -c mro r``

If you use OS X, find the R directory and set the R_HOME environment variable to its path. Look in your home directory, then in your Anaconda or Miniconda directory, then in the environments directory, then in the directory for your current environment, and then in the "lib" directory. For example, if you use Anaconda and your current environment is named my_r_env, you might use this command: ``export R_HOME=~/Anaconda/envs/my_r_env/lib/R``

In addition to installing R packages from conda channels, it is possible to install R packages from the Comprehensive R Archive Network (CRAN) or the Microsoft R Application Network (MRAN). These R packages will install into the currently active conda environment. MRO includes the `checkpoint package <https://github.com/RevolutionAnalytics/checkpoint/>`_, which installs from MRAN and is designed to offer enhanced `reproducibility <https://mran.revolutionanalytics.com/documents/rro/reproducibility/>`_.

To use MRO or R packages, activate the conda environment where they are installed to set your environment variables properly. Executing the programs at the pathname in that environment without activating the environment may result in errors.

Each conda environment may have packages installed from the channel "r" or the channel "mro", but no conda environment should contain packages from both channels, which may result in errors. If this occurs, you may use ``conda remove`` to remove the packages that were installed incorrectly, or create a new environment and install the correct packages there.

Installing the Intel Math Kernel Library (MKL) with Microsoft R Open
====================================================================

The Intel Math Kernel Library (MKL) extensions are also available for MRO on Windows and Linux, while the Accelerate library is used instead on OS X. Just `download the MKL package for your platform <https://mran.revolutionanalytics.com/download/>`_ and install it according to the instructions below.

NOTE: By using our install process, we assume that you have already agreed to the `MKL license <https://mran.revolutionanalytics.com/assets/text/mkl-eula.txt>`_. Proceeding further is an implicit agreement to said license.

When MKL is not installed, each time the R interpreter starts it will display a message saying so, such as::

  No performance acceleration libraries were detected. To take advantage of the 
  available processing power, also install MKL for MRO 3.2.3. Visit 
  http://go.microsoft.com/fwlink/?LinkID=698301 for more details.

When the MKL extensions are properly installed, each time the R interpreter starts it will display a message stating that MKL is enabled, such as::

  Multithreaded BLAS/LAPACK libraries detected.

(BLAS/LAPACK libraries such as MKL are implementations of the Basic Linear Algebra Subprograms specification of the LAPACK Linear Algebra PACKage.)

MKL installation on Windows
---------------------------

1. Download the proper MKL installer file.
2. Find the directory where R is located. Look in the current user's home directory, then in the Anaconda or Miniconda directory, then in the environments directory, and then in the directory for the current environment, for a directory called "R". For example, an Anaconda user on Windows 8 with the username jsmith and an environment named my_r_env might find ``C:\Users\jsmith\Anaconda\envs\my_r_env\R`` .
3. Run the installer, and enter the path when it says "Enter a path to MRO".

Starting the R interpreter should now display the message showing that MKL is enabled.

If you wish to uninstall MKL on Windows and continue using R, uninstall MKL with the Windows Control Panel.

MKL installation on Linux
-------------------------

1. Download and extract the proper MKL package to a temporary folder, which we will call $REVOMATH .
2. Determine where R is located. The path will have the form of ``/path/to/anaconda/envs/<r environment>`` , which we will call $PREFIX . Ensure that you have write permissions to $PREFIX.
3. Make backups of ``$PREFIX/lib/R/lib/libRblas.so`` and ``$PREFIX/lib/R/lib/libRlapack.so`` .
4. Copy all the .so files from ``$REVOMATH/mkl/libs/*.so`` to ``$PREFIX/lib/R/lib`` . (This may prompt you to overwrite libRblas.so and libRlapack.so.)
5. Edit ``$PREFIX/R/etc/Rprofile.site`` and add the following two lines to the top::

     Sys.setenv("MKL_INTERFACE_LAYER"="GNU,LP64")
     Sys.setenv("MKL_THREADING_LAYER"="GNU")

6. Execute this: ``R CMD INSTALL $REVOMATH/RevoUtilsMath.tar.gz``
