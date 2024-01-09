=====================
Installing on Windows
=====================

#. Download the installer:

   * `Miniconda installer for
     Windows <https://docs.conda.io/projects/miniconda/>`_

   * `Anaconda Distribution installer for
     Windows <https://www.anaconda.com/download/>`_

   * `Miniforge installer for Windows <https://github.com/conda-forge/miniforge>`_

#. :ref:`Verify your installer hashes <hash-verification>`.

#. Double-click the ``.exe`` file.

#. Follow the instructions on the screen.

   If you are unsure about any setting, accept the defaults. You
   can change them later.

   When installation is finished, from the **Start** menu, open either Command Prompt (cmd.exe) or
   PowerShell

#. Test your installation. In your terminal window, run the command ``conda list``. A list of
   installed packages appears if it has been installed correctly.


.. _install-win-silent:

Installing in silent mode
=========================

.. note::
   The following instructions are for Miniconda but should also work
   for the Anaconda Distribution or Miniforge installers.

.. note::
   As of ``Anaconda Distribution 2022.05`` and ``Miniconda 4.12.0``, the option to add Anaconda
   to the PATH environment variable during an **All Users** installation has been disabled. This
   was done to address `a security exploit <https://nvd.nist.gov/vuln/detail/CVE-2022-26526>`_.
   You can still add Anaconda to the PATH environment variable during a **Just Me** installation.

To run the the Windows installer for Miniconda in
:ref:`silent mode <silent-mode-glossary>`, use the ``/S``
argument. The following optional arguments are supported:

* ``/InstallationType=[JustMe|AllUsers]``---Default is ``JustMe``.
* ``/AddToPath=[0|1]``---Default is ``0``
* ``/RegisterPython=[0|1]``---Make this the system's default
  Python.
  ``0`` indicates Python won't be registered as the system's default. ``1``
  indicates Python will be registered as the system's default.
* ``/S``---Install in silent mode.
* ``/D=<installation path>``---Destination installation path.
  Must be the last argument. Do not wrap in quotation marks.
  Required if you use ``/S``.

All arguments are case-sensitive.

**Example:** The following command installs Miniconda for the
current user without registering Python as the system's default:

.. code-block:: bat

   start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\Miniconda3


Updating conda
==============

#. Open Command Prompt or PowerShell from the start menu.

#. Run ``conda update conda``.


Uninstalling conda
==================

#. In the Windows Control Panel, click Add or Remove Program.

#. Select Python X.X (Miniconda), where X.X is your version of Python.

#. Click Remove Program.

.. note::
   Removing a program is different in Windows 10.
