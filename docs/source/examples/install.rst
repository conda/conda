.. _install_example:

Install
-------

``conda install`` places a package in an environment that may already exist,
in this case ``/envs/myenv``.

As before, ``conda`` will link all necessary dependencies.

.. code-block:: bash

    $ conda install -p ~/anaconda/envs/myenv scipy

    Package plan for installation in environment /Users/test/anaconda/envs/myenv:

    The following packages will be downloaded:

        numpy-1.7.1-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]
        scipy-0.12.0-np17py27_0.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]


    The following packages will be linked:

        package                    |  build          
        -------------------------  |  ---------------
        mkl-rt-11.0                |               p0
        nose-1.2.1                 |           py27_0
        numpy-1.7.1                |           py27_0
        python-2.7.4               |                0
        readline-6.2               |                1
        scipy-0.12.0               |       np17py27_0
        tk-8.5.13                  |                1
        zlib-1.2.7                 |                1


    Proceed (y/n)? y

    Fetching packages...

    numpy-1.7.1-py27_0.tar.bz2 100% |####################| Time: 0:00:02   1.14 MB/s
    scipy-0.12.0-np17py27_0.tar.bz2 100% |###############| Time: 0:00:11 942.94 kB/s

    Linking packages...

    [      COMPLETE      ] |##################################################| 100%


In this next example, using the name option (``-n``) will install a package or packages in an existing environment located in
``~/anaconda/envs``.

As with :ref:`conda create <create_example>`, we can use the ``--yes`` and ``--quiet`` options to automatically answer yes to the confirmation question and 
hide the progress bar, respectively.

.. code-block:: bash

    $ conda install --yes --quiet -n myenv pandas

    Package plan for installation in environment /Users/maggie/anaconda/envs/myenv:

    The following packages will be downloaded:

        pandas-0.11.0-np17py27_1.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]
        pytz-2013b-py27_0.tar.bz2 [http://repo.continuum.io/pkgs/free/osx-64/]


    The following packages will be linked:

        package                    |  build          
        -------------------------  |  ---------------
        dateutil-2.1               |           py27_0
        pandas-0.11.0              |       np17py27_1
        pytz-2013b                 |           py27_0
        six-1.2.0                  |           py27_0
