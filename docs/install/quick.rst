Quick install
=============

.. contents::

Conda is a cross-platform package manager and environment manager program that installs, 
runs, and updates packages and their dependencies, so you can easily set up and switch 
between environments on your local computer.  Conda is included in all versions 
of **Anaconda, Anaconda Server**, and **Miniconda**.

The fastest way to get and install conda is to `download Miniconda <http://conda.pydata.org/miniconda.html>`_, 
a mini version of Anaconda that includes just conda, its dependencies, and Python. 
Anaconda has all that plus over 720 open source packages that install with Anaconda or 
can be installed with the simple ``conda install`` command. 

You can be using Python in two minutes or less with this quick install guide - including 
install, update and uninstall. If you have any problems, please see the full installation instructions.

TIP: If you prefer to have the over 720 open source packages included with Anaconda, 
and have a few minutes and the disk space required, you can download Anaconda simply by 
replacing the word “Miniconda” with “Anaconda” in the examples below.

Miniconda quick install requirements
------------------------------------

32- or 64-bit computer, 400 MB available, Linux, OS X or Windows.

NOTE: If you choose to install the full Anaconda package, it requires 3 GB of available disk space. 


Windows Miniconda install
-------------------------

In your browser download the `Miniconda installer for Windows <http://conda.pydata.org/miniconda.html>`_, then double click 
the .exe file and follow the instructions on the screen.  If unsure about any setting, 
simply accept the defaults as they all can be changed later.

NOTE: When finished, a new terminal window will open. If not, click Start - Run - Command Prompt. 

To test your installation, enter the command ``conda list.`` If installed 
correctly, you will see a list of packages that were installed. 

Next, go to our :doc:`30-minute conda test drive </test-drive>`.

**Windows Miniconda update**

Open a terminal window with Start - Run - Command Prompt, navigate to the anaconda folder, then type ``conda update conda``

**Windows Miniconda Uninstall**

Go to Control Panel, click “Add or remove Program,” select “Python 2.7 (Miniconda)” and click Remove Program. 


OS X Miniconda install
----------------------

In your browser download the `Miniconda installer for OS X <http://conda.pydata.org/miniconda.html>`_, then in your terminal 
window type the following and follow the prompts on the installer screens. If unsure about any setting, 
simply accept the defaults as they all can be changed later.

.. code::

   bash Miniconda-latest-MacOSX-x86_64.sh

Now close and re-open your terminal window for the changes to take effect.

To test your installation, enter the command ``conda list.`` If installed 
correctly, you will see a list of packages that were installed. 

Next, go to our :doc:`30-minute conda test drive </test-drive>`.

**OS X Miniconda update**

Open a terminal window, navigate to the anaconda directory, then type ``conda update conda``.

**OS X Miniconda uninstall**

To uninstall Miniconda open a terminal window and remove the entire miniconda install 
directory: ``rm -rf ~/miniconda``. You may also edit ``~/.bash_profile`` and remove 
the miniconda directory from your ``PATH`` environment variable, and remove the 
hidden .condarc file and .conda and .continuum directories which may have been created 
in the home directory with ``rm -rf ~/.condarc ~/.conda ~/.continuum``.


Linux Miniconda install
-----------------------

In your browser download the `Miniconda installer for Linux <http://conda.pydata.org/miniconda.html>`_, then in your terminal 
window type the following and follow the prompts on the installer screens. If unsure 
about any setting, simply accept the defaults as they all can be changed later:

.. code::

   bash Miniconda-latest-Linux-x86_64.sh

Now close and re-open your terminal window for the changes to take effect.

To test your installation, enter the command ``conda list.`` If installed 
correctly, you will see a list of packages that were installed. 

Next, go to our :doc:`30-minute conda test drive </test-drive>`.

**Linux Miniconda update**

In your terminal window, type the following:  ``conda update conda``

**Linux Miniconda uninstall**

To uninstall Miniconda open a terminal window and remove the entire miniconda install 
directory: ``rm -rf ~/miniconda``. You may also edit ``~/.bash_profile`` and remove 
the miniconda directory from your ``PATH`` environment variable, and remove the 
hidden .condarc file and .conda and .continuum directories which may have been created 
in the home directory with ``rm -rf ~/.condarc ~/.conda ~/.continuum``.
