============
Installation
============

Conda is a cross-platform package manager and environment manager program that installs, runs, and updates 
packages and their dependencies, so you can easily set up and switch between environments on your local 
computer.  Conda is included in all versions of **Anaconda, Anaconda Server**, and **Miniconda**.

If you are in a hurry, try our two-minute `Miniconda quick install <https://conda.pydata.org/quick-install.html/>`_. 
Miniconda includes only conda, conda-build, and their dependencies so you can install cleanly and quickly.

These instructions are for a full install of Anaconda, which includes conda, conda-build, and 150+ 
open source packages. 

TIP: For installation instructions using our graphical installers for Mac or PC, please see 
the `Anaconda Install <http://docs.continuum.io/anaconda/install.html/>`_ page. 


Anaconda requirements
------------------------------------

32 or 64 bit computer, 32MB available, Linux, Macintosh or Windows.

300 MB to download Anaconda plus another 300 to install it. 

Install instructions
--------------------

Linux Anaconda install 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser download the Anaconda installer for Linux, then in your terminal window type the following 
and follow the prompts on the installer screens. If unsure about any setting, simply accept the defaults as 
they all can be changed later:

.. code::

   bash Anaconda-latest-Linux-x86_64.sh

NOTE: The install will not take effect until AFTER you close and re-open your terminal window.

**Linux Anaconda update**

In your terminal window, type the following:  ``conda update conda``

**Linux Anaconda uninstall**

Because Anaconda is contained in one directory, uninstalling Anaconda is simple -- in your terminal 
window, remove the entire anaconda install directory: ``rm -rf ~/anaconda``


Macintosh Anaconda install
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser download the Anaconda installer for Macintosh, then double click the .pkg file and follow the instructions on the screen. If unsure about any setting, simply accept the defaults as they all can be changed later.

NOTE: The install will not take effect until AFTER you close and reopen your terminal window.

**Macintosh Anaconda update**

Open a terminal window, navigate to the anaconda directory, then type ``conda update conda``

**Macintosh Anaconda uninstall**

Because Anaconda is contained in one directory, uninstalling Anaconda is simple -- in your terminal window, remove the entire miniconda install directory: ``rm -rf ~/miniconda``


Windows Anaconda install
~~~~~~~~~~~~~~~~~~~~~~~~~

In your browser download the Anaconda installer for Windows, then  double click the .exe file and follow the instructions on the screen.  If unsure about any setting, simply accept the defaults as they all can be changed later.

NOTE: When finished, a new terminal window will open. If not, click Start - Run - Command Prompt. 

**Windows Anaconda update**

Open a terminal window with Start - Run - Command Prompt, navigate to the anaconda folder, then type ``conda update conda``

**Windows Anaconda Uninstall**

Go to Control Panel, click “Add or remove Program,” select “Python 2.7 (Miniconda)” and click Remove Program. 




Silent installation
-------------------

Silent installation of Miniconda or Anaconda can be used for deployment or testing or building services such as Travis CI and
Appveyor. In silent mode, screen prompts are not shown on screen and default settings are automatically accepted.

NOTE: These instructions are written for Miniconda, but you can substitute "Anaconda" if you are using that version.

We recommend starting with the latest version of Miniconda or Anaconda. Check to be sure your version
is up to date with a simple:

.. code-block:: console

    conda update conda


Windows
~~~~~~~

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


Linux and OS X
~~~~~~~~~~~~~~

Silent installation of Miniconda for Linux and OS X is a simple as specifying the ``-b`` and ``-p`` arguments of the
bash installer. The following arguments are supported:

- ``-b``, batch mode
- ``-p``, installation prefix/path
- ``-f``, force installation even if prefix ``-p`` already exists

Batch mode assumes that you agree to the license agreement, and it does not
edit the .bashrc or .bash_profile files.

A complete example:

.. code-block:: bash

    wget http://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"


.. seealso::
   :doc:`travis`

