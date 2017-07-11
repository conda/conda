=================
Downloading conda
=================

.. contents::
   :local:
   :depth: 1


You have 3 conda download options:

* `Download Anaconda <http://continuum.io/downloads>`_---free. 

* `Download Miniconda <https://conda.io/miniconda.html>`_---free.

* Purchase an `Anaconda subscription 
  <https://www.continuum.io/anaconda-subscriptions>`_. 

You can download any of these 3 options with legacy Python 2.7 or 
current Python 3. 

You can also choose a version with a GUI or a command line 
installer. 

TIP: If you are unsure of which option to download, choose the 
most recent version of Anaconda3, which includes Python 3.5, the 
most recent version of Python. If you are on Windows or macOS, 
choose the version with the GUI installer. 


Anaconda or Miniconda?
=======================

Choose Anaconda if you:

* Are new to conda or Python.

* Like the convenience of having Python and over 150 scientific 
  packages automatically installed at once.

* Have the time and disk space---a few minutes and 3 GB.

* Do not want to individually install each of the packages you 
  want to use.

Choose Miniconda if you:

* Do not mind installing each of the packages you want to use 
  individually.

* Do not have time or disk space to install over 150 packages at 
  once.

* Want fast access to Python and the conda commands and you wish 
  to sort out the other programs later. 


Choosing a version of Anaconda or Miniconda
=============================================

* Whether you use Anaconda or Miniconda, select the most recent 
  version. 

* Select an older version from the `archive 
  <https://repo.continuum.io/archive/>`_ only if you are testing 
  or need an older version for a specific purpose should.

* To use conda on Windows XP, select Anaconda 2.3.0 and see 
  :doc:`../configuration/use-winxp-with-proxy`.


GUI versus command line installer
==================================

Both GUI and command line installers are available for Windows, 
macOS and Linux:

* If you do not wish to enter commands in a terminal window, 
  choose the GUI installer. 

* If GUIs slow you down, choose the command line version. 


Choosing a version of Python
================================

* The latest version of Python 2 is 2.7, which is included with 
  Anaconda and Miniconda. 
* The newest stable version of Python is 3.5, which is included 
  with Anaconda3 and Miniconda3. 
* You can easily set up additional versions of Python such as 3.4 
  by downloading any version and creating a new environment with 
  just a few clicks. See :doc:`../../user-guide/getting-started`.


Cryptographic hash verification
=================================

MD5 checksums are available for `Miniconda 
<http://repo.continuum.io/miniconda/>`_ and both MD5 and SHA-256 
checksums are available for `Anaconda 
<https://docs.continuum.io/anaconda/hashes/index>`_.

The format for the filenames is as follows:

* macOS: ``md5 filename`` or ``shasum -a 256 filename``.

  NOTE: ``filename`` is the actual path and name of the 
  downloaded package file.

* Linux: ``md5sum filename`` or ``sha256sum filename``

  NOTE: ``filename`` is the actual path and name of the 
  downloaded package file.

For Windows, use the free `online verifier tool 
<https://gallery.technet.microsoft.com/PowerShell-File-Checksum-e57dcd67>`_ 
on the Microsoft website. 

[@cio-docs: Line is over the length limit.]

For macOS and Linux:

#. Download the file and extract it.

#. Open a terminal window. 

#. Navigate to the file.

#. Run one of the following commands:

   * For MD5:

     .. code-block:: none

        Start-PsFCIV -Path C:\path\to\file.ext -HashAlgorithm MD5 -Online

   * For SHA256:

     .. code-block:: none

        Start-PsFCIV -Path C:\path\to\file.ext -HashAlgorithm SHA256 -Online

   [@cio-docs: Lines are over the length limit.]

   NOTE: In both commands, replace ``C:\path\to\file.ext`` with 
   the actual path, filename and extension. 
