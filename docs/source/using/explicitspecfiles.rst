Explicit specification files
============================

Conda may be used to create explicit specification files, which can then be used to build an identical conda environment on the same operating system platform, either on the same machine or a different machine.

The command ``conda list -e`` produces a spec list such as the following:

.. code::

    # This file may be used to create an environment using:
    # $ conda create --name <env> --file <this file>
    # platform: osx-64
    astropy=1.0.4=np19py27_0
    ncurses=5.9=1
    numpy=1.9.2=py27_0
    openssl=1.0.1k=1
    pandas=0.16.2=np19py27_0
    pip=7.1.2=py27_0
    python=2.7.10=0
    python-dateutil=2.4.2=py27_0
    pytz=2015.4=py27_0
    readline=6.2.5=1
    setuptools=18.1=py27_0
    six=1.9.0=py27_0
    sqlite=3.8.4.1=1
    tk=8.5.18=0
    wheel=0.24.0=py27_0
    zlib=1.2.8=1

With the command ``conda list -e > spec-file.txt`` you can create a file containing this spec list in the current working directory. You may use the filename ``spec-file.txt`` or any other filename.

As the comment at the top of the file explains, with the command ``conda create --name MyEnvironment --file spec-file.txt`` you can use the spec file to create an identical environment on the same machine or another machine. Replace ``spec-file.txt`` with whatever file name you chose when you created the file. You may use the environment name ``MyEnvironment`` or substitute any other environment name to give your newly created environment.

NOTE: Explicit spec files like this are not cross platform, and have a comment at the top such as ``# platform: osx-64`` showing the one platform where they were created, which is the one platform where they can be used to create a new environment.
