================
Installing conda
================

To install conda, you must first pick the right installer for you.
The following are the most popular installers currently available:

.. glossary::

    `Miniconda <https://docs.conda.io/projects/miniconda>`_
        Miniconda is a minimal installer provided by Anaconda. Use this installer
        if you want to install most packages yourself.

    `Anaconda Distribution <https://www.anaconda.com/download>`_
        Anaconda Distribution is a full featured installer that comes with a suite
        of packages for data science as well as Anaconda Navigator, a GUI application
        for working with conda environments.

    `Miniforge <https://github.com/conda-forge/miniforge>`_
        Miniforge is an installer maintained by the conda-forge community that comes
        preconfigured for use with the conda-forge channel. To learn more about conda-forge,
        visit `their website <https://conda-forge.org>`_.

.. admonition:: Tip

    If you are just starting out, we recommend installing conda via the
    `Miniconda installer <https://docs.conda.io/projects/miniconda>`_.


.. _system-reqs:

System requirements
===================

* A supported operating systems: Windows, macOS, or Linux

* For Miniconda or Miniforge: 400 MB disk space

* For Anaconda: Minimum 3 GB disk space to download and install

* For Windows: Windows 8.1 or newer for Python 3.9, or Windows Vista or newer for Python 3.8

.. admonition:: Tip

    You do not need administrative or root permissions to install conda if you select a
    user-writable install location (e.g. ``/Users/my-username/conda`` or ``C:\Users\my-username\conda``).

Regular installation
====================

Follow the instructions for your operating system:

* :doc:`Windows <windows>`
* :doc:`macOS <macos>`
* :doc:`Linux <linux>`


Installing in silent mode
=========================

You can use :ref:`silent installation <silent-mode-glossary>` of
Miniconda, Anaconda or Miniforge for deployment or testing or building
services, such as GitHub Actions.

Follow the silent-mode instructions for your operating system:

* :ref:`Windows <install-win-silent>`
* :ref:`macOS <install-macos-silent>`
* :ref:`Linux <install-linux-silent>`


.. _hash-verification:

Cryptographic hash verification
===============================

SHA-256 checksums are available for
`Miniconda <https://conda.io/en/latest/miniconda_hashes.html>`_ and
`Anaconda Distribution <https://docs.anaconda.com/free/anaconda/reference/hashes/all/>`_.
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

.. toctree::
   :maxdepth: 1
   :hidden:

   windows
   macos
   linux
   rpm-debian
