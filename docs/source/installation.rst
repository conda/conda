============
Installation
============

Conda is part of the Anaconda Python distribution which can be downloaded from the `Continuum store
<https://store.continuum.io/cshop/anaconda/>`_.

Conda can also be installed as a stand-alone packages known as *Miniconda*. Installers for Linux, OSX and Windows are
available on `the Conda site <http://conda.pydata.org/miniconda.html#miniconda>`_.


Silent installation
-------------------

Silent installation of Miniconda can be used for deployment or testing or building services such as Travis CI and
Appveyor.

The lastest version of the Miniconda installer can be found `in the repo <http://repo.continuum.io/miniconda/>`_. In any
case, an out of date installation can be updated with a simple:

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

A complete example:

.. code-block:: bash

    wget http://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"


.. seealso::
   :doc:`travis`
