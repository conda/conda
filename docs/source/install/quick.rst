=============
Quick Install
=============

Conda is a cross-platform package manager and environment manager program that installs, 
runs, and updates packages and their dependencies, so you can easily set up and switch 
between environments on your local computer.  Conda is included in all versions 
of **Anaconda, Anaconda Server**, and **Miniconda**.

The fastest way to get and install conda is to download Miniconda, a bootstrap version 
of Anaconda that includes just conda, its dependencies, and Python. Anaconda has all 
that plus 150+ open source packages that install at the same time, and 250 packages 
that can be installed with the simple ``conda install`` command. 

You can be using Python in two minutes or less with this quick install guide - including 
install, update and uninstall. If you have any problems, please see the full installation instructions.

QUICK TIP: If you prefer to have the 150+ open source packages included with Anaconda, 
and have ten minutes for them to install, you can download Anaconda simply by replacing 
the below word  “Miniconda” with “Anaconda.” 


Miniconda quick install requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

32 or 64 bit computer, 32MB available, Linux, Macintosh or Windows.

Note: If you choose to install the full Anaconda package, it requires 300+ MB for 
the download plus another 300+ to install it. 


Linux Miniconda install 
------------------------

In your browser download the `Miniconda installer <http://conda.pydata.org/miniconda.html>`_ for Linux, then in your terminal 
window type the following and follow the prompts on the installer screens. If unsure 
about any setting, simply accept the defaults as they all can be changed later:

.. code::

   bash Miniconda-latest-Linux-x86_64.sh

NOTE: The install will not take effect until AFTER you close and re-open your terminal window.

**Linux Miniconda update**

In your terminal window, type the following:  ``conda update conda``

**Linux Miniconda uninstall**

Because Miniconda is contained in one directory, uninstalling Miniconda is simple -- in 
your terminal window, remove the entire miniconda install directory: ``rm -rf ~/miniconda``


Macintosh Miniconda install
-----------------------------

In your browser download the `Miniconda installer <http://conda.pydata.org/miniconda.html>`_ for Macintosh, then in your terminal 
window type the following and follow the prompts on the installer screens. If unsure about any setting, 
simply accept the defaults as they all can be changed later.

NOTE: The install will not take effect until AFTER you close and reopen your terminal window.

**Macintosh Miniconda update**

Open a terminal window, navigate to the anaconda directory, then type ``conda update conda``.

**Macintosh Miniconda uninstall**

Because Miniconda is contained in one directory, uninstalling Miniconda is simple -- in 
your terminal window, remove the entire miniconda install directory: ``rm -rf ~/miniconda``


Windows Miniconda install
---------------------------

In your browser download the `Miniconda installer <http://conda.pydata.org/miniconda.html>`_ for Windows, then double click 
the .exe file and follow the instructions on the screen.  If unsure about any setting, 
simply accept the defaults as they all can be changed later.

NOTE: When finished, a new terminal window will open. If not, click Start - Run - Command Prompt. 

**Windows Miniconda update**

Open a terminal window with Start - Run - Command Prompt, navigate to the anaconda folder, then type ``conda update conda``

**Windows Miniconda Uninstall**

Go to Control Panel, click “Add or remove Program,” select “Python 2.7 (Miniconda)” and click Remove Program. 
