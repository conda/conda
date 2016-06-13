======================
Using Microsoft R Open
======================

You can easily install the `Microsoft R Open (MRO) <https://mran.revolutionanalytics.com/download/mro-for-mrs/>`_ distribution of the R language by using conda. The MRO R language package and many more are available from the `Anaconda Cloud channel named MRO <https://anaconda.org/mro/packages/>`_.

Operating systems supported 
---------------------------

* For 64-bit systems only (Windows, OS X and Linux)
* Windows: Windows® 7.0 (SP1), 8.1, 10, and Windows Server® 2008 R2 (SP1) and 2012
* OS X versions: Mavericks (10.9), Yosemite (10.10), and El Capitan (10.11)
* Linux: CentOS, Red Hat Enterprise Linux, Debian, Ubuntu. 

Installing MRO and other R language packages
--------------------------------------------

There are several different ways to install MRO and other R language packages: 

* Add the "mro" channel to your :doc:`.condarc configuration file<config>` above the "r" channel, and then use ``conda install r`` and use conda to install other packages. 
* Specify the "mro" channel on the command line each time you use the conda install command: ``conda install -c mro r``
* Install R packages from the Comprehensive R Archive Network (CRAN) or the Microsoft R Application Network (MRAN). These R packages will install into the currently active conda environment. MRO includes the `checkpoint package <https://github.com/RevolutionAnalytics/checkpoint/>`_, which installs from MRAN and is designed to offer enhanced `reproducibility <https://mran.revolutionanalytics.com/documents/rro/reproducibility/>`_.

Use MRO or R language packages
------------------------------

To use MRO or R language packages, first activate the conda environment where they are installed to set your environment variables properly. 

NOTE: You must first activate the program's environment, then execute the program. Errors may result if you try to execute a program at the pathname in that environment without first activating the environment.

NOTE: Each conda environment may have packages installed from the channel "r" OR the channel "mro", but no conda environment should contain packages from both channels. Doing so may result in errors. If this occurs, you may remove the packages that were installed incorrectly by using the command ``conda remove``, or simply create a new environment and install the correct packages there.

Install the Intel Math Kernel Library (MKL) with Microsoft R Open (MRO)
-----------------------------------------------------------------------

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
2. Find the directory where R language is located. Look in the current user's home directory, then in the Anaconda or Miniconda directory, then in the environments directory, and then in the directory for the current environment, for a directory called "R". For example, an Anaconda user on Windows 8 with the username jsmith and an environment named my_r_env might find ``C:\Users\jsmith\Anaconda\envs\my_r_env\R`` .
3. Run the installer, and enter the path when it says "Enter a path to MRO".

Starting the R language interpreter should now display the message showing that MKL is enabled.

If you wish to uninstall MKL on Windows and continue using R language, uninstall MKL with the Windows Control Panel.

MKL installation on Linux
-------------------------

1. Download and extract the proper MKL package to a temporary folder, which we will call $REVOMATH .
2. Determine where R is located. The path will have the form of ``/path/to/anaconda/envs/<r environment>`` , which we will call $PREFIX . Ensure that you have write permissions to $PREFIX.
3. Make backups of ``$PREFIX/lib/R/lib/libRblas.so`` and ``$PREFIX/lib/R/lib/libRlapack.so`` .
4. Copy all the .so files from ``$REVOMATH/mkl/libs/*.so`` to ``$PREFIX/lib/R/lib`` . (This may prompt you to overwrite libRblas.so and libRlapack.so.)
5. Edit ``$PREFIX/lib/R/etc/Rprofile.site`` and add the following two lines to the top::

     Sys.setenv("MKL_INTERFACE_LAYER"="GNU,LP64")
     Sys.setenv("MKL_THREADING_LAYER"="GNU")

6. Execute this: ``R CMD INSTALL $REVOMATH/RevoUtilsMath.tar.gz``

More help with conda and MRO
----------------------------

For community help using conda with MRO, please join the `conda <https://groups.google.com/a/continuum.io/forum/#!forum/conda>`_ email group.
 
