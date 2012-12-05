.. _install_example:

Install
-------

``conda install`` places a package in an environment that may already exist,
in this case ``/envs/myenv``.

As before, conda will activate all necessary dependencies.

.. code-block:: bash

    $ conda install -p /envs/myenv --progress-bar=yes scipy

    Package plan for installation in environment ~/anaconda/envs/myenv:

    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        nose-1.1.2                 |           py27_0
        numpy-1.7.0b2              |           py27_0
        python-2.7.3               |                4
        readline-6.2               |                0
        scipy-0.11.0               |       np17py27_1
        zlib-1.2.7                 |                0


    Proceed (y/n)? y

    Activating packages...

    [      COMPLETE      ] |###########################################| 100%

In this next example, using the name option (``-n``) will install a package or packages in an existing environment located in
``~/anaconda/envs``.

.. code-block:: bash

    $ conda install -n foo pandas


    Package plan for installation in environment ~/anaconda/envs/foo:

    The following packages will be downloaded:

        pandas-0.9.1-np17py27_0.tar.bz2 [http://repo.continuum.io/pkgs/osx-64/]


    The following packages will be activated:

        package                    |  build          
        -------------------------  |  ---------------
        pandas-0.9.1               |       np17py27_0


    Proceed (y/n)? y

    Fetching packages...

    pandas-0.9.1-np17py27_0.tar.bz2 100% |################################| Time: 0:00:01   1.66 MB/s

    Activating packages...

    [      COMPLETE      ] |##############################################| 100%
