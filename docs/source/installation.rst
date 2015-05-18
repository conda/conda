============
Installation
============

Conda is a cross-platform package manager and environment manager program that installs, 
runs, and updates packages and their dependencies, so you can easily set up and switch 
between environments on your local computer.  Conda is included in all versions of 
Anaconda, Anaconda Server, and Miniconda. 

The easiest way to get and install conda is to download Anaconda, the full version 
of Anaconda that includes Python and 150+ open source packages that install at the 
same time. It takes about ten minutes for all the packages to install. 

These installation instructions are for a full install of Anaconda for Windows, Macintosh,
or Linux. 

NOTE: If you prefer to quickly install the minimal Miniconda package, simply download 
it from the `Miniconda downloads page <http://conda.pydata.org/miniconda.html#miniconda>`_
and follow the rest of the instructions below.

Windows Anaconda installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser, download the Anaconda installer for Windows from the `Anaconda downloads 
page <https://store.continuum.io/cshop/anaconda/>`_ then double click the .exe file and follow 
the instructions on the screen.  If unsure about any setting, simply accept the defaults as 
they all can be changed later.

NOTE: When finished, a new terminal window will open. If not, close the terminal
window, then click Start - Run - Command Prompt. The install will not take effect 
until AFTER you close and re-open your terminal window.

Macintosh Anaconda installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser, download the Anaconda installer for Macintosh from the `Anaconda downloads 
page <https://store.continuum.io/cshop/anaconda/>`_  then double click 
the .pkg file and follow the instructions on the screen. If unsure about any setting, 
simply accept the defaults as they all can be changed later.

NOTE: The install will not take effect until AFTER you close and reopen your terminal 
window.

Linux Anaconda installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser, download the Anaconda installer for Linux from the `Anaconda downloads 
page <https://store.continuum.io/cshop/anaconda/>`_ then in your terminal 
window type the following and follow the prompts on the installer screens. If unsure 
about any setting, simply accept the defaults as they all can be changed later:

.. code-block:: console

    bash Anaconda-latest-Linux-x86_64.sh

NOTE: The install will not take effect until AFTER you close and reopen your terminal 
window.

============================
Optional silent installation
============================


Silent mode turns off screen prompts and accepts the system defaults. Silent installation of Miniconda may be used for deployment or testing or building services such as Travis CI and
Appveyor. 


Windows silent installation
---------------------------

The Windows installer of Miniconda can be run in silent mode using the ``/S`` argument. The following optional arguments
are supported:

- ``/InstallationType=[JustMe|AllUsers]``, default: ``JustMe``
- ``/AddToPath=[0|1]``, default: ``1``
- ``/RegisterPython=[0|1]``, make this the system's default Python, default: ``0`` (Just me), ``1`` (All users)
- ``/S``
- ``/D=<installation path>``

All arguments are case-sensitive. The installation path must be the last argument and should **NOT** be wrapped in
quotation marks.

The following command installs Miniconda for all users without registering Python as the system's default:

.. code-block:: bat

    Miniconda-3.7.3-Windows-x86_64.exe /InstallationType=AllUsers /RegisterPython=0 \
        /S /D=C:\Program Files\Miniconda3


Linux and OS X silent installation
----------------------------------

Silent installation of Miniconda for Linux and OS X is a simple as specifying the ``-b`` and ``-p`` arguments of the
bash installer. The following arguments are supported:

- ``-b``, batch mode
- ``-p``, installation prefix/path
- ``-f``, force installation even if prefix ``-p`` already exists

NOTE: Batch mode assumes that you agree to the license agreement, and it does not
edit the .bashrc or .bash_profile files.

A complete example:

.. code-block:: bash

    wget http://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"


.. seealso::
   :doc:`travis`
