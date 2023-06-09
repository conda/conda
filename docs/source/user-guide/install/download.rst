=================
Downloading conda
=================

.. contents::
   :local:
   :depth: 1


You have 3 conda download options:

* `Download Anaconda <https://www.anaconda.com/download/>`_---free.

* `Download Miniconda <https://conda.io/miniconda.html>`_---free.

* Purchase `Anaconda Enterprise <https://www.anaconda.com/enterprise/>`_.

You can download any of these 3 options with legacy Python 2.7 or
current Python 3.

You can also choose a version with a GUI or a command line
installer.

.. tip::
   If you are unsure which option to download, choose the
   most recent version of Anaconda3.
   If you are on Windows or macOS, choose the version with the
   GUI installer.


Anaconda or Miniconda?
======================

Choose Anaconda if you:

* Are new to conda or Python.

* Like the convenience of having Python and over 1,500 scientific
  packages automatically installed at once.

* Have the time and disk space---a few minutes and 3 GB.

* Do not want to individually install each of the packages you
  want to use.

* Wish to use a set of packages curated and vetted for interoperability and usability.

Choose Miniconda if you:

* Do not mind installing each of the packages you want to use
  individually.

* Do not have time or disk space to install over 1,500 packages at
  once.

* Want fast access to Python and the conda commands and you wish
  to sort out the other programs later.


Choosing a version of Anaconda or Miniconda
===========================================

* Whether you use Anaconda or Miniconda, select the most recent
  version.

* Select an older version from the `archive
  <https://repo.continuum.io/archive/>`_ only if you are testing
  or need an older version for a specific purpose.

* To use conda on Windows XP, select Anaconda 2.3.0 and see
  :doc:`../configuration/use-winxp-with-proxy`.


GUI versus command line installer
=================================

Both GUI and command line installers are available for Windows,
macOS, and Linux:

* If you do not wish to enter commands in a terminal window,
  choose the GUI installer.

* If GUIs slow you down, choose the command line version.


Choosing a version of Python
============================

* The last version of Python 2 is 2.7, which is included with
  Anaconda and Miniconda.
* The newest stable version of Python is quickly included
  with Anaconda3 and Miniconda3.
* You can easily set up additional versions of Python such as 3.9
  by downloading any version and creating a new environment with
  just a few clicks. See :doc:`../getting-started`.

.. _hash-verification:

Cryptographic hash verification
===============================

SHA-256 checksums are available for
`Miniconda <https://conda.io/en/latest/miniconda_hashes.html>`_ and
`Anaconda <https://docs.anaconda.com/free/anaconda/reference/hashes/all/>`_.
We do not recommend using MD5 verification as SHA-256 is more secure.

Download the installer file and before installing verify it as follows:

* Windows:

  * If you have PowerShell V4 or later:

    Open a PowerShell console and verify the file as follows::

      Get-FileHash filename -Algorithm SHA256

  * If you don't have PowerShell V4 or later:

    Use the free `online verifier tool
    <https://gallery.technet.microsoft.com/PowerShell-File-Checksum-e57dcd67>`_
    on the Microsoft website.

    #. Download the file and extract it.

    #. Open a Command Prompt window.

    #. Navigate to the file.

    #. Run the following command::

        Start-PsFCIV -Path C:\path\to\file.ext -HashAlgorithm SHA256 -Online

* macOS: In iTerm or a terminal window enter ``shasum -a 256 filename``.

* Linux: In a terminal window enter ``sha256sum filename``.
