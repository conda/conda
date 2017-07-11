=====================
Installing on Windows
=====================

#. Download the installer:

   * `Miniconda installer for 
     Windows <https://conda.io/miniconda.html>`_.

   * `Anaconda installer for 
     Windows <http://continuum.io/downloads>`_.

#. Double-click the ``.exe`` file.

#. Follow the instructions on the screen. 

   If you are unsure about any setting, accept the defaults. You 
   can change them later.

   When installation is finished, a new Command Prompt window 
   opens. If it does not open, in the **Start** menu, select 
   Command Prompt.

#. :doc:`Test your installation <test-installation>`. 


.. _install-win-silent:

Installing in silent mode
=========================

NOTE: The following instructions are for Miniconda. For Anaconda, 
substitute ``Anaconda`` for ``Miniconda`` in all of the commands.

To run the the Windows installer for Miniconda in 
:ref:`silent mode <silent-mode-glossary>`, use the ``/S`` 
argument. The following optional arguments are supported:

* ``/InstallationType=[JustMe|AllUsers]``---Default is``JustMe``.
* ``/AddToPath=[0|1]``---Default is ``1``'
* ``/RegisterPython=[0|1]``---Make this the system's default 
  Python. 
  ``0`` indicates ``JustMe``, which is the default. ``1`` 
  indicates ``AllUsers``.
* ``/S``---Install in silent mode.
* ``/D=<installation path>``---Destination installation path. 
  Must be the last argument. Do not wrap in quotation marks. 
  Required if you use ``/S``. 

All arguments are case-sensitive.

EXAMPLE: The following command installs Miniconda for the 
current user without registering Python as the system's default:

.. code-block:: bat

   start /wait "" Miniconda4-latest-Windows-x86_64.exe/InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\Miniconda3


Updating conda
==============

#. From the command line, navigate to the ``anaconda`` folder.

#. Run ``conda update conda``.


Uninstalling conda
==================

#. In the Windows Control Panel, click Add or Remove Program.

#. Select Python 2.7 (Miniconda). [@cio-docs: Is it always going 
   to be 2.7? What if they used the Python 3.6 installer?]

#. Click Remove Program.

[@cio-docs: Removing a program is different in Windows 10.]