==============
Download conda
==============

Conda can be downloaded with an array of options. This page is to help you decide among the various options.  
To download conda, you will download Anaconda or Miniconda (both are free), or purchase Anaconda Server. All 
can be downloaded with legacy Python 2.7 or current Python 3.5. You 
can choose a version with a GUI or a command line installer. 

TIP: If you are unsure, we recommend the most recent version of Anaconda3 - that automatically includes 
Python 3.5, the most recent version of Python. If you are on Windows or OS X, we recommend you also choose 
the version with GUI installer. 

Should I download Anaconda or Miniconda? 
----------------------------------------

**Choose Anaconda if you:** 

* Are new to conda or Python
* Like the convenience of having Python and over 150 scientific packages automatically installed at once
* Have the time and disk space (a few minutes and 3 GB), and/or
* Don’t want to install each of the packages you want to use individually. 

Anaconda download: http://continuum.io/downloads

**Choose Miniconda if you:**

* Do not mind installing each of the packages you want to use individually
* Do not have time or disk space to install over 150 packages at once, and/or
* Just want fast access to Python and the conda commands, and wish to sort out the other programs later. 

Miniconda download: http://conda.pydata.org/miniconda.html

Which version of Anaconda or Miniconda should I choose?
-------------------------------------------------------

* Whether you use Anaconda or Miniconda, select the most recent version. 
* Only if you are testing or need an older version for a specific purpose should you select an older version from the `archive <https://repo.continuum.io/archive/>`_. 

Should I choose GUI installer or command line installer?
--------------------------------------------------------

Whether you are on Linux, OS X or Windows, there is an installer to make it easy for you. 

* If you do not wish to enter commands in a terminal window, choose the GUI installer. 
* If GUIs slow you down, choose the command line version. 

What version of Python should I choose?
---------------------------------------

* The latest version of Python 2 is 2.7, and that is included with Anaconda and Miniconda. 
* The newest stable version of Python is 3.5, and that is included with Anaconda3 and Miniconda3. 
* You can easily set up additional versions of Python such as 3.4 by downloading any version and creating a new environment with just a few clicks. (See our :doc:`test-drive`.)

What about cryptographic hash verification?
-------------------------------------------

MD5 checksums are available for both `Miniconda <http://repo.continuum.io/miniconda/>`_ and `Anaconda <http://continuum.io/md5>`_.

Download the package and before installing verify it as follows:

**Linux:** ``md5sum filename``

NOTE: Replace "filename" with the actual path and name of the downloaded package file.

**OS X:** ``md5 filename``

NOTE: Replace "filename" with the actual path and name of the downloaded package file.

**Windows:**

Use the free online verifier tool on the Microsoft website: https://support.microsoft.com/en-us/kb/841290 

Download and extract the file, then open a Command Prompt window. 

Navigate to the file, then enter the command ``fciv.exe C:\path\to\file.ext``

NOTE: Replace "C:\\path\\to\\file.ext" with the actual path, filename and extension. 
